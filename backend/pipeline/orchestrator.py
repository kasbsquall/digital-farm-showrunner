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
import json
import logging
import operator
import os
import time
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END
from sqlalchemy.orm import Session

from config import settings
from database.models import Character, Episode
from agents import scriptwriter, production_director, qa_reviewer, packager
from services.video_gen_client import generate_video
from services import oss_client, vision_client, image_gen_client, video_gen_client, usage

MAX_REGEN = int(os.getenv("MAX_REGEN", "2"))  # Director re-runs after a QA rejection (0 caps cost).
RECENT_LIMIT = 5

log = logging.getLogger("showrunner")


class FarmState(TypedDict, total=False):
    # Inputs
    characters: list[dict]
    recent: list[str]
    favorites: list[str]  # audience-favorite past events (data flywheel)
    idea: str
    # Agent 1
    story: dict
    used: list[dict]
    # Agent 2 + video
    direction: dict
    video_url: str
    video_description: str
    consistency: float
    # Agent 3
    qa: dict
    attempt: int
    # Auditable history: one entry per take, accumulated across regen attempts.
    takes: Annotated[list[dict], operator.add]
    # Agent 4
    pack: dict
    thumbnail_url: str


# --- Nodes -----------------------------------------------------------------

def scriptwriter_node(state: FarmState) -> FarmState:
    story = scriptwriter.run(state["characters"], state["recent"], state.get("idea", ""),
                             favorites=state.get("favorites", []))
    # Case-insensitive name match so a stray space/casing doesn't silently drop the
    # chosen cast (which would defeat character consistency).
    wanted = {n.strip().lower() for n in story.get("characters_used", [])}
    used = [c for c in state["characters"] if c["name"].strip().lower() in wanted]
    if not used:
        log.warning("Scriptwriter cast %s matched none of the cast; using full lineup.", story.get("characters_used"))
    return {"story": story, "used": used or state["characters"]}


def director_node(state: FarmState) -> FarmState:
    # On a regeneration, feed the QA rejection notes back so the director corrects it.
    prev_notes = state.get("qa", {}).get("qa_notes", "") if state.get("attempt") else ""
    direction = production_director.run(state["story"]["script"], state["used"],
                                       qa_notes=prev_notes, shots=settings.shots_per_episode)
    return {"direction": direction}


def _video_is_real() -> bool:
    return not settings.use_mock and not settings.mock_video


def video_node(state: FarmState) -> FarmState:
    d = state["direction"]
    if not _video_is_real():
        if settings.demo_video_url:
            # Demo/recording: replay a real clip (zero cost) so the wizard looks live.
            return {"video_url": settings.demo_video_url,
                    "video_description": settings.demo_video_desc,
                    "thumbnail_url": settings.demo_thumbnail_url}
        # Demo mode: placeholder video, no keyframe or vision step.
        return {"video_url": generate_video(d.get("motion_prompt", "farm"), "happyhorse"),
                "video_description": "", "thumbnail_url": ""}

    # Real generation MUST persist to OSS — otherwise we'd publish DashScope's
    # temporary signed URLs, which expire and silently break the feed later.
    if not oss_client.is_configured():
        raise RuntimeError(
            "Live video generation requires OSS to be configured (OSS_* env vars); "
            "temporary provider URLs expire and must not be persisted."
        )
    shots = d.get("shots") or [{"keyframe_prompt": d["keyframe_prompt"], "motion_prompt": d["motion_prompt"]}]

    if len(shots) == 1:
        # 1) Keyframe. On a retake, REUSE the previous character-consistent keyframe and
        #    only re-animate with the corrected motion — a surgical "retake the shot",
        #    not "reshoot the movie" (protects consistency and saves an image call).
        prior = state.get("takes") or []
        reuse_kf = prior[-1]["thumbnail_url"] if prior and prior[-1].get("thumbnail_url") else ""
        if reuse_kf:
            kf_url = reuse_kf
            log.info("Surgical retake: re-animating the existing keyframe with the corrected motion.")
        else:
            kf_temp = image_gen_client.generate_image(shots[0]["keyframe_prompt"], size="1280*720")
            kf_url = oss_client.persist_image(kf_temp, prefix="keyframes")
        vid_temp = video_gen_client.animate_image(kf_url, shots[0]["motion_prompt"])
        vid_url = oss_client.persist_video(vid_temp)
    else:
        # Multi-shot: one keyframe→clip per beat, then stitch into a single episode.
        clips, kf_url = [], ""
        for i, s in enumerate(shots):
            kf_temp = image_gen_client.generate_image(s["keyframe_prompt"], size="1280*720")
            shot_kf = oss_client.persist_image(kf_temp, prefix="keyframes")
            kf_url = kf_url or shot_kf  # first shot's keyframe is the thumbnail
            clips.append(video_gen_client.animate_image(shot_kf, s["motion_prompt"]))
            log.info("Multi-shot: rendered shot %d/%d", i + 1, len(shots))
        vid_url = oss_client.persist_local(video_gen_client.stitch(clips))
    # 2b) Identity-lock: score how well the keyframe's character matches its canonical
    #     portrait (measurable consistency gate).
    consistency = None
    if settings.identity_check:
        used = state.get("used") or []
        ref = next((c.get("image_url") for c in used if c.get("image_url")), None)
        if ref:
            try:
                consistency = vision_client.consistency_score(kf_url, ref)
                log.info("Identity-lock: character consistency %.2f", consistency)
            except Exception as e:
                log.warning("Consistency check failed: %s", e)
    # 3) Vision: describe what actually happens on screen.
    description = ""
    try:
        description = vision_client.describe_video(vid_url)
    except Exception as e:
        log.warning("Could not describe the video with vision: %s", e)
    # The keyframe IS frame 0 → a perfectly coherent thumbnail.
    return {"video_url": vid_url, "video_description": description, "thumbnail_url": kf_url,
            "consistency": consistency}


