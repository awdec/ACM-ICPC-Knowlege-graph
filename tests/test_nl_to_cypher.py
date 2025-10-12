# tests/test_nl_to_cypher.py
"""
自然语言意图识别模块单元测试
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from nl_to_cypher import parse_intent, get_cypher_and_params, INTENT_PATTERNS, CYPHER_TEMPLATES


class TestNLToCypher(unittest.TestCase):
    """测试自然语言转Cypher查询功能"""
    
    def test_parse_intent_problem_difficulty(self):
        """测试题目难度查询意图识别"""
        test_cases = [
            "题目'两数之和'的难度",
            "题目 二叉树遍历 的难度",
            "问题最长公共子序列的rating",
            "problem 'Dijkstra' 的难度",
        ]
        
        for question in test_cases:
            with self.subTest(question=question):
                result = parse_intent(question)
                self.assertEqual(result['intent'], 'get_problem_difficulty')
                self.assertIn('problem', result['slots'])
                self.assertNotEqual(result['slots']['problem'], '')
    
    def test_parse_intent_problems_by_tag(self):
        """测试按标签查询题目意图识别"""
        test_cases = [
            "有哪些关于动态规划的题目",
            "列出涉及图论的题目",
            "给我含有贪心的题目",
        ]
        
        for question in test_cases:
            with self.subTest(question=question):
                result = parse_intent(question)
                self.assertEqual(result['intent'], 'list_problems_by_tag')
                self.assertIn('tag', result['slots'])
    
    def test_parse_intent_contest_winner(self):
        """测试竞赛冠军查询意图识别"""
        test_cases = [
            "谁是2020年冠军",
            "2021ICPC第一名",
            "世界总决赛冠军",
        ]
        
        for question in test_cases:
            with self.subTest(question=question):
                result = parse_intent(question)
                self.assertEqual(result['intent'], 'get_contest_winner')
                self.assertIn('year_or_name', result['slots'])
    
    def test_parse_intent_solutions_by_author(self):
        """测试作者题解查询意图识别"""
        test_cases = [
            "作者张三的题解",
            "由李四写的题解",
        ]
        
        for question in test_cases:
            with self.subTest(question=question):
                result = parse_intent(question)
                self.assertEqual(result['intent'], 'get_solutions_by_author')
                self.assertIn('author', result['slots'])
    
    def test_parse_intent_algorithm_problems(self):
        """测试算法题目查询意图识别"""
        test_cases = [
            "使用Dijkstra算法的题目",
            "用到动态规划的题目",
            "涉及BFS算法",
        ]
        
        for question in test_cases:
            with self.subTest(question=question):
                result = parse_intent(question)
                self.assertEqual(result['intent'], 'find_problems_using_algorithm')
                self.assertIn('algo', result['slots'])
    
    def test_parse_intent_problem_info(self):
        """测试题目信息查询意图识别"""
        test_cases = [
            "题目'最长路径'的信息",
            "problem 快速排序 的详情",
            "题目二分查找是什么",
        ]
        
        for question in test_cases:
            with self.subTest(question=question):
                result = parse_intent(question)
                self.assertEqual(result['intent'], 'get_problem_info')
                self.assertIn('problem', result['slots'])
    
    def test_parse_intent_unknown(self):
        """测试未知意图处理"""
        test_cases = [
            "今天天气怎么样",
            "你好",
            "随机文本",
        ]
        
        for question in test_cases:
            with self.subTest(question=question):
                result = parse_intent(question)
                self.assertEqual(result['intent'], 'unknown')
                self.assertEqual(result['slots'], {})
    
    def test_get_cypher_and_params(self):
        """测试Cypher查询生成"""
        intent_data = {
            'intent': 'get_problem_difficulty',
            'slots': {'problem': '两数之和'}
        }
        
        cypher, params = get_cypher_and_params(intent_data)
        
        self.assertIn('MATCH (p:Problem)', cypher)
        self.assertIn('$problem', cypher)
        self.assertEqual(params['problem'], '两数之和')
    
    def test_all_intents_have_templates(self):
        """测试所有意图都有对应的Cypher模板"""
        intent_names = [pattern[0] for pattern in INTENT_PATTERNS]
        
        for intent in intent_names:
            with self.subTest(intent=intent):
                self.assertIn(intent, CYPHER_TEMPLATES)
    
    def test_cypher_templates_valid_syntax(self):
        """测试Cypher模板语法基本正确性"""
        for intent, template in CYPHER_TEMPLATES.items():
            with self.subTest(intent=intent):
                # 基本语法检查
                self.assertIn('MATCH', template.upper())
                self.assertIn('RETURN', template.upper())
                # 参数化查询检查
                if '$' in template:
                    self.assertTrue(any('$' in template for template in [template]))


if __name__ == '__main__':
    unittest.main(verbosity=2)