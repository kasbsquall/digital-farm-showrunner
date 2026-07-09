"""Central configuration. All secrets come from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database: SQLite by default, swap to Alibaba Cloud RDS (PostgreSQL) via env.
    database_url: str = "sqlite:///./farm.db"

    # Qwen Cloud — OpenAI-compatible. Two account types exist:
    #  - Pay-as-you-go: key "sk-..."        → dashscope-intl base URL
    #  - Token Plan (hackathon credits): key "sk-sp-..." → token-plan base URL
    # NEVER mix a key with the wrong endpoint → 401 InvalidApiKey.
    qwen_api_key: str = ""
    qwen_base_url_payg: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    qwen_base_url_token_plan: str = "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
    # Workspace-specific endpoint (Model Studio, "sk-ws-..." keys). If set, it
    # takes priority over the prefix-based auto-selection.
    qwen_base_url_override: str = ""
    qwen_text_model: str = "qwen3.7-plus"   # reasoning/coherence: qwen3.7-max
    vision_model: str = "qwen3-vl-plus"     # understands video (text↔video concordance)

    # Video generation: HappyHorse or Wan (t2v). Wan2.6-t2i is text→IMAGE.
    video_model: str = "happyhorse-1.1-t2v"   # text→video (fallback)
    video_model_i2v: str = "happyhorse-1.1-i2v"  # image→video (animated keyframe)
    video_model_wan: str = "wan2.7-t2v"       # tool "wan"
    image_model: str = "qwen-image-2.0"       # character portraits + thumbnails
    video_poll_seconds: int = 10              # task polling interval
    video_timeout_seconds: int = 600          # max wait for one video
    # Clip duration. 0 = use the model default (~5s). Set e.g. 10 to attempt
    # longer clips (VERIFY the model accepts it; costs more).
    video_duration: int = 0
    # Keep video in mock even when Qwen text is real (until the real video
    # submit/poll is enabled).
    mock_video: bool = True

    # Alibaba Cloud OSS (video storage).
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_bucket: str = ""
    oss_endpoint: str = ""

    # ElevenLabs (voiceover for the demo video).
    elevenlabs_api_key: str = ""

    # Force mock mode even if a key is present (handy for tests/demo).
    force_mock: bool = False

    @property
    def use_mock(self) -> bool:
        """Mock when no Qwen key is configured, or when explicitly forced."""
        return self.force_mock or not self.qwen_api_key

    @property
    def qwen_base_url(self) -> str:
        """Workspace override if present; otherwise auto-select by key prefix."""
        if self.qwen_base_url_override:
            return self.qwen_base_url_override
        return (
            self.qwen_base_url_token_plan
            if self.qwen_api_key.startswith("sk-sp-")
            else self.qwen_base_url_payg
        )

    @property
    def dashscope_base(self) -> str:
        """Native DashScope endpoint (async video/image). Derived from the OpenAI base."""
        return self.qwen_base_url.replace("/compatible-mode/v1", "/api/v1")


settings = Settings()
