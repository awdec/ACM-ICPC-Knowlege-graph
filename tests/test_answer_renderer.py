# tests/test_answer_renderer.py
"""
答案渲染模块单元测试
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from answer_renderer import render_answer


class TestAnswerRenderer(unittest.TestCase):
    """测试答案渲染功能"""
    
    def test_render_empty_result(self):
        """测试空结果渲染"""
        result = render_answer('get_problem_difficulty', [])
        self.assertEqual(result, "抱歉，未找到匹配的结果。")
    
    def test_render_problem_difficulty(self):
        """测试题目难度答案渲染"""
        rows = [
            {'name': '两数之和', 'rating': 1200},
            {'name': '二叉树遍历', 'rating': 1500}
        ]
        
        result = render_answer('get_problem_difficulty', rows)
        
        self.assertIn('两数之和', result)
        self.assertIn('1200', result)
        self.assertIn('二叉树遍历', result)
        self.assertIn('1500', result)
        self.assertIn('题目：', result)
        self.assertIn('难度：', result)
    
    def test_render_problem_info(self):
        """测试题目信息答案渲染"""
        rows = [
            {
                'name': '最长公共子序列',
                'rating': 1800,
                'tags': ['动态规划', '字符串'],
                'solutions': ['sol001', 'sol002']
            }
        ]
        
        result = render_answer('get_problem_info', rows)
        
        self.assertIn('最长公共子序列', result)
        self.assertIn('1800', result)
        self.assertIn('动态规划', result)
        self.assertIn('字符串', result)
        self.assertIn('sol001', result)
        self.assertIn('sol002', result)
    
    def test_render_problems_by_tag(self):
        """测试标签题目列表渲染"""
        rows = [
            {'name': '背包问题', 'rating': 1600},
            {'name': '最长递增子序列', 'rating': 1400}
        ]
        
        result = render_answer('list_problems_by_tag', rows)
        
        self.assertIn('匹配题目：', result)
        self.assertIn('背包问题', result)
        self.assertIn('1600', result)
        self.assertIn('最长递增子序列', result)
        self.assertIn('1400', result)
        self.assertIn('-', result)
    
    def test_render_algorithm_problems(self):
        """测试算法题目渲染"""
        rows = [
            {'name': '最短路径', 'rating': 1700},
            {'name': '图的遍历', 'rating': 1300}
        ]
        
        result = render_answer('find_problems_using_algorithm', rows)
        
        self.assertIn('匹配题目：', result)
        self.assertIn('最短路径', result)
        self.assertIn('1700', result)
    
    def test_render_contest_winner(self):
        """测试竞赛冠军答案渲染"""
        rows = [
            {'team': 'MIT队', 'region': '北美', 'rank': '1'},
            {'team': '清华队', 'region': '亚洲', 'rank': '1'}
        ]
        
        result = render_answer('get_contest_winner', rows)
        
        self.assertIn('冠军/第一名：', result)
        self.assertIn('MIT队', result)
        self.assertIn('北美', result)
        self.assertIn('清华队', result)
        self.assertIn('亚洲', result)
    
    def test_render_solutions_by_author(self):
        """测试作者题解答案渲染"""
        rows = [
            {
                'problem': '快速排序',
                'sid': 'sol123',
                'snippet': '这是一个关于快速排序的详细解析...'
            },
            {
                'problem': '二分查找',
                'sid': 'sol456',
                'snippet': '二分查找的时间复杂度为O(log n)...'
            }
        ]
        
        result = render_answer('get_solutions_by_author', rows)
        
        self.assertIn('该作者的题解：', result)
        self.assertIn('快速排序', result)
        self.assertIn('sol123', result)
        self.assertIn('快速排序的详细解析', result)
        self.assertIn('二分查找', result)
        self.assertIn('sol456', result)
    
    def test_render_fallback(self):
        """测试未知意图的后备渲染"""
        rows = [{'data': 'test'}]
        result = render_answer('unknown_intent', rows)
        
        # 应该返回原始数据的字符串形式
        self.assertIn('data', result)
        self.assertIn('test', result)
    
    def test_render_missing_fields(self):
        """测试缺失字段的处理"""
        # 测试缺失rating字段
        rows = [{'name': '测试题目'}]
        result = render_answer('get_problem_difficulty', rows)
        self.assertIn('未知', result)
        
        # 测试缺失tags和solutions字段
        rows = [{'name': '测试题目', 'rating': 1000}]
        result = render_answer('get_problem_info', rows)
        self.assertIn('无', result)
    
    def test_render_none_values(self):
        """测试None值的处理"""
        rows = [
            {
                'name': '测试题目',
                'rating': None,
                'tags': None,
                'solutions': None
            }
        ]
        
        result = render_answer('get_problem_info', rows)
        self.assertIn('测试题目', result)
        self.assertIn('无', result)


if __name__ == '__main__':
    unittest.main(verbosity=2)