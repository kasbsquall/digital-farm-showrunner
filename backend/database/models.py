"""Data models: Character, Episode. Kept minimal for the MVP pipeline."""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON

from database.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Character(Base):
    """A recurring farm character used as narrative context by Agent 1."""
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False)
    species = Column(String(64), nullable=False)
    personality = Column(Text, nullable=False)
    visual_desc = Column(Text, nullable=False)
    image_url = Column(Text)  # retrato generado por IA (en OSS)


class Episode(Base):
    """One generated daily micro-drama, from script to packaged release."""
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=_now)
    creator = Column(String(48))  # nickname of whoever prompted this episode

    # Agent 1 — Scriptwriter
    event = Column(Text)          # the absurd event of the day
    script = Column(Text)         # short dialogue script
    characters_used = Column(JSON)  # list of character names, for continuity

    # Agent 2 — Production Director
    video_prompt = Column(Text)
    video_tool = Column(String(32))   # "wan" | "happyhorse"
    video_url = Column(Text)
    video_description = Column(Text)  # what Qwen vision actually sees in the video

    # Agent 3 — QA Reviewer
    qa_status = Column(String(16), default="pending")  # approved | rejected | pending
    qa_notes = Column(Text)
    qa_attempts = Column(Integer, default=0)

    # Agent 4 — Packager
    title = Column(String(200))
    thumbnail_hint = Column(Text)
    thumbnail_url = Column(Text)  # thumbnail generado por IA (en OSS)
    description = Column(Text)

    status = Column(String(16), default="draft")  # draft | published
