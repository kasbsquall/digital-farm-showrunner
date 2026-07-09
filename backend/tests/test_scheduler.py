"""The unattended scheduler: runs the pipeline on its own and shares the single-flight lock."""
import scheduler
from pipeline.orchestrator import generation_lock


class _FakeEpisode:
    id, title, status, qa_status = 7, "A Gag", "published", "approved"


def test_run_once_invokes_pipeline_with_showrunner_creator(db, monkeypatch):
    seen = {}

    def fake_run(db_arg, idea="", creator=""):
        seen["idea"], seen["creator"] = idea, creator
        return _FakeEpisode()

    monkeypatch.setattr(scheduler, "run_daily_episode", fake_run)
    ep = scheduler.run_once(db=db)

    assert ep.id == 7
    assert seen["creator"] == "@showrunner"   # attributed to the autonomous channel
    assert "idea" in seen                     # an idea (possibly "") was chosen from the bank


def test_run_once_skips_when_a_generation_is_already_running(monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr(scheduler, "run_daily_episode", lambda *a, **k: called.__setitem__("n", called["n"] + 1))

    assert generation_lock.acquire(blocking=False)   # simulate an in-flight API run
    try:
        assert scheduler.run_once() is None          # must not start a colliding run
        assert called["n"] == 0
    finally:
        generation_lock.release()


def test_start_background_is_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(scheduler.settings, "scheduler_enabled", False)
    assert scheduler.start_background() is False
