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
    "You are the production director of a claymation stop-motion channel. You turn a "
    "script into TWO things: (1) a KEYFRAME image prompt — a single frozen frame of the "
    "FUNNIEST split-second of the gag, clearly composed and instantly readable; and (2) a "
    "MOTION prompt — the ONE simple continuous movement that animates that exact frame over "
    "~5 seconds. The motion must be a single physical action an image-to-video model can "
    "animate smoothly (a fall, a squish, a splash, a launch, a big head-turn reaction, an "
    "object dropping) — never multiple actions or scene cuts. Describe every character on "
    "screen faithfully to their given look so they stay consistent. You ALWAYS answer in "
    "valid JSON, prompts written in English."
)

USER_TMPL = """Script (the gag):
{script}

FAITHFUL character appearance (match it exactly for consistency):
{visuals}

Return exactly this JSON:
{{"keyframe_prompt": "<English: the single funniest FROZEN instant of the gag. Name and
   faithfully describe each character present (using their look above), mid-reaction with
   exaggerated expressive faces, clear staging with one obvious focal action. Claymation
   plasticine stop-motion, Aardman style, visible clay fingerprints, farm background with
   wooden fences and hay, bright natural daylight, cinematic slightly-wide shot>",
  "motion_prompt": "<English: ONE simple continuous ~5-second motion that animates that
   frame, with exaggerated cartoon physics and a subtle camera push-in. One action only>",
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


def run(script: str, characters: list[dict], qa_notes: str = "") -> dict:
    visuals = "\n".join(f"- {c['name']}: {c.get('visual_desc', '')}" for c in characters)
    user = USER_TMPL.format(script=script, visuals=visuals)
    if qa_notes.strip():
        # Closed feedback loop: the previous take was rejected — fix it specifically.
        user += (
            f"\n\nIMPORTANT — the previous attempt was REJECTED by QA for this reason:\n"
            f'"{qa_notes.strip()}"\n'
            "Redesign the keyframe and motion to directly FIX that problem: make the main "
            "action and the involved characters unmistakably clear and correct."
        )
    text = chat(
        SYSTEM,
        user,
        temperature=0.7,
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
