# tests/test_cypher_validator.py
import unittest
from src.deepseek.cypher_validator import CypherValidator, ValidationResult, ErrorType


class TestCypherValidator(unittest.TestCase):
    """Cypher 验证器测试"""
    
    def setUp(self):
        self.validator = CypherValidator()
    
    def test_valid_match_query(self):
        """测试有效的 MATCH 查询"""
        cypher = "MATCH (p:Problem) WHERE p.name = $name RETURN p.name, p.rating"
        parameters = {"name": "两数之和"}
        
        result = self.validator.validate(cypher, parameters)
        
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.error_type)
        self.assertEqual(result.error_message, "")
    
    def test_dangerous_delete_operation(self):
        """测试危险的 DELETE 操作"""
        cypher = "MATCH (p:Problem) DELETE p"
        
        result = self.validator.validate(cypher)
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_type, ErrorType.SECURITY)
        self.assertIn("DELETE", result.error_message)
    
    def test_dangerous_create_operation(self):
        """测试危险的 CREATE 操作"""
        cypher = "CREATE (p:Problem {name: 'test'})"
        
        result = self.validator.validate(cypher)
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_type, ErrorType.SECURITY)
        self.assertIn("CREATE", result.error_message)
    
    def test_mismatched_brackets(self):
        """测试括号不匹配"""
        cypher = "MATCH (p:Problem WHERE p.name = $name RETURN p.name"  # 缺少右括号
        
        result = self.validator.validate(cypher)
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_type, ErrorType.SYNTAX)
        self.assertIn("bracket", result.error_message.lower())
    
    def test_mismatched_quotes(self):
        """测试引号不匹配"""
        cypher = "MATCH (p:Problem) WHERE p.name = 'test RETURN p.name"  # 缺少右引号
        
        result = self.validator.validate(cypher)
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_type, ErrorType.SYNTAX)
        self.assertIn("quote", result.error_message.lower())
    
    def test_empty_query(self):
        """测试空查询"""
        result = self.validator.validate("")
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_type, ErrorType.SYNTAX)
        self.assertIn("Empty", result.error_message)
    
    def test_missing_parameters(self):
        """测试缺少参数"""
        cypher = "MATCH (p:Problem) WHERE p.name = $name RETURN p.name"
        parameters = {}  # 缺少 name 参数
        
        result = self.validator.validate(cypher, parameters)
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_type, ErrorType.PARAMETER)
        self.assertIn("Missing parameters", result.error_message)
    
    def test_unused_parameters(self):
        """测试多余参数（应该只是警告）"""
        cypher = "MATCH (p:Problem) RETURN p.name"
        parameters = {"unused": "value"}
        
        result = self.validator.validate(cypher, parameters)
        
        self.assertTrue(result.is_valid)  # 应该仍然有效
        self.assertTrue(len(result.warnings) > 0)  # 但有警告
        self.assertIn("Unused", result.warnings[0])
    
    def test_complexity_calculation(self):
        """测试复杂度计算"""
        # 简单查询
        simple_cypher = "MATCH (p:Problem) RETURN p.name LIMIT 10"
        result = self.validator.validate(simple_cypher)
        self.assertTrue(result.is_valid)
        self.assertTrue(result.complexity_score <= 3)
        
        # 复杂查询
        complex_cypher = """
        MATCH (p:Problem)-[:HAS_TAG]->(t:Tag)
        OPTIONAL MATCH (p)-[:HAS_SOLUTION]->(s:Solution)
        WHERE p.rating > 1500 AND t.name = $tag
        WITH p, count(s) as solution_count
        ORDER BY p.rating DESC
        RETURN p.name, p.rating, solution_count
        """
        result = self.validator.validate(complex_cypher, {"tag": "dp"})
        self.assertTrue(result.is_valid)
        self.assertTrue(result.complexity_score > 3)
    
    def test_query_without_return(self):
        """测试没有 RETURN 的查询"""
        cypher = "MATCH (p:Problem) WHERE p.name = $name"
        
        result = self.validator.validate(cypher, {"name": "test"})
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_type, ErrorType.SYNTAX)
        self.assertIn("RETURN", result.error_message)
    
    def test_apoc_call_blocked(self):
        """测试 APOC 调用被阻止"""
        cypher = "CALL apoc.periodic.iterate() RETURN 1"
        
        result = self.validator.validate(cypher)
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_type, ErrorType.SECURITY)
        self.assertIn("apoc", result.error_message.lower())


if __name__ == '__main__':
    unittest.main()