"""V0 配置。以后 Redis、对象存储都在这里加，不要散落进业务代码。"""

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
    pg_user: str = "agent"
    pg_password: str = "@Root123456"
    pg_host: str = "127.0.0.1"
    pg_port: int = 5432
    pg_database: str = "private_agent"

    host: str = "127.0.0.1"
    port: int = 8080
    max_history_messages: int = 20
    max_memories_in_prompt: int = 30
    python_timeout_seconds: int = 15
    web_timeout_seconds: int = 15
    sandbox_dir: Path = ROOT_DIR / "sandbox"


settings = Settings()
settings.sandbox_dir.mkdir(parents=True, exist_ok=True)
