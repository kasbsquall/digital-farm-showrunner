# Architecture — The Digital Farm Showrunner

![Arquitectura](architecture_diagram.png)

> Fuente editable: [`architecture_diagram.svg`](architecture_diagram.svg).

## Flujo de agentes

```
                 recent_events + base cast (PostgreSQL / SQLite)
                                 │
                                 ▼
   ┌─────────────────── LangGraph orchestrator ───────────────────┐
   │                                                              │
   │  Agent 1  Scriptwriter ─► Agent 2  Production Director        │
   │  (Qwen text)             (Qwen text → video prompt)          │
   │                                 │                            │
   │                                 ▼                            │
   │                         Wan / HappyHorse  (video gen)        │
   │                                 │                            │
   │                                 ▼                            │
   │                     Agent 3  QA Reviewer ──reject──┐         │
   │                          │ approve                 │         │
   │                          ▼            regen loop ◄─┘         │
   │                     Agent 4  Packager                        │
   └──────────────────────────────┬───────────────────────────────┘
                                   ▼
             Episode row (PostgreSQL) + video en Alibaba Cloud OSS
                                   │
                                   ▼
                     Next.js feed  ◄── FastAPI /episodes
```

## Servicios de Alibaba Cloud
- **ECS / Function Compute** — corre el backend FastAPI.
- **RDS (PostgreSQL)** — persistencia de episodios y personajes.
- **OSS** — almacenamiento de videos generados (ver `backend/deploy/alibaba_deploy_proof.py`).

## Qwen Cloud (DashScope)
- Modelos de texto (agentes 1-4) vía endpoint OpenAI-compatible.
- Generación de video (Wan / HappyHorse).
