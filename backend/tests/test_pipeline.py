"""End-to-end pipeline tests in mock mode (fully offline)."""
from pipeline.orchestrator import run_stream, run_daily_episode
from database.models import Episode

EXPECTED_STAGES = ["scriptwriter", "director", "video", "qa", "packager", "done"]


def test_run_stream_emits_stages_in_order_and_persists(seeded_db):
    stages = [stage for stage, _ in run_stream(seeded_db, idea="a slapstick gag")]
    assert stages == EXPECTED_STAGES

    episodes = seeded_db.query(Episode).all()
    assert len(episodes) == 1
    assert episodes[0].qa_status == "approved"


def test_run_stream_done_payload_references_saved_episode(seeded_db):
    last_stage, last_data = None, None
    for stage, data in run_stream(seeded_db):
        last_stage, last_data = stage, data
    assert last_stage == "done"
    saved = seeded_db.get(Episode, last_data["id"])
    assert saved is not None


def test_run_daily_episode_returns_complete_episode(seeded_db):
    episode = run_daily_episode(seeded_db, idea="rooster chaos", creator="tester")
    assert episode.id is not None
    assert episode.title            # packager mock supplies a title
    assert episode.script           # scriptwriter mock supplies a script
    assert episode.qa_status == "approved"
    assert episode.creator == "tester"
    # In placeholder-video mode QA auto-approves → status published.
    assert episode.status == "published"


def test_run_daily_episode_works_without_seeded_characters(db):
    # The pipeline must not crash on an empty cast (falls back gracefully).
    episode = run_daily_episode(db)
    assert episode.id is not None
    assert episode.qa_status == "approved"
