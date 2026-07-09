"""Tests for the LangGraph routing decision and graph wiring."""
from pipeline import orchestrator


def test_after_qa_routes_to_packager_when_approved(monkeypatch):
    monkeypatch.setattr(orchestrator, "MAX_REGEN", 2)
    state = {"qa": {"qa_status": "approved"}, "attempt": 1}
    assert orchestrator._after_qa(state) == "packager"


def test_after_qa_routes_to_director_when_rejected_with_budget(monkeypatch):
    monkeypatch.setattr(orchestrator, "MAX_REGEN", 2)
    state = {"qa": {"qa_status": "rejected"}, "attempt": 1}
    assert orchestrator._after_qa(state) == "director"


def test_after_qa_routes_to_packager_when_budget_exhausted(monkeypatch):
    monkeypatch.setattr(orchestrator, "MAX_REGEN", 2)
    # attempt (3) > MAX_REGEN (2): package the best take instead of looping forever.
    state = {"qa": {"qa_status": "rejected"}, "attempt": 3}
    assert orchestrator._after_qa(state) == "packager"


def test_after_qa_director_at_budget_boundary(monkeypatch):
    monkeypatch.setattr(orchestrator, "MAX_REGEN", 2)
    # attempt == MAX_REGEN is still within budget → regenerate.
    state = {"qa": {"qa_status": "rejected"}, "attempt": 2}
    assert orchestrator._after_qa(state) == "director"


def test_graph_node_id_is_qa_review_not_qa():
    node_ids = set(orchestrator.GRAPH.get_graph().nodes.keys())
    assert "qa_review" in node_ids
    assert "qa" not in node_ids
    for expected in ("scriptwriter", "director", "video", "packager"):
        assert expected in node_ids
