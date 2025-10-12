# src/app_demo.py
# 演示版本 - 无需真实Neo4j数据库连接
import streamlit as st
from nl_to_cypher import parse_intent, get_cypher_and_params
from answer_renderer import render_answer

st.set_page_config(page_title="ACM KG 问答 Demo", layout="wide")
st.title("ACM/ICPC KG 智能问答（演示版本）")

st.info("💡 这是演示版本，使用模拟数据展示系统功能。完整版本需要连接Neo4j数据库。")

# 示例问题
st.sidebar.header("示例问题")
example_questions = [
    "题目'两数之和'的难度",
    "有哪些关于动态规划的题目", 
    "谁是2020年冠军",
    "作者张三的题解",
    "使用Dijkstra算法的题目",
    "题目'最长公共子序列'的信息"
]

for i, question in enumerate(example_questions):
    if st.sidebar.button(f"示例{i+1}: {question}", key=f"example_{i}"):
        st.session_state.question = question

# 获取用户输入
if 'question' not in st.session_state:
    st.session_state.question = ""

q = st.text_input("请输入问题（中文）", value=st.session_state.question)

if st.button("查询") and q:
    # 意图解析
    parsed = parse_intent(q)
    intent = parsed['intent']
    slots = parsed['slots']
    
    if intent == "unknown":
        st.warning("未识别意图，请换种表述或使用示例问题。")
    else:
        # 显示解析结果
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 解析结果")
            st.write("**意图类型:**", intent)
            st.write("**提取的槽位:**", slots)
        
        with col2:
            st.subheader("🔍 生成的查询")
            cypher, params = get_cypher_and_params(parsed)
            st.code(cypher, language="cypher")
            st.write("**查询参数:**", params)
        
        # 模拟数据库结果
        st.subheader("💾 模拟数据库结果")
        
        # 根据不同意图生成不同的模拟数据
        mock_data = []
        if intent == "get_problem_difficulty":
            problem_name = slots.get('problem', '示例题目')
            mock_data = [{"name": problem_name, "rating": 1400}]
        
        elif intent == "list_problems_by_tag":
            tag_name = slots.get('tag', '算法')
            mock_data = [
                {"name": f"关于{tag_name}的题目1", "rating": 1200},
                {"name": f"关于{tag_name}的题目2", "rating": 1500},
                {"name": f"关于{tag_name}的题目3", "rating": 1800}
            ]
        
        elif intent == "get_contest_winner":
            year_or_name = slots.get('year_or_name', '2020')
            mock_data = [{"team": f"{year_or_name}年冠军队", "region": "亚洲", "rank": "1"}]
        
        elif intent == "get_solutions_by_author":
            author = slots.get('author', '张三')
            mock_data = [
                {"problem": "快速排序", "sid": "sol001", "snippet": f"这是{author}写的快速排序解法..."},
                {"problem": "二分查找", "sid": "sol002", "snippet": f"这是{author}写的二分查找解法..."}
            ]
        
        elif intent == "find_problems_using_algorithm":
            algo = slots.get('algo', 'Dijkstra')
            mock_data = [
                {"name": f"使用{algo}的题目1", "rating": 1600},
                {"name": f"使用{algo}的题目2", "rating": 1900}
            ]
        
        elif intent == "get_problem_info":
            problem = slots.get('problem', '示例题目')
            mock_data = [{
                "name": problem,
                "rating": 1500,
                "tags": ["动态规划", "字符串"],
                "solutions": ["sol001", "sol002", "sol003"]
            }]
        
        st.json(mock_data)
        
        # 生成最终答案
        st.subheader("✨ 生成的答案")
        answer = render_answer(intent, mock_data)
        st.success(answer)
        
        # 系统信息
        with st.expander("🔧 系统信息"):
            st.write("**支持的查询类型:**")
            st.write("- 题目难度查询")
            st.write("- 按标签查询题目")
            st.write("- 竞赛冠军查询")
            st.write("- 作者题解查询")
            st.write("- 算法题目查询")
            st.write("- 题目详细信息查询")
            
            st.write("**技术栈:**")
            st.write("- Streamlit (Web界面)")
            st.write("- Neo4j (图数据库)")
            st.write("- Python正则表达式 (意图识别)")

# 页脚
st.markdown("---")
st.markdown("**ACM-ICPC知识图谱问答系统** | 基于设计文档实现")