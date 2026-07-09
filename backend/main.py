"""FastAPI app for The Digital Farm Showrunner.

Day 1: healthcheck + list characters + list episodes so the scaffolding is
verifiably alive. Episode-generation endpoint gets wired once the pipeline exists.
"""
from contextlib import asynccontextmanager

import json
import threading

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db import Base, engine, get_db, SessionLocal
from database.models import Character, Episode
from database.generate_portraits import STYLE
from pipeline.orchestrator import run_daily_episode, run_stream
from services import image_gen_client, oss_client
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
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


# Only one generation may run at a time: the pipeline does long, blocking I/O and
# holds a threadpool worker; a second concurrent run could starve /health & friends.
_generation_lock = threading.Lock()


@app.post("/episodes/generate")
def generate_episode(req: GenerateRequest | None = None, db: Session = Depends(get_db)):
    """Run the full 4-agent pipeline and return the new episode."""
    idea = (req.idea if req else "")[:500]
    creator = (req.creator if req else "")[:48]
    if not _generation_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A generation is already running. Try again shortly.")
    try:
        episode = run_daily_episode(db, idea=idea, creator=creator)
        return _episode_dict(episode)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}")
    finally:
        _generation_lock.release()


@app.get("/episodes/generate/stream")
def generate_episode_stream(
    idea: str = Query("", max_length=500),
    creator: str = Query("", max_length=48),
):
    """Server-Sent Events: emits each pipeline stage live for the Studio wizard."""

    def event_source():
        if not _generation_lock.acquire(blocking=False):
            yield f"event: failed\ndata: {json.dumps({'message': 'A generation is already running. Please wait for it to finish.'})}\n\n"
            return
        db = SessionLocal()
        try:
            for stage, data in run_stream(db, idea=idea, creator=creator):
                yield f"event: {stage}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
        except Exception as e:  # surface failures to the client
            db.rollback()
            yield f"event: failed\ndata: {json.dumps({'message': str(e)})}\n\n"
        finally:
            db.close()
            _generation_lock.release()

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/characters")
def list_characters(db: Session = Depends(get_db)):
    rows = db.query(Character).all()
    return [
        {"name": c.name, "species": c.species, "personality": c.personality,
         "image_url": c.image_url}
        for c in rows
    ]


@app.get("/episodes")
def list_episodes(db: Session = Depends(get_db)):
    rows = db.query(Episode).order_by(Episode.created_at.desc()).all()
    return [_episode_dict(e) for e in rows]


class CreateCharacter(BaseModel):
    name: str
    species: str = "creature"
    personality: str
    look: str = ""


@app.post("/characters")
def create_character(req: CreateCharacter, db: Session = Depends(get_db)):
    """Let anyone add their own claymation character to the cast (with an AI portrait)."""
    name = req.name.strip()[:32]
    if not name:
        raise HTTPException(status_code=400, detail="A name is required.")
    if db.query(Character).filter_by(name=name).first():
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