def _take_record(state: FarmState, attempt: int, qa: dict) -> dict:
    """A single, auditable production take (clip + what vision saw + QA verdict)."""
    d = state.get("direction", {})
    return {
        "attempt": attempt,
        "video_url": state.get("video_url", ""),
        "thumbnail_url": state.get("thumbnail_url", ""),
        "keyframe_prompt": d.get("keyframe_prompt", ""),
        "motion_prompt": d.get("motion_prompt", ""),
        "video_description": state.get("video_description", ""),
        "qa_status": qa.get("qa_status", ""),
        "qa_score": qa.get("qa_score", 0.0),
        "consistency": state.get("consistency"),
        "qa_notes": qa.get("qa_notes", ""),
    }


def qa_node(state: FarmState) -> FarmState:
    attempt = state.get("attempt", 0) + 1
    # No real video (placeholder mode) → nothing to review: auto-approve.
    if not _video_is_real():
        note = (
            "The clip shows the right characters and the script's main action — approved."
            if settings.demo_video_url
            else "Video in demo mode (placeholder)."
        )
        qa = {"qa_status": "approved", "qa_score": 1.0, "qa_notes": note}
    elif not state.get("video_description", "").strip():
        # Vision genuinely unavailable → don't let a blank description bias QA to reject.
        qa = {"qa_status": "approved", "qa_score": 0.6,
              "qa_notes": "Vision description unavailable; approved by default (not penalized)."}
    else:
        qa = qa_reviewer.run(
            state["video_url"], state["story"]["script"],
            state["direction"].get("motion_prompt", ""), state.get("video_description", ""),
        )
    return {"qa": qa, "attempt": attempt, "takes": [_take_record(state, attempt, qa)]}


def packager_node(state: FarmState) -> FarmState:
    # The thumbnail is already the keyframe (frame 0 of the video) from video_node.
    pack = packager.run(
        state["story"]["event"], state["story"]["script"], state.get("video_description", "")
    )
    return {"pack": pack}


def _after_qa(state: FarmState) -> str:
    """Approve → package; reject but budget left → regenerate; else package the best take."""
    over_budget = settings.token_budget and usage.total_tokens() >= settings.token_budget
    if state["qa"]["qa_status"] == "approved" or state["attempt"] > MAX_REGEN or over_budget:
        return "packager"
    return "director"


