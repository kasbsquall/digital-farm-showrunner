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
# Appended to every keyframe so the image model avoids the tells that scream "AI".
NEGATIVE = "no text, no watermark, no logos, no distorted or extra limbs, no melted faces, no blurry artifacts"


def _norm_kf(kf: str) -> str:
    """Reinforce the consistent style + anti-artifact guardrails on a keyframe prompt."""
    kf = kf or f"A funny claymation barnyard moment, {STYLE}"
    if "claymation" not in kf.lower():
        kf = f"{kf}, {STYLE}"
    return f"{kf}. {NEGATIVE}"


def _mock(script: str, characters: list[dict], shots: int = 1) -> str:
    names = ", ".join(c["name"] for c in characters)
    one = {
        "keyframe_prompt": (f"A frozen comedic barnyard moment featuring {names}, {STYLE}, "
                            "expressive faces mid-reaction, medium shot, farm background"),
        "motion_prompt": "the characters react with one quick exaggerated comedic beat, subtle camera push-in",
        "video_tool": "happyhorse-i2v",
    }
    if shots > 1:
        one["shots"] = [
            {"keyframe_prompt": one["keyframe_prompt"] + f" (beat {i+1})",
             "motion_prompt": one["motion_prompt"]}
            for i in range(shots)
        ]
    return json.dumps(one, ensure_ascii=False)


def run(script: str, characters: list[dict], qa_notes: str = "", shots: int = 1) -> dict:
    visuals = "\n".join(f"- {c['name']}: {c.get('visual_desc', '')}" for c in characters)
    user = USER_TMPL.format(script=script, visuals=visuals)
    if shots > 1:
        user += (
            f"\n\nThis episode is a {shots}-SHOT mini-arc (setup → escalation → punchline). "
            f'ALSO return a "shots" array of exactly {shots} objects — each '
            '{"keyframe_prompt": "...", "motion_prompt": "..."} — one per shot IN ORDER, '
            "keeping the SAME characters in their exact established look across every shot, "
            "so the arc reads as one continuous scene."
        )
    if qa_notes.strip():
        # Closed feedback loop: the previous take was rejected — fix it specifically.
        user += (
            f"\n\nIMPORTANT — the previous attempt was REJECTED by QA for this reason:\n"
            f'"{qa_notes.strip()}"\n'
            "Redesign the keyframe and motion to directly FIX that problem: make the main "
            "action and the involved characters unmistakably clear and correct."
        )
    text = chat(SYSTEM, user, temperature=0.7, mock=_mock(script, characters, shots))
    data = parse_json(text)
    kf = _norm_kf(data.get("keyframe_prompt"))
    motion = data.get("motion_prompt", "one quick exaggerated comedic beat, subtle camera push-in")
    raw_shots = data.get("shots")
    if isinstance(raw_shots, list) and len(raw_shots) > 1:
        shot_list = [{"keyframe_prompt": _norm_kf(s.get("keyframe_prompt")),
                      "motion_prompt": s.get("motion_prompt", motion)} for s in raw_shots[:shots]]
    else:
        shot_list = [{"keyframe_prompt": kf, "motion_prompt": motion}]
    return {
        "keyframe_prompt": kf,
        "motion_prompt": motion,
        "video_tool": data.get("video_tool", "happyhorse-i2v"),
        "shots": shot_list,
    }
