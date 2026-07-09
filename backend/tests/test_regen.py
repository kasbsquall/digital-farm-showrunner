"""The self-correcting QA loop: a rejected take is regenerated and the take
history accumulates. Runs fully offline by stubbing the real media path."""
import pipeline.orchestrator as orch
from database.models import Character


def _stub_real_media(monkeypatch):
    """Make the 'real' video path deterministic and offline."""
    monkeypatch.setattr(orch, "_video_is_real", lambda: True)
    monkeypatch.setattr(orch.oss_client, "is_configured", lambda: True)
    monkeypatch.setattr(orch.image_gen_client, "generate_image", lambda p, size="": "http://x/kf.png")
    monkeypatch.setattr(orch.oss_client, "persist_image", lambda u, prefix="": u)
    monkeypatch.setattr(orch.video_gen_client, "animate_image", lambda kf, m: "http://x/take.mp4")
    monkeypatch.setattr(orch.oss_client, "persist_video", lambda u: u)
    monkeypatch.setattr(orch.vision_client, "describe_video", lambda u: "a claymation clip of the scene")


def test_qa_loop_rejects_then_regenerates_and_records_takes(db, monkeypatch):
    db.add(Character(name="Pepe", species="pig", personality="mud philosopher", visual_desc="pink pig"))
    db.commit()

    _stub_real_media(monkeypatch)
    monkeypatch.setattr(orch, "MAX_REGEN", 1)

    verdicts = iter([
        {"qa_status": "rejected", "qa_notes": "Pepe is barely visible and the action is unclear."},
        {"qa_status": "approved", "qa_notes": "Pepe and the gag are now clearly shown."},
    ])
    monkeypatch.setattr(orch.qa_reviewer, "run", lambda *a, **k: next(verdicts))

    ep = orch.run_daily_episode(db, idea="Starring Pepe: does something")

    assert ep.qa_attempts == 2                      # the director was re-run once
    assert ep.qa_status == "approved"
    assert ep.status == "published"
    takes = ep.takes or []
    assert len(takes) == 2                          # the loop's history was recorded
    assert takes[0]["qa_status"] == "rejected"
    assert takes[1]["qa_status"] == "approved"
    assert takes[0]["attempt"] == 1 and takes[1]["attempt"] == 2


def test_qa_loop_stops_at_budget_and_publishes_best_take(db, monkeypatch):
    db.add(Character(name="Pepe", species="pig", personality="mud philosopher", visual_desc="pink pig"))
    db.commit()

    _stub_real_media(monkeypatch)
    monkeypatch.setattr(orch, "MAX_REGEN", 1)
    # Always rejects → after MAX_REGEN retakes the budget guard forces packaging.
    monkeypatch.setattr(orch.qa_reviewer, "run", lambda *a, **k: {"qa_status": "rejected", "qa_notes": "still off"})

    ep = orch.run_daily_episode(db, idea="Starring Pepe: does something")

    assert ep.qa_attempts == 2                      # capped by MAX_REGEN=1 (1 + 1 retake)
    assert ep.qa_status == "rejected"
    assert ep.status == "draft"                     # not published when never approved
    assert len(ep.takes or []) == 2
