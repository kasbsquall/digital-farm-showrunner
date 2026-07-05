"""Agent 4 — Packager.

Takes the approved episode and produces a publish-ready title, thumbnail hint
and description — as if launching a daily channel drop.
"""
import json

from services.qwen_client import chat
from agents._json import parse_json

SYSTEM = (
    "Eres el editor de un canal viral de micro-dramas de granja en arcilla. "
    "Escribes títulos y descripciones CON GANCHO, en español, que capturan el gag "
    "EXACTO que ocurre en el video (la acción y su causa-efecto), con humor y ritmo. "
    "Nada de relleno genérico: si el gallo golpea el pan, dilo. Respondes SIEMPRE en JSON válido."
)

USER_TMPL = """Evento del episodio: {event}

Guion:
{script}

LO QUE REALMENTE SE VE EN EL VIDEO (prioriza esto para que el texto coincida):
{video_description}

Genera el paquete de publicación. El título y la descripción deben reflejar lo
que de verdad se ve en el video (arriba), no solo el guion. Devuelve JSON exacto:
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


def run(event: str, script: str, video_description: str = "") -> dict:
    desc = video_description.strip() or "(no disponible — usa el guion)"
    text = chat(
        SYSTEM,
        USER_TMPL.format(event=event, script=script, video_description=desc),
        temperature=0.8,
        mock=_mock(event, script),
    )
    data = parse_json(text)
    return {
        "title": data["title"],
        "thumbnail_hint": data["thumbnail_hint"],
        "description": data["description"],
    }
