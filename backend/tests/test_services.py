"""Network-boundary unit tests for the DashScope service clients.

These exercise the real httpx submit/poll/retry logic that the 31 mock-mode
tests never touch. No real network: respx intercepts httpx at the transport
layer, and time.sleep is stubbed so retries/polls don't actually wait.
"""
import httpx
import pytest
import respx

from config import settings
import services.video_gen_client as vgc
import services.image_gen_client as igc
import services.usage as usage

_SUBMIT_URL = f"{settings.dashscope_base}/services/aigc/video-generation/video-synthesis"
_IMAGE_URL = f"{settings.dashscope_base}/services/aigc/multimodal-generation/generation"


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Never actually sleep during retry/poll backoff."""
    monkeypatch.setattr("time.sleep", lambda *_a, **_k: None)


# --- video_gen_client._poll -------------------------------------------------

def _tasks_url(task_id: str) -> str:
    return f"{settings.dashscope_base}/tasks/{task_id}"


@respx.mock
def test_poll_returns_url_on_succeeded():
    respx.get(_tasks_url("t1")).respond(
        json={"output": {"task_status": "SUCCEEDED", "video_url": "https://cdn/v.mp4"}}
    )
    assert vgc._poll("t1") == "https://cdn/v.mp4"


@respx.mock
def test_poll_returns_nested_results_url():
    respx.get(_tasks_url("t2")).respond(
        json={"output": {"task_status": "SUCCEEDED", "results": {"video_url": "https://cdn/nested.mp4"}}}
    )
    assert vgc._poll("t2") == "https://cdn/nested.mp4"


@respx.mock
def test_poll_succeeded_without_url_raises():
    respx.get(_tasks_url("t3")).respond(json={"output": {"task_status": "SUCCEEDED"}})
    with pytest.raises(RuntimeError, match="no video_url"):
        vgc._poll("t3")


@respx.mock
@pytest.mark.parametrize("status", ["FAILED", "CANCELED", "UNKNOWN"])
def test_poll_raises_on_terminal_failure(status):
    respx.get(_tasks_url("tf")).respond(
        json={"output": {"task_status": status, "message": "boom"}}
    )
    with pytest.raises(RuntimeError, match=status):
        vgc._poll("tf")


@respx.mock
def test_poll_times_out_past_deadline(monkeypatch):
    # Deadline in the past → first non-terminal poll trips the timeout. No sleeping.
    monkeypatch.setattr(settings, "video_timeout_seconds", -1)
    respx.get(_tasks_url("tt")).respond(json={"output": {"task_status": "RUNNING"}})
    with pytest.raises(TimeoutError, match="Timed out"):
        vgc._poll("tt")


# --- video_gen_client._post_with_retries / _submit_raw ----------------------

@respx.mock
def test_post_fails_fast_on_4xx():
    route = respx.post(_SUBMIT_URL).respond(400, json={"error": "bad request"})
    with pytest.raises(httpx.HTTPStatusError):
        vgc._post_with_retries(_SUBMIT_URL, headers={}, json={}, timeout=5)
    assert route.call_count == 1  # no retry on 4xx


@respx.mock
def test_post_retries_on_5xx_then_succeeds():
    route = respx.post(_SUBMIT_URL).mock(
        side_effect=[
            httpx.Response(503, json={"error": "unavailable"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    resp = vgc._post_with_retries(_SUBMIT_URL, headers={}, json={}, timeout=5)
    assert resp.status_code == 200
    assert route.call_count == 2


@respx.mock
def test_post_exhausts_retries_raises_runtimeerror():
    respx.post(_SUBMIT_URL).respond(500, json={"error": "down"})
    with pytest.raises(RuntimeError, match="Video submit failed after"):
        vgc._post_with_retries(_SUBMIT_URL, headers={}, json={}, timeout=5)


@respx.mock
def test_submit_raw_extracts_task_id():
    respx.post(_SUBMIT_URL).respond(json={"output": {"task_id": "abc123"}})
    assert vgc._submit_raw("happyhorse-1.1-t2v", {"prompt": "hi"}) == "abc123"


@respx.mock
def test_submit_raw_missing_task_id_raises():
    respx.post(_SUBMIT_URL).respond(json={"output": {}})
    with pytest.raises(RuntimeError, match="No task_id"):
        vgc._submit_raw("happyhorse-1.1-t2v", {"prompt": "hi"})


# --- video_gen_client.animate_image (mock mode, no network) -----------------

def test_animate_image_mock_is_deterministic():
    # conftest sets FORCE_MOCK + MOCK_VIDEO → no httpx call at all.
    assert settings.use_mock or settings.mock_video
    a = vgc.animate_image("https://img/keyframe.png", "gallop left")
    b = vgc.animate_image("https://img/other.png", "gallop left")
    assert a == vgc.animate_image("https://img/whatever.png", "gallop left")
    assert a == b  # url only depends on the motion prompt in i2v mock
    assert a.startswith(vgc._MOCK_SAMPLE)
    assert "mock-i2v-" in a


def test_generate_video_mock_is_deterministic():
    url = vgc.generate_video("a rooster crows", "wan")
    assert url == vgc.generate_video("a rooster crows", "wan")
    assert "mock-wan-" in url


# --- image_gen_client.generate_image ----------------------------------------

def _image_response(url: str) -> dict:
    return {
        "output": {"choices": [{"message": {"content": [{"text": "here"}, {"image": url}]}}]}
    }


@respx.mock
def test_generate_image_parses_url():
    respx.post(_IMAGE_URL).respond(json=_image_response("https://cdn/pic.png"))
    assert igc.generate_image("a clay pig") == "https://cdn/pic.png"


@respx.mock
def test_generate_image_retries_on_5xx_then_succeeds():
    route = respx.post(_IMAGE_URL).mock(
        side_effect=[
            httpx.Response(500, json={"error": "down"}),
            httpx.Response(200, json=_image_response("https://cdn/ok.png")),
        ]
    )
    assert igc.generate_image("a clay pig") == "https://cdn/ok.png"
    assert route.call_count == 2


@respx.mock
def test_generate_image_fails_fast_on_4xx():
    route = respx.post(_IMAGE_URL).respond(401, json={"error": "unauthorized"})
    with pytest.raises(httpx.HTTPStatusError):
        igc.generate_image("a clay pig")
    assert route.call_count == 1


@respx.mock
def test_generate_image_no_image_raises():
    respx.post(_IMAGE_URL).respond(
        json={"output": {"choices": [{"message": {"content": [{"text": "no image"}]}}]}}
    )
    with pytest.raises(RuntimeError, match="no image"):
        igc.generate_image("a clay pig")


# --- usage token meter ------------------------------------------------------

def test_usage_add_reset_snapshot_math():
    usage.reset()
    usage.add(100, 50)
    usage.add(10, 5)
    snap = usage.snapshot()
    assert snap["prompt_tokens"] == 110
    assert snap["completion_tokens"] == 55
    assert snap["total_tokens"] == 165
    assert snap["calls"] == 2
    assert usage.total_tokens() == 165


def test_usage_cost_is_total_over_1000_times_rate():
    usage.reset()
    usage.add(600, 400)  # 1000 total
    snap = usage.snapshot()
    expected = round(1000 / 1000 * settings.token_cost_per_1k, 6)
    assert snap["cost_usd"] == expected


def test_usage_reset_zeroes_state():
    usage.add(5, 5)
    usage.reset()
    snap = usage.snapshot()
    assert snap == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "calls": 0,
        "cost_usd": 0.0,
    }


def test_usage_add_coerces_none_to_zero():
    usage.reset()
    usage.add(None, None)  # type: ignore[arg-type]
    assert usage.total_tokens() == 0
    assert usage.snapshot()["calls"] == 1


def test_estimate_tokens_monotonic_in_length():
    assert usage.estimate_tokens("") == 1  # floor of 1
    short = usage.estimate_tokens("a" * 20)
    long = usage.estimate_tokens("a" * 200)
    assert long > short
    assert usage.estimate_tokens("a" * 40) == 10
