"""Pipeline orchestration with LangGraph.

The 4 agents are wired as a StateGraph. The QA node routes back to the Director
(regen loop) when the take is rejected, up to MAX_REGEN times — this is the
token-budget guard. On approval (or after exhausting regens) it flows to the
Packager and ends.

Graph:
    START → scriptwriter → director → video → qa ─(approved / out of budget)→ packager → END
                              ▲                    │
                              └──── rejected ──────┘

`run_daily_episode(db)` keeps the same signature the API depends on: it loads
context from the DB, runs the graph, and persists the resulting Episode.
"""
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from sqlalchemy.orm import Session

from config import settings
from database.models import Character, Episode
from agents import scriptwriter, production_director, qa_reviewer, packager
from services.video_gen_client import generate_video
from services import oss_client, vision_client, image_gen_client, video_gen_client

MAX_REGEN = 2  # Director can be re-run this many times after a QA rejection.
RECENT_LIMIT = 5


class FarmState(TypedDict, total=False):
    # Inputs
    characters: list[dict]
    recent: list[str]
    idea: str
    # Agent 1
    story: dict
    used: list[dict]
    # Agent 2 + video
    direction: dict
    video_url: str
    video_description: str
    # Agent 3
    qa: dict
    attempt: int
    # Agent 4
    pack: dict
    thumbnail_url: str


# --- Nodes -----------------------------------------------------------------

def scriptwriter_node(state: FarmState) -> FarmState:
    story = scriptwriter.run(state["characters"], state["recent"], state.get("idea", ""))
    used = [c for c in state["characters"] if c["name"] in story["characters_used"]]
    return {"story": story, "used": used or state["characters"]}


def director_node(state: FarmState) -> FarmState:
    # On a regeneration, feed the QA rejection notes back so the director corrects it.
    prev_notes = state.get("qa", {}).get("qa_notes", "") if state.get("attempt") else ""
    direction = production_director.run(state["story"]["script"], state["used"], qa_notes=prev_notes)
    return {"direction": direction}


def _video_is_real() -> bool:
    return not settings.use_mock and not settings.mock_video


def video_node(state: FarmState) -> FarmState:
    d = state["direction"]
    if not _video_is_real():
        # Modo demo: video placeholder, sin keyframe ni visión.
        return {"video_url": generate_video(d.get("motion_prompt", "farm"), "happyhorse"),
                "video_description": "", "thumbnail_url": ""}

    # 1) Keyframe: imagen fija de la escena, en el estilo de los personajes.
    kf_temp = image_gen_client.generate_image(d["keyframe_prompt"], size="1280*720")
    kf_url = oss_client.persist_image(kf_temp, prefix="keyframes") if oss_client.is_configured() else kf_temp
    # 2) Animar el keyframe (image→video) → hereda el look de los personajes.
    vid_temp = video_gen_client.animate_image(kf_url, d["motion_prompt"])
    vid_url = oss_client.persist_video(vid_temp) if oss_client.is_configured() else vid_temp
    # 3) Visión: describir lo que realmente pasa.
    description = ""
    try:
        description = vision_client.describe_video(vid_url)
    except Exception as e:
        print(f"[vision] no se pudo describir el video: {e}")
    # El keyframe ES el primer frame → thumbnail perfectamente coherente.
    return {"video_url": vid_url, "video_description": description, "thumbnail_url": kf_url}


def qa_node(state: FarmState) -> FarmState:
    attempt = state.get("attempt", 0) + 1
    # Sin video real (modo placeholder) no hay nada que revisar: aprobamos.
    if not _video_is_real():
        return {"qa": {"qa_status": "approved", "qa_notes": "Video en modo demo (placeholder)."},
                "attempt": attempt}
    qa = qa_reviewer.run(
        state["video_url"], state["story"]["script"],
        state["direction"].get("motion_prompt", ""), state.get("video_description", ""),
    )
    return {"qa": qa, "attempt": attempt}


def packager_node(state: FarmState) -> FarmState:
    # El thumbnail ya es el keyframe (primer frame del video) desde video_node.
    pack = packager.run(
        state["story"]["event"], state["story"]["script"], state.get("video_description", "")
    )
    return {"pack": pack}


def _after_qa(state: FarmState) -> str:
    """Approve → package; reject but budget left → regenerate; else package best take."""
    if state["qa"]["qa_status"] == "approved" or state["attempt"] > MAX_REGEN:
        return "packager"
    return "director"


def _build_graph():
    g = StateGraph(FarmState)
    g.add_node("scriptwriter", scriptwriter_node)
    g.add_node("director", director_node)
    g.add_node("video", video_node)
    g.add_node("qa", qa_node)
    g.add_node("packager", packager_node)

    g.add_edge(START, "scriptwriter")
    g.add_edge("scriptwriter", "director")
    g.add_edge("director", "video")
    g.add_edge("video", "qa")
    g.add_conditional_edges("qa", _after_qa, {"director": "director", "packager": "packager"})
    g.add_edge("packager", END)
    return g.compile()


GRAPH = _build_graph()


# --- Public entry ----------------------------------------------------------

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


def _episode_from_state(final: FarmState) -> Episode:
    story, direction, qa, pack = final["story"], final["direction"], final["qa"], final["pack"]
    approved = qa["qa_status"] == "approved"
    return Episode(
        event=story["event"],
        script=story["script"],
        characters_used=story["characters_used"],
        video_prompt=f"KEYFRAME: {direction.get('keyframe_prompt','')}\nMOTION: {direction.get('motion_prompt','')}",
        video_tool=direction["video_tool"],
        video_url=final["video_url"],
        video_description=final.get("video_description", ""),
        qa_status=qa["qa_status"],
        qa_notes=qa["qa_notes"],
        qa_attempts=final["attempt"],
        title=pack["title"],
        thumbnail_hint=pack["thumbnail_hint"],
        thumbnail_url=final.get("thumbnail_url", ""),
        description=pack["description"],
        status="published" if approved else "draft",
    )


def run_daily_episode(db: Session, idea: str = "", creator: str = "") -> Episode:
    characters, recent = _load_context(db)
    final: FarmState = GRAPH.invoke(
        {"characters": characters, "recent": recent, "idea": idea}
    )
    episode = _episode_from_state(final)
    episode.creator = (creator or "").strip()[:48] or None
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode


def run_stream(db: Session, idea: str = "", creator: str = ""):
    """Generator yielding (stage, data) per pipeline node, then ('done', episode).

    Powers the live "Studio" wizard so the user watches each agent work.
    """
    characters, recent = _load_context(db)
    final: FarmState = {}
    for chunk in GRAPH.stream(
        {"characters": characters, "recent": recent, "idea": idea}, stream_mode="updates"
    ):
        for node, update in chunk.items():
            if update:
                final.update(update)
            yield node, update or {}

    episode = _episode_from_state(final)
    episode.creator = (creator or "").strip()[:48] or None
    db.add(episode)
    db.commit()
    db.refresh(episode)
    yield "done", {"id": episode.id}
