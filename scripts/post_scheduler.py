"""
Standalone scheduler run (cron/Hermes). Fills the review queue from
schedule.csv for anything due. Actual posting to Facebook is done via the
review dashboard (backend/app.py) after human approval — this script only
enqueues, it does NOT auto-post, so nothing goes live unreviewed.

Usage:
    python scripts/post_scheduler.py            # enqueue due items
    python scripts/post_scheduler.py --dry-run   # preview only
"""
import argparse
import os
import sys

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from queue_store import enqueue_due_from_schedule  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    added = enqueue_due_from_schedule(dry_run=args.dry_run)
    if args.dry_run:
        print(f"[dry-run] {len(added)} item(s) would be enqueued for review.")
        for item in added:
            print(f"  - id={item['id']} {item['content_type']} {item['city']} ({item['scheduled_for']})")
    else:
        print(f"Enqueued {len(added)} new item(s) into the review queue.")


if __name__ == "__main__":
    main()
