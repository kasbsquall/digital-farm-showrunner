# 🐔 MUCKFLIX — The Digital Farm Showrunner

> An autonomous pipeline of AI agents that writes, art-directs, films, quality-checks and packages a brand-new claymation farm micro-drama **video every single day** — end to end, with no human production team.

![Track](https://img.shields.io/badge/Qwen%20Cloud%20Hackathon-Track%202%3A%20AI%20Showrunner-e7501f)
![License](https://img.shields.io/badge/license-MIT-blue)
![Models](https://img.shields.io/badge/models-Qwen%20Cloud%20(DashScope)-6d28d9)
![Cloud](https://img.shields.io/badge/deploy-Alibaba%20Cloud%20ECS%20%2B%20OSS-ff6a00)
![Backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20LangGraph-009688)
![Frontend](https://img.shields.io/badge/frontend-Next.js%2014-000000)

**Hackathon:** Qwen Cloud Global AI Hackathon 2026 — **Track 2: AI Showrunner**.
**Deliverable:** a general **engine for daily, on-brand, character-consistent serialized video**. The claymation farm ("MUCKFLIX") is the demo channel; the pipeline is the product.

---

## 🎬 Demo & live proof

**▶ Demo video:** _(YouTube link — TODO)_

**Flagship proof — the self-correcting QA loop, shown live.** The retake loop isn't a claim: it's visible in the "How it was made" retake view, and there is a **committed real episode** whose take history reads `rejected → rejected → approved` (see the "Wobbly Gold Spheres…" episode in [`backend/database/snapshot.json`](backend/database/snapshot.json), rendered as the per-take retake UI in the behind-the-scenes modal). The clip that finally passed is the one shipped to the feed.

- **Architecture at a glance:** [`docs/architecture_diagram.png`](docs/architecture_diagram.png)
- **Alibaba Cloud deploy proof:** [`docs/deploy_proof/`](docs/deploy_proof/)
- **Test suite (fully offline):** [`backend/tests/`](backend/tests/)
- **QA-gate evaluation (100% on a labeled set):** [`docs/EVALUATION.md`](docs/EVALUATION.md)
- **Multi-shot & identity-lock, validated on real generation:** a 3-shot Pepe episode stitched into one **15.5-second** video on OSS, and an identity-lock check that scored **0.9** for a matching character vs. **0.0** for a mismatch (see [§5a](#5-the-two-signature-techniques)).

---

## 1. The problem & the insight

### The problem

Short-form video is the oxygen of the modern internet. But **producing a *serialized daily show* is slow, expensive, and needs a whole team** — a writer, an art director, a camera/animation crew, a QA pass, and an editor to package and publish. Creators, SMBs and brands are stuck on a treadmill they can't staff.

Generic AI-video tools don't solve this. They generate **one-off clips** with two fatal gaps for anyone running a *show*:

| Gap in one-off AI video | Why it kills a serialized show |
|---|---|
| **No character continuity** | Your mascot looks different every clip. There is no cast, so there is no "show." |
| **No quality control** | The model frequently produces something *other* than what you asked for — and nobody catches it. You cannot publish unsupervised. |

### The insight

A daily show doesn't need a better *clip generator* — it needs a **studio**: a repeatable production line where recurring characters stay on-model, and where a step at the end actually *watches the footage* and calls a retake when it's wrong. That is exactly what a human showrunner's team provides, and it is what MUCKFLIX automates.

Two techniques make this work (detailed in [§5](#5-the-two-signature-techniques)):

1. **Keyframe → image-to-video** for character consistency: a still is generated *in each character's established look*, and that exact still is animated — so the cast stays on-model, and the still doubles as a perfectly coherent thumbnail.
2. **A vision-grounded, self-correcting QA loop**: a vision model describes what the *actual* generated clip shows; QA rejects on mismatch; the rejection note is fed back to the Director to regenerate — bounded so cost can never run away.

---

## 2. What it does (the product)

MUCKFLIX takes a **one-line idea** (or nothing at all) and runs the *entire* production of a finished, publish-ready episode:

- **Bring your own character.** Anyone can add their own claymation character to the cast (with an AI-generated portrait). Point the same engine at *your* mascot and it runs *your* daily show.
- **Audience co-creation.** A viewer casts the stars, pitches a gag, and gets **credited** on the resulting episode — the built-in path to virality and monetization (subscriptions per channel + microtransactions to prioritize your idea for tomorrow).
- **Watch it produce, live.** The "Studio" wizard streams every production stage over Server-Sent Events, including the QA retake loop, so you can watch the agents work in real time.
- **A finished episode, not a raw clip.** Each run yields a viral title, a coherent thumbnail (the keyframe), a QA verdict, and a publish-ready video with consistent characters.

### Engine vs. demo framing

The farm — a claymation barnyard of romantic cows, mud philosophers, and an aggressively territorial goose — is a **demo channel** chosen because it makes character-consistency and comedic QA visually obvious. Swap the cast, the style prompt, and the brand, and the *same* pipeline produces a daily show for any vertical: brand mascots, kids' channels, educational series.

---

## 3. The base cast

Seeded so the Scriptwriter has continuity from day one (see `backend/database/seed_characters.py`). All plasticine, all Aardman-style.

| Character | Species | Personality (one-liner) |
|---|---|---|
| **Lola** | cow | Hopeless romantic — falls in love with buckets, fenceposts, clouds. |
| **Pepe** | pig | The mud philosopher; deep-sounding nonsense, never leaves the puddle. |
| **Nina** | hen | Breaking-news reporter treating every triviality as a world-shaking scoop. |
| **Gus** | goat | Chaotic troublemaker who eats everything, zero remorse. |
| **Dora** | duck | Dramatic diva and conspiracy theorist. |
| **Bex** | sheep | Anxious overthinker; agrees with whoever spoke last. |
| **Momo** | donkey | Deadpan pessimist with a gloomy one-liner for everything. |
| **Kiki** | goose | Self-appointed, extremely aggressive pond security guard. |

---

## 4. Architecture

The backend is a **LangGraph `StateGraph`** wiring four agents plus a video sub-stage. State flows through a single typed dict (`FarmState`) and each node returns a partial update.

### The agents

| # | Agent | File | Qwen model / surface | Input | Output |
|---|---|---|---|---|---|
| 1 | **Scriptwriter** | `backend/agents/scriptwriter.py` | `qwen3.7-plus` (text) | Full cast, recent episode events (for continuity), optional user idea | `event`, `script` (2–4 lines), `characters_used` |
| 2 | **Production Director** | `backend/agents/production_director.py` | `qwen3.7-plus` (text) | The script + the *faithful visual description* of each cast member; on a retake, the QA rejection note | `keyframe_prompt` (a frozen funniest instant), `motion_prompt` (one 5s action), `video_tool` |
| — | **Video sub-stage** | `backend/pipeline/orchestrator.py` → services | `qwen-image-2.0` → `happyhorse-1.1-i2v` → `qwen3-vl-plus` | Director's keyframe + motion prompts (a `shots` list when `SHOTS_PER_EPISODE > 1`) | Persisted `video_url` (multi-shot clips stitched into one), `thumbnail_url` (= the keyframe), a vision `video_description`, and an optional identity-lock `consistency` score |
| 3 | **QA Reviewer** | `backend/agents/qa_reviewer.py` | `qwen3.7-plus` (text), reasoning over `qwen3-vl-plus` output | Script, motion prompt, and **what the clip actually shows** | `qa_status` (`approved`/`rejected`), `qa_notes` |
| 4 | **Packager** | `backend/agents/packager.py` | `qwen3.7-plus` (text) | Event, script, and the vision description | `title` (with emojis), `thumbnail_hint`, `description` (+ hashtags) |

Every agent asks the model for **strict JSON** and parses it through a tolerant extractor (`backend/agents/_json.py`) that strips code fences, isolates the outer `{...}`, and repairs trailing commas / smart quotes before a second `json.loads`. An LLM formatting slip therefore never crashes the pipeline — each agent also falls back to safe defaults on missing keys.

### The pipeline flow

```
recent events + cast (SQLite / Alibaba Cloud RDS PostgreSQL)
                     │
                     ▼
 ┌──────────────── LangGraph StateGraph ─────────────────┐
 │                                                       │
 │  START → scriptwriter → director → video → qa_review  │
 │                           ▲                    │      │
 │                           │                    │      │
 │                  ┌────────┘   rejected &       │      │
 │                  │            attempt≤MAX_REGEN │      │
 │                  └────────────────◄────────────┘      │
 │                                    │                  │
 │                        approved OR out of budget      │
 │                                    ▼                  │
 │                                packager → END         │
 └──────────────────────────┬────────────────────────────┘
                            ▼
        Episode row (DB) + video/thumbnail on Alibaba Cloud OSS
                            │
                            ▼
              Next.js feed  ◄── FastAPI /episodes
```

The **conditional edge** after `qa_review` (`_after_qa` in the orchestrator) is the heart of the graph:

- `qa_status == "approved"` → go to **packager**.
- rejected **and** `attempt > MAX_REGEN` → go to **packager** anyway (publish the best take, never loop forever).
- rejected **and** budget remains → go back to **director**, this time with the rejection note.

> A rendering of the full architecture lives at [`docs/architecture_diagram.png`](docs/architecture_diagram.png) (editable source: `docs/architecture_diagram.svg`), with the agent flow also described in [`docs/README.md`](docs/README.md).

### How Qwen Cloud connects to backend, DB and frontend

- **Backend ↔ Qwen Cloud.** Text agents call the **OpenAI-compatible** DashScope endpoint via `backend/services/qwen_client.py`. Image, video and vision calls use the **native DashScope** endpoint, derived automatically from the same base URL (`/compatible-mode/v1` → `/api/v1`, see `config.dashscope_base`). The correct base URL is auto-selected by API-key prefix (see [§10](#10-local-setup--deploy)).
- **Backend ↔ DB.** SQLAlchemy models (`Character`, `Episode`) persist to SQLite by default, or Alibaba Cloud RDS PostgreSQL by swapping `DATABASE_URL`. Every finished run is written as one `Episode` row.
- **Backend ↔ OSS.** Generated media is downloaded from DashScope's temporary URLs and re-uploaded to Alibaba Cloud OSS for a stable public link (`backend/services/oss_client.py`).
- **Frontend ↔ Backend.** Next.js reads `/characters` and `/episodes` (REST) and consumes `/episodes/generate/stream` (SSE) to render the live Studio wizard. OSS images are downsized on the fly with `?x-oss-process=image/resize,...` (`ossThumb` in `frontend/lib/api.ts`).

---

## 5. The two signature techniques

### (a) Keyframe → image-to-video for character consistency

Instead of a blind text-to-video prompt, the video sub-stage runs three deliberate steps (`video_node` in `backend/pipeline/orchestrator.py`):

1. **Keyframe** — `qwen-image-2.0` paints a **single frozen still** of the funniest split-second of the gag, describing every character *in their established look* (the Director is fed each cast member's `visual_desc`). This still is persisted to OSS.
2. **Animate** — `happyhorse-1.1-i2v` (image-to-video) takes **that exact still as frame 0** and animates one continuous ~5-second motion. Because the video *starts from* the on-model keyframe, the characters inherit their established appearance instead of being re-hallucinated.
3. **Describe** — `qwen3-vl-plus` watches the resulting clip (feeds the next technique).

Two consequences fall out for free:

- **The keyframe *is* the thumbnail.** `thumbnail_url` is set to the keyframe URL — a thumbnail that is guaranteed to match frame 0 of the video, at no extra generation cost.
- **A consistent clay universe.** A shared style string (Aardman plasticine, visible clay fingerprints, chunky proportions) plus an anti-artifact negative prompt (`no text, no watermark, no distorted limbs, no melted faces…`) is appended to every keyframe so episodes look like the same show and avoid the tells that scream "AI."

**Two shipped extensions of this technique (both validated on real Alibaba Cloud generation):**

- **Multi-shot episodes.** An episode can be *N* chained shots — **setup → escalation → punchline** — instead of a single gag. Each shot gets its own keyframe (`qwen-image-2.0`) → i2v clip (`happyhorse-1.1-i2v`), and all shots are stitched into one continuous video via ffmpeg (`video_gen_client.stitch()`, `oss_client.persist_local()`; the Director emits a `shots` list when `SHOTS_PER_EPISODE > 1`, and `video_node` takes the multi-shot branch). The first shot's keyframe becomes the thumbnail. Config flag `SHOTS_PER_EPISODE` (default **1** = the classic single-gag micro-drama). A real **3-shot Pepe episode** was generated and stitched into a single **15.5-second** video (3 × ~5s shots) and persisted to OSS.
- **Identity-lock consistency gate.** After a keyframe is generated, a `qwen3-vl-plus` vision pass (`vision_client.consistency_score()`) scores how well the character in the keyframe matches its canonical reference portrait, `0.0–1.0`, stored per take as `consistency`. This is now an **enforcing gate, not just telemetry**: when the score falls below `IDENTITY_MIN` (default **0.55**), the take is **rejected as off-model** — a hard fail that overrides the action-quality verdict and drives the regen loop, and on that retake the keyframe is regenerated **fresh** (not surgically reused), because the off-model keyframe is the problem. `IDENTITY_MIN=0` measures without gating. Because the `qwen-image` endpoint does not accept a reference image, identity is enforced by *scoring* the result (vision), not by conditioning the image generator. Config flag `IDENTITY_CHECK`. It calibrated correctly on real generation: a Pepe keyframe vs. the Pepe portrait scored **0.9**, and the same keyframe vs. a *different* character's portrait scored **0.0**.

### (b) The vision-grounded, self-correcting QA loop

One-off tools generate and hope. MUCKFLIX **closes the loop on the real footage**:

1. **Vision grounding.** `qwen3-vl-plus` (`backend/services/vision_client.py`) narrates the *actual chronological cause-and-effect* of the generated clip — who hits/pushes/throws what, and how the other reacts — observing only what's on screen.
2. **QA judges reality, not intent.** The QA agent compares that description against the script and the motion prompt. It is strict but not a perfectionist: it rejects only on serious incoherence or a broken/empty video. And if the vision description comes back **empty** (vision unavailable), QA **rejects** (score 0.0, "Vision could not verify the clip — not approved") instead of auto-approving, so *nothing publishes unwatched* — the loop retries and, if vision never resolves, the episode is published as a **draft**, never as approved.
3. **Targeted feedback.** On rejection, the `qa_notes` are fed **back into the Director** (`director_node` reads `state["qa"]["qa_notes"]` on any attempt after the first), which redesigns the keyframe and motion to *specifically fix that problem*.
4. **Bounded by `MAX_REGEN`.** The loop can run at most `MAX_REGEN` (default **2**) Director re-runs. If still rejected, the best take is packaged and published as a **draft** rather than looping forever — this is the token-budget guard.

Downstream, both the **QA verdict and the Packager's title/description are grounded in the vision output**, so the published copy describes what the video *actually* shows ("the rooster smacks the bread into Pepe's mouth"), not merely what the script intended.

---

## 6. Qwen Cloud & Alibaba Cloud usage

### Qwen Cloud (DashScope) capabilities

| Capability | Model (default) | Endpoint surface | File |
|---|---|---|---|
| Text agents (Writer, Director, QA, Packager) | `qwen3.7-plus` | OpenAI-compatible `/compatible-mode/v1` | `backend/services/qwen_client.py` |
| Keyframe & portrait generation | `qwen-image-2.0` | Native DashScope multimodal-generation (sync) | `backend/services/image_gen_client.py` |
| Image-to-video (animate the keyframe) | `happyhorse-1.1-i2v` | Native DashScope video-synthesis (async submit/poll) | `backend/services/video_gen_client.py` |
| Text-to-video (fallback) | `happyhorse-1.1-t2v` / `wan2.7-t2v` | Native DashScope video-synthesis (async submit/poll) | `backend/services/video_gen_client.py` |
| Video understanding for QA/packaging | `qwen3-vl-plus` | OpenAI-compatible (`video_url` content part) | `backend/services/vision_client.py` |

DashScope video generation is genuinely **asynchronous**: the client POSTs with `X-DashScope-Async: enable` to get a `task_id`, then polls `GET /tasks/{id}` every `video_poll_seconds` until `SUCCEEDED`/`FAILED`, capped by `video_timeout_seconds`. Transient network/5xx errors are retried with backoff; 4xx errors fail fast.

### Alibaba Cloud

| Service | Role | Proof / file |
|---|---|---|
| **ECS** (Docker on Ubuntu) | Runs the FastAPI backend | `backend/deploy/deploy.sh`, [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) |
| **OSS** (Object Storage) | Permanent public storage for generated videos, keyframes/thumbnails and portraits | `backend/services/oss_client.py` |
| **OSS deploy-proof** | A standalone script that uploads a marker object and reads it back — a real service call, not a mention | `backend/deploy/alibaba_deploy_proof.py` |
| **RDS PostgreSQL** (optional) | Production database (swap `DATABASE_URL`) | `docker-compose.yml`, `backend/database/db.py` |

**Why OSS is mandatory for live generation.** DashScope returns *temporary signed URLs* for generated media that expire. Persisting those would silently break the feed later, so live video generation **refuses to run unless OSS is configured** (`video_node` raises if `oss_client.is_configured()` is false). Every generated asset is downloaded and re-hosted on OSS before it reaches the DB.

---

## 7. Tech stack

| Layer | Technology |
|---|---|
| Orchestration | **LangGraph** `StateGraph` (typed state, conditional regen edge) |
| Backend API | **FastAPI** + Uvicorn (Python 3.11) |
| AI models | **Qwen Cloud (DashScope)** — text, image, video, vision |
| HTTP / SDK | `openai` (OpenAI-compatible), `httpx` (native DashScope async) |
| Config / validation | `pydantic-settings`, Pydantic v2 |
| Database | **SQLAlchemy 2** → SQLite (default) or Alibaba Cloud **RDS PostgreSQL** |
| Object storage | Alibaba Cloud **OSS** (`oss2`) |
| Frontend | **Next.js 14** (App Router), React 18, TypeScript, SSE (`EventSource`) |
| Deploy | **Docker** on Alibaba Cloud **ECS**; `docker-compose` for local Postgres |

---

## 8. Project structure

```
cloudhackathon/
├── README.md                  # (this file)
├── LICENSE                    # MIT
├── docker-compose.yml         # local Postgres + backend
├── backend/
│   ├── main.py                # FastAPI app: health, characters, episodes, generate, SSE stream
│   ├── config.py              # env config; endpoint auto-select by key prefix; mock/demo flags
│   ├── Dockerfile             # python:3.11-slim → uvicorn
│   ├── requirements.txt
│   ├── pipeline/
│   │   └── orchestrator.py    # LangGraph graph + nodes + regen loop + DB persistence
│   ├── agents/
│   │   ├── scriptwriter.py    # Agent 1 — the day's gag + tiny script
│   │   ├── production_director.py  # Agent 2 — keyframe + motion prompts (+ QA feedback)
│   │   ├── qa_reviewer.py     # Agent 3 — approve/reject on the real clip
│   │   ├── packager.py        # Agent 4 — viral title + description
│   │   └── _json.py           # tolerant LLM-JSON extractor/repair
│   ├── services/
│   │   ├── qwen_client.py     # text (OpenAI-compatible) + mock mode + retries
│   │   ├── image_gen_client.py# keyframe/portrait (sync DashScope multimodal)
│   │   ├── video_gen_client.py# image→video & text→video (async submit/poll)
│   │   ├── vision_client.py   # qwen3-vl video description
│   │   └── oss_client.py      # persist media to Alibaba Cloud OSS
│   ├── database/
│   │   ├── models.py          # Character, Episode
│   │   ├── db.py              # engine/session
│   │   ├── seed_characters.py # base 8-animal cast
│   │   ├── seed_from_snapshot.py  # zero-cost seed of real episodes/portraits
│   │   └── snapshot.json      # committed demo data (media on OSS)
│   └── deploy/
│       ├── deploy.sh          # one-command ECS deploy
│       └── alibaba_deploy_proof.py  # real OSS call (deploy proof)
├── frontend/                  # Next.js 14 App Router
│   ├── app/page.tsx           # landing: hero, Studio, CinemaFeed, CastGrid
│   ├── components/
│   │   ├── Studio.tsx         # live SSE wizard (cast picker, idea, per-stage activity)
│   │   ├── CinemaFeed.tsx     # episode feed + behind-the-scenes modal
│   │   └── CastGrid.tsx       # cast + "create your own character"
│   └── lib/api.ts             # REST + SSE client, OSS thumbnail helper
└── docs/
    ├── DEPLOYMENT.md          # Alibaba Cloud deploy + proof capture
    ├── README.md              # architecture notes
    ├── architecture_diagram.png / .svg
    └── pipeline_graph.md
```

---

## 9. API reference

Base URL defaults to `http://localhost:8000`. Served by `backend/main.py`.

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness + current mock flags (`mock_text`, `mock_video`). |
| `/characters` | GET | List the cast (name, species, personality, portrait URL). |
| `/characters` | POST | Create your own character (optionally with an AI portrait). Body: `name`, `species`, `personality`, `look`. |
| `/episodes` | GET | All episodes, newest first (full record incl. video, thumbnail, QA). |
| `/episodes/generate` | POST | Run the full 4-agent pipeline and return the new episode. Body: `idea`, `creator`. |
| `/episodes/generate/stream` | GET | **Server-Sent Events**: emits each pipeline stage live for the Studio wizard. Query: `idea`, `creator`. |

**Concurrency guard.** Generation is CPU/IO-heavy and blocking, so a process-wide lock allows only **one** generation at a time; a second concurrent request gets `409` (POST) or a `failed` SSE event. The SSE stream emits one event per node (`scriptwriter`, `director`, `video`, `qa`, `packager`) and finally `done` with the new episode id — or `failed` with a message on error.

---

## 10. Local setup & deploy

### 10.1 Environment variables

All config is env-driven (`backend/config.py`). **Mock mode is the default** so the whole app runs with zero keys and zero cost.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./farm.db` | DB DSN; swap for Alibaba Cloud RDS PostgreSQL. |
| `QWEN_API_KEY` | *(empty)* | Qwen Cloud key. **Empty ⇒ mock mode.** |
| `QWEN_BASE_URL_OVERRIDE` | *(empty)* | Workspace/Model Studio endpoint; wins over auto-selection. |
| `QWEN_BASE_URL_PAYG` | `dashscope-intl…/compatible-mode/v1` | Endpoint for pay-as-you-go keys (`sk-…`). |
| `QWEN_BASE_URL_TOKEN_PLAN` | `token-plan.ap-southeast-1…/compatible-mode/v1` | Endpoint for hackathon token-plan keys (`sk-sp-…`). |
| `QWEN_TEXT_MODEL` | `qwen3.7-plus` | Text model for the 4 agents. |
| `VISION_MODEL` | `qwen3-vl-plus` | Video-understanding model. |
| `IMAGE_MODEL` | `qwen-image-2.0` | Keyframe + portrait generation. |
| `VIDEO_MODEL_I2V` | `happyhorse-1.1-i2v` | Image-to-video (the primary path). |
| `VIDEO_MODEL` / `VIDEO_MODEL_WAN` | `happyhorse-1.1-t2v` / `wan2.7-t2v` | Text-to-video fallbacks. |
| `MOCK_VIDEO` | `true` | Keep video mocked even when text is live (flip to `false` for real video). |
| `FORCE_MOCK` | `false` | Force full mock mode even with a key present. |
| `MAX_REGEN` | `2` | Max Director retakes after a QA rejection (cost cap). |
| `SHOTS_PER_EPISODE` | `1` | Shots per episode (setup→escalation→punchline); `>1` renders N keyframe→i2v shots stitched into one video. `1` = classic single-gag. |
| `IDENTITY_CHECK` | `false` | Score each keyframe's character vs. its canonical portrait with `qwen3-vl-plus` (`0.0–1.0`), stored per take as a measurable consistency gate. |
| `IDENTITY_MIN` | `0.55` | Reject + regenerate (fresh keyframe) any take scoring below this vs. the canonical portrait. `0` = measure only, don't gate. |
| `IMAGE_COST_USD` / `VIDEO_COST_USD_PER_SECOND` | `0.02` / `0.05` | List-price **estimates** for the blended per-episode cost meter (image + video, not just text tokens). |
| `SCHEDULER_ENABLED` / `SCHEDULER_INTERVAL_HOURS` | `false` / `24` | Unattended daily-channel loop: run the showrunner on an interval and publish on the QA verdict. |
| `VIDEO_POLL_SECONDS` / `VIDEO_TIMEOUT_SECONDS` | `10` / `600` | Async video poll interval / timeout. |
| `VIDEO_DURATION` | `0` | Clip length; `0` = model default (~5s). |
| `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` / `OSS_BUCKET` / `OSS_ENDPOINT` | *(empty)* | Alibaba Cloud OSS (**required for live video**). |
| `DEMO_VIDEO_URL` / `DEMO_THUMBNAIL_URL` / `DEMO_VIDEO_DESC` / `DEMO_PACE_SECONDS` | *(empty/0)* | Recording/demo mode: replay a real clip at zero cost and pace the SSE so each stage is visible. |
| `CREATE_REAL_PORTRAITS` | `false` | Generate a real portrait for user-created characters even in mock mode. |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | (frontend) Backend base URL. |

### 10.2 Run modes at a glance

| Mode | How | Cost | Behavior |
|---|---|---|---|
| **Mock** (default) | No `QWEN_API_KEY`, or `FORCE_MOCK=true` | $0 | Every agent returns a deterministic canned response; video is a placeholder URL; QA auto-approves. The whole graph runs offline — ideal for tests and CI. |
| **Demo / recording** | Mock + `DEMO_VIDEO_URL` (+ `DEMO_PACE_SECONDS`) | $0 | Replays a real clip and paces the SSE so the wizard looks live end-to-end. |
| **Text-live, video-mock** | `QWEN_API_KEY` set, `MOCK_VIDEO=true` | text tokens only | Real Qwen scripts/direction/QA/packaging; placeholder video. |
| **Fully live** | `QWEN_API_KEY` + `MOCK_VIDEO=false` + `OSS_*` | full | Real keyframe → i2v → vision → QA loop; media persisted to OSS. |

The `mock`/live switch requires **no code change** — every service checks `settings.use_mock` and returns caller-supplied mock data (`backend/services/qwen_client.py`).

### 10.3 Backend (local)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # optional; empty .env = mock mode, $0
python -m database.seed_characters # seed the base cast
uvicorn main:app --reload
```

Verify: <http://localhost:8000/health> · <http://localhost:8000/characters>

To populate the app with the committed **real** episodes/portraits (served from OSS) at zero cost:

```bash
python -m database.seed_from_snapshot   # idempotent
```

### 10.4 Frontend (local)

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000  (set NEXT_PUBLIC_API_URL if backend isn't on :8000)
```

### 10.5 Local Postgres via Docker

```bash
docker compose up --build   # Postgres 16 + backend on :8000
```

### 10.6 One-command Alibaba Cloud deploy

On a fresh Ubuntu **ECS** instance (allow inbound TCP 22 + 80):

```bash
ssh root@<ECS_PUBLIC_IP>
curl -fsSL https://raw.githubusercontent.com/kasbsquall/digital-farm-showrunner/main/backend/deploy/deploy.sh | bash
```

This installs Docker, builds the image, runs it on port 80→8000, writes a **`FORCE_MOCK=true`** `.env` (no keys, no credits), and seeds the cast + real episodes from the snapshot — so the app is fully populated and live for **$0**. Verify with `curl http://<ip>/health` and `/episodes`.

To enable live generation and prove OSS *from the instance*, set `FORCE_MOCK=false`, add `QWEN_API_KEY` + `OSS_*`, re-run the container, then:

```bash
docker exec muckflix python -m deploy.alibaba_deploy_proof   # OSS upload ok=True url=...
```

Full steps and proof-capture checklist: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## 11. Testing

The mock harness makes the pipeline **fully deterministic and offline-testable**: with `FORCE_MOCK=true`, every agent returns a canned response derived from its own inputs, so the entire LangGraph flow (including the QA→Director regen edge) can be exercised without any network or credits.

A **31-test pytest suite** lives under [`backend/tests/`](backend/tests/) and runs fully offline:

```bash
cd backend
pip install pytest httpx
FORCE_MOCK=true python -m pytest tests/ -q     # 31 passed
```

Coverage highlights:

| Test file | What it locks in |
|---|---|
| `test_regen.py` | The **self-correcting loop**: a rejected take is regenerated, the corrected take is approved & published, and the auditable take history accumulates — plus the budget-cap path. |
| `test_orchestrator.py` | `_after_qa` routing (approve / retake / out-of-budget) and graph node ids. |
| `test_pipeline.py` | Full mock-mode E2E: `run_stream` yields every stage in order and persists an Episode. |
| `test_api.py` | `/health`, `/characters` (+409 duplicate), `/episodes`, the SSE stream, and the in-flight lock. |
| `test_json.py` / `test_config.py` | JSON repair (fences, trailing commas, smart quotes) and endpoint auto-selection by key prefix. |

---

## 12. Cost & token-budget notes

Cost control is a first-class design goal, not an afterthought:

| Lever | Effect |
|---|---|
| **Keyframe → i2v** | One image + one short i2v job is cheaper and more controllable than brute-forcing long text-to-video, and the keyframe *doubles as the thumbnail* (no extra generation). |
| **`MAX_REGEN`** | Hard cap on QA retakes (default 2). The loop *always* terminates into the Packager; it can never run away on tokens/video jobs. |
| **Mock mode** | No key ⇒ every model call is skipped; the full app runs at **$0** for development, CI and demos. |
| **Demo/recording mode** | Replays a real clip at **$0** so the pipeline can be recorded end-to-end without spending credits. |
| **Snapshot seeding** | A deployed instance shows real episodes/portraits (served from OSS) with **zero API calls**. |
| **`MOCK_VIDEO` split** | Run real text agents while keeping the expensive video step mocked, to iterate on prompts cheaply. |
| **OSS on-the-fly resize** | `ossThumb` requests downscaled WebP (`x-oss-process`), cutting feed payloads from ~1.4 MB to a few KB. |

---

## Defensibility & unit economics

**The moat is three layers that compound, not one trick.**

- **Character consistency by construction — and now *enforced*.** Keyframe → i2v pins the cast to an established look ([§5a](#5-the-two-signature-techniques)); competitors doing blind text-to-video can't hold a mascot across a daily series. An optional identity-lock gate (`IDENTITY_CHECK`) scores each keyframe against its canonical portrait with `qwen3-vl-plus` (calibrated **0.9** for a matching character, **0.0** for a mismatch) and **rejects** any take below `IDENTITY_MIN`, regenerating a fresh keyframe — so consistency is a number the pipeline acts on, not just reports.
- **A self-correcting QA gate that never publishes unwatched.** The vision-grounded retake loop is committed and reproducible — the "Wobbly Gold Spheres…" episode passed only on take 3 (`rejected → rejected → approved` in `snapshot.json`). Unsupervised daily publishing is only safe because a step actually watches the footage — and when vision can't watch the clip at all, QA rejects rather than approving blind, so the episode ships as a draft instead of unverified.
- **A per-channel data flywheel (the compounding advantage).** Every episode's cast, prompts, take history and QA verdicts are logged per channel, so each channel's prompting and continuity get better with volume — an advantage a one-off clip tool can't accumulate.

**ICP.** First wedge: solo creators and small brand/SMB social teams who need a *recurring on-model character series* (mascot channels, kids' shorts, brand serials) but can't staff a daily production crew.

**Unit economics.** Cost per episode stays low by design: the keyframe *doubles as the thumbnail* (no separate thumbnail render), and `MAX_REGEN` hard-caps retakes so a bad generation can't burn budget in a loop ([§12](#12-cost--token-budget-notes)). Each episode surfaces a **blended per-episode cost meter** — text tokens *plus* the image and video calls (`usage.add_image()` / `usage.add_video()`), so the receipt reflects the true marginal cost (a real approved multi-shot episode metered at **$0.86**), not just the cheap text half.

---

## 13. Roadmap / productization

The farm proves the engine; the business is **serialized daily video as a service**.

- **Per-creator channels.** Point the pipeline at any cast + style to run a distinct daily show per creator/brand.
- **Monetization.** Channel subscriptions + **microtransactions** to prioritize your submitted idea for tomorrow's episode (audience co-creation is already wired via the `creator` credit).
- **Richer casts & continuity.** Deeper multi-episode story arcs and larger character rosters.
- **Multi-shot episodes — ✅ shipped.** Beyond the ~5s single-gag format: an episode can now be N chained shots (setup→escalation→punchline) stitched into one continuous video (`SHOTS_PER_EPISODE`; a real 3-shot Pepe episode stitched to 15.5s on OSS). Next: even longer multi-beat story arcs.
- **Identity-lock consistency check — ✅ shipped.** A `qwen3-vl-plus` pass scores each keyframe's character against its canonical portrait (`IDENTITY_CHECK`), turning character consistency into a measurable per-take number.
- **Scheduling & auto-publish — ✅ shipped.** An unattended daily-channel loop (`backend/scheduler.py`, `SCHEDULER_ENABLED`) runs the showrunner on an interval and publishes on the QA verdict — in-process on app startup, or standalone (`python -m scheduler [--once]`, cron-friendly). The vision-grounded QA loop is what makes unsupervised publishing safe. Next: even longer multi-beat story arcs.
- **Managed RDS + CDN.** Production Postgres on Alibaba Cloud RDS and OSS-backed CDN delivery for the feed.

---

## 14. License

**MIT** — see [`LICENSE`](LICENSE).

Built for the **Qwen Cloud Global AI Hackathon 2026 — Track 2: AI Showrunner**.
