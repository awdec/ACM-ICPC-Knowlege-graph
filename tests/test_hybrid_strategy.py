# tests/test_hybrid_strategy.py
import unittest
from unittest.mock import Mock, patch
from src.deepseek.hybrid_strategy import HybridStrategy, ComplexityMetrics, QueryResult
from src.deepseek.cypher_validator import ValidationResult


class TestHybridStrategy(unittest.TestCase):
    """混合策略测试"""
    
    def setUp(self):
        # 使用 mock 对象避免实际的 API 调用和数据库连接
        self.mock_llm_generator = Mock()
        self.mock_validator = Mock()
        
        # 设置默认的 mock 返回值
        self.mock_validator.validate.return_value = ValidationResult(is_valid=True)
        
        # 创建策略实例
        self.strategy = HybridStrategy(
            llm_generator=self.mock_llm_generator,
            validator=self.mock_validator
        )
    
    def test_analyze_question_complexity_simple(self):
        """测试简单问题的复杂度分析"""
        question = "有哪些关于动态规划的题目"
        
        metrics = self.strategy._analyze_question_complexity(question)
        
        self.assertIsInstance(metrics, ComplexityMetrics)
        self.assertGreaterEqual(metrics.entity_count, 1)
        self.assertGreaterEqual(metrics.relation_depth, 1)
        self.assertTrue(metrics.complexity_score >= 0)
    
    def test_analyze_question_complexity_complex(self):
        """测试复杂问题的复杂度分析"""
        question = "统计使用动态规划算法且难度大于1500的题目数量，按照来源排序"
        
        metrics = self.strategy._analyze_question_complexity(question)
        
        self.assertTrue(metrics.has_aggregation)  # 包含"统计"、"数量"
        self.assertTrue(metrics.has_sorting)      # 包含"排序"
        self.assertGreater(metrics.complexity_score, 5)  # 应该是复杂查询
    
    def test_select_strategy_simple_known_pattern(self):
        """测试简单已知模式的策略选择"""
        # 模拟规则匹配成功的复杂度指标
        metrics = ComplexityMetrics(
            entity_count=1,
            relation_depth=1,
            condition_count=1,
            has_aggregation=False,
            has_sorting=False,
            pattern_match_confidence=0.9
        )
        
        strategy = self.strategy._select_strategy(metrics)
        
        self.assertEqual(strategy, "rule")
    
    def test_select_strategy_complex_unknown_pattern(self):
        """测试复杂未知模式的策略选择"""
        metrics = ComplexityMetrics(
            entity_count=3,
            relation_depth=3,
            condition_count=2,
            has_aggregation=True,
            has_sorting=True,
            pattern_match_confidence=0.1  # 规则匹配失败
        )
        
        strategy = self.strategy._select_strategy(metrics)
        
        self.assertEqual(strategy, "llm")
    
    @patch('src.deepseek.hybrid_strategy.parse_intent')
    @patch('src.deepseek.hybrid_strategy.get_cypher_and_params')
    def test_generate_rule_only_success(self, mock_get_cypher, mock_parse_intent):
        """测试纯规则模式成功生成"""
        # 设置 mock 返回值
        mock_parse_intent.return_value = {
            'intent': 'list_problems_by_tag',
            'slots': {'tag': '动态规划'}
        }
        mock_get_cypher.return_value = (
            "MATCH (p:Problem)-[:HAS_TAG]->(t:Tag) WHERE t.name = $tag RETURN p.name",
            {'tag': '动态规划'}
        )
        
        result = self.strategy._generate_rule_only("有哪些关于动态规划的题目")
        
        self.assertIsInstance(result, QueryResult)
        self.assertEqual(result.source, "rule")
        self.assertEqual(result.intent, "list_problems_by_tag")
        self.assertIn("MATCH", result.cypher)
        self.assertEqual(result.parameters['tag'], '动态规划')
    
    @patch('src.deepseek.hybrid_strategy.parse_intent')
    def test_generate_rule_only_unknown_intent(self, mock_parse_intent):
        """测试规则模式遇到未知意图"""
        mock_parse_intent.return_value = {
            'intent': 'unknown',
            'slots': {}
        }
        
        with self.assertRaises(Exception):
            self.strategy._generate_rule_only("这是一个未知的问题")
    
    def test_generate_llm_only_success(self):
        """测试纯 LLM 模式成功生成"""
        # 设置 mock LLM 生成器返回值
        expected_result = QueryResult(
            cypher="MATCH (p:Problem) RETURN p.name",
            parameters={},
            source="llm",
            confidence=0.8
        )
        self.mock_llm_generator.parse_question_to_cypher.return_value = expected_result
        
        result = self.strategy._generate_llm_only("测试问题")
        
        self.assertEqual(result, expected_result)
        self.mock_llm_generator.parse_question_to_cypher.assert_called_once_with("测试问题")
    
    def test_generate_llm_only_api_unavailable(self):
        """测试 LLM API 不可用的情况"""
        with patch.object(self.strategy.config, 'is_llm_available', return_value=False):
            with self.assertRaises(Exception) as context:
                self.strategy._generate_llm_only("测试问题")
            
            self.assertIn("not available", str(context.exception))
    
    def test_cache_functionality(self):
        """测试缓存功能"""
        question = "测试缓存问题"
        
        # 第一次调用 - 应该生成查询
        with patch.object(self.strategy, '_generate_rule_only') as mock_rule:
            mock_result = QueryResult(cypher="MATCH (p:Problem) RETURN p.name", parameters={}, source="rule")
            mock_rule.return_value = mock_result
            
            result1 = self.strategy.generate_query(question, force_mode="rule")
            
            # 验证第一次调用了生成方法
            mock_rule.assert_called_once()
        
        # 第二次调用 - 应该从缓存获取
        with patch.object(self.strategy, '_generate_rule_only') as mock_rule:
            result2 = self.strategy.generate_query(question, force_mode="rule")
            
            # 验证第二次没有调用生成方法（使用缓存）
            mock_rule.assert_not_called()
            self.assertTrue(result2.metadata.get("from_cache", False))
    
    def test_validation_failure_fallback(self):
        """测试验证失败时的降级"""
        question = "测试降级问题"
        
        # 设置验证失败
        self.mock_validator.validate.return_value = ValidationResult(
            is_valid=False,
            error_message="Test validation error"
        )
        
        # 设置 LLM 生成成功（作为降级选项）
        mock_llm_result = QueryResult(cypher="MATCH (p:Problem) RETURN p.name", parameters={}, source="llm")
        self.mock_llm_generator.parse_question_to_cypher.return_value = mock_llm_result
        
        # 设置规则生成失败
        with patch.object(self.strategy, '_generate_rule_only', side_effect=Exception("Rule failed")):
            with patch.object(self.strategy.config, 'is_llm_available', return_value=True):
                result = self.strategy.generate_query(question, force_mode="hybrid")
        
        # 应该降级到 LLM 并标记
        self.assertEqual(result.source, "llm")
        self.assertIn("fallback", result.metadata.get("flags", []))
    
    def test_get_cache_key(self):
        """测试缓存键生成"""
        question = "Test Question"
        
        key1 = self.strategy._get_cache_key(question, "rule")
        key2 = self.strategy._get_cache_key(question.lower(), "rule")
        key3 = self.strategy._get_cache_key(question, "llm")
        
        self.assertEqual(key1, key2)  # 大小写不敏感
        self.assertNotEqual(key1, key3)  # 不同模式不同键
    
    def test_metrics_recording(self):
        """测试性能指标记录"""
        question = "测试指标记录"
        
        # 清空现有指标
        self.strategy.metrics_data = []
        
        with patch.object(self.strategy, '_generate_rule_only') as mock_rule:
            mock_result = QueryResult(cypher="MATCH (p:Problem) RETURN p.name", parameters={}, source="rule")
            mock_rule.return_value = mock_result
            
            self.strategy.generate_query(question, force_mode="rule")
        
        # 验证指标被记录
        self.assertEqual(len(self.strategy.metrics_data), 1)
        
        metrics = self.strategy.metrics_data[0]
        self.assertEqual(metrics.question, question)
        self.assertEqual(metrics.strategy_used, "rule")
        self.assertTrue(metrics.success)
        self.assertGreater(metrics.response_time, 0)
    
    def test_metrics_summary(self):
        """测试指标摘要生成"""
        # 添加一些测试数据
        from src.deepseek.hybrid_strategy import MetricsData
        import time
        
        self.strategy.metrics_data = [
            MetricsData(
                timestamp=time.time(),
                question="test1",
                strategy_used="rule",
                success=True,
                response_time=100.0,
                fallback_triggered=False,
                validation_passed=True
            ),
            MetricsData(
                timestamp=time.time(),
                question="test2", 
                strategy_used="llm",
                success=False,
                response_time=200.0,
                fallback_triggered=True,
                validation_passed=False
            )
        ]
        
        summary = self.strategy.get_metrics_summary()
        
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["success_count"], 1)
        self.assertEqual(summary["success_rate"], 0.5)
        self.assertEqual(summary["fallback_count"], 1)
        self.assertEqual(summary["fallback_rate"], 0.5)
        self.assertEqual(summary["avg_response_time"], 150.0)


if __name__ == '__main__':
    unittest.main()