"""API tests via FastAPI TestClient (mock mode, temp sqlite DB)."""
import main


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


def test_generate_conflicts_when_lock_held(client):
    # Simulate a concurrent in-flight generation by holding the lock directly.
    assert main._generation_lock.acquire(blocking=False)
    try:
        resp = client.post("/episodes/generate", json={"idea": "x"})
        assert resp.status_code == 409
        assert "already running" in resp.json()["detail"].lower()
    finally:
        main._generation_lock.release()


def test_stream_reports_failed_event_when_lock_held(client):
    assert main._generation_lock.acquire(blocking=False)
    try:
        resp = client.get("/episodes/generate/stream")
        assert resp.status_code == 200
        assert "event: failed" in resp.text
    finally:
        main._generation_lock.release()
