"""Central configuration. All secrets come from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database: SQLite by default, swap to Alibaba Cloud RDS (PostgreSQL) via env.
    database_url: str = "sqlite:///./farm.db"

    # Qwen Cloud — OpenAI-compatible. Two account types exist (ver PDF pág. 7):
    #  - Pay-as-you-go: key "sk-..."     → dashscope-intl base URL
    #  - Token Plan (créditos hackathon): key "sk-sp-..." → token-plan base URL
    # NUNCA mezclar key con el endpoint equivocado → 401 InvalidApiKey.
    qwen_api_key: str = ""
    qwen_base_url_payg: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    qwen_base_url_token_plan: str = "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
    qwen_text_model: str = "qwen3.7-plus"   # razonamiento/coherencia: qwen3.7-max

    # Generación de video: HappyHorse (texto→video). Wan2.6 es texto→IMAGEN.
    video_model: str = "happyhorse-1.1-t2v"
    image_model: str = "wan2.6-t2i"         # para thumbnails del episodio

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

    @property
    def qwen_base_url(self) -> str:
        """Auto-selecciona el endpoint según el prefijo de la key (evita el 401)."""
        return (
            self.qwen_base_url_token_plan
            if self.qwen_api_key.startswith("sk-sp-")
            else self.qwen_base_url_payg
        )


settings = Settings()
