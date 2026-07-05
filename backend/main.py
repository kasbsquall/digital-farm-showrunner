"""FastAPI app for The Digital Farm Showrunner.

Day 1: healthcheck + list characters + list episodes so the scaffolding is
verifiably alive. Episode-generation endpoint gets wired once the pipeline exists.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db import Base, engine, get_db
from database.models import Character, Episode
from pipeline.orchestrator import run_daily_episode
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
        "description": e.description,
        "status": e.status,
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "digital-farm-showrunner", "mock_mode": settings.use_mock}


class GenerateRequest(BaseModel):
    idea: str = ""


@app.post("/episodes/generate")
def generate_episode(req: GenerateRequest | None = None, db: Session = Depends(get_db)):
    """Run the full 4-agent pipeline and return the new episode."""
    idea = req.idea if req else ""
    episode = run_daily_episode(db, idea=idea)
    return _episode_dict(episode)


@app.get("/characters")
def list_characters(db: Session = Depends(get_db)):
    rows = db.query(Character).all()
    return [
        {"name": c.name, "species": c.species, "personality": c.personality}
        for c in rows
    ]


@app.get("/episodes")
def list_episodes(db: Session = Depends(get_db)):
    rows = db.query(Episode).order_by(Episode.created_at.desc()).all()
    return [
        {
            "id": e.id,
            "title": e.title,
            "event": e.event,
            "video_url": e.video_url,
            "thumbnail_hint": e.thumbnail_hint,
            "description": e.description,
            "status": e.status,
            "qa_status": e.qa_status,
        }
        for e in rows
    ]
