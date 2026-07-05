"""Qwen vision: describe what actually happens in a generated video.

This closes the loop so QA and packaging reflect the REAL video content instead
of just the intended script — fixing text/video mismatches.
"""
from openai import OpenAI

from config import settings

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.qwen_api_key, base_url=settings.qwen_base_url)
    return _client


def describe_video(video_url: str) -> str:
    """Return a short factual description of what visibly happens in the video."""
    resp = _get_client().chat.completions.create(
        model=settings.vision_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "video_url", "video_url": {"url": video_url}},
                    {"type": "text", "text": (
                        "Describe en 2-3 frases, en español, EXACTAMENTE lo que se ve y "
                        "sucede en este video corto: qué personajes/objetos aparecen y qué "
                        "acción hacen. Solo lo observable, sin inventar diálogo ni intención."
                    )},
                ],
            }
        ],
    )
    return resp.choices[0].message.content.strip()
