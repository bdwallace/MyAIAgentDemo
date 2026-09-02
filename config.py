"""集中配置。Postgres / Redis / 模型地址都从这里读，不要散落进业务代码。"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-v4-flash"
    llm_timeout_seconds: int = 600

    # 密码里有 @ 等特殊字符时，不要写成一条 URL，用下面分项。
    # Docker：127.0.0.1:5433（见 docker-compose）。本机安装的 PG 一般是 5432。
    pg_user: str = "agent"
    pg_password: str = "@Root123456"
    pg_host: str = "127.0.0.1"
    pg_port: int = 5433
    pg_database: str = "private_agent"

    host: str = "127.0.0.1"
    port: int = 8080
    max_history_messages: int = 20
    max_memories_in_prompt: int = 30
    python_timeout_seconds: int = 15
    shell_timeout_seconds: int = 15
    web_timeout_seconds: int = 15
    graph_recursion_limit: int = 32
    sandbox_dir: Path = ROOT_DIR / "sandbox"

    # RAG。embedding_base_url 为空则用本机 bge-small-zh（modelscope）。
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_dim: int = 512
    rag_top_k: int = 4
    rag_min_score: float = 0.35
    rag_chunk_size: int = 400
    rag_chunk_overlap: int = 60

    redis_url: str = "redis://127.0.0.1:6379/0"
    rag_cache_ttl_seconds: int = 60


settings = Settings()
settings.sandbox_dir.mkdir(parents=True, exist_ok=True)
