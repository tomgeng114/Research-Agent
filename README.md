# Research-Agent

> 基于多智能体协作的 AI 研究系统——输入主题，自动完成规划、搜索、写作，输出结构化研究报告。

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Demo

![Home](home.png)

## 核心能力

- **多智能体协作** — Planner、Researcher、Writer 三个 Agent 分工协作，通过强类型管道传递数据
- **真实联网搜索** — 集成 [Tavily Search API](https://tavily.com)，获取实时网页结果并附来源链接；网络不可用时自动降级为 LLM 知识库搜索
- **SSE 流式输出** — 浏览器端实时展示进度：制定计划 → 收集信息 → 撰写报告 → 完成
- **长期记忆** — SQLite 持久化每次研究，支持关键词检索；新研究自动注入相关历史上下文
- **标准 Tool Calling** — Agent 通过 OpenAI 兼容的 function calling 协议调用工具，可扩展
- **开箱即用的 Web 界面** — 原生 HTML/CSS/JS + marked.js，无需前端构建

## 系统架构

```
用户输入主题
       │
       ▼
┌─────────────────┐
│  PlannerAgent    │  分析主题，拆分为 3-5 个研究步骤
│  (LLM 驱动)      │  输出: [{step, title, query, focus_areas}, ...]
└────────┬────────┘
         │ 研究计划
         ▼
┌─────────────────┐
│ ResearcherAgent  │  逐步骤调用搜索工具收集信息
│  (工具调用者)     │  ┌──────────────────────────┐
│                  │  │ WebSearchTool             │
│                  │  │  ├─ Tavily API (优先)      │
│                  │  │  └─ LLM 兜底              │
│                  │  └──────────────────────────┘
└────────┬────────┘  输出: [{step, findings, raw_content}, ...]
         │ 研究笔记
         ▼
┌─────────────────┐
│  WriterAgent     │  汇总所有研究结果，生成结构化 Markdown 报告
│  (LLM 驱动)      │  输出: 完整报告文本
└────────┬────────┘
         │ 报告
         ▼
┌─────────────────┐     ┌──────────────────┐
│   ReportTool     │     │  MemoryManager    │
│   保存到磁盘      │     │  SQLite 持久化    │
└─────────────────┘     └──────────────────┘
```

## 技术栈

| 层级 | 技术 |
|------|------|
| Web 框架 | FastAPI (async) |
| 大模型 | DeepSeek / OpenAI（通过环境变量切换） |
| 真实搜索 | Tavily Search API |
| 流式传输 | Server-Sent Events (SSE) |
| 数据库 | SQLite |
| 前端 | HTML/CSS/JS + marked.js |
| Python | 3.10+ |

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/tomgeng114/Research-Agent.git
cd Research-Agent

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DeepSeek 和 Tavily 的 Key

# 4. 初始化数据库
python init_db.py

# 5. 启动服务
uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8001

# 6. 打开浏览器
# http://127.0.0.1:8001
```

## API

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/` | Web 前端界面 |
| `GET` | `/api/research/stream?topic=...&max_steps=4` | SSE 流式研究 |
| `POST` | `/api/research` | 同步研究（返回 JSON） |
| `GET` | `/api/history` | 历史记录列表 |
| `GET` | `/api/research/{id}` | 查看研究详情 |
| `DELETE` | `/api/research/{id}` | 删除研究记录 |
| `GET` | `/health` | 健康检查 |

### 流式研究调用示例

```bash
curl -N "http://127.0.0.1:8001/api/research/stream?topic=AI%20Agent%20发展趋势&max_steps=3"
```

SSE 事件流：

```
data: {"phase":"planning","message":"正在分析研究主题，生成研究计划..."}
data: {"phase":"plan_done","plan":[...]}
data: {"phase":"researching","message":"正在执行第 1/3 步: ..."}
data: {"phase":"step_done","step":{...}}
data: {"phase":"writing","message":"正在撰写研究报告..."}
data: {"phase":"done","result":{"report":"...","id":1}}
```

## 项目结构

```
Research-Agent/
├── app/
│   ├── agents/
│   │   ├── base_agent.py          # Agent 基类：LLM 客户端 + 工具注册
│   │   ├── planner_agent.py       # 规划 Agent：拆分研究步骤
│   │   ├── researcher_agent.py    # 研究 Agent：调用工具收集信息
│   │   └── writer_agent.py        # 写作 Agent：生成报告
│   ├── tools/
│   │   ├── base_tool.py           # 工具抽象基类 (name/desc/params/run)
│   │   ├── web_search_tool.py     # 搜索工具：Tavily API + LLM 兜底
│   │   └── report_tool.py         # 报告工具：保存 Markdown 文件
│   ├── memory/
│   │   └── memory_manager.py      # 记忆管理：SQLite CRUD + 历史检索
│   ├── api/
│   │   └── routes.py              # API 路由：SSE 流式 + REST 端点
│   ├── config.py                  # 配置中心（环境变量驱动）
│   └── main.py                    # FastAPI 应用 + Web 前端页面
├── tests/
│   └── test_agents.py             # 13 个单元测试
├── reports/                       # 生成的报告（自动创建）
├── .env.example                   # 配置文件模板
├── init_db.py                     # 数据库初始化脚本
├── start.bat                      # Windows 一键启动
└── requirements.txt
```

## 设计思路

### 为什么用多智能体？

单次 LLM 调用处理长篇研究时容易跳过步骤、产生幻觉或输出浮于表面。拆成三个专职 Agent 迫使结构化推理：

- **Planner** 被约束为只输出 JSON 计划，无法直接跳跃到结论
- **Researcher** 逐步骤执行，每次只处理一个问题，产出扎实的笔记
- **Writer** 只看到整理好的研究素材，不接触原始计划，确保综合而非照搬

### 为什么 Tavily + LLM 双路？

真实搜索提供时效性强的可验证信息，附带来源 URL。但 API 可能出问题——限流、网络故障、Key 未配置。双路设计确保系统永远可用：

```
WebSearchTool.run()
  ├─ Tavily API  → 返回带 URL 的真实搜索结果
  └─ LLM 兜底    → 返回基于模型知识的搜索结果
```

### 为什么用 SSE 而不是 WebSocket？

SSE 是单向的（服务端 → 客户端），恰好匹配研究管道的特性。无需管理双向状态，实现简单，浏览器原生支持（EventSource）。

## 未来规划

- [ ] **CrewAI 集成** — 用 CrewAI 替换手写编排，支持更复杂的多智能体拓扑
- [ ] **工具扩展** — ArXiv 论文搜索、GitHub 代码搜索、PDF 文档解析
- [ ] **报告模板** — 学术论文、商业分析、技术深潜等多种预设格式
- [ ] **WebSocket 模式** — 支持交互式研究，可在中途修正研究方向
- [ ] **向量记忆** — 用 Embedding 相似度检索替代关键词匹配
- [ ] **Docker 部署** — 一条命令 `docker compose up` 启动

## License

MIT
