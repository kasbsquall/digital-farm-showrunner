"""Seed the DB from a committed snapshot (characters + real episodes).

Lets a fresh deployment (e.g. Alibaba Cloud ECS) show the full, polished app —
portraits and real videos served from public OSS — with ZERO API calls or credits.

Run:  python -m database.seed_from_snapshot
Idempotent: skips rows that already exist (characters by name, episodes by title).
"""
import json
import pathlib

from database.db import Base, engine, SessionLocal
from database.models import Character, Episode

SNAPSHOT = pathlib.Path(__file__).with_name("snapshot.json")


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    if not SNAPSHOT.exists():
        print("No snapshot.json found — skipping.")
        return
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        c_added = e_added = 0
        for c in data.get("characters", []):
            if db.query(Character).filter_by(name=c["name"]).first():
                continue
            db.add(Character(**c))
            c_added += 1
        for e in data.get("episodes", []):
            if e.get("title") and db.query(Episode).filter_by(title=e["title"]).first():
                continue
            db.add(Episode(**e))
            e_added += 1
        db.commit()
        print(f"Snapshot seeded. Characters +{c_added}, episodes +{e_added}.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
