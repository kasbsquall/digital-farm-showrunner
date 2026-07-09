"""Per-run token & cost meter.

The meter is **thread-local**: each pipeline run (an API request thread or the
scheduler thread) accumulates into its own state, so multiple channels can generate
concurrently without clobbering each other's receipt. The orchestrator resets it at
the start of a run and snapshots it at the end to persist tokens + estimated cost on
the Episode — making the track's "quality under a token budget" claim measurable.
"""
import threading

from config import settings

_local = threading.local()


def _state() -> dict:
    s = getattr(_local, "state", None)
    if s is None:
        s = {"prompt": 0, "completion": 0, "calls": 0, "media_cost": 0.0, "media_calls": 0}
        _local.state = s
    return s


def reset() -> None:
    _local.state = {"prompt": 0, "completion": 0, "calls": 0, "media_cost": 0.0, "media_calls": 0}


def add(prompt_tokens: int, completion_tokens: int) -> None:
    s = _state()
    s["prompt"] += int(prompt_tokens or 0)
    s["completion"] += int(completion_tokens or 0)
    s["calls"] += 1


def add_media(cost_usd: float) -> None:
    """Meter a per-unit media call (image / video) whose cost is NOT token-based."""
    s = _state()
    s["media_cost"] += float(cost_usd or 0.0)
    s["media_calls"] += 1


def add_image() -> None:
    add_media(settings.image_cost_usd)


def add_video(seconds: float) -> None:
    add_media(float(seconds) * settings.video_cost_usd_per_second)


def estimate_tokens(text: str) -> int:
    """Rough estimate (~4 chars/token) for mock mode, so demos show a number."""
    return max(1, len(text or "") // 4)


def total_tokens() -> int:
    s = _state()
    return s["prompt"] + s["completion"]


def snapshot() -> dict:
    s = _state()
    total = s["prompt"] + s["completion"]
    text_cost = total / 1000 * settings.token_cost_per_1k
    media_cost = s["media_cost"]
    return {
        "prompt_tokens": s["prompt"],
        "completion_tokens": s["completion"],
        "total_tokens": total,
        "calls": s["calls"],
        "media_calls": s["media_calls"],
        "text_cost_usd": round(text_cost, 6),
        "media_cost_usd": round(media_cost, 6),
        # Blended per-episode cost: text tokens + image + video, not just text.
        "cost_usd": round(text_cost + media_cost, 6),
    }
