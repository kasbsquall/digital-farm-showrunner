#!/usr/bin/env bash
# One-shot deploy of the FULL MUCKFLIX app (frontend + backend) on a fresh Ubuntu
# Alibaba Cloud ECS instance.
#
#   ssh root@<ECS_PUBLIC_IP>
#   curl -fsSL https://raw.githubusercontent.com/kasbsquall/digital-farm-showrunner/main/backend/deploy/deploy.sh | bash
#
# It installs Docker, clones the repo, builds ONE image (root Dockerfile: Next.js static
# export served by the FastAPI backend), runs it on port 80, and seeds the DB from the
# committed snapshot (real episodes + portraits from OSS) — the whole browsable app on
# ONE URL, WITHOUT any API keys or credits.
set -euo pipefail

REPO="https://github.com/kasbsquall/digital-farm-showrunner.git"
DIR="/opt/digital-farm-showrunner"

echo "==> 1/5 Installing Docker (if needed)…"
command -v docker >/dev/null 2>&1 || curl -fsSL https://get.docker.com | sh

echo "==> 2/5 Fetching the code…"
if [ -d "$DIR" ]; then git -C "$DIR" pull --ff-only; else git clone "$REPO" "$DIR"; fi
cd "$DIR"

echo "==> 3/5 Preparing .env…"
if [ ! -f backend/.env ]; then
  # FORCE_MOCK lets it run with NO API keys and NO credits — perfect for the
  # deploy-proof demo. Add QWEN_API_KEY + OSS_* later to enable live generation.
  cat > backend/.env <<'EOF'
DATABASE_URL=sqlite:///./farm.db
FORCE_MOCK=true
EOF
  echo "    Wrote a zero-cost backend/.env (FORCE_MOCK=true). Edit it to enable live generation."
fi

echo "==> 4/5 Building & running the full-stack container (frontend + backend)…"
docker build -t muckflix .
docker rm -f muckflix >/dev/null 2>&1 || true
docker run -d --name muckflix --restart unless-stopped -p 80:8000 --env-file backend/.env muckflix

echo "==> 5/5 Seeding cast + real episodes from snapshot…"
sleep 6
docker exec muckflix python -m database.seed_from_snapshot

IP=$(curl -fsS https://api.ipify.org 2>/dev/null || echo "<this-server-ip>")
echo
echo "✅ Done. The full MUCKFLIX app is live on this Alibaba Cloud instance:"
echo "   http://${IP}/            ← the browsable app (UI)"
echo "   http://${IP}/health      ← API health"
echo "   http://${IP}/episodes    ← API (the real episodes)"
echo
echo "Proof of Alibaba services (OSS) from ON this instance:"
echo "   docker exec muckflix python -m deploy.alibaba_deploy_proof   # needs OSS_* in .env"
