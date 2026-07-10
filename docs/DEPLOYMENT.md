# Deploying MUCKFLIX on Alibaba Cloud (proof of deployment)

The backend runs on an **Alibaba Cloud ECS** instance (Docker), and stores generated
videos/images in **Alibaba Cloud OSS**. This page is the required *proof of deployment*.

- **Alibaba service used in code:** [`backend/services/oss_client.py`](../backend/services/oss_client.py)
  and [`backend/deploy/alibaba_deploy_proof.py`](../backend/deploy/alibaba_deploy_proof.py)
  (real `oss2` calls to Alibaba Cloud OSS).
- **One-command deploy:** [`backend/deploy/deploy.sh`](../backend/deploy/deploy.sh)

## 1. Create the ECS instance (Alibaba Cloud console)

1. **ECS → Create Instance** → Pay-As-You-Go (or use your ECS free-trial credit) →
   cheapest burstable type (~1 vCPU / 1–2 GB) → **Ubuntu 22.04** → assign a **public IP**.
2. **Security Group** → allow inbound TCP **22** (SSH) and **80** (HTTP — the API).
3. Launch and note the **public IP**.

## 2. Deploy (one command)

```bash
ssh root@<ECS_PUBLIC_IP>
curl -fsSL https://raw.githubusercontent.com/kasbsquall/digital-farm-showrunner/main/backend/deploy/deploy.sh | bash
```

That installs Docker, builds **one image** (the root `Dockerfile`: the Next.js frontend
compiled to a static export and served by the FastAPI backend), runs it on **port 80**,
and seeds the cast + real episodes from the committed snapshot (media served from public
OSS). It runs with `FORCE_MOCK=true` by default, so **it needs no API keys and costs
nothing** — the whole browsable app on one URL.

**Verify:**
```bash
curl http://localhost/            # the app (HTML)
curl http://localhost/health      # {"status":"ok", ...}
curl http://localhost/episodes    # the real episodes (JSON)
```
Then open `http://<ECS_PUBLIC_IP>/` in a browser — the full UI, same origin as the API
(no CORS, no mixed-content).

### (Optional) enable live generation + prove OSS from the instance
Edit `/opt/digital-farm-showrunner/backend/.env`, set `FORCE_MOCK=false`, add
`QWEN_API_KEY`, `QWEN_BASE_URL_OVERRIDE` and the `OSS_*` vars, then from the repo root:
```bash
cd /opt/digital-farm-showrunner && docker rm -f muckflix
docker build -t muckflix .
docker run -d --name muckflix --restart unless-stopped -p 80:8000 --env-file backend/.env muckflix
docker exec muckflix python -m deploy.alibaba_deploy_proof   # OSS upload ok=True url=...
```

## 3. Capture the proof (this is the deliverable)

Screenshot **all** of these into `docs/deploy_proof/`:

1. **ECS console** — the instance list showing status **Running**, its **public IP**, region.
2. **Browser** at `http://<ECS_PUBLIC_IP>/health` and `/episodes` returning JSON —
   with the Alibaba public IP visible in the address bar.
3. **Terminal** (SSH'd into the instance, so the prompt shows the Alibaba host) running
   `docker ps` (container up) and, if OSS is configured, the `alibaba_deploy_proof`
   output with `ok=True` and the OSS URL.

## 4. Frontend

No separate step — the one-command deploy above already builds the Next.js UI (static
export, `NEXT_PUBLIC_API_URL=""` → same-origin API) into the same image and serves it at
`http://<ECS_PUBLIC_IP>/`. The full app runs from **one container on Alibaba Cloud**.

> 💡 Tear down the instance right after recording to avoid ongoing charges.
