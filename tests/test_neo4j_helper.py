# tests/test_neo4j_helper.py
"""
Neo4j数据库辅助模块单元测试
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from unittest.mock import Mock, patch, MagicMock
from neo4j_helper import Neo4jHelper


class TestNeo4jHelper(unittest.TestCase):
    """测试Neo4j数据库辅助功能"""
    
    def setUp(self):
        """测试前设置"""
        # 使用Mock对象避免真实数据库连接
        self.mock_driver = Mock()
        self.mock_session = Mock()
        self.mock_result = Mock()
        
        # 设置Mock行为 - 正确设置上下文管理器
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        self.mock_driver.session.return_value = mock_context
    
    @patch('neo4j_helper.GraphDatabase')
    def test_init(self, mock_graph_database):
        """测试Neo4jHelper初始化"""
        mock_graph_database.driver.return_value = self.mock_driver
        
        helper = Neo4jHelper(
            uri="bolt://test:7687",
            user="test_user",
            pwd="test_password"
        )
        
        mock_graph_database.driver.assert_called_once_with(
            "bolt://test:7687",
            auth=("test_user", "test_password")
        )
        self.assertEqual(helper.driver, self.mock_driver)
    
    @patch('neo4j_helper.GraphDatabase')
    def test_run_query_success(self, mock_graph_database):
        """测试成功执行查询"""
        mock_graph_database.driver.return_value = self.mock_driver
        
        # 模拟查询结果
        mock_record1 = {'name': '题目1', 'rating': 1200}
        mock_record2 = {'name': '题目2', 'rating': 1500}
        self.mock_session.run.return_value = [mock_record1, mock_record2]
        
        helper = Neo4jHelper()
        
        cypher = "MATCH (p:Problem) RETURN p.name AS name, p.rating AS rating"
        params = {'limit': 10}
        
        result = helper.run_query(cypher, params)
        
        # 验证调用
        self.mock_session.run.assert_called_once_with(cypher, limit=10)
        
        # 验证结果
        expected = [mock_record1, mock_record2]
        self.assertEqual(result, expected)
    
    @patch('neo4j_helper.GraphDatabase')
    def test_run_query_no_params(self, mock_graph_database):
        """测试无参数查询"""
        mock_graph_database.driver.return_value = self.mock_driver
        
        self.mock_session.run.return_value = []
        
        helper = Neo4jHelper()
        result = helper.run_query("MATCH (n) RETURN count(n)")
        
        self.mock_session.run.assert_called_once_with("MATCH (n) RETURN count(n)")
        self.assertEqual(result, [])
    
    @patch('neo4j_helper.GraphDatabase')
    def test_run_query_none_params(self, mock_graph_database):
        """测试None参数处理"""
        mock_graph_database.driver.return_value = self.mock_driver
        
        self.mock_session.run.return_value = []
        
        helper = Neo4jHelper()
        result = helper.run_query("MATCH (n) RETURN count(n)", None)
        
        self.mock_session.run.assert_called_once_with("MATCH (n) RETURN count(n)")
        self.assertEqual(result, [])
    
    @patch('neo4j_helper.GraphDatabase')
    def test_close(self, mock_graph_database):
        """测试关闭连接"""
        mock_graph_database.driver.return_value = self.mock_driver
        
        helper = Neo4jHelper()
        helper.close()
        
        self.mock_driver.close.assert_called_once()
    
    @patch('neo4j_helper.GraphDatabase')
    def test_context_manager_usage(self, mock_graph_database):
        """测试上下文管理器的正确使用"""
        mock_graph_database.driver.return_value = self.mock_driver
        
        helper = Neo4jHelper()
        helper.run_query("MATCH (n) RETURN n")
        
        # 验证使用了上下文管理器
        self.mock_driver.session.assert_called_once()
    
    @patch('neo4j_helper.GraphDatabase')
    def test_record_to_dict_conversion(self, mock_graph_database):
        """测试记录到字典的转换"""
        mock_graph_database.driver.return_value = self.mock_driver
        
        # 创建mock记录对象
        mock_record = MagicMock()
        mock_record.__iter__.return_value = iter([('name', '测试题目'), ('rating', 1000)])
        
        # 模拟dict()函数的行为
        def mock_dict(record):
            return {'name': '测试题目', 'rating': 1000}
        
        self.mock_session.run.return_value = [mock_record]
        
        helper = Neo4jHelper()
        
        with patch('builtins.dict', side_effect=mock_dict):
            result = helper.run_query("MATCH (p:Problem) RETURN p.name, p.rating")
        
        expected = [{'name': '测试题目', 'rating': 1000}]
        self.assertEqual(result, expected)


class TestNeo4jHelperIntegration(unittest.TestCase):
    """Neo4j集成测试（需要真实数据库连接）"""
    
    def setUp(self):
        """设置测试环境"""
        self.test_uri = os.getenv("TEST_NEO_URI", "bolt://localhost:7687")
        self.test_user = os.getenv("TEST_NEO_USER", "neo4j")
        self.test_pwd = os.getenv("TEST_NEO_PWD", "test")
        
        # 标记是否跳过集成测试
        self.skip_integration = os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true"
    
    def test_real_connection(self):
        """测试真实数据库连接（可选）"""
        if self.skip_integration:
            self.skipTest("集成测试被跳过，设置SKIP_INTEGRATION_TESTS=false来启用")
        
        try:
            helper = Neo4jHelper(
                uri=self.test_uri,
                user=self.test_user,
                pwd=self.test_pwd
            )
            
            # 简单的健康检查查询
            result = helper.run_query("RETURN 1 as test")
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['test'], 1)
            
            helper.close()
            
        except Exception as e:
            self.skipTest(f"无法连接到测试数据库: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)