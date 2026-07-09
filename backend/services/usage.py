"""Per-run token & cost meter.

The single-flight generation lock guarantees one pipeline runs at a time, so a
module-level accumulator is safe. The orchestrator resets it at the start of a run
and snapshots it at the end to persist tokens + estimated cost on the Episode —
making the track's "quality under a token budget" claim measurable.
"""
import threading

from config import settings

_lock = threading.Lock()
_state = {"prompt": 0, "completion": 0, "calls": 0, "media_cost": 0.0, "media_calls": 0}


def reset() -> None:
    with _lock:
        _state.update(prompt=0, completion=0, calls=0, media_cost=0.0, media_calls=0)


def add(prompt_tokens: int, completion_tokens: int) -> None:
    with _lock:
        _state["prompt"] += int(prompt_tokens or 0)
        _state["completion"] += int(completion_tokens or 0)
        _state["calls"] += 1


def add_media(cost_usd: float) -> None:
    """Meter a per-unit media call (image / video) whose cost is NOT token-based."""
    with _lock:
        _state["media_cost"] += float(cost_usd or 0.0)
        _state["media_calls"] += 1


def add_image() -> None:
    add_media(settings.image_cost_usd)


def add_video(seconds: float) -> None:
    add_media(float(seconds) * settings.video_cost_usd_per_second)


def estimate_tokens(text: str) -> int:
    """Rough estimate (~4 chars/token) for mock mode, so demos show a number."""
    return max(1, len(text or "") // 4)


def total_tokens() -> int:
    with _lock:
        return _state["prompt"] + _state["completion"]


def snapshot() -> dict:
    with _lock:
        total = _state["prompt"] + _state["completion"]
        text_cost = total / 1000 * settings.token_cost_per_1k
        media_cost = _state["media_cost"]
        return {
            "prompt_tokens": _state["prompt"],
            "completion_tokens": _state["completion"],
            "total_tokens": total,
            "calls": _state["calls"],
            "media_calls": _state["media_calls"],
            "text_cost_usd": round(text_cost, 6),
            "media_cost_usd": round(media_cost, 6),
            # Blended per-episode cost: text tokens + image + video, not just text.
            "cost_usd": round(text_cost + media_cost, 6),
        }
