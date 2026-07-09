"""Agent 4 — Packager.

Produces a publish-ready title and description that match the gag actually seen in
the video (cause and effect). English output.
"""
import json

from services.qwen_client import chat
from agents._json import parse_json

SYSTEM = (
    "You are the editor of a viral channel of claymation farm micro-dramas. You write "
    "hooky titles and descriptions in ENGLISH that capture the EXACT gag that happens in "
    "the video (the action and its cause-effect), with humor and rhythm. No generic filler: "
    "if the rooster punches the bread, say so. You ALWAYS answer in valid JSON."
)

USER_TMPL = """Episode event: {event}

Script:
{script}

WHAT THE VIDEO ACTUALLY SHOWS (prioritize this so the text matches):
{video_description}

Write the publishing package. Title and description must reflect what is really seen in
the video (above), not just the script. Return exactly this JSON:
{{"title": "<viral title, with 1-2 emojis>",
  "thumbnail_hint": "<visual description of the suggested thumbnail>",
  "description": "<2-3 sentences + 3 hashtags>"}}"""


def _mock(event: str, script: str) -> str:
    return json.dumps(
        {
            "title": "🐔 The day the farm lost its mind",
            "thumbnail_hint": ("Close-up of a barnyard animal mid-reaction, wide-eyed, "
                               "saturated colors, hay and wooden fences behind."),
            "description": (f"{event} Another chapter of the barnyard's most absurd daily drama. "
                            "#DigitalFarm #AI #MicroDrama"),
        },
        ensure_ascii=False,
    )


def run(event: str, script: str, video_description: str = "") -> dict:
    desc = video_description.strip() or "(unavailable — use the script)"
    text = chat(
        SYSTEM,
        USER_TMPL.format(event=event, script=script, video_description=desc),
        temperature=0.8,
        mock=_mock(event, script),
    )
    data = parse_json(text)
    return {
        "title": data.get("title", "A brand-new barnyard episode 🐔"),
        "thumbnail_hint": data.get("thumbnail_hint", ""),
        "description": data.get("description", event),
    }
