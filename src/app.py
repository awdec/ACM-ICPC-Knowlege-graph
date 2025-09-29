# src/app.py
import streamlit as st
from nl_to_cypher import parse_intent, get_cypher_and_params
from neo4j_helper import Neo4jHelper
from answer_renderer import render_answer
import os

st.set_page_config(page_title="ACM KG 问答 Demo", layout="wide")
st.title("ACM/ICPC KG 智能问答（课程演示）")

# Neo4j 连接配置（可以用环境变量覆盖）
NEO_URI = os.getenv("NEO_URI", "bolt://localhost:7687")
NEO_USER = os.getenv("NEO_USER", "neo4j")
NEO_PWD = os.getenv("NEO_PWD", "luogu20201208")

nh = Neo4jHelper(uri=NEO_URI, user=NEO_USER, pwd=NEO_PWD)

q = st.text_input("请输入问题（中文）", "")
if st.button("查询"):
    parsed = parse_intent(q)
    intent = parsed['intent']
    slots = parsed['slots']
    if intent == "unknown":
        st.warning("未识别意图，请换种表述或使用示例问题。")
    else:
        cypher, params = get_cypher_and_params(parsed)
        st.subheader("解析结果")
        st.write("意图：", intent)
        st.write("槽位：", slots)
        st.subheader("执行 Cypher（带参数）")
        st.code(cypher)
        st.write("params:", params)

        try:
            rows = nh.run_query(cypher, params)
            st.subheader("原始结果（前 50 条）")
            st.write(rows[:50])
            st.subheader("生成的答案")
            st.text(render_answer(intent, rows))
        except Exception as e:
            st.error(f"查询出错：{e}")

# 关闭连接（Streamlit 运行时可忽略）
# nh.close()
