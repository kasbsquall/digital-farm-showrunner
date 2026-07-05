"""Agent 1 — Scriptwriter.

Decides today's absurd event and writes a short (20-30s) dialogue script,
keeping continuity with recent events. Uses a Qwen reasoning model.
"""
from services.qwen_client import chat
from agents._json import parse_json

SYSTEM = (
    "Eres el guionista de una granja digital de micro-dramas absurdos y virales. "
    "Escribes en español, con humor tonto pero encantador. Mantienes continuidad "
    "entre episodios. Respondes SIEMPRE en JSON válido, sin texto extra."
)

USER_TMPL = """Personajes disponibles (usa 2 o 3):
{cast}

Eventos recientes (evita repetir, pero puedes dar continuidad):
{recent}
{idea}
Inventa el EVENTO ABSURDO de hoy y escribe un guion corto de 20-30 segundos con
diálogo simple entre los animales involucrados.

Devuelve JSON exacto con esta forma:
{{"event": "<una frase describiendo el evento>",
  "script": "<guion con diálogo, formato PERSONAJE: línea>",
  "characters_used": ["<nombre>", "..."]}}"""


def _mock(characters: list[dict], recent_events: list[str]) -> str:
    ideas = [
        {
            "event": "Bruno organiza una huelga porque el gallo del pueblo vecino canta más temprano.",
            "script": ("BRUNO: ¡Camaradas, exijo horario justo de cacareo!\n"
                       "NINA: (anotando) Última hora: el gallinero se levanta en armas.\n"
                       "PEPE: El amanecer es solo una idea... impuesta por el sol."),
            "characters_used": ["Bruno", "Nina", "Pepe"],
        },
        {
            "event": "Lola le escribe un poema al Tractor y espera respuesta.",
            "script": ("LOLA: Tractor, mi motor arde por ti.\n"
                       "TRACTOR: ...bip.\n"
                       "PEPE: El amor correspondido es una avería del alma."),
            "characters_used": ["Lola", "Tractor", "Pepe"],
        },
        {
            "event": "Nina inventa un noticiero en vivo sobre un charco misterioso.",
            "script": ("NINA: ¡El charco ha crecido tres centímetros!\n"
                       "BRUNO: ¡Es sabotaje del sistema!\n"
                       "LOLA: ¿Y si el Tractor lo cruza y me rescata?"),
            "characters_used": ["Nina", "Bruno", "Lola"],
        },
    ]
    idea = ideas[len(recent_events) % len(ideas)]
    import json
    return json.dumps(idea, ensure_ascii=False)


def run(characters: list[dict], recent_events: list[str], idea: str = "") -> dict:
    cast = "\n".join(f"- {c['name']} ({c['species']}): {c['personality']}" for c in characters)
    recent = "\n".join(f"- {e}" for e in recent_events) or "- (ninguno todavía)"
    idea_block = f"\nIDEA SUGERIDA por el usuario (respétala como base): {idea}\n" if idea.strip() else ""
    text = chat(
        SYSTEM,
        USER_TMPL.format(cast=cast, recent=recent, idea=idea_block),
        temperature=0.9,
        mock=_mock(characters, recent_events),
    )
    data = parse_json(text)
    return {
        "event": data["event"],
        "script": data["script"],
        "characters_used": data["characters_used"],
    }
