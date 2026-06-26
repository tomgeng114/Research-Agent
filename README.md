# Research-Agent

> A multi-agent collaborative research system that turns a single topic into a structured report — planning, real web search, and writing, all in one pipeline.

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## Features

- **Multi-Agent Architecture** — Planner, Researcher, and Writer agents collaborate in a typed pipeline, each with a dedicated role
- **Real Web Search (Tavily)** — Not simulated. Integrates [Tavily Search API](https://tavily.com) for live web results with automatic LLM fallback
- **SSE Streaming** — Real-time progress pushed to the browser: planning → researching → writing → done
- **Long-Term Memory (SQLite)** — Every research session is persisted and searchable; historical context enhances future queries
- **Tool-Calling Design** — Agents use OpenAI-compatible function calling to select and invoke tools
- **Clean Web UI** — Built with vanilla HTML/CSS/JS + `marked.js` for instant markdown rendering

## Architecture

```
User Input (topic)
       │
       ▼
┌─────────────────┐
│  PlannerAgent    │  Decomposes topic into sequential research steps
│  (LLM-powered)   │  Output: [{step, title, query, focus_areas}, ...]
└────────┬────────┘
         │ plan
         ▼
┌─────────────────┐
│ ResearcherAgent  │  Executes each step via tool calling
│  (Tool invoker)  │  ┌──────────────────────────┐
│                  │  │ WebSearchTool             │
│                  │  │  ├─ Tavily API (primary)  │
│                  │  │  └─ LLM (fallback)        │
│                  │  └──────────────────────────┘
└────────┬────────┘  Output: [{step, findings, raw_content}, ...]
         │ notes
         ▼
┌─────────────────┐
│  WriterAgent     │  Synthesizes findings into a structured Markdown report
│  (LLM-powered)   │  Output: full report string
└────────┬────────┘
         │ report
         ▼
┌─────────────────┐     ┌──────────────────┐
│   ReportTool     │     │  MemoryManager    │
│   Save to disk   │     │  SQLite persist   │
└─────────────────┘     └──────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (async) |
| LLM | DeepSeek / OpenAI (switchable via env) |
| Real Search | Tavily Search API |
| Streaming | Server-Sent Events (SSE) |
| Database | SQLite |
| Frontend | HTML/CSS/JS + marked.js |
| Python | 3.10+ |

## Quick Start

```bash
# 1. Clone
git clone <repo-url> && cd Research-Agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API keys
cp .env.example .env
# Edit .env — add your DeepSeek and Tavily keys

# 4. Initialize database
python init_db.py

# 5. Start
uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8001

# 6. Open
# http://127.0.0.1:8001
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web UI |
| `GET` | `/api/research/stream?topic=...&max_steps=4` | SSE streaming research |
| `POST` | `/api/research` | Synchronous research (JSON) |
| `GET` | `/api/history` | List past sessions |
| `GET` | `/api/research/{id}` | Get session detail |
| `DELETE` | `/api/research/{id}` | Delete session |
| `GET` | `/health` | Health check |

### Example: Streaming Research

```bash
curl -N "http://127.0.0.1:8001/api/research/stream?topic=AI%20Agent%20trends&max_steps=3"
```

SSE events:
```
data: {"phase":"planning","message":"正在分析研究主题..."}
data: {"phase":"plan_done","plan":[...]}
data: {"phase":"researching","message":"正在执行第 1/3 步: ..."}
data: {"phase":"step_done","step":{...}}
data: {"phase":"writing","message":"正在撰写报告..."}
data: {"phase":"done","result":{"report":"...","id":1}}
```

## Project Structure

```
Research-Agent/
├── app/
│   ├── agents/
│   │   ├── base_agent.py          # Base class: LLM client + tool registry
│   │   ├── planner_agent.py       # Task decomposition agent
│   │   ├── researcher_agent.py    # Information gathering agent
│   │   └── writer_agent.py        # Report synthesis agent
│   ├── tools/
│   │   ├── base_tool.py           # Abstract tool (name/desc/params/run)
│   │   ├── web_search_tool.py     # Tavily API + LLM fallback
│   │   └── report_tool.py         # Markdown file writer
│   ├── memory/
│   │   └── memory_manager.py      # SQLite CRUD + history search
│   ├── api/
│   │   └── routes.py              # SSE stream + REST endpoints
│   ├── config.py                  # Env-based configuration
│   └── main.py                    # FastAPI app + web UI
├── tests/
│   └── test_agents.py             # 13 unit tests
├── reports/                       # Generated reports (auto-created)
├── .env.example                   # Config template
├── init_db.py                     # DB bootstrap script
├── start.bat                      # Windows one-click launcher
└── requirements.txt
```

## Key Design Decisions

### Why Multi-Agent?

A single LLM call struggles with long-form research: it skips steps, hallucinates, or produces shallow output. Splitting into three specialized agents forces structured reasoning:

- **Planner** is constrained to output only a JSON plan, preventing it from jumping to conclusions
- **Researcher** processes one step at a time with real tool calls, producing grounded notes
- **Writer** sees only the compiled research — not the raw plan — ensuring it synthesizes rather than copies

### Why Tavily + LLM Fallback?

Real web search provides current, verifiable information with source URLs. But APIs fail — rate limits, network issues, missing keys. The dual-path design ensures the system always works:

```
WebSearchTool.run()
  ├─ Tavily API  → findings with real URLs + source content
  └─ LLM (catch) → knowledge-grounded findings (no URLs)
```

### Why SSE over WebSocket?

SSE is unidirectional (server → client), which matches the research pipeline perfectly. No bidirectional state to manage, trivial to implement, and natively supported by browsers via `EventSource`.

## Roadmap

- [ ] **CrewAI integration** — Replace hand-rolled agent orchestration with CrewAI for more complex multi-agent topologies
- [ ] **Tool expansion** — ArXiv search, GitHub code search, PDF ingestion
- [ ] **Configurable report templates** — Academic, business, technical deep-dive presets
- [ ] **WebSocket mode** — For interactive research with mid-course correction
- [ ] **Vector memory** — Replace keyword-based history search with embedding similarity
- [ ] **Docker deployment** — Single-command `docker compose up`

## License

MIT
