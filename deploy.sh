#!/usr/bin/env bash
# One-shot setup for the review dashboard on a VPS.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# Load .env so BASE_PATH/PORT are available to this script and the build.
if [ -f .env ]; then
  set -a; . ./.env; set +a
fi
BASE_PATH="${DASHBOARD_BASE_PATH:-/dashboard}"
PORT="${DASHBOARD_PORT:-8412}"

echo "==> Setting up Python virtual environment (venv/)"
if [ ! -d venv ]; then
  python3 -m venv venv
fi
# shellcheck disable=SC1091
. venv/bin/activate

echo "==> Installing backend dependencies into venv"
pip install --upgrade pip >/dev/null
pip install -r backend/requirements.txt

echo "==> Building frontend (React + Vite) with base path: $BASE_PATH"
cd frontend
npm install
DASHBOARD_BASE_PATH="$BASE_PATH" npm run build
cd ..

echo ""
echo "Build complete. The dashboard will be served under $BASE_PATH."
echo ""
echo "Start the dashboard with (uses the venv's uvicorn):"
echo "    cd backend && DASHBOARD_BASE_PATH=$BASE_PATH ../venv/bin/uvicorn app:app --host 0.0.0.0 --port $PORT"
echo ""
echo "Then open:  http://<your-vps-ip>:$PORT$BASE_PATH"