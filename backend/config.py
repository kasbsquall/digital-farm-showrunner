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
    # Endpoint específico de workspace (Model Studio, keys "sk-ws-..."). Si se
    # define, tiene prioridad sobre la auto-selección por prefijo.
    qwen_base_url_override: str = ""
    qwen_text_model: str = "qwen3.7-plus"   # razonamiento/coherencia: qwen3.7-max
    vision_model: str = "qwen3-vl-plus"     # entiende video (concordancia texto↔video)

    # Generación de video: HappyHorse o Wan (t2v). Wan2.6-t2i es texto→IMAGEN.
    video_model: str = "happyhorse-1.1-t2v"   # texto→video (fallback)
    video_model_i2v: str = "happyhorse-1.1-i2v"  # imagen→video (keyframe animado)
    video_model_wan: str = "wan2.7-t2v"       # tool "wan"
    image_model: str = "qwen-image-2.0"       # retratos de personajes + thumbnails
    video_poll_seconds: int = 10              # intervalo de sondeo de la tarea
    video_timeout_seconds: int = 600          # tope de espera por un video
    # Mantener el video en mock aunque Qwen texto sea real (hasta implementar
    # el submit/poll real de generación de video).
    mock_video: bool = True

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
        """Override de workspace si existe; si no, auto-selecciona por prefijo."""
        if self.qwen_base_url_override:
            return self.qwen_base_url_override
        return (
            self.qwen_base_url_token_plan
            if self.qwen_api_key.startswith("sk-sp-")
            else self.qwen_base_url_payg
        )

    @property
    def dashscope_base(self) -> str:
        """Endpoint DashScope nativo (async video/imagen). Deriva del base OpenAI."""
        return self.qwen_base_url.replace("/compatible-mode/v1", "/api/v1")


settings = Settings()
