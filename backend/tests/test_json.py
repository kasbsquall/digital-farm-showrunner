"""Unit tests for agents._json.parse_json — pure, no network."""
from agents._json import parse_json


def test_valid_json():
    assert parse_json('{"a": 1, "b": "two"}') == {"a": 1, "b": "two"}


def test_trailing_commas_are_repaired():
    text = '{"list": [1, 2, 3,], "name": "x",}'
    assert parse_json(text) == {"list": [1, 2, 3], "name": "x"}


def test_json_fenced_block():
    text = '```json\n{"ok": true}\n```'
    assert parse_json(text) == {"ok": True}


def test_bare_fence_without_language():
    text = '```\n{"ok": true}\n```'
    assert parse_json(text) == {"ok": True}


def test_smart_quotes_are_normalized():
    # Curly quotes around the value would break json.loads without the repair pass.
    text = '{“title”: “Hello ’world’”}'
    result = parse_json(text)
    assert result["title"] == "Hello 'world'"


def test_embedded_prose_around_json():
    text = 'Sure! Here is the result:\n{"event": "chaos", "n": 2}\nHope that helps.'
    assert parse_json(text) == {"event": "chaos", "n": 2}
