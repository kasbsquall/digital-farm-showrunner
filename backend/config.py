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

    # Demo/recording mode (all optional, off by default): in mock, replay a real
    # clip so the pipeline can be recorded end-to-end at zero cost, and pace the
    # SSE so each stage is visible on screen.
    demo_video_url: str = ""
    demo_thumbnail_url: str = ""
    demo_video_desc: str = ""
    demo_pace_seconds: float = 0.0
    # Generate a real portrait for user-created characters even in mock mode
    # (cheap image call — lets the "bring your own character" flow look real).
    create_real_portraits: bool = False

    # Alibaba Cloud OSS (video storage).
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_bucket: str = ""
    oss_endpoint: str = ""

    # ElevenLabs (voiceover for the demo video).
    elevenlabs_api_key: str = ""

    # Force mock mode even if a key is present (handy for tests/demo).
    force_mock: bool = False

    # Token budget & cost: the pipeline meters tokens and estimates cost per
    # episode; token_budget (0 = unlimited) also gates whether another retake fits.
    token_cost_per_1k: float = 0.002
    token_budget: int = 0
    # Media cost is NOT token-based — it is priced per unit. These are list-price
    # ESTIMATES so the per-episode receipt reflects the true blended cost (text +
    # image + video), not just the cheap text half.
    image_cost_usd: float = 0.02              # per generated keyframe/image
    video_cost_usd_per_second: float = 0.05   # per second of i2v/t2v video
    video_default_seconds: int = 5            # assumed clip length when duration=0 (for costing)

    # Multi-shot: episodes of N chained shots (setup → escalation → punchline),
    # stitched into one video. 1 = the classic single-gag micro-drama.
    shots_per_episode: int = 1
    # Identity-lock: after generating a keyframe, a Qwen3-VL check scores how well the
    # character matches its canonical portrait (0-1), stored per take — a measurable
    # consistency gate (the qwen-image endpoint does not accept a reference image).
    identity_check: bool = False
    # A take whose keyframe scores below this vs the canonical portrait is REJECTED
    # (wrong/off-model character) and regenerated with a fresh keyframe. 0 = measure
    # only, don't gate. Applies only when identity_check is on.
    identity_min: float = 0.55

    # Unattended "daily channel" scheduler: runs the showrunner on an interval and
    # publishes on the QA verdict — the autonomous loop the track asks for. Off by
    # default so tests/demos never spend credits unprompted.
    scheduler_enabled: bool = False
    scheduler_interval_hours: float = 24.0

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
