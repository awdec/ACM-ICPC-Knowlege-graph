# src/deepseek/hybrid_strategy.py
import time
import logging
import re
from typing import Dict, Any, Optional, Tuple
from cachetools import TTLCache
from enum import Enum
from dataclasses import dataclass

# 导入内部模块
from deepseek.deepseek_cypher import DeepSeekCypherGenerator, QueryResult, GenerationError, ParseError
from deepseek.cypher_validator import CypherValidator, ValidationResult
from nl_to_cypher import parse_intent, get_cypher_and_params
from config.config_manager import ConfigManager

# 设置日志
logger = logging.getLogger(__name__)


class QueryMode(Enum):
    """查询模式"""
    RULE = "rule"
    LLM = "llm"  
    HYBRID = "hybrid"


@dataclass
class ComplexityMetrics:
    """复杂度评估指标"""
    entity_count: int = 0
    relation_depth: int = 0
    condition_count: int = 0
    has_aggregation: bool = False
    has_sorting: bool = False
    pattern_match_confidence: float = 0.0
    
    @property
    def complexity_score(self) -> int:
        """计算复杂度评分"""
        score = 0
        
        # 实体数量
        if self.entity_count > 2:
            score += (self.entity_count - 2) * 2
        
        # 关系深度
        score += max(0, self.relation_depth - 1) * 3
        
        # 条件数量
        score += max(0, self.condition_count - 1) * 2
        
        # 聚合
        if self.has_aggregation:
            score += 3
        
        # 排序
        if self.has_sorting:
            score += 1
        
        # 模式匹配置信度低
        if self.pattern_match_confidence < 0.5:
            score += 5
        
        return score


@dataclass
class MetricsData:
    """性能指标数据"""
    timestamp: float
    question: str
    strategy_used: str
    success: bool
    response_time: float
    fallback_triggered: bool
    validation_passed: bool
    complexity_score: int = 0


