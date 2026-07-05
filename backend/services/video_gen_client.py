"""Client for text-to-video generation (Wan / HappyHorse via DashScope).

Mock mode returns a deterministic placeholder video URL so the pipeline runs
offline. Real submit/poll against DashScope lands Day 2-3 once we confirm which
video model Kevin's Qwen Cloud credits unlock.
"""
import hashlib

from config import settings

# A small, always-available sample clip stands in for generated video in mock mode.
_MOCK_SAMPLE = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBigBuckBunny.mp4"


def generate_video(prompt: str, tool: str = "wan") -> str:
    """Submit a generation job and return a playable video URL."""
    if settings.use_mock or settings.mock_video:
        # Deterministic per-prompt tag so different episodes look distinct in logs.
        tag = hashlib.sha1(prompt.encode()).hexdigest()[:8]
        return f"{_MOCK_SAMPLE}#mock-{tool}-{tag}"

    raise NotImplementedError(
        f"Real video gen pending Day 2-3. tool={tool} model={settings.video_model}"
    )
