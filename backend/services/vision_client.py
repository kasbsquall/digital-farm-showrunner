"""Qwen vision: describe what actually happens in a generated video.

This closes the loop so QA and packaging reflect the REAL video content instead
of just the intended script — fixing text/video mismatches.
"""
import time

from openai import OpenAI

from config import settings
from services import usage

_client = None
_MAX_RETRIES = 3


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.qwen_api_key, base_url=settings.qwen_base_url)
    return _client


def describe_video(video_url: str) -> str:
    """Return a short factual description of what visibly happens in the video.

    Retries on transient errors. A blank description would bias QA toward a
    rejection, so exhausting the retries raises instead of returning "".
    """
    prompt = (
        "In English, in 2-4 sentences, narrate the exact CHRONOLOGICAL SEQUENCE "
        "of actions in this short video: what each character does, in what order, "
        "and what CAUSES what (who hits, pushes, throws or moves something, and how "
        "the other reacts). Be precise about the gag's cause-and-effect. Only what "
        "is observable on screen; do not invent dialogue or inner intent."
    )
    last_err = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = _get_client().chat.completions.create(
                model=settings.vision_model,
                messages=[{"role": "user", "content": [
                    {"type": "video_url", "video_url": {"url": video_url}},
                    {"type": "text", "text": prompt},
                ]}],
            )
            u = getattr(resp, "usage", None)
            if u is not None:
                usage.add(getattr(u, "prompt_tokens", 0), getattr(u, "completion_tokens", 0))
            return resp.choices[0].message.content.strip()
        except Exception as e:  # transient vision/network error → backoff and retry
            last_err = e
            if attempt < _MAX_RETRIES - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Vision description failed after {_MAX_RETRIES} attempts: {last_err}")
