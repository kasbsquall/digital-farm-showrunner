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
    "Eres director de producción de video IA. Un video dura solo ~5 SEGUNDOS, así "
    "que diseñas UN gag visual instantáneo: una sola acción que se lee de golpe y "
    "da risa en el momento. Describes personajes fieles a su apariencia establecida. "
    "Respondes SIEMPRE en JSON válido, en inglés para los prompts."
)

USER_TMPL = """Guion (concepto):
{script}

Apariencia FIEL de los personajes (respétala al pie de la letra para consistencia):
{visuals}

Diseña el episodio de 5 segundos. Devuelve JSON exacto:
{{"keyframe_prompt": "<prompt en inglés de UNA imagen fija: el instante más gracioso,
   claymation stop-motion style, con los personajes tal cual su apariencia, encuadre
   cinematográfico, fondo de granja>",
  "motion_prompt": "<prompt en inglés de la ÚNICA acción de ~5s que anima esa imagen:
   un movimiento simple y cómico, cámara sutil>",
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
