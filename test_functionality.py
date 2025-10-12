# test_functionality.py
"""
功能完整性测试脚本
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from nl_to_cypher import parse_intent, get_cypher_and_params
from answer_renderer import render_answer

def test_intent_recognition():
    """测试意图识别功能"""
    print("=== 意图识别功能测试 ===")
    
    test_cases = [
        ("题目'两数之和'的难度", "get_problem_difficulty"),
        ("有哪些关于动态规划的题目", "list_problems_by_tag"), 
        ("谁是2020年冠军", "get_contest_winner"),
        ("作者张三的题解", "get_solutions_by_author"),
        ("使用Dijkstra算法的题目", "find_problems_using_algorithm"),
        ("题目'最长公共子序列'的信息", "get_problem_info"),
        ("今天天气怎么样", "unknown")
    ]
    
    passed = 0
    total = len(test_cases)
    
    for question, expected_intent in test_cases:
        result = parse_intent(question)
        actual_intent = result['intent']
        
        if actual_intent == expected_intent:
            print(f"✓ '{question}' -> {actual_intent}")
            passed += 1
        else:
            print(f"✗ '{question}' -> 期望: {expected_intent}, 实际: {actual_intent}")
    
    print(f"\n意图识别测试结果: {passed}/{total} 通过")
    return passed == total

def test_cypher_generation():
    """测试Cypher查询生成"""
    print("\n=== Cypher查询生成测试 ===")
    
    test_cases = [
        {
            "intent_data": {"intent": "get_problem_difficulty", "slots": {"problem": "两数之和"}},
            "expected_contains": ["MATCH (p:Problem)", "$problem", "RETURN"]
        },
        {
            "intent_data": {"intent": "list_problems_by_tag", "slots": {"tag": "动态规划"}},
            "expected_contains": ["MATCH (p:Problem)-[:HAS_TAG]->(t:Tag)", "$tag"]
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for case in test_cases:
        cypher, params = get_cypher_and_params(case["intent_data"])
        
        all_contains = all(keyword in cypher for keyword in case["expected_contains"])
        
        if all_contains and cypher:
            print(f"✓ {case['intent_data']['intent']} -> Cypher生成成功")
            passed += 1
        else:
            print(f"✗ {case['intent_data']['intent']} -> Cypher生成失败")
            print(f"   生成的查询: {cypher}")
    
    print(f"\nCypher生成测试结果: {passed}/{total} 通过")
    return passed == total

def test_answer_rendering():
    """测试答案渲染功能"""
    print("\n=== 答案渲染功能测试 ===")
    
    test_cases = [
        {
            "intent": "get_problem_difficulty",
            "data": [{"name": "两数之和", "rating": 1200}],
            "expected_contains": ["两数之和", "1200", "题目", "难度"]
        },
        {
            "intent": "list_problems_by_tag", 
            "data": [{"name": "背包问题", "rating": 1600}],
            "expected_contains": ["匹配题目", "背包问题", "1600"]
        },
        {
            "intent": "unknown_intent",
            "data": [],
            "expected_contains": ["未找到", "结果"]
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for case in test_cases:
        answer = render_answer(case["intent"], case["data"])
        
        all_contains = all(keyword in answer for keyword in case["expected_contains"])
        
        if all_contains:
            print(f"✓ {case['intent']} -> 答案渲染成功")
            passed += 1
        else:
            print(f"✗ {case['intent']} -> 答案渲染失败")
            print(f"   生成的答案: {answer}")
    
    print(f"\n答案渲染测试结果: {passed}/{total} 通过")
    return passed == total

def test_end_to_end():
    """端到端功能测试"""
    print("\n=== 端到端功能测试 ===")
    
    question = "题目'快速排序'的难度"
    
    print(f"输入问题: {question}")
    
    # 步骤1: 意图识别
    parsed = parse_intent(question)
    print(f"1. 意图识别: {parsed}")
    
    # 步骤2: 生成Cypher查询
    cypher, params = get_cypher_and_params(parsed)
    print(f"2. Cypher查询: {cypher}")
    print(f"   参数: {params}")
    
    # 步骤3: 模拟数据库结果
    mock_result = [{"name": "快速排序", "rating": 1300}]
    print(f"3. 模拟数据库结果: {mock_result}")
    
    # 步骤4: 答案渲染
    answer = render_answer(parsed['intent'], mock_result)
    print(f"4. 最终答案: {answer}")
    
    # 验证完整流程
    success = (
        parsed['intent'] == 'get_problem_difficulty' and
        '快速排序' in params.get('problem', '') and
        'MATCH (p:Problem)' in cypher and
        '快速排序' in answer and
        '1300' in answer
    )
    
    if success:
        print("✓ 端到端测试通过")
        return True
    else:
        print("✗ 端到端测试失败")
        return False

def main():
    """主测试函数"""
    print("ACM-ICPC知识图谱问答系统 - 功能测试")
    print("=" * 50)
    
    tests = [
        ("意图识别", test_intent_recognition),
        ("Cypher生成", test_cypher_generation), 
        ("答案渲染", test_answer_rendering),
        ("端到端", test_end_to_end)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed_tests += 1
        except Exception as e:
            print(f"✗ {test_name}测试出现异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"总体测试结果: {passed_tests}/{total_tests} 测试模块通过")
    
    if passed_tests == total_tests:
        print("🎉 所有功能测试通过！系统基本功能正常。")
        print("\n后续步骤:")
        print("1. 启动Neo4j数据库服务")
        print("2. 导入ACM-ICPC知识图谱数据") 
        print("3. 运行 streamlit run src/app.py 启动Web应用")
    else:
        print("⚠️ 部分测试失败，请检查相关功能。")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    main()