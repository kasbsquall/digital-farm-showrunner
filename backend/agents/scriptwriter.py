"""Agent 1 — Scriptwriter.

Decides today's absurd event and writes a tiny script that resolves in a single
instant visual gag (the video is only ~5 seconds). English output.
"""
import json

from services.qwen_client import chat
from agents._json import parse_json

SYSTEM = (
    "You are the writer of a viral daily channel of absurd claymation farm micro-dramas. "
    "You write in ENGLISH with wild, ridiculous, laugh-out-loud slapstick humor. Since each "
    "video is only ~5 SECONDS, the whole thing must be ONE instant, CRAZY, unexpected visual "
    "gag that lands immediately — the more absurd the better (a duck brandishing a tiny "
    "bazooka, a goose bodyslamming a scarecrow, a pig launched by a catapult). Think "
    "physical, explosive, cartoonish, meme-worthy. Keep loose continuity between episodes. "
    "You ALWAYS answer in valid JSON, no extra text."
)

USER_TMPL = """Available characters (use 2 or 3):
{cast}

Recent events (avoid repeating, but you may build continuity):
{recent}
{idea}
Invent TODAY'S absurd event and write a very short script whose punchline is a single
instant physical gag that can play out in ~5 seconds.

Return exactly this JSON:
{{"event": "<one sentence describing the event>",
  "script": "<short script, format CHARACTER: line>",
  "characters_used": ["<name>", "..."]}}"""


def _mock(characters: list[dict], recent_events: list[str]) -> str:
    ideas = [
        {
            "event": "Bruno the rooster tries to raise his protest placard but smacks a falling bread into Pepe's mouth.",
            "script": ("BRUNO: Workers of the mud, RISE UP!\n"
                       "PEPE: (mouth full) ...the revolution tastes like sourdough.\n"
                       "NINA: Breaking news: bread solidarity achieved."),
            "characters_used": ["Bruno", "Pepe", "Nina"],
        },
        {
            "event": "Lola falls in love with a shiny bucket and tries to serenade it.",
            "script": ("LOLA: My love, you reflect my soul!\n"
                       "MOMO: It's a bucket.\n"
                       "LOLA: Don't ruin this for us."),
            "characters_used": ["Lola", "Momo"],
        },
        {
            "event": "Kiki the goose honks so hard she launches Bex the sheep into the air.",
            "script": ("KIKI: HONK! No trespassing!\n"
                       "BEX: I wasn't even— AAAH!\n"
                       "DORA: I KNEW the pond was a trap."),
            "characters_used": ["Kiki", "Bex", "Dora"],
        },
    ]
    return json.dumps(ideas[len(recent_events) % len(ideas)], ensure_ascii=False)


def run(characters: list[dict], recent_events: list[str], idea: str = "") -> dict:
    cast = "\n".join(f"- {c['name']} ({c['species']}): {c['personality']}" for c in characters)
    recent = "\n".join(f"- {e}" for e in recent_events) or "- (none yet)"
    idea_block = f"\nUSER-SUGGESTED idea (respect it as the base): {idea}\n" if idea.strip() else ""
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
