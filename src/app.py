# src/app.py
import streamlit as st
import logging
import time
import os
from typing import Optional

# 导入原有模块
from neo4j_helper import Neo4jHelper
from answer_renderer import render_answer

# 导入新的查询生成系统
from config.config_manager import ConfigManager
from deepseek.hybrid_strategy import HybridStrategy
from deepseek.cypher_validator import ValidationResult

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Streamlit 页面配置
st.set_page_config(
    page_title="ACM-ICPC KG 智能问答", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化配置管理器
@st.cache_resource
def initialize_components():
    """Lazy initialization of components"""
    try:
        config_manager = ConfigManager()
        
        # 初始化 Neo4j 连接
        neo4j_config = config_manager.get_neo4j_config()
        neo4j_helper = Neo4jHelper(
            uri=neo4j_config.uri,
            user=neo4j_config.user,
            pwd=neo4j_config.password
        )
        
        # 初始化混合策略
        hybrid_strategy = HybridStrategy()
        
        logger.info(f"Initialized with query mode: {config_manager.get_query_mode()}")
        logger.info(f"LLM available: {config_manager.is_llm_available()}")
        
        return config_manager, neo4j_helper, hybrid_strategy
        
    except Exception as e:
        logger.error(f"Failed to initialize components: {str(e)}")
        st.error(f"初始化失败: {str(e)}")
        st.stop()

# 初始化组件
config_manager, nh, hybrid_strategy = initialize_components()

# 主标题
st.title("🏆 ACM-ICPC 知识图谱智能问答系统")
st.markdown("""
✨ **推荐尝试以下问题类型:**
- “有哪些关于动态规划的题目”
- “题目两数之和的难度”
- “张三写了哪些题解”
- “使用贪心算法的题目有哪些”
""")

# 侧边栏 - 系统状态
with st.sidebar:
    st.header("🔧 系统状态")
    
    # 显示当前查询模式
    query_mode = config_manager.get_query_mode()
    mode_display = {
        "rule": "📜 规则模式",
        "llm": "🤖 AI 模式", 
        "hybrid": "🤝 混合模式"
    }
    st.info(f"当前模式: {mode_display.get(query_mode, query_mode)}")
    
    # LLM 可用性
    llm_available = config_manager.is_llm_available()
    if llm_available:
        st.success("✅ AI 服务已连接")
    else:
        st.warning("⚠️ AI 服务不可用")
    
    st.divider()
    
    # 系统操作
    st.header("⚙️ 系统操作")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 清空缓存"):
            hybrid_strategy.clear_cache()
            st.success("缓存已清空")
    
    with col2:
        if st.button("🔄 刷新Schema"):
            hybrid_strategy.refresh_schema()
            st.success("Schema已刷新")
    
    # 显示性能指标
    st.header("📊 性能指标")
    try:
        metrics = hybrid_strategy.get_metrics_summary(last_n=10)
        if metrics.get("total", 0) > 0:
            st.metric("成功率", f"{metrics['success_rate']:.1%}")
            st.metric("平均响应时间", f"{metrics['avg_response_time']:.0f}ms")
            if metrics.get("fallback_rate", 0) > 0:
                st.metric("降级率", f"{metrics['fallback_rate']:.1%}")
    except Exception as e:
        st.write("暂无数据")

# 主查询界面
st.header("💬 请输入您的问题")

# 创建两列布局
col1, col2 = st.columns([4, 1])

with col1:
    q = st.text_input(
        "问题", 
        placeholder="例如：有哪些关于动态规划的题目？",
        label_visibility="collapsed"
    )

with col2:
    query_button = st.button("🔍 查询", type="primary", use_container_width=True)

# 查询处理
if query_button and q.strip():
    with st.spinner("🤔 正在分析您的问题..."):
        start_time = time.time()
        
        try:
            # 使用混合策略生成查询
            query_result = hybrid_strategy.generate_query(q.strip())
            
            # 显示生成信息
            st.success(f"✅ 查询生成成功 （{query_result.generation_time:.0f}ms）")
            
            # 显示查询详情
            with st.expander("🔍 查询详情", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**生成来源:**", {
                        "rule": "📜 规则匹配",
                        "llm": "🤖 AI 生成",
                        "hybrid": "🤝 混合模式"
                    }.get(query_result.source, query_result.source))
                    
                    if query_result.intent:
                        st.write("**查询意图:**", query_result.intent)
                    
                    if query_result.confidence > 0:
                        st.write("**置信度:**", f"{query_result.confidence:.1%}")
                
                with col2:
                    # 显示验证结果
                    validation = query_result.metadata.get("validation")
                    if validation:
                        if validation.is_valid:
                            st.success("✅ 查询验证通过")
                            if validation.complexity_score > 0:
                                st.write(f"**复杂度评分:** {validation.complexity_score}/10")
                        else:
                            st.error(f"❌ 验证失败: {validation.error_message}")
                        
                        if validation.warnings:
                            st.warning("\n".join([f"⚠️ {w}" for w in validation.warnings]))
                    
                    # 显示特殊标记
                    flags = query_result.metadata.get("flags", [])
                    if "fallback" in flags:
                        st.info("🔄 已触发降级机制")
                    
                    if query_result.metadata.get("from_cache"):
                        st.info("💾 从缓存获取")
                
                # 显示生成的 Cypher 查询
                st.write("**生成的 Cypher 查询:**")
                st.code(query_result.cypher, language="cypher")
                
                if query_result.parameters:
                    st.write("**查询参数:**")
                    st.json(query_result.parameters)
            
            # 执行查询
            validation = query_result.metadata.get("validation")
            if not validation or validation.is_valid:
                with st.spinner("📊 正在执行查询..."):
                    try:
                        rows = nh.run_query(query_result.cypher, query_result.parameters)
                        
                        if rows:
                            st.subheader("📊 查询结果")
                            
                            # 显示结果数量
                            st.info(f"共找到 {len(rows)} 条结果")
                            
                            # 显示原始数据（可折叠）
                            with st.expander("📋 原始数据（前50条）", expanded=False):
                                st.dataframe(rows[:50], use_container_width=True)
                            
                            # 生成并显示答案
                            st.subheader("📝 智能答案")
                            intent_for_render = query_result.intent or "general"
                            answer = render_answer(intent_for_render, rows)
                            st.markdown(answer)
                            
                        else:
                            st.warning("🔍 未找到相关结果，请尝试调整问题表述。")
                    
                    except Exception as e:
                        st.error(f"❌ 数据库查询错误: {str(e)}")
                        logger.error(f"Database query error: {str(e)}")
            else:
                st.error("❌ 查询验证失败，无法执行。请尝试重新表述问题。")
        
        except Exception as e:
            st.error(f"❌ 查询生成失败: {str(e)}")
            logger.error(f"Query generation error: {str(e)}")
        
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"Query processing completed in {elapsed_time:.2f}s")

elif query_button and not q.strip():
    st.warning("⚠️ 请输入问题后再查询")

# 示例问题
if not q:
    st.subheader("💡 示例问题")
    
    example_questions = [
        "有哪些关于动态规划的题目？",
        "题目两数之和的难度是多少？",
        "张三写了哪些题解？",
        "使用贪心算法的题目有哪些？",
        "谁是2023年ICPC世界冠军？"
    ]
    
    cols = st.columns(2)
    for i, example in enumerate(example_questions):
        with cols[i % 2]:
            if st.button(f"📋 {example}", key=f"example_{i}"):
                st.rerun()
