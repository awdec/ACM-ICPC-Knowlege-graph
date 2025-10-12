# src/config/config_manager.py
import os
import yaml
from dataclasses import dataclass
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# 尝试加载 .env 文件
load_dotenv()


@dataclass
class DeepSeekConfig:
    """DeepSeek API 配置"""
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    timeout: int = 30
    max_retries: int = 3
    temperature: float = 0.1
    max_tokens: int = 2000


@dataclass
class StrategyConfig:
    """查询策略配置"""
    mode: str = "hybrid"  # rule/llm/hybrid
    complexity_threshold: int = 6
    llm_fallback_enabled: bool = True
    rule_fallback_enabled: bool = True
    enable_cache: bool = True
    cache_ttl: int = 3600


@dataclass
class ValidationConfig:
    """验证配置"""
    enable_syntax_check: bool = True
    enable_security_check: bool = True
    enable_complexity_check: bool = True
    max_complexity_score: int = 8


@dataclass
class Neo4jConfig:
    """Neo4j 数据库配置"""
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "luogu20201208"


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None


@dataclass
class AppConfig:
    """应用配置"""
    deepseek: DeepSeekConfig
    strategy: StrategyConfig
    validation: ValidationConfig
    neo4j: Neo4jConfig
    logging: LoggingConfig


class ConfigManager:
    """配置管理器"""
    
    _instance: Optional['ConfigManager'] = None
    _config: Optional[AppConfig] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._config = self._load_config()
    
    def _load_config(self) -> AppConfig:
        """加载配置"""
        # 从环境变量加载配置
        deepseek_config = DeepSeekConfig(
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            timeout=int(os.getenv("DEEPSEEK_TIMEOUT", "30")),
            max_retries=int(os.getenv("DEEPSEEK_MAX_RETRIES", "3")),
            temperature=float(os.getenv("DEEPSEEK_TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("DEEPSEEK_MAX_TOKENS", "2000"))
        )
        
        strategy_config = StrategyConfig(
            mode=os.getenv("QUERY_MODE", "hybrid"),
            complexity_threshold=int(os.getenv("COMPLEXITY_THRESHOLD", "6")),
            llm_fallback_enabled=os.getenv("LLM_FALLBACK_ENABLED", "true").lower() == "true",
            rule_fallback_enabled=os.getenv("RULE_FALLBACK_ENABLED", "true").lower() == "true",
            enable_cache=os.getenv("ENABLE_QUERY_CACHE", "true").lower() == "true",
            cache_ttl=int(os.getenv("CACHE_TTL", "3600"))
        )
        
        validation_config = ValidationConfig(
            enable_syntax_check=os.getenv("ENABLE_SYNTAX_CHECK", "true").lower() == "true",
            enable_security_check=os.getenv("ENABLE_SECURITY_CHECK", "true").lower() == "true",
            enable_complexity_check=os.getenv("ENABLE_COMPLEXITY_CHECK", "true").lower() == "true",
            max_complexity_score=int(os.getenv("MAX_COMPLEXITY_SCORE", "8"))
        )
        
        neo4j_config = Neo4jConfig(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "luogu20201208")
        )
        
        logging_config = LoggingConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            file=os.getenv("LOG_FILE")
        )
        
        return AppConfig(
            deepseek=deepseek_config,
            strategy=strategy_config,
            validation=validation_config,
            neo4j=neo4j_config,
            logging=logging_config
        )
    
    @property
    def config(self) -> AppConfig:
        """获取配置"""
        return self._config
    
    def get_deepseek_config(self) -> DeepSeekConfig:
        """获取 DeepSeek 配置"""
        return self._config.deepseek
    
    def get_strategy_config(self) -> StrategyConfig:
        """获取策略配置"""
        return self._config.strategy
    
    def get_validation_config(self) -> ValidationConfig:
        """获取验证配置"""
        return self._config.validation
    
    def get_neo4j_config(self) -> Neo4jConfig:
        """获取 Neo4j 配置"""
        return self._config.neo4j
    
    def get_logging_config(self) -> LoggingConfig:
        """获取日志配置"""
        return self._config.logging
    
    def is_llm_available(self) -> bool:
        """检查 LLM 是否可用"""
        return bool(self._config.deepseek.api_key.strip())
    
    def get_query_mode(self) -> str:
        """获取查询模式，如果 API Key 不可用则强制使用规则模式"""
        if not self.is_llm_available():
            return "rule"
        return self._config.strategy.mode


# 全局配置管理器实例
config_manager = ConfigManager()