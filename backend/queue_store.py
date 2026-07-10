"""
JSON-backed review queue shared between the scheduler (enqueues due items)
and the FastAPI backend (serves them for review, posts approved ones).

Each queue item is a dict:
{
  "id": "sched-12" | "manual-<uuid>",
  "source": "schedule" | "manual",
  "content_type": "countdown",
  "city": "Munich",
  "platform": "facebook",
  "media_file": "GENERATE" | "flyer_main.jpg" | "<url>",
  "background": "" | "venue_photo_2.jpg",
  "headline": "...",
  "subtext": "...",
  "caption": "...",             # fully rendered caption text (editable)
  "scheduled_for": "2026-08-04 11:00",
  "status": "pending_review" | "approved" | "posted" | "rejected" | "error",
  "preview_path": "content/generated/<id>.jpg",
  "posted_at": "",
  "note": ""
}
"""
import csv
import json
import os
import sys
import uuid
from datetime import datetime
from threading import Lock

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "scripts"))
from utils import parse_schedule_datetime, render_template, parse_extra, EVENT_DATE  # noqa: E402

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
SCHEDULE_PATH = os.path.join(REPO_ROOT, "content", "schedule.csv")
QUEUE_PATH = os.path.join(REPO_ROOT, "content", "queue.json")
GENERATED_DIR = os.path.join(REPO_ROOT, "content", "generated")

_lock = Lock()


def _load() -> list:
    if not os.path.isfile(QUEUE_PATH):
        return []
    with open(QUEUE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save(items: list):
    os.makedirs(os.path.dirname(QUEUE_PATH), exist_ok=True)
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def get_queue(status: str = None) -> list:
    items = _load()
    if status:
        items = [i for i in items if i["status"] == status]
    return items


def get_item(item_id: str):
    for i in _load():
        if i["id"] == item_id:
            return i
    return None


def _resolve_caption_file(caption_file: str, city: str, post_date, extra: dict) -> str:
    path = os.path.join(REPO_ROOT, "content", "captions", caption_file)
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    return render_template(raw, city, as_of=post_date, extra=extra)


def enqueue_due_from_schedule(dry_run: bool = False) -> list:
    """Read schedule.csv, enqueue any due rows not already in the queue."""
    with _lock:
        items = _load()
        existing_sched_ids = {i["id"] for i in items if i["source"] == "schedule"}
        now = datetime.now()
        added = []

        if not os.path.isfile(SCHEDULE_PATH):
            return []

        with open(SCHEDULE_PATH, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        for row in rows:
            if row.get("status", "pending") != "pending":
                continue
            qid = f"sched-{row['id']}"
            if qid in existing_sched_ids:
                continue
            scheduled_at = parse_schedule_datetime(row["date"], row["time"])
            if scheduled_at > now:
                continue

            post_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
            extra = parse_extra(row.get("extra", ""))
            caption = _resolve_caption_file(row.get("caption_file", ""), row["city"], post_date, extra)

            item = {
                "id": qid,
                "source": "schedule",
                "content_type": row.get("content_type", ""),
                "city": row.get("city", ""),
                "platform": row.get("platform", "facebook"),
                "media_file": row.get("media_file", "GENERATE"),
                "background": extra.get("background", ""),
                "headline": render_template(row.get("headline", ""), row["city"], as_of=post_date, extra=extra),
                "subtext": render_template(row.get("subtext", ""), row["city"], as_of=post_date, extra=extra),
                "caption": caption,
                "scheduled_for": scheduled_at.strftime("%Y-%m-%d %H:%M"),
                "status": "pending_review",
                "preview_path": "",
                "posted_at": "",
                "note": "",
            }
            added.append(item)

        if not dry_run and added:
            items.extend(added)
            _save(items)
    return added


def add_manual_item(data: dict) -> dict:
    with _lock:
        items = _load()
        item = {
            "id": f"manual-{uuid.uuid4().hex[:8]}",
            "source": "manual",
            "content_type": data.get("content_type", "countdown"),
            "city": data.get("city", ""),
            "platform": data.get("platform", "facebook"),
            "media_file": data.get("media_file", "GENERATE"),
            "background": data.get("background", ""),
            "headline": data.get("headline", ""),
            "subtext": data.get("subtext", ""),
            "caption": data.get("caption", ""),
            "scheduled_for": data.get("scheduled_for", datetime.now().strftime("%Y-%m-%d %H:%M")),
            "status": "pending_review",
            "preview_path": "",
            "posted_at": "",
            "note": "",
        }
        items.append(item)
        _save(items)
    return item


def update_item(item_id: str, updates: dict) -> dict:
    with _lock:
        items = _load()
        for i in items:
            if i["id"] == item_id:
                for k, v in updates.items():
                    if k in i:
                        i[k] = v
                _save(items)
                return i
    return None


def mark_status(item_id: str, status: str, posted_at: str = "", note: str = "") -> dict:
    updates = {"status": status}
    if posted_at:
        updates["posted_at"] = posted_at
    if note:
        updates["note"] = note
    return update_item(item_id, updates)
