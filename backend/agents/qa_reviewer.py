"""Agent 3 — QA Reviewer.

Reviews the generated video and decides approve vs regenerate. This guards the
token budget: catching a bad take here avoids wasting downstream generations.

In real mode this can inspect a frame/caption of the video; for the MVP it
reasons over the prompt+script coherence. Mock approves.
"""
import json

from services.qwen_client import chat
from agents._json import parse_json

SYSTEM = (
    "Eres control de calidad de video. Decides si un episodio pasa o si hay que "
    "regenerar por incoherencia visual, error de continuidad o problema técnico. "
    "Eres estricto pero no perfeccionista. Respondes SIEMPRE en JSON válido."
)

USER_TMPL = """Guion original:
{script}

Prompt de video usado:
{video_prompt}

Video generado (URL): {video_url}

¿El episodio es válido para publicar? Devuelve JSON exacto:
{{"qa_status": "approved"|"rejected", "qa_notes": "<motivo breve>"}}"""


def _mock(video_url: str) -> str:
    return json.dumps(
        {"qa_status": "approved",
         "qa_notes": "Coherencia visual y continuidad correctas; timing cómico adecuado."},
        ensure_ascii=False,
    )


def run(video_url: str, script: str, video_prompt: str = "") -> dict:
    text = chat(
        SYSTEM,
        USER_TMPL.format(script=script, video_prompt=video_prompt, video_url=video_url),
        temperature=0.2,
        mock=_mock(video_url),
    )
    data = parse_json(text)
    status = data.get("qa_status", "rejected")
    if status not in ("approved", "rejected"):
        status = "rejected"
    return {"qa_status": status, "qa_notes": data.get("qa_notes", "")}
