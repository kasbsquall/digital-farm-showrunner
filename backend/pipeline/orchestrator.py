"""Pipeline orchestration: runs the 4 agents in sequence.

Day 1-2: plain sequential runner (this file) so we can test end-to-end now.
Day 3: this gets ported to LangGraph, keeping the same QA -> Director regen loop.

Sequence:
  scriptwriter -> production_director -> [video gen] -> qa_reviewer
                                              ▲            │
                                              └── reject ──┘ (up to MAX_REGEN)
                                                         │ approve
                                                         ▼
                                                     packager
"""
from sqlalchemy.orm import Session

from database.models import Character, Episode
from agents import scriptwriter, production_director, qa_reviewer, packager
from services.video_gen_client import generate_video

MAX_REGEN = 2  # QA can bounce back to the Director this many times before giving up.
RECENT_LIMIT = 5


def _load_context(db: Session) -> tuple[list[dict], list[str]]:
    characters = [
        {
            "name": c.name,
            "species": c.species,
            "personality": c.personality,
            "visual_desc": c.visual_desc,
        }
        for c in db.query(Character).all()
    ]
    recent = [
        e.event
        for e in db.query(Episode).order_by(Episode.created_at.desc()).limit(RECENT_LIMIT)
        if e.event
    ]
    return characters, recent


def run_daily_episode(db: Session) -> Episode:
    characters, recent = _load_context(db)

    # Agent 1 — Scriptwriter
    story = scriptwriter.run(characters, recent)
    used = [c for c in characters if c["name"] in story["characters_used"]] or characters

    episode = Episode(
        event=story["event"],
        script=story["script"],
        characters_used=story["characters_used"],
    )

    # Agent 2 + video gen + Agent 3, with regen loop.
    qa = {"qa_status": "rejected", "qa_notes": ""}
    attempt = 0
    while attempt <= MAX_REGEN:
        direction = production_director.run(story["script"], used)
        video_url = generate_video(direction["video_prompt"], direction["video_tool"])
        qa = qa_reviewer.run(video_url, story["script"], direction["video_prompt"])
        attempt += 1

        episode.video_prompt = direction["video_prompt"]
        episode.video_tool = direction["video_tool"]
        episode.video_url = video_url
        episode.qa_status = qa["qa_status"]
        episode.qa_notes = qa["qa_notes"]
        episode.qa_attempts = attempt

        if qa["qa_status"] == "approved":
            break

    # Agent 4 — Packager (only meaningful when approved, but we always package
    # the best take so nothing is lost).
    pack = packager.run(story["event"], story["script"])
    episode.title = pack["title"]
    episode.thumbnail_hint = pack["thumbnail_hint"]
    episode.description = pack["description"]
    episode.status = "published" if qa["qa_status"] == "approved" else "draft"

    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode
