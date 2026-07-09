# MUCKFLIX — The Digital Farm Showrunner

**Track 2: AI Showrunner**

## Inspiration
Staying relevant online now means posting fresh short‑form video *every single day*. But making it still needs a writer, a director, a camera, an editor and a budget. Today's AI video tools help — but they generate **one‑off clips**: the character looks different every time, nobody checks whether the clip matches the idea, and there's no notion of a *series*. You can't run a show on that.

## What it does
**MUCKFLIX is an autonomous AI showrunner.** You pick a character (or **bring your own**), pitch a one‑line gag, and a pipeline of AI agents produces a finished, **character‑consistent** claymation episode end‑to‑end — written, filmed, quality‑checked and packaged — with no production team.

The public demo is a daily claymation farm channel, but the farm is just the demo: the **engine is the product** — point it at *your* mascot and it runs *your* daily show.

Every generation streams live in a "Studio" wizard so you watch each agent work, and every finished episode keeps its "receipts": a **How it was made** view that replays exactly how the agents built it.

## How it works — the 4‑agent pipeline
Orchestrated as a **LangGraph `StateGraph`** with a real conditional self‑correction loop:

1. **Scriptwriter** *(Qwen3.7)* — invents today's absurd event and writes a tiny, punchy script.
2. **Production Director** *(Qwen3.7)* — turns the script into a **keyframe prompt** (the funniest frozen split‑second) plus a single 5‑second **motion prompt**.
3. **Keyframe → Video → Vision** — **Qwen‑Image** paints the keyframe, **HappyHorse image‑to‑video** animates *that exact still* into a 5‑second clip, and **Qwen3‑VL** watches the finished clip and describes what actually happens. An episode can also be **N chained shots** (setup→escalation→punchline) — one keyframe→clip per beat, stitched into one continuous video (a real 3‑shot Pepe episode was stitched to 15.5s).
4. **Quality Control** *(Qwen3.7)* — compares the clip (via the vision description) to the script. On a mismatch it **rejects the take and feeds the reason back to the Director**, which regenerates — bounded by a `MAX_REGEN` token‑budget guard. Only an approved take moves on.
5. **Packager** *(Qwen3.7)* — writes the viral title and description; the episode publishes to the feed.

## Two signature techniques
- **Keyframe‑as‑frame‑0 for character consistency.** Instead of text‑to‑video (which drifts), we generate a still with Qwen‑Image and animate *that exact image* with image‑to‑video. The recurring character's look is locked across episodes — and the keyframe doubles as a perfectly coherent thumbnail. We show the **same character (Pepe) in two completely different episodes** to prove it. An optional **identity‑lock** check makes this *measurable*: a Qwen3‑VL pass scores each keyframe's character against its canonical portrait (`0.0–1.0`) — enforced by *scoring* the result, since Qwen‑Image takes no reference image (calibrated 0.9 for a matching character, 0.0 for a mismatch).
- **Vision‑grounded, self‑correcting QA.** A Qwen3‑VL vision pass describes what the video *actually* shows, and QA + Packager reason over that — not just the intended script — closing the text↔video mismatch that plagues AI video, and enabling an autonomous "retake" loop.

## Built on Qwen Cloud + Alibaba Cloud
- **Qwen models:** Qwen3.7‑plus (all 4 text agents), Qwen‑Image (keyframes + character portraits), HappyHorse i2v (video), Qwen3‑VL (video understanding) — via DashScope (OpenAI‑compatible + native async submit/poll).
- **Alibaba Cloud:** backend deployed on **ECS** (Docker, one‑command deploy); all generated videos and keyframes persisted to **Alibaba Cloud OSS** (proof‑of‑deployment code in `backend/services/oss_client.py` and `backend/deploy/alibaba_deploy_proof.py`).

## Tech stack
FastAPI (SSE streaming) · LangGraph · SQLAlchemy · Next.js 14 (App Router) · Docker · Alibaba Cloud ECS + OSS · Qwen Cloud / DashScope.

## Bring your own character
Describe any character — a name, a personality, a look — and Qwen‑Image sculpts an original claymation portrait on the spot. It joins the cast instantly and is ready to star in the next episode. This is the "creator economy" wedge: an autonomous studio for serialized, on‑brand short video.

## What's next
Per‑creator channels, subscription + microtransaction monetization, and a growing library of user‑created characters — the same engine, scaled from one farm to every creator's daily show. (Multi‑shot episodes and the measurable identity‑lock consistency check already shipped; next is even longer multi‑beat story arcs.)

## Try it / repo
Public, MIT‑licensed repository with a one‑command Alibaba Cloud deploy and a zero‑cost demo mode so anyone can stand it up. Architecture diagram and deployment proof included in `docs/`.
