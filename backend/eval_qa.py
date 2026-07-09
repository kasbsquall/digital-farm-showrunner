"""Evaluation harness for the self-correcting QA gate.

The QA agent's whole value is catching takes that don't match the script. This
measures that directly on a hand-labeled fixture of (script, what-the-vision-saw,
expected-verdict) cases, and reports precision / recall / false-approve / false-reject.

Run (real Qwen text — a handful of cheap calls, no video):
    FORCE_MOCK=false python eval_qa.py
Writes docs/EVALUATION.md-ready numbers to stdout and eval_qa_out.json.
"""
import json
import pathlib

from agents import qa_reviewer

# (script, vision_description, expected_verdict). "approve" = the take delivers the gag.
CASES = [
    # --- clear matches → approve ---
    ("PEPE slips on a banana peel and faceplants into the mud.",
     "The pink pig steps on a yellow banana peel, his legs fly up, and he lands flat on his back in the mud puddle with a splash.", "approved"),
    ("KIKI the goose honks and launches BEX the sheep over the fence.",
     "The goose opens its beak wide and honks; the recoil blast throws the woolly sheep backward and up over the wooden fence.", "approved"),
    ("GUS headbutts a bucket off the fence post.",
     "The grey goat lowers its head, charges, and rams a metal bucket that flies off the fence post and tumbles away.", "approved"),
    ("LOLA the cow serenades a shiny bucket.",
     "The cow leans toward a shiny metal bucket, eyes half-closed, mouth open mid-song, hooves clasped adoringly.", "approved"),
    ("DORA fires a tiny bazooka at a hay bale, blasting it into confetti.",
     "The duck holds a small bazooka; it fires and the hay bale bursts into a cloud of colorful confetti while she recoils.", "approved"),
    ("MOMO the donkey wins the lottery and stays completely unimpressed.",
     "The donkey holds a lottery ticket, confetti falls around it, but its face stays flat and droopy-eyed, unmoved.", "approved"),

    # --- clear failures → reject ---
    ("PEPE slips on a banana peel and faceplants into the mud.",
     "The pink pig stands still next to a banana peel in a sunny field. Nothing moves; the pig simply looks at the camera.", "rejected"),
    ("KIKI the goose honks and launches BEX the sheep over the fence.",
     "A single goose stands alone by a pond, preening its feathers. No sheep and no fence are visible.", "rejected"),
    ("GUS headbutts a bucket off the fence post.",
     "The goat inflates like a balloon and floats upward; there is no bucket and no headbutt.", "rejected"),
    ("NINA the hen reports live as the goat detonates the mailbox.",
     "The video is a blurry, smeared mass of brown and grey with no recognizable characters or action.", "rejected"),
    ("DORA fires a tiny bazooka at a hay bale.",
     "A cat sits on a sofa in a living room, licking its paw. This is unrelated to a farm.", "rejected"),
    ("LOLA the cow serenades a shiny bucket.",
     "The cow stands motionless facing away from an empty patch of grass; there is no bucket in the scene.", "rejected"),

    # --- borderline (understated but correct) → approve ---
    ("PEPE tosses a turnip up and it bonks him on the head.",
     "The pig lightly tosses a turnip upward; it drops and taps the top of his head, and he blinks in mild surprise.", "approved"),
    ("GUS eats the last fence post and the barn tips over.",
     "The goat chews the wooden fence post; in the background the barn leans noticeably to one side.", "approved"),
]


def main() -> None:
    rows, tp = [], 0
    fa = fr = 0  # false-approve, false-reject
    for script, vis, expected in CASES:
        qa = qa_reviewer.run("http://x", script, "", vis)
        got = qa["qa_status"]
        ok = got == expected
        if not ok and got == "approved":
            fa += 1
        if not ok and got == "rejected":
            fr += 1
        if ok:
            tp += 1
        rows.append({"expected": expected, "got": got, "score": qa.get("qa_score"),
                     "ok": ok, "notes": qa.get("qa_notes", "")[:90], "vision": vis[:60]})

    n = len(CASES)
    pos = [r for r in rows if r["expected"] == "rejected"]          # "reject" is the detection target
    detected = sum(1 for r in pos if r["got"] == "rejected")
    approved_true = [r for r in rows if r["expected"] == "approved"]
    kept = sum(1 for r in approved_true if r["got"] == "approved")
    metrics = {
        "cases": n,
        "accuracy": round(tp / n, 3),
        "reject_recall": round(detected / len(pos), 3),      # of the bad takes, how many were caught
        "approve_recall": round(kept / len(approved_true), 3),  # of the good takes, how many were kept
        "false_approve": fa,   # bad take wrongly published
        "false_reject": fr,    # good take wrongly retaken (wasted cost)
    }
    print(json.dumps(metrics, indent=2))
    for r in rows:
        mark = "OK " if r["ok"] else "XX "
        print(f"  {mark}exp={r['expected']:8} got={r['got']:8} score={r['score']}  {r['vision']}")
    pathlib.Path("eval_qa_out.json").write_text(
        json.dumps({"metrics": metrics, "rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
