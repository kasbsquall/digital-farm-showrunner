# 🐔 The Digital Farm Showrunner

**Qwen Cloud Hackathon 2026 · Track 2: AI Showrunner**

Una granja digital donde animales con personalidad viven micro-dramas absurdos
generados automáticamente cada día por un pipeline de **4 agentes de IA** — desde
el guion hasta el episodio empaquetado listo para publicar, sin intervención humana.

## Los 4 agentes

| # | Agente | Rol |
|---|--------|-----|
| 1 | **Scriptwriter** | Decide el evento absurdo del día y escribe el guion (con continuidad narrativa). |
| 2 | **Production Director** | Traduce el guion a un prompt técnico de video (Wan / HappyHorse). |
| 3 | **QA Reviewer** | Aprueba o pide regenerar — protege el presupuesto de tokens. |
| 4 | **Packager** | Genera título, thumbnail y descripción listos para publicar. |

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
