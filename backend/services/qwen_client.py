"""Client for Qwen Cloud (DashScope) text models via the OpenAI-compatible API.

Mock mode: when no QWEN_API_KEY is set (or FORCE_MOCK=true) `chat()` returns the
caller-provided `mock` string instead of hitting the network. This lets us build
and run the whole pipeline offline while the hackathon credits are pending, then
flip to real Qwen by just setting the key — no code change.
"""
import time

from config import settings

_client = None
_MAX_RETRIES = 3


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=settings.qwen_api_key, base_url=settings.qwen_base_url)
    return _client


def chat(system: str, user: str, temperature: float = 0.8, mock: str | None = None) -> str:
    """Single-turn completion. Returns assistant text.

    In mock mode returns `mock` (each agent supplies a canned response derived
    from its own inputs, so the pipeline stays deterministic and testable).
    """
    from services import usage
    if settings.use_mock:
        if mock is None:
            raise RuntimeError("Mock mode active but caller provided no mock response.")
        usage.add(usage.estimate_tokens(system + user), usage.estimate_tokens(mock))
        return mock

    last_err = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = _get_client().chat.completions.create(
                model=settings.qwen_text_model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            u = getattr(resp, "usage", None)
            if u is not None:
                usage.add(getattr(u, "prompt_tokens", 0), getattr(u, "completion_tokens", 0))
            return resp.choices[0].message.content.strip()
        except Exception as e:  # transient API/network errors → backoff and retry
            last_err = e
            if attempt < _MAX_RETRIES - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Qwen chat failed after {_MAX_RETRIES} attempts: {last_err}")
