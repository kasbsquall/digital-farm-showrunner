#!/usr/bin/env bash
# One-shot deploy of the MUCKFLIX backend on a fresh Ubuntu Alibaba Cloud ECS instance.
#
#   ssh root@<ECS_PUBLIC_IP>
#   curl -fsSL https://raw.githubusercontent.com/kasbsquall/digital-farm-showrunner/main/backend/deploy/deploy.sh | bash
#
# It installs Docker, clones the repo, builds the image, runs it on port 8000,
# and seeds the DB from the committed snapshot (real episodes + portraits from OSS)
# so the app is fully populated WITHOUT any API keys or credits.
set -euo pipefail

REPO="https://github.com/kasbsquall/digital-farm-showrunner.git"
DIR="/opt/digital-farm-showrunner"

echo "==> 1/5 Installing Docker (if needed)…"
command -v docker >/dev/null 2>&1 || curl -fsSL https://get.docker.com | sh

echo "==> 2/5 Fetching the code…"
if [ -d "$DIR" ]; then git -C "$DIR" pull --ff-only; else git clone "$REPO" "$DIR"; fi
cd "$DIR/backend"

echo "==> 3/5 Preparing .env…"
if [ ! -f .env ]; then
  # FORCE_MOCK lets it run with NO API keys and NO credits — perfect for the
  # deploy-proof demo. Add QWEN_API_KEY + OSS_* later to enable live generation.
  cat > .env <<'EOF'
DATABASE_URL=sqlite:///./farm.db
FORCE_MOCK=true
EOF
  echo "    Wrote a zero-cost .env (FORCE_MOCK=true). Edit it to enable live generation."
fi

echo "==> 4/5 Building & running the container…"
docker build -t muckflix-backend .
docker rm -f muckflix >/dev/null 2>&1 || true
docker run -d --name muckflix --restart unless-stopped -p 8000:8000 --env-file .env muckflix-backend

echo "==> 5/5 Seeding cast + real episodes from snapshot…"
sleep 6
docker exec muckflix python -m database.seed_from_snapshot

IP=$(curl -fsS https://api.ipify.org 2>/dev/null || echo "<this-server-ip>")
echo
echo "✅ Done. The MUCKFLIX backend is live on this Alibaba Cloud instance:"
echo "   http://${IP}:8000/health"
echo "   http://${IP}:8000/episodes"
echo
echo "Proof of Alibaba services (OSS) from ON this instance:"
echo "   docker exec muckflix python -m deploy.alibaba_deploy_proof   # needs OSS_* in .env"
