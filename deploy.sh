#!/usr/bin/env bash
# One-shot setup for the review dashboard on a VPS.
#   ./deploy.sh          # build frontend + install backend, then print how to run
#
# Reads DASHBOARD_BASE_PATH and DASHBOARD_PORT from .env (if present) so the
# frontend is built with the same base path the backend serves under.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# Load .env so BASE_PATH/PORT are available to this script and the build.
if [ -f .env ]; then
  set -a; . ./.env; set +a
fi
BASE_PATH="${DASHBOARD_BASE_PATH:-/dashboard}"
PORT="${DASHBOARD_PORT:-8412}"

echo "==> Installing backend dependencies"
pip install -r backend/requirements.txt

echo "==> Building frontend (React + Vite) with base path: $BASE_PATH"
cd frontend
npm install
DASHBOARD_BASE_PATH="$BASE_PATH" npm run build
cd ..

echo ""
echo "Build complete. The dashboard will be served under $BASE_PATH."
echo ""
echo "Make sure .env in the project root has FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN,"
echo "DASHBOARD_TOKEN, DASHBOARD_BASE_PATH=$BASE_PATH, DASHBOARD_PORT=$PORT."
echo ""
echo "Start the dashboard with:"
echo "    cd backend && DASHBOARD_BASE_PATH=$BASE_PATH uvicorn app:app --host 0.0.0.0 --port $PORT"
echo ""
echo "Then open:  http://<your-vps-ip>:$PORT$BASE_PATH"
echo "(put it behind HTTPS + a firewall in production)."
echo ""
echo "Point Hermes/cron at scripts/run_scheduler.sh to auto-fill the queue daily."
