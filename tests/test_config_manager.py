# tests/test_config_manager.py
import unittest
import os
from unittest.mock import patch
from src.config.config_manager import ConfigManager, DeepSeekConfig, StrategyConfig


class TestConfigManager(unittest.TestCase):
    """配置管理器测试"""
    
    def setUp(self):
        # 清除单例实例，确保每个测试都是独立的
        ConfigManager._instance = None
        ConfigManager._config = None
    
    def tearDown(self):
        # 清理单例实例
        ConfigManager._instance = None
        ConfigManager._config = None
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        
        self.assertIs(manager1, manager2)
    
    @patch.dict(os.environ, {
        'DEEPSEEK_API_KEY': 'test_api_key',
        'DEEPSEEK_MODEL': 'test-model',
        'QUERY_MODE': 'llm',
        'COMPLEXITY_THRESHOLD': '8'
    })
    def test_environment_variable_loading(self):
        """测试环境变量加载"""
        manager = ConfigManager()
        
        deepseek_config = manager.get_deepseek_config()
        self.assertEqual(deepseek_config.api_key, 'test_api_key')
        self.assertEqual(deepseek_config.model, 'test-model')
        
        strategy_config = manager.get_strategy_config()
        self.assertEqual(strategy_config.mode, 'llm')
        self.assertEqual(strategy_config.complexity_threshold, 8)
    
    def test_default_values(self):
        """测试默认值"""
        with patch.dict(os.environ, {}, clear=True):
            manager = ConfigManager()
            
            deepseek_config = manager.get_deepseek_config()
            self.assertEqual(deepseek_config.api_key, "")
            self.assertEqual(deepseek_config.base_url, "https://api.deepseek.com")
            self.assertEqual(deepseek_config.temperature, 0.1)
            
            strategy_config = manager.get_strategy_config()
            self.assertEqual(strategy_config.mode, "hybrid")
            self.assertEqual(strategy_config.complexity_threshold, 6)
            self.assertTrue(strategy_config.llm_fallback_enabled)
    
    def test_is_llm_available_with_api_key(self):
        """测试有 API Key 时 LLM 可用性"""
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'valid_key'}):
            manager = ConfigManager()
            self.assertTrue(manager.is_llm_available())
    
    def test_is_llm_available_without_api_key(self):
        """测试无 API Key 时 LLM 不可用"""
        with patch.dict(os.environ, {}, clear=True):
            manager = ConfigManager()
            self.assertFalse(manager.is_llm_available())
    
    def test_is_llm_available_with_empty_api_key(self):
        """测试空 API Key 时 LLM 不可用"""
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': '   '}):
            manager = ConfigManager()
            self.assertFalse(manager.is_llm_available())
    
    def test_get_query_mode_with_llm_available(self):
        """测试 LLM 可用时的查询模式"""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'valid_key',
            'QUERY_MODE': 'hybrid'
        }):
            manager = ConfigManager()
            self.assertEqual(manager.get_query_mode(), 'hybrid')
    
    def test_get_query_mode_force_rule_when_llm_unavailable(self):
        """测试 LLM 不可用时强制使用规则模式"""
        with patch.dict(os.environ, {
            'QUERY_MODE': 'llm'  # 设置为 LLM 模式
        }, clear=True):
            manager = ConfigManager()
            # 应该强制返回规则模式，因为没有 API Key
            self.assertEqual(manager.get_query_mode(), 'rule')
    
    def test_neo4j_config_loading(self):
        """测试 Neo4j 配置加载"""
        with patch.dict(os.environ, {
            'NEO4J_URI': 'bolt://test:7687',
            'NEO4J_USER': 'test_user',
            'NEO4J_PASSWORD': 'test_password'
        }):
            manager = ConfigManager()
            neo4j_config = manager.get_neo4j_config()
            
            self.assertEqual(neo4j_config.uri, 'bolt://test:7687')
            self.assertEqual(neo4j_config.user, 'test_user')
            self.assertEqual(neo4j_config.password, 'test_password')
    
    def test_boolean_environment_variables(self):
        """测试布尔型环境变量解析"""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('1', False),  # 非 'true' 字符串都是 False
            ('yes', False),
            ('', False)
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {'LLM_FALLBACK_ENABLED': env_value}):
                # 重置单例
                ConfigManager._instance = None
                ConfigManager._config = None
                
                manager = ConfigManager()
                strategy_config = manager.get_strategy_config()
                
                self.assertEqual(
                    strategy_config.llm_fallback_enabled, 
                    expected,
                    f"Failed for env_value='{env_value}', expected={expected}"
                )
    
    def test_integer_environment_variables(self):
        """测试整型环境变量解析"""
        with patch.dict(os.environ, {
            'DEEPSEEK_TIMEOUT': '45',
            'DEEPSEEK_MAX_RETRIES': '5',
            'CACHE_TTL': '7200'
        }):
            manager = ConfigManager()
            
            deepseek_config = manager.get_deepseek_config()
            self.assertEqual(deepseek_config.timeout, 45)
            self.assertEqual(deepseek_config.max_retries, 5)
            
            strategy_config = manager.get_strategy_config()
            self.assertEqual(strategy_config.cache_ttl, 7200)
    
    def test_float_environment_variables(self):
        """测试浮点型环境变量解析"""
        with patch.dict(os.environ, {
            'DEEPSEEK_TEMPERATURE': '0.5'
        }):
            manager = ConfigManager()
            deepseek_config = manager.get_deepseek_config()
            
            self.assertEqual(deepseek_config.temperature, 0.5)
    
    def test_validation_config(self):
        """测试验证配置"""
        with patch.dict(os.environ, {
            'ENABLE_SYNTAX_CHECK': 'false',
            'MAX_COMPLEXITY_SCORE': '12'
        }):
            manager = ConfigManager()
            validation_config = manager.get_validation_config()
            
            self.assertFalse(validation_config.enable_syntax_check)
            self.assertEqual(validation_config.max_complexity_score, 12)
    
    def test_logging_config(self):
        """测试日志配置"""
        with patch.dict(os.environ, {
            'LOG_LEVEL': 'DEBUG',
            'LOG_FILE': '/tmp/test.log'
        }):
            manager = ConfigManager()
            logging_config = manager.get_logging_config()
            
            self.assertEqual(logging_config.level, 'DEBUG')
            self.assertEqual(logging_config.file, '/tmp/test.log')


if __name__ == '__main__':
    unittest.main()