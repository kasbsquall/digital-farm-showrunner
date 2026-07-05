"""Agent 4 — Packager.

Takes the approved episode and produces a publish-ready title, thumbnail hint
and description — as if launching a daily channel drop.
"""
import json

from services.qwen_client import chat
from agents._json import parse_json

SYSTEM = (
    "Eres el encargado de publicar un canal diario de micro-dramas de granja. "
    "Creas títulos virales, ideas de thumbnail y descripciones atractivas en "
    "español. Respondes SIEMPRE en JSON válido."
)

USER_TMPL = """Evento del episodio: {event}

Guion:
{script}

Genera el paquete de publicación. Devuelve JSON exacto:
{{"title": "<título viral, con 1-2 emojis>",
  "thumbnail_hint": "<descripción visual del thumbnail sugerido>",
  "description": "<2-3 frases + 3 hashtags>"}}"""


def _mock(event: str, script: str) -> str:
    return json.dumps(
        {
            "title": "🐔 El día que la granja se rebeló",
            "thumbnail_hint": ("Primer plano de Bruno el gallo con expresión indignada "
                               "sosteniendo una pancarta, colores saturados, fondo del corral."),
            "description": (f"{event} Un nuevo capítulo del drama diario más absurdo del corral. "
                            "#GranjaDigital #IA #MicroDrama"),
        },
        ensure_ascii=False,
    )


def run(event: str, script: str) -> dict:
    text = chat(
        SYSTEM,
        USER_TMPL.format(event=event, script=script),
        temperature=0.8,
        mock=_mock(event, script),
    )
    data = parse_json(text)
    return {
        "title": data["title"],
        "thumbnail_hint": data["thumbnail_hint"],
        "description": data["description"],
    }
