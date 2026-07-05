"""Client for text-to-video generation (HappyHorse / Wan) via DashScope.

DashScope video generation is asynchronous:
  1. POST .../services/aigc/video-generation/video-synthesis  (header X-DashScope-Async: enable)
     → returns output.task_id
  2. GET  .../tasks/{task_id}  until task_status is SUCCEEDED / FAILED
     → SUCCEEDED returns output.video_url

Mock mode (settings.use_mock or settings.mock_video) returns a placeholder URL so
the pipeline runs without spending credits. Flip MOCK_VIDEO=false to generate for real.
"""
import time
import hashlib

import httpx

from config import settings

_MOCK_SAMPLE = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBigBuckBunny.mp4"

# tool label (del Agente 2) → modelo real de DashScope
_TOOL_TO_MODEL = {
    "happyhorse": lambda: settings.video_model,
    "wan": lambda: settings.video_model_wan,
}


def _mock_url(prompt: str, tool: str) -> str:
    tag = hashlib.sha1(prompt.encode()).hexdigest()[:8]
    return f"{_MOCK_SAMPLE}#mock-{tool}-{tag}"


def _headers(extra: dict | None = None) -> dict:
    h = {
        "Authorization": f"Bearer {settings.qwen_api_key}",
        "Content-Type": "application/json",
    }
    if extra:
        h.update(extra)
    return h


def _submit(model: str, prompt: str) -> str:
    url = f"{settings.dashscope_base}/services/aigc/video-generation/video-synthesis"
    # HappyHorse/Wan exigen un objeto `parameters` (usa defaults del modelo si va vacío).
    body = {"model": model, "input": {"prompt": prompt}, "parameters": {}}
    resp = httpx.post(url, headers=_headers({"X-DashScope-Async": "enable"}), json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    task_id = data.get("output", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"Sin task_id en la respuesta de submit: {data}")
    return task_id


def _poll(task_id: str) -> str:
    url = f"{settings.dashscope_base}/tasks/{task_id}"
    deadline = time.monotonic() + settings.video_timeout_seconds
    while True:
        resp = httpx.get(url, headers=_headers(), timeout=60)
        resp.raise_for_status()
        output = resp.json().get("output", {})
        status = output.get("task_status")
        if status == "SUCCEEDED":
            video_url = output.get("video_url") or output.get("results", {}).get("video_url")
            if not video_url:
                raise RuntimeError(f"Tarea SUCCEEDED sin video_url: {output}")
            return video_url
        if status in ("FAILED", "CANCELED", "UNKNOWN"):
            raise RuntimeError(f"Generación de video {status}: {output.get('message', output)}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"Timeout esperando el video (task {task_id}, último estado {status})")
        time.sleep(settings.video_poll_seconds)


def generate_video(prompt: str, tool: str = "happyhorse") -> str:
    """Submit a generation job and return a playable video URL."""
    if settings.use_mock or settings.mock_video:
        return _mock_url(prompt, tool)

    model = _TOOL_TO_MODEL.get(tool, _TOOL_TO_MODEL["happyhorse"])()
    task_id = _submit(model, prompt)
    return _poll(task_id)
