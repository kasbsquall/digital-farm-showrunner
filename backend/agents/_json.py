"""Extract a JSON object from an LLM text response (tolerant of common glitches)."""
import json
import re


def _clean(text: str) -> str:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    if not text.startswith("{"):
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            text = m.group(0)
    return text


def parse_json(text: str) -> dict:
    cleaned = _clean(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Repair pass: drop trailing commas and smart quotes, then retry.
        repaired = re.sub(r",\s*([}\]])", r"\1", cleaned)
        repaired = repaired.replace("“", '"').replace("”", '"').replace("’", "'")
        return json.loads(repaired)
