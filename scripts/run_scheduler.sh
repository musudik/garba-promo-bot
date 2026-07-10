#!/usr/bin/env bash
# Wrapper for cron / an agent runner (e.g. Hermes) to call on a schedule.
# It fills the REVIEW QUEUE with any posts due — it does NOT post to Facebook.
# Posting happens only when a team member approves an item in the dashboard.
#
# Point your scheduler at this script:
#   /full/path/to/garba-promo-bot/scripts/run_scheduler.sh
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
if [ -f "venv/bin/activate" ]; then source venv/bin/activate; fi
mkdir -p logs
echo "=== Run at $(date '+%Y-%m-%d %H:%M:%S') ===" >> logs/cron.log
python3 scripts/post_scheduler.py >> logs/cron.log 2>&1
