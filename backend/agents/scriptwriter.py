"""Agent 1 — Scriptwriter.

Decides today's absurd event and writes a tiny script that resolves in a single
instant visual gag (the video is only ~5 seconds). English output.
"""
import json

from services.qwen_client import chat
from agents._json import parse_json

SYSTEM = (
    "You are the head writer of MUCKFLIX, a viral daily channel of claymation farm "
    "micro-dramas in the Aardman / Wallace-and-Gromit style. Every episode is a SINGLE "
    "~5-second clip, so each one is ONE crisp, hilarious, PHYSICAL sight-gag that reads "
    "instantly: exaggerated cartoon slapstick — a character getting launched, squished, "
    "faceplanting, buried under an avalanche of hay, bonked on the head by a falling "
    "object, headbutting something across the yard, or having a huge over-the-top "
    "reaction. Big physical comedy and expressive faces beat dialogue. Keep it "
    "wholesome-absurd and meme-worthy: NO real weapons, blood or anything a stop-motion "
    "kids' film wouldn't show — reframe any 'weapon' idea as a silly prop or slapstick "
    "mishap. Use ONLY the given farm animals, true to their personalities. A little "
    "continuity between episodes is a bonus. You ALWAYS answer in valid JSON, no extra text."
)

USER_TMPL = """Farm cast available (use 2, maybe 3):
{cast}

Recent episodes (don't repeat these, light continuity is welcome):
{recent}
{idea}
Write TODAY'S episode as ONE instant physical gag that can be shown in ~5 seconds, with a
clear cause and effect (who does what to whom, and the funny result).

Return exactly this JSON:
{{"event": "<one vivid sentence: the single funny thing that happens, cause -> effect>",
  "script": "<2-4 short punchy lines, format CHARACTER: line, ending right as the gag lands>",
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
