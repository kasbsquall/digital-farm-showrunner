"""Agent 3 — QA Reviewer.

Reviews the generated video and decides approve vs regenerate, guarding the token
budget. Reasons over what the video actually shows (from Qwen vision). English output.
"""
import json

from services.qwen_client import chat
from agents._json import parse_json

SYSTEM = (
    "You are the quality-control reviewer of an autonomous video showrunner. You gate "
    "whether a generated take is fit to publish or must be regenerated. You judge ONLY "
    "from the vision analysis of what the clip ACTUALLY shows, against the script's intent. "
    "You are fair but rigorous: a take must clearly deliver the gag to pass. You ALWAYS "
    "answer in valid JSON, in English."
)

USER_TMPL = """Original script (the intended gag):
{script}

Intended 5-second action:
{video_prompt}

WHAT THE VIDEO ACTUALLY SHOWS (Qwen vision analysis of the real clip):
{video_description}

Judge the take against this rubric — ALL must hold to APPROVE:
1. Characters: the main character(s) from the script are clearly present.
2. Action: the core action / cause→effect of the gag is recognizably taking place. It may
   be understated, but it must visibly be the RIGHT action — reject a static, wrong, or
   unrelated scene, but do not demand a perfect or exaggerated performance.
3. Integrity: the clip is not broken, empty, blurred-beyond-recognition, or off-topic.
Reject if any check clearly fails or is ambiguous; approve when the gag reads.

Return exactly this JSON:
{{"qa_status": "approved"|"rejected",
  "qa_score": <0.0-1.0 confidence that the take delivers the gag: 1.0 = perfect, ~0.5 = borderline, 0.0 = broken/off>,
  "qa_notes": "<one concrete sentence: what passed, or exactly what to fix on the retake>"}}"""


def _mock(video_url: str) -> str:
    return json.dumps(
        {"qa_status": "approved", "qa_score": 0.9,
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
    try:
        score = max(0.0, min(1.0, float(data.get("qa_score", 1.0 if status == "approved" else 0.0))))
    except (TypeError, ValueError):
        score = 1.0 if status == "approved" else 0.0
    return {"qa_status": status, "qa_score": score, "qa_notes": data.get("qa_notes", "")}
