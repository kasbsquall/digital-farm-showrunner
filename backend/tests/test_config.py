"""Unit tests for config.Settings computed properties.

Fresh Settings instances are constructed with explicit kwargs; pydantic-settings
gives init kwargs the highest priority, so these assertions are independent of
the committed .env and the process environment.
"""
from config import Settings

_PAYG = "https://payg.example/compatible-mode/v1"
_TOKEN = "https://token-plan.example/compatible-mode/v1"


def _settings(**kw) -> Settings:
    base = dict(qwen_base_url_override="", qwen_base_url_payg=_PAYG,
                qwen_base_url_token_plan=_TOKEN)
    base.update(kw)
    return Settings(**base)


def test_qwen_base_url_token_plan_for_sk_sp_keys():
    s = _settings(qwen_api_key="sk-sp-abc123")
    assert s.qwen_base_url == _TOKEN


def test_qwen_base_url_payg_for_other_keys():
    s = _settings(qwen_api_key="sk-abc123")
    assert s.qwen_base_url == _PAYG


def test_qwen_base_url_override_takes_priority():
    override = "https://workspace.example/compatible-mode/v1"
    s = _settings(qwen_api_key="sk-sp-abc123", qwen_base_url_override=override)
    assert s.qwen_base_url == override


def test_dashscope_base_derivation():
    s = _settings(qwen_api_key="sk-abc123")
    assert s.dashscope_base == "https://payg.example/api/v1"


def test_use_mock_true_when_force_mock():
    s = _settings(qwen_api_key="sk-real-key", force_mock=True)
    assert s.use_mock is True


def test_use_mock_true_when_no_key():
    s = _settings(qwen_api_key="", force_mock=False)
    assert s.use_mock is True


def test_use_mock_false_when_key_and_not_forced():
    s = _settings(qwen_api_key="sk-real-key", force_mock=False)
    assert s.use_mock is False
