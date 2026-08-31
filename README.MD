一、整体架构

                         ┌──────────────────────┐
                         │       Clients        │
                         │                      │
                         │ CLI / Web / Desktop  │
                         │ Mobile / Bot / IDE   │
                         └──────────┬───────────┘
                                    │
                              HTTP / WS / SSE
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    Agent Gateway     │
                         │                      │
                         │ Auth                 │
                         │ Session              │
                         │ Streaming            │
                         │ Request Routing      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                 ┌────────────────────────────────────┐
                 │          Agent Runtime             │
                 │                                    │
                 │  ┌──────────┐    ┌─────────────┐   │
                 │  │ Planner  │───>│ Agent Loop  │   │
                 │  └──────────┘    └──────┬──────┘   │
                 │                         │          │
                 │      ┌──────────────────┼──────┐   │
                 │      ↓                  ↓      ↓   │
                 │   Memory              Tools   RAG  │
                 │                                    │
                 │              LangGraph             │
                 └──────────────┬─────────────┬───────┘
                                │             │
                 ┌──────────────┘             └──────────────┐
                 ▼                                           ▼
        ┌─────────────────┐                         ┌─────────────────┐
        │   Model Layer   │                         │   Data Layer    │
        │                 │                         │                 │
        │ OpenAI          │                         │ PostgreSQL      │
        │ Claude          │                         │ pgvector        │
        │ DeepSeek        │                         │ Redis           │
        │ Qwen            │                         │ File Storage    │
        │ Ollama          │                         │                 │
        └─────────────────┘                         └─────────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │    Tool Runtime     │
                     │                     │
                     │ Python              │
                     │ Shell               │
                     │ Filesystem          │
                     │ Browser             │
                     │ Web Search          │
                     │ Git                 │
                     │ Trading API         │
                     └─────────────────────┘

二、最终RoadMap
                  TARGET ARCHITECTURE
                         │
                         │
        ┌────────────────┴────────────────┐
        │                                 │
   Agent Runtime                     Infrastructure
        │                                 │
 ┌──────┼────────┐                ┌───────┼────────┐
 ↓      ↓        ↓                ↓       ↓        ↓
LLM   Memory    Tools          PostgreSQL Redis   Storage
 │      │        │
 └──────┴────────┘
          │
       LangGraph
          │
          ↓
      Agent Core
          │
          ↓
      Gateway
          │
          ↓
   Web / CLI / Mobile


IMPLEMENTATION ROADMAP

V0
Agent + LLM + Tools
       ↓
V0.5
Memory + PostgreSQL
       ↓
V0.6
RAG + pgvector
       ↓
V1
完整 Tool System
       ↓
V1.5
Redis + Celery
       ↓
V2
Django + DRF Gateway
       ↓
V3
Web / Desktop / Mobile
       ↓
V4
Multi-Agent / Distributed

请求怎么从浏览器走到模型、LangGraph 每个节点做什么：见 `docs/请求流程.md`。

三、V0 怎么跑

范围：Python + LangGraph + OpenAI-compatible LLM + 3 个 Tools + PostgreSQL。
  对应目录：

  clients/web     → Clients
  gateway/        → Agent Gateway（FastAPI 临时；V2 换成 Django）
  runtime/        → Agent Runtime（LangGraph Loop + Memory 装配）
  model/          → Model Layer
  data/           → Data Layer（会话 + memories 表）
  tools/          → Tool Runtime（外部工具 + remember / recall / forget）

1. 启动 Postgres

  需要本机有 Docker Desktop，然后：

    docker compose up -d

  如果没有 Docker，也可以自己安装 PostgreSQL 16，创建数据库 `myaiagent`、用户 `agent` / 密码 `agent`，
  或把 `.env` 里的 `DATABASE_URL` 改成你的连接串。

2. 安装并配置

  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  copy .env.example .env

  模型走 OpenAI 兼容协议，本地和云端只改这三项：

    LLM_BASE_URL
    LLM_API_KEY
    LLM_MODEL

  本地（Ollama 跑 OpenAI 公开权重 gpt-oss）：

    ollama pull gpt-oss:20b
    .env:
      LLM_BASE_URL=http://127.0.0.1:11434/v1
      LLM_API_KEY=local
      LLM_MODEL=gpt-oss:20b

  LM Studio 把 Local Server 打开后，端口一般是 1234。
  云端 DeepSeek / OpenAI 则填官方 base_url 和真实 API Key。

  本地模型尽量选支持 tool calling 的（gpt-oss、Qwen2.5、Llama 3.1），V0 的三个工具才调得起来。

3. 启动 Gateway

  python run.py

  打开 http://127.0.0.1:8080

  本地 Hugging Face `transformers serve` 占用 8000，所以 Gateway 用 8080。

四、V0.5 多了什么

范围：在 V0 上加长期记忆。PostgreSQL 新表 `memories`，不碰 pgvector（那是 V0.6）。

三层怎么拆：

  data/memory.py     → 落库（upsert / 关键字检索 / 删除）
  runtime/memory.py  → 每轮把记忆装进 System Prompt
  tools/memory.py    → Agent 用工具主动记、查、忘

短时记忆仍是 `messages`：当前对话最近 N 条。
长期记忆是 `memories`：换对话、删会话都还在。

怎么验证：

  1. 说「记住：我叫阿旺，住在杭州」
  2. 左侧「长期记忆」出现条目
  3. 点「新对话」，问「我住哪？」——不应再问你一次

本轮不包含：RAG / pgvector、Celery、完整 Tool System、多端客户端。

