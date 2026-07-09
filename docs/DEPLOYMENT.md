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
2. **Security Group** → allow inbound TCP **22** (SSH) and **8000** (the API).
3. Launch and note the **public IP**.

## 2. Deploy (one command)

```bash
ssh root@<ECS_PUBLIC_IP>
curl -fsSL https://raw.githubusercontent.com/kasbsquall/digital-farm-showrunner/main/backend/deploy/deploy.sh | bash
```

That installs Docker, builds the image, runs it on port 8000, and seeds the cast +
real episodes from the committed snapshot (media served from public OSS). It runs
with `FORCE_MOCK=true` by default, so **it needs no API keys and costs nothing**.

**Verify:**
```bash
curl http://localhost:8000/health      # {"status":"ok", ...}
curl http://localhost:8000/episodes    # the real episodes
```

### (Optional) enable live generation + prove OSS from the instance
Edit `/opt/digital-farm-showrunner/backend/.env`, set `FORCE_MOCK=false`, add
`QWEN_API_KEY`, `QWEN_BASE_URL_OVERRIDE` and the `OSS_*` vars, then:
```bash
cd /opt/digital-farm-showrunner/backend && docker rm -f muckflix
docker run -d --name muckflix --restart unless-stopped -p 8000:8000 --env-file .env muckflix-backend
docker exec muckflix python -m deploy.alibaba_deploy_proof   # OSS upload ok=True url=...
```

## 3. Capture the proof (this is the deliverable)

Screenshot **all** of these into `docs/deploy_proof/`:

1. **ECS console** — the instance list showing status **Running**, its **public IP**, region.
2. **Browser** at `http://<ECS_PUBLIC_IP>:8000/health` and `/episodes` returning JSON —
   with the Alibaba public IP visible in the address bar.
3. **Terminal** (SSH'd into the instance, so the prompt shows the Alibaba host) running
   `docker ps` (container up) and, if OSS is configured, the `alibaba_deploy_proof`
   output with `ok=True` and the OSS URL.

## 4. Frontend (optional, for the full demo)

Point the Next.js app at the deployed API by setting `NEXT_PUBLIC_API_URL=http://<ECS_PUBLIC_IP>:8000`,
or run it locally against the deployed backend. The frontend can be hosted anywhere
(Vercel/static) — the *backend on Alibaba Cloud* is what the requirement asks for.

> 💡 Tear down the instance right after recording to avoid ongoing charges.