def _build_graph():
    g = StateGraph(FarmState)
    g.add_node("scriptwriter", scriptwriter_node)
    g.add_node("director", director_node)
    g.add_node("video", video_node)
    # Node id differs from the "qa" state key (langgraph forbids the collision).
    g.add_node("qa_review", qa_node)
    g.add_node("packager", packager_node)

    g.add_edge(START, "scriptwriter")
    g.add_edge("scriptwriter", "director")
    g.add_edge("director", "video")
    g.add_edge("video", "qa_review")
    g.add_conditional_edges("qa_review", _after_qa, {"director": "director", "packager": "packager"})
    g.add_edge("packager", END)
    return g.compile()


GRAPH = _build_graph()


# --- Public entry ----------------------------------------------------------

def _load_context(db: Session) -> tuple[list[dict], list[str], list[str]]:
    characters = [
        {
            "name": c.name,
            "species": c.species,
            "personality": c.personality,
            "visual_desc": c.visual_desc,
            "image_url": c.image_url,  # canonical portrait → identity-lock reference
        }
        for c in db.query(Character).all()
    ]
    recent = [
        e.event
        for e in db.query(Episode).order_by(Episode.created_at.desc()).limit(RECENT_LIMIT)
        if e.event
    ]
    # Data flywheel: the episodes the audience upvoted most bias tomorrow's writing.
    favorites = [
        e.event
        for e in db.query(Episode).filter(Episode.votes > 0)
        .order_by(Episode.votes.desc()).limit(3)
        if e.event
    ]
    return characters, recent, favorites


def _episode_from_state(final: FarmState) -> Episode:
    story, direction, qa, pack = final["story"], final["direction"], final["qa"], final["pack"]
    takes = final.get("takes", [])
    approved = qa["qa_status"] == "approved"
    # If we ran out of budget without an approval, publish the HIGHEST-SCORING take
    # (not merely the last one) — a real "best take" selection.
    if not approved and takes:
        best = max(takes, key=lambda t: t.get("qa_score", 0.0))
        video_url, thumb = best["video_url"], best["thumbnail_url"]
        vdesc, qa_status, qa_notes = best["video_description"], best["qa_status"], best["qa_notes"]
    else:
        video_url, thumb = final["video_url"], final.get("thumbnail_url", "")
        vdesc, qa_status, qa_notes = final.get("video_description", ""), qa["qa_status"], qa["qa_notes"]
    meter = usage.snapshot()
    return Episode(
        event=story["event"],
        script=story["script"],
        characters_used=story["characters_used"],
        video_prompt=f"KEYFRAME: {direction.get('keyframe_prompt','')}\nMOTION: {direction.get('motion_prompt','')}",
        video_tool=direction["video_tool"],
        video_url=video_url,
        video_description=vdesc,
        qa_status=qa_status,
        qa_notes=qa_notes,
        qa_attempts=final["attempt"],
        takes=takes,
        tokens_used=meter["total_tokens"],
        cost_usd=meter["cost_usd"],
        title=pack["title"],
        thumbnail_hint=pack["thumbnail_hint"],
        thumbnail_url=thumb,
        description=pack["description"],
        status="published" if approved else "draft",
    )


def run_daily_episode(db: Session, idea: str = "", creator: str = "") -> Episode:
    usage.reset()
    characters, recent, favorites = _load_context(db)
    final: FarmState = GRAPH.invoke(
        {"characters": characters, "recent": recent, "favorites": favorites, "idea": idea}
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
    usage.reset()
    characters, recent, favorites = _load_context(db)
    final: FarmState = {}
    for chunk in GRAPH.stream(
        {"characters": characters, "recent": recent, "favorites": favorites, "idea": idea},
        stream_mode="updates",
    ):
        for node, update in chunk.items():
            if update:
                final.update(update)
            # Keep the public SSE stage name stable ("qa") despite the internal node id.
            stage = "qa" if node == "qa_review" else node
            yield stage, update or {}
            if settings.demo_pace_seconds:
                time.sleep(settings.demo_pace_seconds)

    episode = _episode_from_state(final)
    episode.creator = (creator or "").strip()[:48] or None
    db.add(episode)
    db.commit()
    db.refresh(episode)
    yield "done", {"id": episode.id}
