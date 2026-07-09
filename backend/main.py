"""FastAPI app for The Digital Farm Showrunner.

Day 1: healthcheck + list characters + list episodes so the scaffolding is
verifiably alive. Episode-generation endpoint gets wired once the pipeline exists.
"""
from contextlib import asynccontextmanager

import json

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db import Base, engine, get_db, SessionLocal
from database.models import Character, Episode
from pipeline.orchestrator import run_daily_episode, run_stream
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


@app.post("/episodes/generate")
def generate_episode(req: GenerateRequest | None = None, db: Session = Depends(get_db)):
    """Run the full 4-agent pipeline and return the new episode."""
    idea = req.idea if req else ""
    creator = req.creator if req else ""
    episode = run_daily_episode(db, idea=idea, creator=creator)
    return _episode_dict(episode)


@app.get("/episodes/generate/stream")
def generate_episode_stream(idea: str = "", creator: str = ""):
    """Server-Sent Events: emits each pipeline stage live for the Studio wizard."""

    def event_source():
        db = SessionLocal()
        try:
            for stage, data in run_stream(db, idea=idea, creator=creator):
                yield f"event: {stage}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
        except Exception as e:  # surface failures to the client
            yield f"event: failed\ndata: {json.dumps({'message': str(e)})}\n\n"
        finally:
            db.close()

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
