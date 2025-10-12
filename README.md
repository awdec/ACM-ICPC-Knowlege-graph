# ACM-ICPC 知识图谱智能问答系统

基于 Neo4j 知识图谱和 DeepSeek LLM 的智能问答系统，支持自然语言查询 ACM-ICPC 竞赛相关信息。

## ✨ 核心特性

- 🤖 **智能查询生成**: 集成 DeepSeek LLM，支持自然语言理解
- 📖 **规则引擎**: 保留传统正则匹配，确保系统可靠性
- 🔄 **混合策略**: 根据问题复杂度智能选择生成方式
- 🛡️ **安全验证**: 全面的 Cypher 查询安全检查
- ⚡ **性能优化**: 智能缓存和降级机制
- 📊 **实时监控**: 完整的性能指标和状态反馈

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，设置必要的配置项：
# - NEO4J_URI: Neo4j 数据库地址
# - NEO4J_USER: 数据库用户名
# - NEO4J_PASSWORD: 数据库密码
# - DEEPSEEK_API_KEY: DeepSeek API 密钥（可选）
```

### 3. 启动应用

```bash
cd src
streamlit run app.py
```

浏览器访问 `http://localhost:8501`

## 🎯 支持的查询类型

| 查询类型 | 示例问题 |
|---------|----------|
| 题目难度 | "题目两数之和的难度是多少？" |
| 标签查询 | "有哪些关于动态规划的题目？" |
| 比赛信息 | "谁是2023年ICPC世界冠军？" |
| 题解作者 | "张三写了哪些题解？" |
| 算法查询 | "使用贪心算法的题目有哪些？" |

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户自然语言问题                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              混合策略协调器 (HybridStrategy)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ 复杂度分析    │  │ 策略选择      │  │ 降级机制      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└────────────┬──────────────────────┬─────────────────────┘
             │                      │
    ┌────────▼────────┐    ┌───────▼────────┐
    │  规则匹配引擎    │    │  LLM 生成器     │
    │ (nl_to_cypher)  │    │ (DeepSeek API) │
    └────────┬────────┘    └───────┬────────┘
             │                      │
             └──────────┬───────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   Cypher 验证器        │
            │  - 安全检查            │
            │  - 语法验证            │
            │  - 复杂度评估          │
            └───────────┬───────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   Neo4j 数据库         │
            └───────────┬───────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   结果渲染             │
            └───────────────────────┘
```

## 📦 项目结构

```
ACM-ICPC-Knowlege-graph/
├── src/
│   ├── app.py                    # Streamlit 主应用
│   ├── config/
│   │   └── config_manager.py     # 配置管理器
│   ├── deepseek/
│   │   ├── deepseek_client.py    # DeepSeek API 客户端
│   │   ├── schema_provider.py    # Schema 提供者
│   │   ├── deepseek_cypher.py    # Cypher 生成器
│   │   ├── cypher_validator.py   # 查询验证器
│   │   └── hybrid_strategy.py    # 混合策略
│   ├── neo4j_helper.py           # Neo4j 助手
│   ├── nl_to_cypher.py           # 规则引擎
│   └── answer_renderer.py        # 答案渲染器
├── tests/                        # 测试用例
├── requirements.txt              # 依赖包
├── .env.example                  # 配置模板
├── USAGE_GUIDE.md                # 使用指南
└── PROJECT_SUMMARY.md            # 项目总结
```

## ⚙️ 配置说明

### 查询模式

- **rule**: 仅使用规则匹配（无需 API 密钥）
- **llm**: 仅使用 LLM 生成（需要 API 密钥）
- **hybrid**: 智能混合模式（推荐，自动选择）

### 环境变量

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| NEO4J_URI | Neo4j 连接地址 | bolt://localhost:7687 | 是 |
| NEO4J_USER | 数据库用户名 | neo4j | 是 |
| NEO4J_PASSWORD | 数据库密码 | - | 是 |
| DEEPSEEK_API_KEY | DeepSeek API 密钥 | - | 否* |
| QUERY_MODE | 查询模式 | hybrid | 否 |
| ENABLE_QUERY_CACHE | 启用缓存 | true | 否 |

*仅在使用 LLM 或混合模式时需要

## 🧪 运行测试

```bash
# 运行集成测试
python test_integration.py

# 运行单元测试（如果有 pytest）
pytest tests/ -v
```

## 🛡️ 安全特性

- ✅ 参数化查询防止注入攻击
- ✅ 阻止危险 Cypher 操作（DELETE、CREATE 等）
- ✅ API 密钥安全管理
- ✅ 输入验证和清洗
- ✅ 查询复杂度限制

## 📊 性能优化

- 🚀 Schema 信息缓存
- 🚀 查询结果缓存（可配置 TTL）
- 🚀 智能降级机制
- 🚀 性能指标监控

## 📖 文档

- [使用指南](USAGE_GUIDE.md) - 详细的使用说明
- [项目总结](PROJECT_SUMMARY.md) - 实施总结和技术细节
- [设计文档](设计文档链接) - 系统设计文档

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

[待添加]

## 🙏 致谢

- [DeepSeek](https://www.deepseek.com/) - 提供强大的 LLM API
- [Neo4j](https://neo4j.com/) - 图数据库平台
- [Streamlit](https://streamlit.io/) - Web 应用框架