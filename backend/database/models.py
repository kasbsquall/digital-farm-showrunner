"""Data models: Character, Episode. Kept minimal for the MVP pipeline."""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, Float, String, Text, DateTime, JSON, UniqueConstraint

from database.db import Base

# A channel is one creator's show: its own cast + its own audience whose votes bias
# only that channel's writing. The demo runs a single "farm" channel by default.
DEFAULT_CHANNEL = "farm"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Character(Base):
    """A recurring character used as narrative context by Agent 1 (scoped to a channel)."""
    __tablename__ = "characters"
    __table_args__ = (UniqueConstraint("channel_id", "name", name="uq_character_channel_name"),)

    id = Column(Integer, primary_key=True)
    channel_id = Column(String(48), default=DEFAULT_CHANNEL, nullable=False, index=True)
    name = Column(String(64), nullable=False)  # unique per channel (see __table_args__)
    species = Column(String(64), nullable=False)
    personality = Column(Text, nullable=False)
    visual_desc = Column(Text, nullable=False)
    image_url = Column(Text)  # retrato generado por IA (en OSS)


class Episode(Base):
    """One generated daily micro-drama, from script to packaged release."""
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True)
    channel_id = Column(String(48), default=DEFAULT_CHANNEL, nullable=False, index=True)
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
    # Auditable take history: each attempt's clip + what vision saw + the QA verdict,
    # so the self-correcting loop (rejected take → corrected take) is provable.
    takes = Column(JSON)  # list[dict]: attempt, video_url, thumbnail_url, vision, qa_status, qa_notes, qa_score

    # Token/cost receipt — makes "quality under a token budget" measurable.
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)

    # Agent 4 — Packager
    title = Column(String(200))
    thumbnail_hint = Column(Text)
    thumbnail_url = Column(Text)  # AI-generated thumbnail (on OSS)
    description = Column(Text)

    status = Column(String(16), default="draft")  # draft | published
    votes = Column(Integer, default=0)  # denormalized count of Vote rows (data flywheel signal)


class Vote(Base):
    """One audience upvote, deduped per (episode, voter) so the flywheel can't be
    trivially spammed by re-posting. `voter_id` is a client-supplied stable id."""
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("episode_id", "voter_id", name="uq_vote_episode_voter"),)

    id = Column(Integer, primary_key=True)
    episode_id = Column(Integer, nullable=False, index=True)
    voter_id = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=_now)
