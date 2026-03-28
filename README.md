# 数据库AI助手 - DBAI-Copilot

**数据库AI助手**（DBAI-Copilot）是一个集成了「竞赛教练智能助手」和「数据库运维智能助手」的多功能智能系统，为数据库管理和技术竞赛提供AI驱动的智能辅助。

## 功能模块

### 1. 竞赛教练 Agent（人工智能应用赛道）
上传比赛需求文件后，系统会用 RAG（检索增强）把文件内容转成可引用的上下文，然后生成：

- 需求解析与功能拆解
- 模块/流程/技术路线方案
- Demo 剧本与评测指标
- 答辩 PPT 大纲
- 风险与对策

### 2. 数据库运维 Agent
提供全面的数据库监控、诊断、优化和AI辅助功能：

- **基础监控层**：实时性能监控（QPS/TPS/CPU/内存/磁盘/连接数）、慢查询管理
- **诊断分析层**：执行计划可视化（DAG图）、SQL指纹聚类、锁等待分析与死锁检测
- **智能优化层**：索引推荐引擎、SQL改写建议、参数调优建议
- **AI对话层**：自然语言问答、智能诊断报告

## 快速启动

### 1. 环境准备
1. 建立虚拟环境（PowerShell）
   - `py -m venv .venv`
   - `\.venv\Scripts\Activate.ps1`

2. 安装依赖
   - `pip install -r requirements.txt`

3. 设置 LLM（两选一）
   - 使用 OpenAI（建议做最简单 Demo）
     - 新增环境变量：`OPENAI_API_KEY`
   - 使用 Ollama（本地离线/较稳定的 Demo）
     - 启动 Ollama，并确认可用模型（例如 `llama3`）

4. 启动 Streamlit
   - `streamlit run streamlit_app.py`

## 界面使用流程

### 竞赛教练 Agent 使用流程
1. 在左侧导航栏选择「竞赛教练」
2. 上传比赛需求（PDF/DOCX/TXT）
3. 点击「建立索引」
4. 选择你要输出的内容类型（方案/功能/ Demo 剧本/评测/答辩等）
5. 在「补充指令」填写你希望的输出深度或限制（例如字数、必做功能）
6. 点击「生成」

### 数据库运维 Agent 使用流程
1. 在左侧导航栏选择「数据库运维Agent」
2. 在侧边栏配置数据库连接信息：
   - 主机：数据库服务器地址（默认：localhost）
   - 端口：数据库端口（默认：3306）
   - 用户名：数据库用户名（默认：root）
   - 密码：数据库密码
   - 数据库：要连接的数据库名
3. 点击「连接数据库」
4. 在各个标签页使用相应功能：
   - **实时监控**：查看数据库性能指标
   - **诊断分析**：分析SQL执行计划
   - **智能优化**：获取索引推荐和参数调优建议
   - **AI对话**：生成诊断报告或提问

## 输入文件格式（竞赛教练 Agent）

- PDF：会尝试逐页抽取文字
- DOCX：会抽取正文文字
- TXT：直接读取

## 系统要求

- Python 3.12+
- MySQL 5.7+（用于数据库运维 Agent）
- 网络连接（用于 LLM API 调用）
- 推荐配置：4GB+内存，2核+CPU

## 默认限制

- 若没有设置可用的 LLM provider（OpenAI/Ollama），系统无法生成文本内容。
- 数据库运维 Agent 需要连接到 MySQL 数据库才能使用完整功能。
- 建议先用 OpenAI API 或 Ollama 跑通 Demo 流程，再考虑离线化。

## 技术栈

- **前端**：Streamlit
- **后端**：Python 3.12
- **数据库连接**：MySQL Connector Python
- **系统监控**：psutil
- **LLM 集成**：LangChain
- **向量数据库**：ChromaDB（用于 RAG 功能）

## 项目结构

```
competition-ai-agent-coach/
├── app/
│   ├── db_agent/          # 数据库运维 Agent 模块
│   │   ├── ai_dialogue/    # AI 对话功能
│   │   ├── core/           # 核心数据库连接
│   │   ├── diagnosis/      # 诊断分析功能
│   │   ├── monitoring/     # 监控功能
│   │   └── optimization/   # 优化功能
│   ├── doc_loader.py       # 文档加载
│   ├── llm.py              # LLM 集成
│   ├── prompts.py          # 提示词模板
│   └── rag.py              # RAG 功能
├── docs/                   # 项目文档
│   ├── 实验实例.md          # 实验实例设计
│   └── 参考文献.md          # 参考文献
├── .env.example            # 环境变量示例
├── config.py               # 配置文件
├── requirements.txt        # 依赖包
└── streamlit_app.py        # 主应用
```

