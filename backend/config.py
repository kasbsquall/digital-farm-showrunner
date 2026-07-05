"""Central configuration. All secrets come from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database: SQLite by default, swap to Alibaba Cloud RDS (PostgreSQL) via env.
    database_url: str = "sqlite:///./farm.db"

    # Qwen Cloud (DashScope) — OpenAI-compatible endpoint.
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    qwen_text_model: str = "qwen-plus"

    # Video generation (Wan / HappyHorse via DashScope).
    video_model: str = "wan2.1-t2v-turbo"

    # Alibaba Cloud OSS (video storage).
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_bucket: str = ""
    oss_endpoint: str = ""

    # Force mock mode even if a key is present (handy for tests/demo).
    force_mock: bool = False

    @property
    def use_mock(self) -> bool:
        """Mock when no Qwen key is configured, or when explicitly forced."""
        return self.force_mock or not self.qwen_api_key


settings = Settings()
