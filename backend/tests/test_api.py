"""API tests via FastAPI TestClient (mock mode, temp sqlite DB)."""
import main
from pipeline.orchestrator import channel_lock


def test_health_reports_mock_flags(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["mock_text"] is True     # FORCE_MOCK active
    assert body["mock_video"] is True


def test_list_characters_after_seeding(seeded_db, client):
    resp = client.get("/characters")
    assert resp.status_code == 200
    names = {c["name"] for c in resp.json()}
    assert {"Bruno", "Pepe", "Nina"} <= names


def test_create_character_then_duplicate_conflicts(client):
    payload = {"name": "Dora", "species": "duck", "personality": "paranoid"}
    first = client.post("/characters", json=payload)
    assert first.status_code == 200
    assert first.json()["name"] == "Dora"
    # No portrait generated in mock mode (create_real_portraits off) → no network.
    assert first.json()["image_url"] is None

    dup = client.post("/characters", json=payload)
    assert dup.status_code == 409
    assert "already" in dup.json()["detail"].lower()


def test_list_episodes_after_generation(seeded_db, client):
    gen = client.post("/episodes/generate", json={"idea": "chaos"})
    assert gen.status_code == 200

    resp = client.get("/episodes")
    assert resp.status_code == 200
    episodes = resp.json()
    assert len(episodes) == 1
    assert episodes[0]["qa_status"] == "approved"
    assert episodes[0]["title"]


def test_sse_stream_returns_event_lines(seeded_db, client):
    resp = client.get("/episodes/generate/stream")
    assert resp.status_code == 200
    text = resp.text
    assert "event:" in text
    # The stream should walk through the named stages and finish with `done`.
    for stage in ("scriptwriter", "director", "video", "qa", "packager", "done"):
        assert f"event: {stage}" in text


def test_vote_is_idempotent_per_voter(seeded_db, client):
    ep_id = client.post("/episodes/generate", json={"idea": "chaos"}).json()["id"]

    first = client.post(f"/episodes/{ep_id}/vote", json={"voter_id": "alice"})
    assert first.status_code == 200 and first.json() == {"id": ep_id, "votes": 1, "counted": True}
    # Same voter re-posts → not counted again (can't spam the flywheel).
    again = client.post(f"/episodes/{ep_id}/vote", json={"voter_id": "alice"})
    assert again.json() == {"id": ep_id, "votes": 1, "counted": False}
    # A different voter does count.
    bob = client.post(f"/episodes/{ep_id}/vote", json={"voter_id": "bob"})
    assert bob.json() == {"id": ep_id, "votes": 2, "counted": True}


def test_vote_requires_a_voter_id(seeded_db, client):
    ep_id = client.post("/episodes/generate", json={"idea": "chaos"}).json()["id"]
    resp = client.post(f"/episodes/{ep_id}/vote", json={"voter_id": ""})
    assert resp.status_code == 400


def test_episodes_are_scoped_by_channel(seeded_db, client):
    client.post("/episodes/generate", json={"idea": "farm show"})   # default "farm" channel

    farm = client.get("/episodes").json()                            # defaults to "farm"
    other = client.get("/episodes", params={"channel": "space"}).json()
    assert len(farm) == 1 and all(e["channel_id"] == "farm" for e in farm)
    assert other == []                                               # another channel sees none of it


def test_generate_conflicts_when_channel_lock_held(client):
    # Simulate a concurrent in-flight generation on the default channel by holding its lock.
    lock = channel_lock("farm")
    assert lock.acquire(blocking=False)
    try:
        resp = client.post("/episodes/generate", json={"idea": "x"})
        assert resp.status_code == 409
        assert "already running" in resp.json()["detail"].lower()
    finally:
        lock.release()


def test_channels_have_independent_locks(client):
    # Per-channel concurrency: a busy "farm" must NOT block a different channel.
    farm = channel_lock("farm")
    space = channel_lock("space")
    assert farm is not space
    assert farm.acquire(blocking=False)
    try:
        assert space.acquire(blocking=False)   # not blocked by the busy farm channel
        space.release()
    finally:
        farm.release()


def test_stream_reports_failed_event_when_lock_held(client):
    lock = channel_lock("farm")
    assert lock.acquire(blocking=False)
    try:
        resp = client.get("/episodes/generate/stream")
        assert resp.status_code == 200
        assert "event: failed" in resp.text
    finally:
        lock.release()
