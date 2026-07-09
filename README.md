# 🐔 MUCKFLIX — The Digital Farm Showrunner

**Qwen Cloud Hackathon 2026 · Track 2: AI Showrunner**

**An autonomous "showrunner" that produces a serialized, character-consistent short
video show — every single day, with zero human production team.**

MUCKFLIX is a claymation farm channel where a pipeline of **4 AI agents** takes a
one-line idea and runs the *entire* production — writing, art-directing, filming,
QA and packaging — into a finished, publish-ready episode. The farm is the demo;
the real deliverable is a **general engine for daily, on-brand, serialized video**.

## The problem it actually solves

Short-form video is the oxygen of the modern internet — but **producing consistent
daily video is slow, expensive, and needs a whole team.** Creators, SMBs and brands
are stuck on a treadmill they can't afford. Existing AI video tools make *one-off*
clips with **no character continuity and no quality control** — you can't run a
*show* on them.

MUCKFLIX closes exactly those gaps:

- **Serialized, character-consistent cast.** A keyframe→image-to-video technique locks
  each recurring character's look across episodes (the generated still *is* frame 0 of
  the clip). Point the engine at *your* mascot and it runs *your* daily show.
- **Autonomous quality control you can trust.** A vision model (Qwen3-VL) watches the
  *actual* generated clip and, if it doesn't match the intended gag, **feeds the reason
  back to the director to regenerate** — a real self-correcting loop, so it can publish
  unsupervised.
- **Audience co-creation → built-in virality & monetization.** Anyone submits an idea and
  gets **credited** on the episode. The obvious business model: subscriptions per channel
  + microtransactions to prioritize your idea for tomorrow's episode.

**Who it's for:** creators who need a daily show without a studio, brands that want mascot
marketing at scale, and educators who want an endless, on-brand animated series.

## The 4 agents

| # | Agent | Role | Qwen surface |
|---|-------|------|--------------|
| 1 | **Scriptwriter** | Invents the day's gag + tiny script, with continuity from past episodes. | qwen3.7 (text) |
| 2 | **Production Director** | Turns the script into a keyframe image prompt + a single 5s motion. | qwen3.7 (text) |
| — | *Keyframe → Video* | Paints the scene (Qwen-Image) then animates that exact still (HappyHorse i2v). | qwen-image · happyhorse-i2v |
| 3 | **Quality Control** | Watches the *real* clip via vision; if it misses the gag, feeds the reason back to the Director to regenerate. | qwen3-vl |
| 4 | **Packager** | Writes the viral title + description that match what the video actually shows. | qwen3.7 (text) |

## Stack

- **Backend:** FastAPI (Python 3.11) — Alibaba Cloud ECS / Function Compute
- **Orquestación:** LangGraph
- **Modelos:** Qwen Cloud (DashScope)
- **Video:** Wan / HappyHorse
- **DB:** PostgreSQL (Alibaba Cloud RDS) / SQLite
- **Storage:** Alibaba Cloud OSS
- **Frontend:** Next.js

## Setup rápido (local)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # rellena QWEN_API_KEY, OSS_*
python -m database.seed_characters   # siembra la granja
uvicorn main:app --reload
```

Verifica: <http://localhost:8000/health> · <http://localhost:8000/characters>

## Docker

```bash
docker compose up --build
```

## Personajes base

Bruno (gallo sindicalista) · Lola (vaca romántica) · Tractor (indiferente) ·
Pepe (cerdo filósofo) · Nina (gallina reportera).

## Arquitectura

Ver [`docs/README.md`](docs/README.md).

## Licencia

MIT — ver [LICENSE](LICENSE).
