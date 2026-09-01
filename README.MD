一、整体架构

```text
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
```

二、最终RoadMap

```text
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
```

IMPLEMENTATION ROADMAP

```text
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
完整 Tool System(简易沙箱)
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
```

请求怎么从浏览器走到模型、LangGraph 每个节点做什么：见 `系统文档.md`。

三、V0 怎么跑

范围：Python + LangGraph + OpenAI-compatible LLM + 3 个 Tools + PostgreSQL。
  对应目录：

  clients/web     → Clients
  gateway/        → Agent Gateway（FastAPI 临时；V2 换成 Django）
  runtime/        → Agent Runtime（LangGraph Loop + Memory 装配）
  model/          → Model Layer
  data/           → Data Layer（会话 + memories 表）
  tools/          → Tool Runtime（外部工具 + remember / recall / forget）

1. 启动 Postgres（Docker + pgvector）
  安装 Docker Desktop，然后在项目根目录：
    docker compose up -d
  容器内是 PostgreSQL 16 + vector 扩展。本机 Windows 若已装 PG 18，5432 已被占用，
  所以映射到 **5433**。`.env` 里保持：
    PG_HOST=127.0.0.1
    PG_PORT=5433
    PG_USER=agent
    PG_PASSWORD=@Root123456
    PG_DATABASE=private_agent
  第一次启动会建空库；Gateway 起来后会自动建表并灌入 `docs/knowledge`。
2. 安装并配置
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  copy .env.example .env
  模型走 OpenAI 兼容协议，本地和云端只改这三项：
    LLM_BASE_URL
    LLM_API_KEY
    LLM_MODEL
  本地（Ollama 跑 OpenAI 公开权重 gpt-oss）：
    ollama pull gpt-oss:20b
    .env:
      LLM_BASE_URL=[http://127.0.0.1:11434/v1](http://127.0.0.1:11434/v1)
      LLM_API_KEY=local
      LLM_MODEL=gpt-oss:20b
  LM Studio 把 Local Server 打开后，端口一般是 1234。
  云端 DeepSeek / OpenAI 则填官方 base_url 和真实 API Key。
  本地模型尽量选支持 tool calling 的（gpt-oss、Qwen2.5、Llama 3.1），V0 的三个工具才调得起来。
3. 启动 Gateway
  python run.py
  打开 [http://127.0.0.1:8080](http://127.0.0.1:8080)
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

本轮相对 V0：长期记忆。V0.6 才是 RAG。

五、V0.6 多了什么

范围：私有文档 RAG。切块 → 向量 → 按问题检索 → 塞进 Prompt。

不要和 V0.5 的 memories 混：
  memories     → 用户是谁（姓名、城市）
  documents    → 资料里写了什么（手册、笔记）

本机 Windows PostgreSQL 18 通常没有 vector 扩展。V0.6 推荐用 Docker：`pgvector/pgvector:pg16`，宿主机端口 **5433**。
向量列用 pgvector 的 `vector` 类型，检索用余弦距离 `<=>`。

对应文件：

  model/embed.py     → 本机 bge-small-zh，或 OpenAI 兼容 /v1/embeddings
  data/rag.py        → documents / doc_chunks、切块、入库、检索
  runtime/rag.py     → 每轮把命中片段装进 System Prompt
  tools/rag.py       → search_docs / ingest_doc
  docs/knowledge/    → 启动时空库时自动灌进去的示例手册

怎么验证：

1. 打开 [http://127.0.0.1:8080](http://127.0.0.1:8080) ，左侧应出现《内部手册》
2. 新对话问「知识库里的暗号是什么？不要搜网。」
3. 应答「落叶归根」，且不应去 search_web

可选：.env 里配 EMBEDDING_BASE_URL 走云端 embedding；留空则本机下载 BAAI/bge-small-zh-v1.5（第一次较慢）。

六、V1 多了什么

范围：完整 Tool System。不是再堆几个 @tool，而是先有注册表，再按 README 的 Tool Runtime 补齐组。

  tools/registry.py  → 分组登记，ALL_TOOLS 从这里拼；Graph 不要手写工具列表
  tools/sandbox.py   → 路径必须落在 sandbox/
  新增组：
    文件  list_dir / read_file / write_file / delete_file
    代码  execute_shell（Python 原本就有）
    Git   git_init / git_status / git_log / git_diff / git_commit
  未做：Trading API（要独立密钥，不进 V1）

怎么验证：

1. 页面副标题为 V1，状态行显示工具数量
2. 「写 hello-v1.txt 再 list_dir」→ 侧栏工具块出现 write_file / list_dir
3. sandbox/ 里能看到该文件
4. 「git_init 然后 git_status」→ 需要本机已安装 Git

V1.5 才是 Redis + Celery，本轮没有任务队列。