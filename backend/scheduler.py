"""Unattended "daily channel" scheduler.

The track asks for an *autonomous* showrunner. This runs the full pipeline on an
interval with no human trigger and lets the QA verdict decide what publishes — the
missing piece between "on-demand pipeline" and "runs a channel by itself".

Off by default (SCHEDULER_ENABLED=false) so tests and demos never spend credits
unprompted. Two ways to run it:

    # In-process: the FastAPI app starts it on boot when SCHEDULER_ENABLED=true.
    # Standalone (cron-friendly):
    python -m scheduler --once     # generate one episode now, then exit
    python -m scheduler            # loop forever, one episode every N hours
"""
import logging
import threading
import time

from config import settings
from database.db import SessionLocal
from pipeline.orchestrator import run_daily_episode, generation_lock

log = logging.getLogger("scheduler")

# A small rotating idea bank so unattended episodes vary instead of repeating.
# "" lets the Scriptwriter invent freely (still biased by the audience flywheel).
_IDEA_BANK = [
    "",
    "a squabble over the last bucket of feed",
    "someone gets spectacularly stuck in the mud",
    "a wildly overconfident plan goes wrong",
    "a tiny misunderstanding escalates into chaos",
]
_state = {"n": 0}

_thread: threading.Thread | None = None


def run_once(db=None):
    """Generate exactly one episode unattended. Publishes iff QA approves.

    Uses the shared single-flight lock so it never collides with an API run.
    Returns the Episode, or None if a generation was already in flight.
    """
    if not generation_lock.acquire(blocking=False):
        log.info("Scheduler: a generation is already running; skipping this tick.")
        return None
    own_session = db is None
    db = db or SessionLocal()
    try:
        idea = _IDEA_BANK[_state["n"] % len(_IDEA_BANK)]
        _state["n"] += 1
        ep = run_daily_episode(db, idea=idea, creator="@showrunner")
        log.info("Scheduler produced episode #%s '%s' → %s (qa=%s)",
                 ep.id, ep.title, ep.status, ep.qa_status)
        return ep
    finally:
        if own_session:
            db.close()
        generation_lock.release()


def start_background() -> bool:
    """Start the interval loop in a daemon thread. No-op unless SCHEDULER_ENABLED.

    Returns True if the loop was started.
    """
    global _thread
    if not settings.scheduler_enabled or (_thread and _thread.is_alive()):
        return False
    interval = max(60.0, settings.scheduler_interval_hours * 3600)

    def _loop():
        while True:
            try:
                run_once()
            except Exception as e:  # never let one bad run kill the channel
                log.exception("Scheduled run failed: %s", e)
            time.sleep(interval)

    _thread = threading.Thread(target=_loop, name="showrunner-scheduler", daemon=True)
    _thread.start()
    log.info("Scheduler started: one episode every %.1fh.", settings.scheduler_interval_hours)
    return True


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    if "--once" in sys.argv:
        run_once()
    else:
        interval = max(60.0, settings.scheduler_interval_hours * 3600)
        log.info("Scheduler loop: one episode every %.1fh (Ctrl-C to stop).",
                 settings.scheduler_interval_hours)
        while True:
            run_once()
            time.sleep(interval)
