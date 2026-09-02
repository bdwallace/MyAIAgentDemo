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
  gateway/        → Agent Gateway（V2 起 Django + DRF；ASGI 跑 SSE）
  runtime/        → Agent Runtime（LangGraph Loop + Memory 装配）
  model/          → Model Layer
  data/           → Data Layer（会话 + memories 表）
  tools/          → Tool Runtime（外部工具 + remember / recall / forget）

1. 启动 Docker（Postgres + Redis + 沙箱容器）
  安装 Docker Desktop，然后在项目根目录：
    docker compose up -d
  容器内是 PostgreSQL 16 + vector 扩展，以及 Redis 7。本机 Windows 若已装 PG 18，5432 已被占用，
  所以 Postgres 映射到 **5433**，Redis 映射 **6379**。`.env` 里保持：
    PG_HOST=127.0.0.1
    PG_PORT=5433
    PG_USER=agent
    PG_PASSWORD=@Root123456
    PG_DATABASE=private_agent
    REDIS_URL=redis://127.0.0.1:6379/0
  第一次启动会建空库；Gateway 起来后会自动建表并灌入 `docs/knowledge`。
  V1.5 起 Gateway 启动会 ping Redis；文档入库还要另开终端跑 `.\scripts\run_worker.ps1`。
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
  tools/sandbox.py   → 路径牢 + Docker 进程隔离（安全沙箱）
  新增组：
    文件  list_dir / read_file / write_file / delete_file
    代码  execute_shell（Python 原本就有）
    Git   git_init / git_status / git_log / git_diff / git_commit
  未做：Trading API（要独立密钥，不进 V1）

怎么验证：

1. 页面副标题为 V1，状态行显示工具数量
2. 「写 hello-v1.txt 再 list_dir」→ 侧栏工具块出现 write_file / list_dir
3. sandbox/ 里能看到该文件
4. 「git_init 然后 git_status」→ Git 在沙箱容器里跑，不依赖本机是否装 Git

七、V1.5 多了什么

范围：Redis + Celery。聊天 SSE 仍在 Gateway，不把会话搬进 Redis。

  Redis（Docker）     → Celery broker / result backend + RAG 检索短缓存
  Celery worker（本机）→ 文档入库（切块 + 向量化）。Worker 必须跟 Gateway 共用 .venv 和 modelscope 缓存，不要放进 Docker。
  Windows 上 Celery 用 `--pool=solo`（默认 prefork 容易挂）

对应文件：

  docker-compose.yml     → 多了 redis 服务（本机 6379）
  data/cache.py          → ping / RAG epoch / 短 TTL 缓存
  worker/celery_app.py   → Celery 应用
  worker/tasks.py        → ingest_document_task
  worker/jobs.py         → 排队、查进度
  scripts/run_worker.ps1 → 启动 worker

聊天仍走 `POST /api/chat` 流式。入库变成：

  POST /api/documents  → `{ job_id, status: queued }`
  GET  /api/jobs/{id}  → PENDING / STARTED / SUCCESS / FAILURE

怎么跑：

1. `docker compose up -d`（Postgres 5433 + Redis 6379）
2. `.env` 增加：`REDIS_URL=redis://127.0.0.1:6379/0`
3. 另开终端：`.\scripts\run_worker.ps1`
4. `python run.py`，打开 http://127.0.0.1:8080

怎么验证：

1. 状态行 Redis ok、Celery ok（worker 没开则 Celery down，聊天仍可用）
2. 侧栏粘贴一段文字点入库 → 按钮显示「排队中…」，完成后文档列表出现
3. 新对话问刚才那段内容，应能召回；同一问题短期内再问，走 Redis 缓存（入库/删文档会 bump epoch 让缓存失效）

八、V2 多了什么

范围：Gateway 从 FastAPI 换成 Django + DRF。Runtime / Data / Celery / 前端路径都不动。

  gateway/settings.py  → Django 设置（SECRET、静态文件、DRF）
  gateway/urls.py      → 仍是 /api/health、/api/chat、会话、记忆、文档、jobs
  gateway/api.py       → DRF APIView
  gateway/chat.py      → ASGI 上的 SSE（uvicorn gateway.asgi:application）
  manage.py            → Django 管理命令；日常启动仍是 python run.py

会话、记忆、RAG 表继续用 SQLAlchemy（data/），不迁 Django ORM。Auth / 多端路由仍留给后面。

怎么验证：

1. 页面副标题为 V2 · Django + DRF Gateway
2. GET /api/health 仍返回 postgres / redis / celery
3. 发一条消息能流式出字；点终止仍走 POST /api/conversations/{id}/stop
4. 侧栏入库仍是排队 + 轮询 /api/jobs/{id}

九、安全沙箱

V1 的 sandbox 只是路径牢：命令仍在宿主机跑，黑名单挡不住 `python -c` 读项目外的文件。
现在 Python / Shell / Git 进 Docker 容器：

  能出网（Docker bridge），但不加入 Postgres/Redis 的 compose 网络
  只读根文件系统，只挂 sandbox/ → /workspace
  丢掉全部 Linux capability，no-new-privileges
  内存 256MB、最多 128 进程
  不传入宿主机环境变量，不挂 Docker socket

文件工具仍在 Gateway 进程里读写，但绝对路径 / UNC / `..` 会被拒绝。
`docker compose up -d --build` 会带上 `myaiagent-sandbox`。状态行 Jail ok 表示容器在跑。

怎么验证：

1. 让 Agent `execute_python` 打印 1+1 → 容器内出 2
2. 让它读 `/etc/passwd` 只能看到容器自己的，不是 Windows 主机
3. 让它读项目根目录的 `.env` 应失败（工作区外）
4. 容器内可以访问公网；用服务名访问 postgres/redis 应失败