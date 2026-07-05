"""Agent 2 — Production Director.

Turns the script into a technical text-to-video prompt: scene, characters,
camera framing, visual tone. Picks the generation tool (wan | happyhorse).
"""
import json

from services.qwen_client import chat
from agents._json import parse_json

SYSTEM = (
    "Eres director de producción de video generado por IA. Traduces un guion en un "
    "prompt técnico en inglés para un modelo text-to-video. Describes escena, "
    "personajes, encuadre de cámara y tono visual. Respondes SIEMPRE en JSON válido."
)

USER_TMPL = """Guion:
{script}

Descripciones visuales de los personajes:
{visuals}

Crea el prompt de generación de video (en inglés, cinematográfico, un solo párrafo,
sin diálogo hablado — describe la acción visual). Elige la herramienta:
- "wan" para escenas con movimiento/acción física.
- "happyhorse" para escenas expresivas de personajes/emoción.

Devuelve JSON exacto:
{{"video_prompt": "<prompt en inglés>", "video_tool": "wan"|"happyhorse"}}"""


def _mock(script: str, characters: list[dict]) -> str:
    names = ", ".join(c["name"] for c in characters)
    prompt = (
        f"Cinematic barnyard scene, claymation style, featuring {names}. "
        "Warm golden-hour light, shallow depth of field, medium tracking shot. "
        "Expressive cartoon farm animals acting out an absurd everyday drama, "
        "playful comedic timing, vivid saturated colors, 24fps, 25 seconds."
    )
    tool = "wan" if "huelga" in script.lower() or "cruza" in script.lower() else "happyhorse"
    return json.dumps({"video_prompt": prompt, "video_tool": tool}, ensure_ascii=False)


def run(script: str, characters: list[dict]) -> dict:
    visuals = "\n".join(f"- {c['name']}: {c.get('visual_desc', '')}" for c in characters)
    text = chat(
        SYSTEM,
        USER_TMPL.format(script=script, visuals=visuals),
        temperature=0.5,
        mock=_mock(script, characters),
    )
    data = parse_json(text)
    tool = data.get("video_tool", "wan")
    if tool not in ("wan", "happyhorse"):
        tool = "wan"
    return {"video_prompt": data["video_prompt"], "video_tool": tool}
