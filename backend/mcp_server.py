"""MCP (Model Context Protocol) server for The Digital Farm Showrunner.

Exposes the showrunner pipeline as callable MCP tools over stdio, so a Qwen/LLM
agent can drive it: generate episodes, manage the cast, and read back history.

Each tool opens its own ``SessionLocal()`` and closes it in a ``finally`` block
(the FastAPI request-scoped ``get_db`` dependency isn't available here). The tool
logic mirrors the FastAPI endpoints in ``main.py`` so behavior stays identical.

Run it as a stdio server:

    cd backend && python mcp_server.py

Register it with an MCP-capable client (Qwen agent, Claude Desktop, etc.) by
pointing the client at that command with ``backend/`` as the working directory.

Built on the official ``mcp`` Python SDK (``mcp.server.fastmcp.FastMCP``).
"""
from mcp.server.fastmcp import FastMCP
from sqlalchemy.orm import Session

from database.db import SessionLocal
from database.models import Character, Episode
from database.generate_portraits import STYLE
from pipeline.orchestrator import run_daily_episode
from services import image_gen_client, oss_client
from config import settings

mcp = FastMCP("digital-farm-showrunner")


def _episode_dict(e: Episode) -> dict:
    """Serialize an Episode to a plain dict (same field mapping as main._episode_dict)."""
    return {
        "id": e.id,
        "creator": e.creator,
        "title": e.title,
        "event": e.event,
        "script": e.script,
        "characters_used": e.characters_used,
        "video_prompt": e.video_prompt,
        "video_tool": e.video_tool,
        "video_url": e.video_url,
        "video_description": e.video_description,
        "qa_status": e.qa_status,
        "qa_notes": e.qa_notes,
        "qa_attempts": e.qa_attempts,
        "takes": e.takes or [],
        "thumbnail_hint": e.thumbnail_hint,
        "thumbnail_url": e.thumbnail_url,
        "description": e.description,
        "status": e.status,
    }


def _character_dict(c: Character) -> dict:
    return {"name": c.name, "species": c.species, "personality": c.personality,
            "image_url": c.image_url}


@mcp.tool()
def generate_episode(idea: str = "", creator: str = "") -> dict:
    """Run the full 4-agent pipeline and return the new episode as a dict.

    idea: optional creative seed for the day's micro-drama.
    creator: optional nickname credited on the episode.
    """
    db: Session = SessionLocal()
    try:
        episode = run_daily_episode(db, idea=idea[:500], creator=creator[:48])
        return _episode_dict(episode)
    finally:
        db.close()


@mcp.tool()
def create_character(name: str, personality: str, species: str = "creature",
                     look: str = "") -> dict:
    """Add a claymation character to the cast (with an AI portrait when enabled).

    Mirrors POST /characters. Raises on empty or duplicate name.
    """
    db: Session = SessionLocal()
    try:
        clean_name = name.strip()[:32]
        if not clean_name:
            raise ValueError("A name is required.")
        if db.query(Character).filter_by(name=clean_name).first():
            raise ValueError(f"'{clean_name}' is already in the cast.")

        look_desc = (look.strip() or f"a {species}, {personality}")
        visual_desc = (
            f"{look_desc}. claymation stop-motion plasticine character, Aardman-style, "
            "visible fingerprints in the clay, big expressive eyes, chunky proportions."
        )

        image_url = None
        if not settings.use_mock or settings.create_real_portraits:
            try:
                temp = image_gen_client.generate_image(f"{look_desc}. {STYLE}")
                image_url = (oss_client.persist_image(temp, prefix="characters")
                             if oss_client.is_configured() else temp)
            except Exception as e:  # out of image quota / API error → character still created
                print(f"[create_character] portrait generation failed: {e}")

        c = Character(
            name=clean_name,
            species=species.strip()[:32] or "creature",
            personality=personality.strip()[:400],
            visual_desc=visual_desc,
            image_url=image_url,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        return _character_dict(c)
    finally:
        db.close()


@mcp.tool()
def list_episodes(limit: int = 10) -> list[dict]:
    """Return the most recent episodes (newest first)."""
    db: Session = SessionLocal()
    try:
        rows = (db.query(Episode).order_by(Episode.created_at.desc())
                .limit(max(1, limit)).all())
        return [_episode_dict(e) for e in rows]
    finally:
        db.close()


@mcp.tool()
def list_characters() -> list[dict]:
    """Return the full cast of characters."""
    db: Session = SessionLocal()
    try:
        return [_character_dict(c) for c in db.query(Character).all()]
    finally:
        db.close()


@mcp.tool()
def get_episode(episode_id: int) -> dict:
    """Return one episode by id, including its full `takes` history."""
    db: Session = SessionLocal()
    try:
        e = db.query(Episode).filter_by(id=episode_id).first()
        if not e:
            raise ValueError(f"Episode {episode_id} not found.")
        return _episode_dict(e)
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()
