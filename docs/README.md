# Architecture — The Digital Farm Showrunner

![Architecture](architecture_diagram.png)

> Editable source: [`architecture_diagram.svg`](architecture_diagram.svg).

## Agent flow

```
                 recent_events + base cast (SQLite / Alibaba RDS)
                                 │
                                 ▼
   ┌─────────────────── LangGraph orchestrator ───────────────────┐
   │                                                              │
   │  Agent 1  Scriptwriter ─► Agent 2  Production Director        │
   │  (Qwen text)             (Qwen text → keyframe + motion)     │
   │                                 │                            │
   │                                 ▼                            │
   │            Keyframe → Image-to-Video → Vision                │
   │            (Qwen-Image · HappyHorse i2v · Qwen3-VL)          │
   │                                 │                            │
   │                                 ▼                            │
   │                     Agent 3  Quality Control ──reject──┐     │
   │                          │ approve                     │     │
   │                          ▼            retake loop  ◄────┘     │
   │                     Agent 4  Packager                        │
   └──────────────────────────────┬───────────────────────────────┘
                                   ▼
             Episode row (DB) + video & keyframe on Alibaba Cloud OSS
                                   │
                                   ▼
                     Next.js feed  ◄── FastAPI /episodes
```

## Alibaba Cloud services
- **ECS (Docker)** — runs the FastAPI backend (one-command deploy in [`deploy/deploy.sh`](../backend/deploy/deploy.sh)).
- **RDS (PostgreSQL)** — optional production persistence for episodes and characters (SQLite by default).
- **OSS** — storage for generated videos and keyframes (see [`backend/services/oss_client.py`](../backend/services/oss_client.py) and [`backend/deploy/alibaba_deploy_proof.py`](../backend/deploy/alibaba_deploy_proof.py)).

## Qwen Cloud (DashScope)
- Text models (agents 1-4): `qwen3.7-plus` via the OpenAI-compatible endpoint.
- Image (keyframes + character portraits): `qwen-image-2.0` via the native multimodal endpoint.
- Video (image-to-video): `happyhorse-1.1-i2v` via the native async submit/poll endpoint.
- Video understanding (QA vision): `qwen3-vl-plus`.
