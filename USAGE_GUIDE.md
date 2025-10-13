# ACM-ICPC 知识图谱智能问答系统使用指南

## 📋 项目概述

本项目是一个基于 Neo4j 知识图谱的智能问答系统，专门用于 ACM-ICPC 竞赛相关信息查询。系统集成了传统规则匹配和 DeepSeek LLM 两种查询生成方式，能够智能地将自然语言问题转换为 Cypher 查询语句。

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置必要的配置
```

### 2. 环境变量配置

在 `.env` 文件中设置以下配置：

```bash
# DeepSeek API 配置（可选，不设置则只使用规则模式）
DEEPSEEK_API_KEY=your_api_key_here

# Neo4j 数据库配置（必需）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# 查询模式配置
QUERY_MODE=hybrid  # rule/llm/hybrid
```

### 3. 启动应用

```bash
# 进入源码目录
cd src

# 启动 Streamlit 应用
streamlit run app.py
```

## 🎯 功能特性

### 查询模式

1. **规则模式 (rule)**: 使用预定义的正则表达式规则匹配
2. **LLM 模式 (llm)**: 使用 DeepSeek API 进行智能查询生成
3. **混合模式 (hybrid)**: 根据问题复杂度智能选择生成方式

### 支持的问题类型

- 题目难度查询："题目两数之和的难度"
- 标签相关题目："有哪些关于动态规划的题目"
- 比赛冠军查询："谁是2023年ICPC冠军"
- 题解作者查询："张三写了哪些题解"
- 算法相关题目："使用贪心算法的题目有哪些"
- 题目详细信息："题目两数之和的信息"

## 🛠️ 系统架构

```
src/
├── app.py                      # Streamlit 主应用
├── config/
│   └── config_manager.py       # 配置管理器
├── deepseek/
│   ├── deepseek_client.py      # DeepSeek API 客户端
│   ├── schema_provider.py      # 图数据库 Schema 提供者
│   ├── deepseek_cypher.py      # LLM Cypher 生成器
│   ├── cypher_validator.py     # Cypher 验证器
│   └── hybrid_strategy.py      # 混合策略协调器
├── neo4j_helper.py             # Neo4j 连接助手
├── nl_to_cypher.py             # 规则匹配引擎
└── answer_renderer.py          # 答案渲染器
```

## ⚙️ 配置说明

### 必需配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| NEO4J_URI | Neo4j 数据库地址 | bolt://localhost:7687 |
| NEO4J_USER | 数据库用户名 | neo4j |
| NEO4J_PASSWORD | 数据库密码 | luogu20201208 |

### 可选配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| DEEPSEEK_API_KEY | DeepSeek API 密钥 | (空) |
| QUERY_MODE | 查询模式 | hybrid |
| COMPLEXITY_THRESHOLD | 复杂度阈值 | 6 |
| ENABLE_QUERY_CACHE | 启用查询缓存 | true |
| MAX_COMPLEXITY_SCORE | 最大复杂度评分 | 8 |

## 🔧 开发说明

### 运行测试

```bash
# 运行集成测试
python test_integration.py

# 运行特定测试模块（如果有 pytest）
pytest tests/test_config_manager.py -v
pytest tests/test_cypher_validator.py -v
pytest tests/test_hybrid_strategy.py -v
```

### 添加新的查询模式

1. 在 `nl_to_cypher.py` 中添加新的正则表达式模式
2. 在 `CYPHER_TEMPLATES` 中添加对应的 Cypher 模板
3. 在 `answer_renderer.py` 中添加对应的答案渲染逻辑

### LLM 提示词优化

修改 `deepseek/deepseek_client.py` 中的 `_get_system_prompt()` 方法来优化系统提示词。

## 🛡️ 安全特性

### Cypher 查询验证

系统会自动验证生成的 Cypher 查询，防止以下危险操作：

- DELETE / DETACH DELETE
- CREATE / MERGE  
- SET / REMOVE
- LOAD CSV
- CALL apoc.* / CALL dbms.*
- DROP / CREATE INDEX

### 参数化查询

所有查询都使用参数化形式，防止注入攻击。

## 📊 性能监控

系统提供以下性能指标监控：

- 查询成功率
- 平均响应时间
- 降级触发率
- 缓存命中率
- 按策略分组的统计信息

## 🔍 故障排除

### 常见问题

1. **LLM 不可用**
   - 检查 DEEPSEEK_API_KEY 是否正确设置
   - 系统会自动降级到规则模式

2. **Neo4j 连接失败**
   - 检查 Neo4j 服务是否运行
   - 验证连接配置是否正确

3. **查询验证失败**
   - 查看详细错误信息
   - 检查生成的 Cypher 语句是否符合安全规则

4. **Schema 加载失败**
   - 确保 Neo4j 数据库包含预期的数据结构
   - 可以手动刷新 Schema 缓存

### 调试模式

设置环境变量开启详细日志：

```bash
LOG_LEVEL=DEBUG
```

## 📈 扩展功能

### 添加新的 LLM 支持

1. 实现新的客户端类，继承相同的接口
2. 在配置中添加新的模型选项
3. 在混合策略中集成新的生成器

### 支持多语言查询

1. 扩展 Schema 描述的多语言支持
2. 添加语言检测和处理逻辑
3. 更新提示词模板

## 📝 更新日志

### v1.0.0
- 实现基本的规则匹配查询生成
- 集成 DeepSeek LLM API
- 添加混合策略支持
- 实现 Cypher 查询验证
- 提供 Streamlit Web 界面

## 🤝 贡献指南

1. Fork 项目仓库
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 📄 许可证

MIT License

Copyright (c) 2024 GC

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## 📞 联系方式

15167095059

15167095059@163.com