"""Seed the base farm cast so the Scriptwriter has continuity from day one.

Run:  python -m database.seed_characters
All animals, all claymation. Descriptions in English (content is generated in English).
"""
from database.db import Base, engine, SessionLocal
from database.models import Character

# Shared style so every portrait/keyframe looks like the same clay universe.
CLAY = ("claymation stop-motion plasticine character, Aardman-style, visible fingerprints "
        "in the clay, big expressive eyes, chunky proportions")

BASE_CAST = [
    {
        "name": "Bruno",
        "species": "rooster",
        "personality": "The tireless union leader of the coop. Turns every tiny inconvenience into a strike, a rally or a heroic speech about workers' rights.",
        "visual_desc": f"A bold red {CLAY}, huge floppy comb, always clutching a tiny handmade protest placard, confident chest-out posture.",
    },
    {
        "name": "Lola",
        "species": "cow",
        "personality": "A hopeless romantic who falls head-over-hooves in love with the most random objects — a fencepost, a passing cloud, a shiny bucket.",
        "visual_desc": f"A white cow with black spots, {CLAY}, big dreamy lovestruck eyes, a little daisy tucked behind one ear.",
    },
    {
        "name": "Pepe",
        "species": "pig",
        "personality": "The mud philosopher. Comments on everything with deep-sounding nonsense while never leaving his puddle.",
        "visual_desc": f"A chubby pink pig lounging in mud, {CLAY}, a straw of hay in his mouth, half-closed thoughtful eyes.",
    },
    {
        "name": "Nina",
        "species": "hen",
        "personality": "The coop's breaking-news reporter. Documents every trivial event as a world-shaking scoop.",
        "visual_desc": f"A small nervous brown hen, {CLAY}, tiny notebook and pencil, wide alert eyes, feathers slightly frazzled.",
    },
    {
        "name": "Gus",
        "species": "goat",
        "personality": "A chaotic troublemaker who eats absolutely everything — laundry, fences, important documents — with zero remorse.",
        "visual_desc": f"A scruffy grey goat with a lopsided grin, {CLAY}, one horn slightly bent, a scrap of chewed cloth hanging from his mouth.",
    },
    {
        "name": "Dora",
        "species": "duck",
        "personality": "A dramatic diva and conspiracy theorist who is convinced everything on the farm is a plot against her.",
        "visual_desc": f"A glossy white duck with an over-the-top expression, {CLAY}, tiny sunglasses pushed up on her head, suspicious raised brow.",
    },
    {
        "name": "Bex",
        "species": "sheep",
        "personality": "An anxious overthinker who agrees with whoever spoke last and panics about decisions that don't matter.",
        "visual_desc": f"A fluffy cream sheep with a worried face, {CLAY}, enormous nervous eyes, wool sticking out in tufts.",
    },
    {
        "name": "Momo",
        "species": "donkey",
        "personality": "The deadpan pessimist. Responds to every exciting event with a flat, gloomy one-liner.",
        "visual_desc": f"A grey droopy-eared donkey with heavy eyelids, {CLAY}, unimpressed deadpan expression, slightly slouched.",
    },
    {
        "name": "Kiki",
        "species": "goose",
        "personality": "The self-appointed, extremely aggressive security guard of the pond. Honks first, asks questions never.",
        "visual_desc": f"A white goose mid-honk with wings flared, {CLAY}, furious tiny eyes, neck stretched forward menacingly.",
    },
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        added = 0
        for data in BASE_CAST:
            if db.query(Character).filter_by(name=data["name"]).first():
                continue
            db.add(Character(**data))
            added += 1
        db.commit()
        print(f"Seed done. New characters: {added}. Total: {db.query(Character).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
