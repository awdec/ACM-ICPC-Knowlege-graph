# src/deepseek/deepseek_cypher.py
import json
import re
import logging
import time
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from deepseek.deepseek_client import DeepSeekClient, APIConnectionError, APITimeoutError, APIRateLimitError
from deepseek.schema_provider import SchemaProvider
from config.config_manager import ConfigManager

# 设置日志
logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """查询结果"""
    cypher: str
    parameters: Dict[str, Any]
    intent: Optional[str] = None
    confidence: float = 0.0
    source: str = "llm"
    generation_time: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ParseError(Exception):
    """解析错误"""
    pass


class GenerationError(Exception):
    """生成错误"""
    pass


class DeepSeekCypherGenerator:
    """DeepSeek Cypher 查询生成器"""
    
    def __init__(self, 
                 client: Optional[DeepSeekClient] = None,
                 schema_provider: Optional[SchemaProvider] = None):
        """初始化生成器
        
        Args:
            client: DeepSeek 客户端
            schema_provider: Schema 提供者
        """
        self.client = client or DeepSeekClient()
        self.schema_provider = schema_provider or SchemaProvider()
        self.config = ConfigManager().get_deepseek_config()
        
        # 缓存 Schema 文本
        self._schema_text = None
    
    def parse_question_to_cypher(self, question: str) -> QueryResult:
        """将自然语言问题转换为 Cypher 查询
        
        Args:
            question: 用户自然语言问题
            
        Returns:
            QueryResult 对象
            
        Raises:
            GenerationError: 生成失败
            ParseError: 解析失败
        """
        if not question or not question.strip():
            raise GenerationError("Question cannot be empty")
        
        start_time = time.time()
        
        try:
            # 构建完整的 Prompt
            prompt = self._build_prompt(question.strip())
            
            # 调用 LLM API
            logger.debug(f"Calling DeepSeek API for question: {question}")
            raw_response = self.client.generate_cypher(prompt)
            
            # 解析响应
            result = self._parse_response(raw_response)
            
            # 设置生成时间和来源
            result.generation_time = (time.time() - start_time) * 1000  # 转换为毫秒
            result.source = "llm"
            
            logger.info(f"Generated Cypher successfully in {result.generation_time:.2f}ms")
            return result
            
        except (APIConnectionError, APITimeoutError, APIRateLimitError) as e:
            logger.error(f"API error: {str(e)}")
            raise GenerationError(f"DeepSeek API error: {str(e)}")
        except ParseError as e:
            logger.error(f"Parse error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise GenerationError(f"Unexpected error: {str(e)}")
    
    def _build_prompt(self, question: str) -> str:
        """构建完整的 Prompt
        
        Args:
            question: 用户问题
            
        Returns:
            完整的 Prompt 字符串
        """
        # 获取 Schema 信息
        if self._schema_text is None:
            self._schema_text = self.schema_provider.get_schema_text()
        
        # 构建示例
        examples = self._get_examples()
        
        # 构建用户 Prompt
        prompt = f"""【用户问题】
{question}

【图数据库Schema】
{self._schema_text}

【示例参考】
{examples}

现在请根据用户问题生成Cypher查询。"""
        
        return prompt
    
    def _get_examples(self) -> str:
        """获取示例查询"""
        examples = [
            {
                "question": "题目\"两数之和\"的难度",
                "cypher": "MATCH (p:Problem) WHERE toLower(p.name) CONTAINS toLower($problem) RETURN p.name AS name, p.rating AS rating LIMIT 10",
                "parameters": {"problem": "两数之和"}
            },
            {
                "question": "有哪些关于动态规划的题目",
                "cypher": "MATCH (p:Problem)-[:HAS_TAG]->(t:Tag) WHERE toLower(t.name)=toLower($tag) RETURN p.name AS name, p.rating AS rating LIMIT 100",
                "parameters": {"tag": "动态规划"}
            },
            {
                "question": "谁是2023年ICPC世界冠军",
                "cypher": "MATCH (tm:Team)-[r:PLACED]->(c:Contest) WHERE toLower(c.name) CONTAINS toLower($year_or_name) AND r.rank IN ['1','1st','冠军'] RETURN tm.name AS team, r.rank AS rank, r.region AS region LIMIT 5",
                "parameters": {"year_or_name": "2023"}
            },
            {
                "question": "张三写了哪些题解",
                "cypher": "MATCH (pr:Person {name:$author})<-[:AUTHOR]-(s:Solution)<-[:HAS_SOLUTION]-(p:Problem) RETURN p.name AS problem, s.id AS sid, substring(s.content,0,300) AS snippet LIMIT 50",
                "parameters": {"author": "张三"}
            }
        ]
        
        example_texts = []
        for example in examples:
            params_str = json.dumps(example["parameters"], ensure_ascii=False)
            example_texts.append(
                f"问题：{example['question']}\n"
                f"Cypher: {example['cypher']}\n"
                f"Parameters: {params_str}"
            )
        
        return "\n\n".join(example_texts)
    
    def _parse_response(self, raw_response: str) -> QueryResult:
        """解析 LLM 响应
        
        Args:
            raw_response: LLM 原始响应
            
        Returns:
            QueryResult 对象
            
        Raises:
            ParseError: 解析失败
        """
        try:
            # 首先尝试 JSON 格式解析
            result = self._parse_json_response(raw_response)
            if result:
                return result
            
            # 如果 JSON 解析失败，尝试代码块解析
            result = self._parse_code_block_response(raw_response)
            if result:
                return result
            
            # 如果都失败，尝试正则提取
            result = self._parse_regex_response(raw_response)
            if result:
                return result
            
            raise ParseError("Cannot parse response: no valid Cypher found")
            
        except json.JSONDecodeError as e:
            raise ParseError(f"JSON decode error: {str(e)}")
        except Exception as e:
            raise ParseError(f"Parse error: {str(e)}")
    
    def _parse_json_response(self, response: str) -> Optional[QueryResult]:
        """解析 JSON 格式的响应"""
        try:
            # 尝试直接解析整个响应为 JSON
            data = json.loads(response.strip())
            return self._extract_from_json(data)
        except:
            pass
        
        # 尝试提取 JSON 代码块
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                data = json.loads(match.group(1))
                return self._extract_from_json(data)
            except:
                pass
        
        # 尝试提取行内 JSON
        json_pattern = r'\{[^{}]*"cypher"[^{}]*\}'
        match = re.search(json_pattern, response, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return self._extract_from_json(data)
            except:
                pass
        
        return None
    
    def _extract_from_json(self, data: Dict[str, Any]) -> Optional[QueryResult]:
        """从 JSON 数据中提取查询结果"""
        if not isinstance(data, dict):
            return None
        
        cypher = data.get("cypher", "").strip()
        if not cypher:
            return None
        
        parameters = data.get("parameters", {})
        if not isinstance(parameters, dict):
            parameters = {}
        
        intent = data.get("intent", "")
        confidence = float(data.get("confidence", 0.8))
        
        return QueryResult(
            cypher=cypher,
            parameters=parameters,
            intent=intent,
            confidence=confidence
        )
    
    def _parse_code_block_response(self, response: str) -> Optional[QueryResult]:
        """解析代码块格式的响应"""
        # 提取 Cypher 代码块
        cypher_pattern = r'```(?:cypher|sql)?\s*(.*?)\s*```'
        cypher_match = re.search(cypher_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if not cypher_match:
            return None
        
        cypher = cypher_match.group(1).strip()
        if not cypher:
            return None
        
        # 尝试提取参数
        parameters = {}
        
        # 查找参数定义
        param_patterns = [
            r'[Pp]arameters?[:\s]*\{([^}]+)\}',
            r'[Pp]arams?[:\s]*\{([^}]+)\}',
            r'\$(\w+)[:\s]*["\']([^"\']+)["\']'
        ]
        
        for pattern in param_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple) and len(match) == 2:
                    parameters[match[0]] = match[1]
        
        return QueryResult(
            cypher=cypher,
            parameters=parameters,
            confidence=0.6
        )
    
    def _parse_regex_response(self, response: str) -> Optional[QueryResult]:
        """使用正则表达式解析响应"""
        # 查找 MATCH 开头的 Cypher 语句
        cypher_pattern = r'(MATCH\s+.*?)(?:\n\n|\n$|$)'
        match = re.search(cypher_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if not match:
            return None
        
        cypher = match.group(1).strip()
        
        # 提取参数中的变量
        parameters = {}
        param_vars = re.findall(r'\$(\w+)', cypher)
        
        for var in param_vars:
            # 尝试从响应中找到对应的值
            value_pattern = rf'{var}[:\s]*["\']([^"\']+)["\']'
            value_match = re.search(value_pattern, response, re.IGNORECASE)
            if value_match:
                parameters[var] = value_match.group(1)
            else:
                parameters[var] = ""  # 默认空值
        
        return QueryResult(
            cypher=cypher,
            parameters=parameters,
            confidence=0.4
        )
    
    def test_generation(self, test_questions: list = None) -> Dict[str, Any]:
        """测试生成功能
        
        Args:
            test_questions: 测试问题列表，如果为 None 使用默认问题
            
        Returns:
            测试结果统计
        """
        if test_questions is None:
            test_questions = [
                "有哪些关于动态规划的题目",
                "题目两数之和的难度",
                "张三写了哪些题解"
            ]
        
        results = {
            "total": len(test_questions),
            "success": 0,
            "failed": 0,
            "avg_time": 0.0,
            "details": []
        }
        
        total_time = 0.0
        
        for question in test_questions:
            try:
                start_time = time.time()
                query_result = self.parse_question_to_cypher(question)
                
                elapsed_time = (time.time() - start_time) * 1000
                total_time += elapsed_time
                
                results["success"] += 1
                results["details"].append({
                    "question": question,
                    "success": True,
                    "cypher": query_result.cypher,
                    "parameters": query_result.parameters,
                    "time": elapsed_time
                })
                
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "question": question,
                    "success": False,
                    "error": str(e)
                })
        
        if results["success"] > 0:
            results["avg_time"] = total_time / results["success"]
        
        return results
    
    def refresh_schema(self) -> None:
        """刷新 Schema 缓存"""
        self._schema_text = None
        self.schema_provider.refresh_schema()
        logger.info("Schema cache refreshed")