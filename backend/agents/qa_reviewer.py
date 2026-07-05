"""Agent 3 — QA Reviewer.

Reviews the generated video and decides approve vs regenerate, guarding the token
budget. Reasons over what the video actually shows (from Qwen vision). English output.
"""
import json

from services.qwen_client import chat
from agents._json import parse_json

SYSTEM = (
    "You are a video QA reviewer. You decide whether an episode is valid to publish, or "
    "must be regenerated due to visual incoherence, continuity errors or technical issues. "
    "You are strict but not a perfectionist. You ALWAYS answer in valid JSON, in English."
)

USER_TMPL = """Original script:
{script}

Motion prompt used:
{video_prompt}

WHAT THE VIDEO ACTUALLY SHOWS (vision analysis):
{video_description}

Does the video reasonably reflect the script's intent (main characters and action
present)? Don't demand perfection; reject only on serious incoherence or a broken/empty
video. Return exactly this JSON:
{{"qa_status": "approved"|"rejected", "qa_notes": "<brief reason>"}}"""


def _mock(video_url: str) -> str:
    return json.dumps(
        {"qa_status": "approved",
         "qa_notes": "Visual coherence and continuity are correct; comedic timing works."},
        ensure_ascii=False,
    )


def run(video_url: str, script: str, video_prompt: str = "", video_description: str = "") -> dict:
    desc = video_description.strip() or "(unavailable — video in placeholder mode)"
    text = chat(
        SYSTEM,
        USER_TMPL.format(script=script, video_prompt=video_prompt, video_description=desc),
        temperature=0.2,
        mock=_mock(video_url),
    )
    data = parse_json(text)
    status = data.get("qa_status", "rejected")
    if status not in ("approved", "rejected"):
        status = "rejected"
    return {"qa_status": status, "qa_notes": data.get("qa_notes", "")}
