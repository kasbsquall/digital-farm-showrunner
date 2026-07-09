"""FastAPI app for The Digital Farm Showrunner.

Day 1: healthcheck + list characters + list episodes so the scaffolding is
verifiably alive. Episode-generation endpoint gets wired once the pipeline exists.
"""
from contextlib import asynccontextmanager

import json

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sqlalchemy.exc import IntegrityError

from database.db import Base, engine, get_db, SessionLocal
from database.models import Character, Episode, Vote, DEFAULT_CHANNEL
from database.generate_portraits import STYLE
from pipeline.orchestrator import run_daily_episode, run_stream, channel_lock
from services import image_gen_client, oss_client
from config import settings
import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    scheduler.start_background()  # unattended daily channel (no-op unless SCHEDULER_ENABLED)
    yield


app = FastAPI(title="The Digital Farm Showrunner", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _episode_dict(e: Episode) -> dict:
    return {
        "id": e.id,
        "channel_id": e.channel_id,
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
        "tokens_used": e.tokens_used or 0,
        "cost_usd": e.cost_usd or 0.0,
        "votes": e.votes or 0,
        "thumbnail_hint": e.thumbnail_hint,
        "thumbnail_url": e.thumbnail_url,
        "description": e.description,
        "status": e.status,
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "digital-farm-showrunner",
        "mock_text": settings.use_mock,
        "mock_video": settings.mock_video,
    }


class GenerateRequest(BaseModel):
    idea: str = ""
    creator: str = ""
    channel: str = DEFAULT_CHANNEL


@app.post("/episodes/generate")
def generate_episode(req: GenerateRequest | None = None, db: Session = Depends(get_db)):
    """Run the full 4-agent pipeline and return the new episode."""
    idea = (req.idea if req else "")[:500]
    creator = (req.creator if req else "")[:48]
    channel = ((req.channel if req else "") or DEFAULT_CHANNEL).strip()[:48] or DEFAULT_CHANNEL
    # Per-channel single-flight: this channel serializes, but other channels run concurrently.
    lock = channel_lock(channel)
    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail=f"A generation is already running for channel '{channel}'. Try again shortly.")
    try:
        episode = run_daily_episode(db, idea=idea, creator=creator, channel_id=channel)
        return _episode_dict(episode)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}")
    finally:
        lock.release()


@app.get("/episodes/generate/stream")
def generate_episode_stream(
    idea: str = Query("", max_length=500),
    creator: str = Query("", max_length=48),
    channel: str = Query(DEFAULT_CHANNEL, max_length=48),
):
    """Server-Sent Events: emits each pipeline stage live for the Studio wizard."""
    channel_id = (channel or DEFAULT_CHANNEL).strip()[:48] or DEFAULT_CHANNEL

    def event_source():
        lock = channel_lock(channel_id)
        if not lock.acquire(blocking=False):
            yield f"event: failed\ndata: {json.dumps({'message': f'A generation is already running for channel {channel_id!r}. Please wait for it to finish.'})}\n\n"
            return
        db = SessionLocal()
        try:
            for stage, data in run_stream(db, idea=idea, creator=creator, channel_id=channel_id):
                yield f"event: {stage}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
        except Exception as e:  # surface failures to the client
            db.rollback()
            yield f"event: failed\ndata: {json.dumps({'message': str(e)})}\n\n"
        finally:
            db.close()
            lock.release()

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/characters")
def list_characters(channel: str = Query(DEFAULT_CHANNEL, max_length=48), db: Session = Depends(get_db)):
    rows = db.query(Character).filter(Character.channel_id == channel).all()
    return [
        {"name": c.name, "species": c.species, "personality": c.personality,
         "image_url": c.image_url}
        for c in rows
    ]


@app.get("/episodes")
def list_episodes(channel: str = Query(DEFAULT_CHANNEL, max_length=48), db: Session = Depends(get_db)):
    rows = (db.query(Episode).filter(Episode.channel_id == channel)
            .order_by(Episode.created_at.desc()).all())
    return [_episode_dict(e) for e in rows]


class VoteRequest(BaseModel):
    voter_id: str = ""


@app.post("/episodes/{episode_id}/vote")
def vote_episode(episode_id: int, req: VoteRequest | None = None, db: Session = Depends(get_db)):
    """Audience upvote — the data flywheel. Idempotent per (episode, voter): re-posting
    the same vote does not inflate the count, so the signal can't be trivially spammed."""
    ep = db.get(Episode, episode_id)
    if ep is None:
        raise HTTPException(status_code=404, detail="Episode not found.")
    voter = ((req.voter_id if req else "") or "").strip()[:64]
    if not voter:
        raise HTTPException(status_code=400, detail="A voter_id is required.")
    if db.query(Vote).filter(Vote.episode_id == episode_id, Vote.voter_id == voter).first():
        return {"id": ep.id, "votes": ep.votes or 0, "counted": False}
    db.add(Vote(episode_id=episode_id, voter_id=voter))
    ep.votes = (ep.votes or 0) + 1
    try:
        db.commit()
    except IntegrityError:  # concurrent duplicate slipped past the check → treat as already-counted
        db.rollback()
        db.refresh(ep)
        return {"id": ep.id, "votes": ep.votes or 0, "counted": False}
    return {"id": ep.id, "votes": ep.votes, "counted": True}


class CreateCharacter(BaseModel):
    name: str
    species: str = "creature"
    personality: str
    look: str = ""
    channel: str = DEFAULT_CHANNEL


@app.post("/characters")
def create_character(req: CreateCharacter, db: Session = Depends(get_db)):
    """Let anyone add their own claymation character to the cast (with an AI portrait)."""
    name = req.name.strip()[:32]
    channel = (req.channel or DEFAULT_CHANNEL).strip()[:48] or DEFAULT_CHANNEL
    if not name:
        raise HTTPException(status_code=400, detail="A name is required.")
    if db.query(Character).filter_by(channel_id=channel, name=name).first():
        raise HTTPException(status_code=409, detail=f"'{name}' is already in the cast.")

    look = (req.look.strip() or f"a {req.species}, {req.personality}")
    visual_desc = f"{look}. claymation stop-motion plasticine character, Aardman-style, visible fingerprints in the clay, big expressive eyes, chunky proportions."

    image_url = None
    if not settings.use_mock or settings.create_real_portraits:
        try:
            temp = image_gen_client.generate_image(f"{look}. {STYLE}")
            image_url = oss_client.persist_image(temp, prefix="characters") if oss_client.is_configured() else temp
        except Exception as e:  # out of image quota / API error → character still created
            print(f"[create_character] portrait generation failed: {e}")

    c = Character(
        channel_id=channel,
        name=name,
        species=req.species.strip()[:32] or "creature",
        personality=req.personality.strip()[:400],
        visual_desc=visual_desc,
        image_url=image_url,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"name": c.name, "species": c.species, "personality": c.personality, "image_url": c.image_url}
