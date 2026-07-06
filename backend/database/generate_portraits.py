"""Generate one AI portrait per farm character and store it in OSS.

Run:  python -m database.generate_portraits
Idempotent: skips characters that already have an image_url.
"""
from database.db import SessionLocal
from database.models import Character
from services.image_gen_client import generate_image
from services import oss_client

STYLE = (
    "charming claymation / stop-motion EXTREME CLOSE-UP portrait, the animal's head "
    "and face FILL THE ENTIRE FRAME edge to edge, cropped very tight with the top of "
    "the head touching the top edge, absolutely NO empty background or headroom above, "
    "soft studio lighting, big expressive face, high detail, cohesive children's "
    "animated film style"
)


def run() -> None:
    db = SessionLocal()
    try:
        chars = db.query(Character).all()
        for c in chars:
            if c.image_url:
                print(f"· {c.name}: ya tiene retrato, se omite")
                continue
            prompt = f"{c.visual_desc}. {STYLE}"
            print(f"→ generando retrato de {c.name}...")
            temp_url = generate_image(prompt)
            c.image_url = oss_client.persist_image(temp_url, prefix="characters")
            db.commit()
            print(f"  ✓ {c.name}: {c.image_url}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
