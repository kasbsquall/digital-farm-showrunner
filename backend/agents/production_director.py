"""Agent 2 — Production Director.

Designs a single 5-second visual gag. Produces:
  - keyframe_prompt: a still "frozen moment" of the funniest beat, featuring the
    involved characters IN THEIR established look (so the video is consistent with
    the character portraits). This still is generated, then animated (image→video).
  - motion_prompt: the short, single action that plays out in ~5 seconds.
"""
import json

from services.qwen_client import chat
from agents._json import parse_json

SYSTEM = (
    "You are an AI video production director. A clip is only ~5 SECONDS, so you design "
    "ONE instant visual gag: a single action that reads at a glance and is funny in the "
    "moment. You describe the characters faithfully to their established look. You ALWAYS "
    "answer in valid JSON, with the prompts written in English."
)

USER_TMPL = """Script (concept):
{script}

FAITHFUL character appearance (respect it exactly for consistency):
{visuals}

Design the 5-second episode. Return exactly this JSON:
{{"keyframe_prompt": "<English prompt for ONE still image: the funniest instant,
   claymation stop-motion style, characters exactly as described, cinematic framing,
   farm background>",
  "motion_prompt": "<English prompt for the SINGLE ~5s action that animates that image:
   one simple comedic movement, subtle camera>",
  "video_tool": "happyhorse-i2v"}}"""

STYLE = "charming claymation stop-motion style, cohesive children's animated film look, warm cinematic lighting"


def _mock(script: str, characters: list[dict]) -> str:
    names = ", ".join(c["name"] for c in characters)
    return json.dumps({
        "keyframe_prompt": (f"A frozen comedic barnyard moment featuring {names}, {STYLE}, "
                            "expressive faces mid-reaction, medium shot, farm background"),
        "motion_prompt": "the characters react with one quick exaggerated comedic beat, subtle camera push-in",
        "video_tool": "happyhorse-i2v",
    }, ensure_ascii=False)


def run(script: str, characters: list[dict]) -> dict:
    visuals = "\n".join(f"- {c['name']}: {c.get('visual_desc', '')}" for c in characters)
    text = chat(
        SYSTEM,
        USER_TMPL.format(script=script, visuals=visuals),
        temperature=0.6,
        mock=_mock(script, characters),
    )
    data = parse_json(text)
    # Refuerza el estilo consistente en el keyframe.
    kf = data["keyframe_prompt"]
    if "claymation" not in kf.lower():
        kf = f"{kf}, {STYLE}"
    return {
        "keyframe_prompt": kf,
        "motion_prompt": data["motion_prompt"],
        "video_tool": data.get("video_tool", "happyhorse-i2v"),
    }
