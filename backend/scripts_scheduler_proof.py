"""Run the UNATTENDED scheduler for N real episodes on live infra and commit the
evidence (timestamps, per-episode receipts, QA verdicts) — proof the autonomous
'daily channel' loop actually runs, not just that it's wired."""
import json
import pathlib

import scheduler
import pipeline.orchestrator as orch
from config import settings
from services import oss_client
from database.db import Base, engine, SessionLocal
from database.models import Character

N = 3


def main() -> None:
    assert not settings.use_mock and not settings.mock_video, "Refusing: not in real mode."
    assert oss_client.is_configured(), "Refusing: OSS not configured."
    Base.metadata.create_all(bind=engine)

    snap = json.loads(pathlib.Path("database/snapshot.json").read_text(encoding="utf-8"))
    db = SessionLocal()
    if db.query(Character).count() == 0:
        for c in snap["characters"]:
            db.add(Character(name=c["name"], species=c["species"], personality=c["personality"],
                             visual_desc=c["visual_desc"], image_url=c.get("image_url")))
        db.commit()
    db.close()

    print(f"[scheduler-proof] UNATTENDED. MAX_REGEN={orch.MAX_REGEN} channel=farm", flush=True)
    runs = []
    for i in range(N):
        ep = scheduler.run_once()   # no human trigger; opens its own session; publishes on QA verdict
        runs.append({
            "n": i + 1, "episode_id": ep.id, "created_at": str(ep.created_at),
            "channel_id": ep.channel_id, "creator": ep.creator, "title": ep.title,
            "qa_status": ep.qa_status, "qa_attempts": ep.qa_attempts, "status": ep.status,
            "tokens_used": ep.tokens_used, "cost_usd": ep.cost_usd, "video_url": ep.video_url,
        })
        print(f"[{i+1}/{N}] #{ep.id} {ep.title!r} -> {ep.status} qa={ep.qa_status} "
              f"attempts={ep.qa_attempts} ${ep.cost_usd}", flush=True)

    total_cost = round(sum(r["cost_usd"] or 0 for r in runs), 6)
    out = {
        "channel_id": "farm",
        "unattended": True,
        "episodes_generated": len(runs),
        "published": sum(1 for r in runs if r["status"] == "published"),
        "total_cost_usd": total_cost,
        "note": ("Produced by scheduler.run_once() with NO human trigger per episode "
                 "(rotating idea bank). Each publishes strictly on the QA verdict; "
                 "rejected episodes ship as drafts. Real Alibaba Cloud generation."),
        "runs": runs,
    }
    pathlib.Path("../docs/deploy_proof/scheduler_run.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"saved -> docs/deploy_proof/scheduler_run.json  ({len(runs)} eps, ${total_cost})", flush=True)


if __name__ == "__main__":
    main()
