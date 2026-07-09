"""Text-to-image generation (Qwen-Image / Wan) via DashScope multimodal endpoint.

This workspace does not allow async image calls, so we use the synchronous
multimodal-generation endpoint with a `messages` payload. Returns a temporary
image URL that callers persist to OSS.
"""
import time

import httpx

from config import settings

_MAX_RETRIES = 3


def generate_image(prompt: str, size: str = "1024*1024") -> str:
    """Generate an image and return its (temporary) URL."""
    url = f"{settings.dashscope_base}/services/aigc/multimodal-generation/generation"
    headers = {"Authorization": f"Bearer {settings.qwen_api_key}", "Content-Type": "application/json"}
    body = {
        "model": settings.image_model,
        "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
        "parameters": {"size": size, "n": 1},
    }
    last: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = httpx.post(url, headers=headers, json=body, timeout=120)
            resp.raise_for_status()
            content = resp.json()["output"]["choices"][0]["message"]["content"]
            for item in content:
                if item.get("image"):
                    return item["image"]
            raise RuntimeError(f"Image response had no image: {content}")
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status is not None and status < 500:
                raise
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Image generation failed after {_MAX_RETRIES} retries: {last}")
