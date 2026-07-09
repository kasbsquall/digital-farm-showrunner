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
_MAX_RETRIES = 3


def _post_with_retries(url: str, *, headers: dict, json: dict, timeout: int) -> httpx.Response:
    """POST with a short retry/backoff on transient network or 5xx errors."""
    last: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = httpx.post(url, headers=headers, json=json, timeout=timeout)
            resp.raise_for_status()
            return resp
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            # Retry only on transient failures (network errors or 5xx); fail fast on 4xx.
            if status is not None and status < 500:
                raise
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Video submit failed after {_MAX_RETRIES} retries: {last}")

# tool label (from Agent 2) → real DashScope model
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


def _submit_raw(model: str, inp: dict, parameters: dict | None = None) -> str:
    url = f"{settings.dashscope_base}/services/aigc/video-generation/video-synthesis"
    body = {"model": model, "input": inp, "parameters": parameters or {}}
    resp = _post_with_retries(url, headers=_headers({"X-DashScope-Async": "enable"}), json=body, timeout=60)
    task_id = resp.json().get("output", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id in submit response: {resp.json()}")
    return task_id


def _params() -> dict:
    # Only send duration when explicitly configured (avoids unsupported-param errors).
    return {"duration": settings.video_duration} if settings.video_duration > 0 else {}


def animate_image(image_url: str, motion_prompt: str) -> str:
    """Image→video (HappyHorse i2v): animate a keyframe. Returns a playable URL."""
    if settings.use_mock or settings.mock_video:
        return _mock_url(motion_prompt, "i2v")
    task_id = _submit_raw(
        settings.video_model_i2v,
        {"media": [{"url": image_url}], "prompt": motion_prompt},
        _params(),
    )
    return _poll(task_id)


def _submit(model: str, prompt: str) -> str:
    # HappyHorse/Wan require a `parameters` object (empty = model defaults).
    return _submit_raw(model, {"prompt": prompt}, {})


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
                raise RuntimeError(f"Task SUCCEEDED but no video_url: {output}")
            return video_url
        if status in ("FAILED", "CANCELED", "UNKNOWN"):
            raise RuntimeError(f"Video generation {status}: {output.get('message', output)}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"Timed out waiting for video (task {task_id}, last status {status})")
        time.sleep(settings.video_poll_seconds)


def generate_video(prompt: str, tool: str = "happyhorse") -> str:
    """Submit a generation job and return a playable video URL."""
    if settings.use_mock or settings.mock_video:
        return _mock_url(prompt, tool)

    model = _TOOL_TO_MODEL.get(tool, _TOOL_TO_MODEL["happyhorse"])()
    task_id = _submit(model, prompt)
    return _poll(task_id)


def stitch(clip_urls: list[str]) -> str:
    """Download the per-shot clips and concatenate them into one mp4 (multi-shot episode).

    Returns a LOCAL file path (upload it with oss_client.persist_local).
    """
    import os
    import subprocess
    import tempfile

    import imageio_ffmpeg

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmp = tempfile.mkdtemp(prefix="muckflix_stitch_")
    files = []
    for i, u in enumerate(clip_urls):
        p = os.path.join(tmp, f"shot{i}.mp4")
        r = httpx.get(u, timeout=120, follow_redirects=True)
        r.raise_for_status()
        with open(p, "wb") as fh:
            fh.write(r.content)
        files.append(p)
    listfile = os.path.join(tmp, "list.txt")
    with open(listfile, "w") as fh:
        fh.write("".join(f"file '{f}'\n" for f in files))
    out = os.path.join(tmp, "stitched.mp4")
    # Re-encode on concat so clips with slightly different params join cleanly.
    subprocess.run(
        [ff, "-y", "-f", "concat", "-safe", "0", "-i", listfile,
         "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", "24", out],
        check=True, capture_output=True,
    )
    return out
