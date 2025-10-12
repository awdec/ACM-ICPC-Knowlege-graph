# src/deepseek/deepseek_client.py
import json
import time
import logging
from typing import Dict, Any, Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config.config_manager import ConfigManager, DeepSeekConfig

# 设置日志
logger = logging.getLogger(__name__)


class APIConnectionError(Exception):
    """API 连接错误"""
    pass


class APITimeoutError(Exception):
    """API 超时错误"""
    pass


class APIRateLimitError(Exception):
    """API 限流错误"""
    pass


class APIAuthenticationError(Exception):
    """API 认证错误"""
    pass


class APIResponseError(Exception):
    """API 响应错误"""
    pass


class DeepSeekClient:
    """DeepSeek API 客户端"""
    
    def __init__(self, config: Optional[DeepSeekConfig] = None):
        """初始化客户端
        
        Args:
            config: DeepSeek 配置，如果为 None 则从 ConfigManager 获取
        """
        self.config = config or ConfigManager().get_deepseek_config()
        self.session = requests.Session()
        
        # 设置请求头
        self.session.headers.update({
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ACM-ICPC-KG/1.0"
        })
        
        # 验证配置
        if not self.config.api_key:
            logger.warning("DeepSeek API key is not configured")
    
    def _build_request_payload(self, messages: list, **kwargs) -> Dict[str, Any]:
        """构建请求载荷"""
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        
        # 添加额外参数
        for key, value in kwargs.items():
            if key in ["top_p", "frequency_penalty", "presence_penalty"]:
                payload[key] = value
        
        return payload
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((APIRateLimitError, requests.exceptions.RequestException))
    )
    def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """发送 API 请求"""
        if not self.config.api_key:
            raise APIAuthenticationError("DeepSeek API key is not configured")
        
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        
        try:
            logger.debug(f"Making request to {url}")
            response = self.session.post(
                url,
                json=payload,
                timeout=self.config.timeout
            )
            
            # 检查响应状态
            if response.status_code == 401:
                raise APIAuthenticationError("Invalid API key")
            elif response.status_code == 429:
                raise APIRateLimitError("Rate limit exceeded")
            elif response.status_code >= 500:
                raise APIConnectionError(f"Server error: {response.status_code}")
            elif response.status_code != 200:
                raise APIResponseError(f"HTTP {response.status_code}: {response.text}")
            
            return response.json()
            
        except requests.exceptions.Timeout:
            raise APITimeoutError(f"Request timeout after {self.config.timeout} seconds")
        except requests.exceptions.ConnectionError as e:
            raise APIConnectionError(f"Connection error: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise APIConnectionError(f"Request error: {str(e)}")
        except json.JSONDecodeError as e:
            raise APIResponseError(f"Invalid JSON response: {str(e)}")
    
    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        """从响应中提取内容"""
        try:
            choices = response_data.get("choices", [])
            if not choices:
                raise APIResponseError("No choices in response")
            
            message = choices[0].get("message", {})
            content = message.get("content", "")
            
            if not content:
                raise APIResponseError("Empty content in response")
            
            return content.strip()
            
        except (KeyError, IndexError, TypeError) as e:
            raise APIResponseError(f"Invalid response structure: {str(e)}")
    
    def generate_cypher(self, prompt: str, **kwargs) -> str:
        """生成 Cypher 查询
        
        Args:
            prompt: 完整的提示词（包含问题和 Schema）
            **kwargs: 额外的 API 参数
            
        Returns:
            生成的 Cypher 查询语句
            
        Raises:
            APIConnectionError: 连接错误
            APITimeoutError: 超时错误
            APIRateLimitError: 限流错误
            APIAuthenticationError: 认证错误
            APIResponseError: 响应错误
        """
        # 构建消息
        messages = [
            {
                "role": "system",
                "content": self._get_system_prompt()
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # 构建请求载荷
        payload = self._build_request_payload(messages, **kwargs)
        
        # 发送请求
        start_time = time.time()
        try:
            response_data = self._make_request(payload)
            
            # 提取内容
            content = self._extract_content(response_data)
            
            # 记录使用情况
            usage = response_data.get("usage", {})
            logger.info(
                f"DeepSeek API call successful. "
                f"Time: {time.time() - start_time:.2f}s, "
                f"Tokens: {usage.get('total_tokens', 0)}"
            )
            
            return content
            
        except Exception as e:
            logger.error(f"DeepSeek API call failed: {str(e)}")
            raise
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个专业的Neo4j Cypher查询专家。你的任务是根据用户的中文自然语言问题和提供的图数据库Schema信息，生成准确、高效、安全的Cypher查询语句。

【核心要求】
1. 查询必须符合提供的Schema结构，不得使用不存在的节点标签、关系类型或属性
2. 使用参数化查询，将用户输入的实体名称作为参数（使用$parameter语法）
3. 对字符串匹配使用toLower()函数进行不区分大小写的匹配
4. 只返回Cypher查询语句和参数，不要包含任何解释说明
5. 如果问题不明确或无法生成有效查询，返回ERROR标记

【返回格式】
严格按照以下JSON格式返回：
{
  "cypher": "生成的Cypher查询语句",
  "parameters": {
    "param1": "value1",
    "param2": "value2"
  },
  "intent": "查询意图类型(可选)"
}

【安全规则】
- 禁止使用DELETE、DETACH DELETE、REMOVE、SET、CREATE、MERGE等修改操作
- 禁止使用LOAD CSV、CALL apoc.*等潜在危险操作
- 只允许使用MATCH、OPTIONAL MATCH、WHERE、RETURN、WITH、ORDER BY、LIMIT等只读操作"""
    
    def test_connection(self) -> bool:
        """测试 API 连接"""
        try:
            test_prompt = "测试连接"
            messages = [
                {
                    "role": "user",
                    "content": test_prompt
                }
            ]
            
            payload = {
                "model": self.config.model,
                "messages": messages,
                "max_tokens": 10,
                "temperature": 0.1
            }
            
            response_data = self._make_request(payload)
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def get_usage_info(self) -> Dict[str, Any]:
        """获取使用信息（如果 API 支持）"""
        # 这里可以添加获取使用统计的逻辑
        return {
            "api_available": bool(self.config.api_key),
            "model": self.config.model,
            "base_url": self.config.base_url
        }