class HybridStrategy:
    """混合策略协调器"""
    
    def __init__(self, 
                 llm_generator: Optional[DeepSeekCypherGenerator] = None,
                 validator: Optional[CypherValidator] = None):
        """初始化混合策略协调器
        
        Args:
            llm_generator: LLM 生成器
            validator: Cypher 验证器
        """
        self.config = ConfigManager()
        self.llm_generator = llm_generator or DeepSeekCypherGenerator()
        self.validator = validator or CypherValidator()
        
        # 初始化缓存
        if self.config.get_strategy_config().enable_cache:
            cache_ttl = self.config.get_strategy_config().cache_ttl
            self.cache = TTLCache(maxsize=1000, ttl=cache_ttl)
        else:
            self.cache = None
        
        # 性能指标存储
        self.metrics_data = []
        
        logger.info(f"Initialized HybridStrategy with mode: {self.config.get_query_mode()}")
    
    def generate_query(self, question: str, force_mode: Optional[str] = None) -> QueryResult:
        """生成查询
        
        Args:
            question: 用户问题
            force_mode: 强制使用的模式 (rule/llm/hybrid)
            
        Returns:
            QueryResult 对象
            
        Raises:
            GenerationError: 生成失败
        """
        if not question or not question.strip():
            raise GenerationError("Question cannot be empty")
        
        question = question.strip()
        start_time = time.time()
        
        # 检查缓存
        cache_key = self._get_cache_key(question, force_mode)
        if self.cache and cache_key in self.cache:
            logger.debug(f"Cache hit for question: {question}")
            cached_result = self.cache[cache_key]
            cached_result.metadata = cached_result.metadata or {}
            cached_result.metadata["from_cache"] = True
            return cached_result
        
        # 确定运行模式
        mode = force_mode or self.config.get_query_mode()
        
        try:
            # 根据模式生成查询
            if mode == "rule":
                result = self._generate_rule_only(question)
            elif mode == "llm":
                result = self._generate_llm_only(question)
            elif mode == "hybrid":
                result = self._generate_hybrid(question)
            else:
                raise GenerationError(f"Unknown query mode: {mode}")
            
            # 验证查询
            validation_result = self.validator.validate(result.cypher, result.parameters)
            if not validation_result.is_valid:
                logger.warning(f"Validation failed: {validation_result.error_message}")
                
                # 如果启用了降级，尝试降级
                if self._should_fallback(mode, result):
                    logger.info("Attempting fallback due to validation failure")
                    fallback_result = self._attempt_fallback(question, mode, result)
                    if fallback_result:
                        result = fallback_result
                        validation_result = self.validator.validate(result.cypher, result.parameters)
            
            # 设置验证结果
            result.metadata = result.metadata or {}
            result.metadata["validation"] = validation_result
            
            # 记录指标
            elapsed_time = (time.time() - start_time) * 1000
            self._record_metrics(MetricsData(
                timestamp=time.time(),
                question=question,
                strategy_used=result.source,
                success=validation_result.is_valid,
                response_time=elapsed_time,
                fallback_triggered="fallback" in result.metadata.get("flags", []),
                validation_passed=validation_result.is_valid,
                complexity_score=validation_result.complexity_score
            ))
            
            # 存储到缓存
            if self.cache and validation_result.is_valid:
                self.cache[cache_key] = result
            
            return result
            
        except Exception as e:
            # 记录失败指标
            elapsed_time = (time.time() - start_time) * 1000
            self._record_metrics(MetricsData(
                timestamp=time.time(),
                question=question,
                strategy_used=mode,
                success=False,
                response_time=elapsed_time,
                fallback_triggered=False,
                validation_passed=False
            ))
            
            raise GenerationError(f"Query generation failed: {str(e)}")
    
    def _generate_rule_only(self, question: str) -> QueryResult:
        """仅使用规则模式生成"""
        logger.debug("Using rule-only mode")
        
        try:
            parsed = parse_intent(question)
            intent = parsed['intent']
            slots = parsed['slots']
            
            if intent == "unknown":
                raise GenerationError("Unknown intent, cannot generate query using rules")
            
            cypher, params = get_cypher_and_params(parsed)
            if not cypher:
                raise GenerationError("Failed to generate Cypher using rules")
            
            return QueryResult(
                cypher=cypher,
                parameters=params,
                intent=intent,
                confidence=0.9,  # 规则匹配通常有较高置信度
                source="rule"
            )
            
        except Exception as e:
            logger.error(f"Rule generation failed: {str(e)}")
            raise GenerationError(f"Rule generation failed: {str(e)}")
    
    def _generate_llm_only(self, question: str) -> QueryResult:
        """仅使用 LLM 模式生成"""
        logger.debug("Using LLM-only mode")
        
        if not self.config.is_llm_available():
            raise GenerationError("LLM is not available (API key not configured)")
        
        try:
            result = self.llm_generator.parse_question_to_cypher(question)
            return result
            
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            raise GenerationError(f"LLM generation failed: {str(e)}")
    
    def _generate_hybrid(self, question: str) -> QueryResult:
        """使用混合模式生成"""
        logger.debug("Using hybrid mode")
        
        # 分析问题复杂度
        complexity_metrics = self._analyze_question_complexity(question)
        
        # 决定使用哪种策略
        strategy = self._select_strategy(complexity_metrics)
        
        logger.debug(f"Selected strategy: {strategy}, complexity score: {complexity_metrics.complexity_score}")
        
        try:
            if strategy == "rule":
                result = self._generate_rule_only(question)
                
                # 如果规则生成失败或为 unknown，尝试 LLM
                if (not result.cypher or result.intent == "unknown") and self.config.is_llm_available():
                    logger.info("Rule failed, fallback to LLM")
                    result = self._generate_llm_only(question)
                    result.metadata = result.metadata or {}
                    result.metadata["flags"] = result.metadata.get("flags", []) + ["fallback"]
                
            else:  # strategy == "llm"
                if not self.config.is_llm_available():
                    logger.info("LLM not available, fallback to rule")
                    result = self._generate_rule_only(question)
                    result.metadata = result.metadata or {}
                    result.metadata["flags"] = result.metadata.get("flags", []) + ["fallback"]
                else:
                    result = self._generate_llm_only(question)
            
            return result
            
        except GenerationError as e:
            # 尝试降级
            fallback_result = self._attempt_fallback(question, strategy, None)
            if fallback_result:
                return fallback_result
            raise e
    
    def _analyze_question_complexity(self, question: str) -> ComplexityMetrics:
        """分析问题复杂度"""
        metrics = ComplexityMetrics()
        
        question_lower = question.lower()
        
        # 1. 实体数量估算
        # 寻找可能的实体（引号包围的文本、专有名词等）
        entities = re.findall(r'["\'](.*?)["\']', question)
        entities.extend(re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', question))
        metrics.entity_count = len(set(entities)) if entities else 1
        
        # 2. 关系深度估算
        # 通过"的"、"和"、"或"等词估算
        relation_indicators = ['的', '和', '或者', '以及', '相关', '关于']
        depth = 1
        for indicator in relation_indicators:
            depth += question_lower.count(indicator)
        metrics.relation_depth = min(depth, 5)  # 限制最大深度
        
        # 3. 条件数量
        condition_words = ['哪些', '什么', '多少', '如何', '为什么', '是否']
        conditions = sum(1 for word in condition_words if word in question_lower)
        metrics.condition_count = max(conditions, 1)
        
        # 4. 聚合需求
        aggregation_words = ['总共', '一共', '数量', '个数', '统计', '平均', '最多', '最少']
        metrics.has_aggregation = any(word in question_lower for word in aggregation_words)
        
        # 5. 排序需求
        sorting_words = ['排序', '排列', '最', '前', '后', '顺序']
        metrics.has_sorting = any(word in question_lower for word in sorting_words)
        
        # 6. 规则匹配置信度
        parsed = parse_intent(question)
        if parsed['intent'] != "unknown":
            metrics.pattern_match_confidence = 0.9
        else:
            metrics.pattern_match_confidence = 0.1
        
        return metrics
    
    def _select_strategy(self, metrics: ComplexityMetrics) -> str:
        """选择生成策略"""
        complexity_threshold = self.config.get_strategy_config().complexity_threshold
        
        # 如果规则匹配置信度高且复杂度不高，优先使用规则
        if (metrics.pattern_match_confidence > 0.8 and 
            metrics.complexity_score <= complexity_threshold):
            return "rule"
        
        # 如果复杂度很高或规则匹配失败，优先使用 LLM
        if (metrics.complexity_score > complexity_threshold or 
            metrics.pattern_match_confidence < 0.5):
            return "llm"
        
        # 默认先尝试规则
        return "rule"
    
    def _should_fallback(self, current_mode: str, result: QueryResult) -> bool:
        """判断是否应该降级"""
        config = self.config.get_strategy_config()
        
        if current_mode == "llm" and config.llm_fallback_enabled:
            return True
        elif current_mode == "rule" and config.rule_fallback_enabled:
            return True
        
        return False
    
    def _attempt_fallback(self, question: str, original_mode: str, original_result: Optional[QueryResult]) -> Optional[QueryResult]:
        """尝试降级"""
        config = self.config.get_strategy_config()
        
        try:
            if original_mode == "llm" and config.llm_fallback_enabled:
                logger.info("LLM failed, fallback to rule mode")
                result = self._generate_rule_only(question)
                result.metadata = result.metadata or {}
                result.metadata["flags"] = result.metadata.get("flags", []) + ["fallback"]
                return result
                
            elif original_mode == "rule" and config.rule_fallback_enabled and self.config.is_llm_available():
                logger.info("Rule failed, fallback to LLM mode")
                result = self._generate_llm_only(question)
                result.metadata = result.metadata or {}
                result.metadata["flags"] = result.metadata.get("flags", []) + ["fallback"]
                return result
                
        except Exception as e:
            logger.error(f"Fallback failed: {str(e)}")
        
        return None
    
    def _get_cache_key(self, question: str, mode: Optional[str]) -> str:
        """生成缓存键"""
        actual_mode = mode or self.config.get_query_mode()
        return f"{actual_mode}:{question.lower().strip()}"
    
    def _record_metrics(self, metrics: MetricsData) -> None:
        """记录性能指标"""
        self.metrics_data.append(metrics)
        
        # 限制存储数量，保留最近的 1000 条记录
        if len(self.metrics_data) > 1000:
            self.metrics_data = self.metrics_data[-1000:]
        
        logger.debug(f"Recorded metrics: {metrics}")
    
    def get_metrics_summary(self, last_n: Optional[int] = None) -> Dict[str, Any]:
        """获取性能指标摘要
        
        Args:
            last_n: 获取最近 n 条记录的统计，如果为 None 则使用全部记录
            
        Returns:
            指标摘要
        """
        data = self.metrics_data[-last_n:] if last_n else self.metrics_data
        
        if not data:
            return {"total": 0}
        
        total = len(data)
        success_count = sum(1 for d in data if d.success)
        fallback_count = sum(1 for d in data if d.fallback_triggered)
        
        # 按策略分组统计
        strategy_stats = {}
        for metrics in data:
            strategy = metrics.strategy_used
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {"count": 0, "success": 0, "avg_time": 0.0}
            
            strategy_stats[strategy]["count"] += 1
            if metrics.success:
                strategy_stats[strategy]["success"] += 1
            strategy_stats[strategy]["avg_time"] += metrics.response_time
        
        # 计算平均时间
        for strategy in strategy_stats:
            count = strategy_stats[strategy]["count"]
            if count > 0:
                strategy_stats[strategy]["avg_time"] /= count
        
        avg_response_time = sum(d.response_time for d in data) / total
        success_rate = success_count / total
        fallback_rate = fallback_count / total
        
        return {
            "total": total,
            "success_count": success_count,
            "success_rate": success_rate,
            "fallback_count": fallback_count,
            "fallback_rate": fallback_rate,
            "avg_response_time": avg_response_time,
            "strategy_stats": strategy_stats
        }
    
    def clear_cache(self) -> None:
        """清空缓存"""
        if self.cache:
            self.cache.clear()
            logger.info("Cache cleared")
    
    def refresh_schema(self) -> None:
        """刷新 Schema"""
        if self.llm_generator:
            self.llm_generator.refresh_schema()
        logger.info("Schema refreshed")
    
    def test_strategies(self, test_questions: list = None) -> Dict[str, Any]:
        """测试不同策略的效果
        
        Args:
            test_questions: 测试问题列表
            
        Returns:
            测试结果
        """
        if test_questions is None:
            test_questions = [
                "有哪些关于动态规划的题目",
                "题目两数之和的难度",
                "谁是2023年ICPC冠军",
                "张三写了哪些题解",
                "使用贪心算法的题目有哪些"
            ]
        
        modes = ["rule", "llm", "hybrid"]
        results = {}
        
        for mode in modes:
            if mode == "llm" and not self.config.is_llm_available():
                results[mode] = {"skipped": "LLM not available"}
                continue
            
            mode_results = {
                "success": 0,
                "failed": 0,
                "total_time": 0.0,
                "details": []
            }
            
            for question in test_questions:
                try:
                    start_time = time.time()
                    result = self.generate_query(question, force_mode=mode)
                    elapsed_time = (time.time() - start_time) * 1000
                    
                    validation = result.metadata.get("validation")
                    is_valid = validation.is_valid if validation else True
                    
                    if is_valid:
                        mode_results["success"] += 1
                    else:
                        mode_results["failed"] += 1
                    
                    mode_results["total_time"] += elapsed_time
                    mode_results["details"].append({
                        "question": question,
                        "success": is_valid,
                        "time": elapsed_time,
                        "cypher": result.cypher,
                        "source": result.source
                    })
                    
                except Exception as e:
                    mode_results["failed"] += 1
                    mode_results["details"].append({
                        "question": question,
                        "success": False,
                        "error": str(e)
                    })
            
            total_questions = len(test_questions)
            mode_results["success_rate"] = mode_results["success"] / total_questions
            mode_results["avg_time"] = mode_results["total_time"] / total_questions
            
            results[mode] = mode_results
        
        return results