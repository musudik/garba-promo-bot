"""
FastAPI backend for the Garba promo review dashboard.

Runs on your VPS. Serves:
  - JSON API under /api/* for the review queue
  - generated preview images under /previews/*
  - the built React frontend (frontend/dist) at / for a single-origin deploy

Facebook posting happens ONLY when a human approves an item here — the
access token stays on this server and is never exposed to the browser.

The whole app is served under DASHBOARD_BASE_PATH (default /dashboard) on
DASHBOARD_PORT (default 8412), so the public URL is:
    http://<vps-ip>:<port>/dashboard

Run:
    cd backend && DASHBOARD_BASE_PATH=/dashboard uvicorn app:app --host 0.0.0.0 --port 8412
"""
import os
import sys
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "scripts"))
import image_overlay  # noqa: E402
import facebook_api  # noqa: E402
import queue_store  # noqa: E402
from utils import EVENT_DATE  # noqa: E402

EVENT_FOOTER = f"{EVENT_DATE.strftime('%d %b %Y').upper()} · #GarbaGermany"

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
GENERATED_DIR = os.path.join(REPO_ROOT, "content", "generated")
MEDIA_DIR = os.path.join(REPO_ROOT, "content", "media")
FRONTEND_DIST = os.path.join(REPO_ROOT, "frontend", "dist")

CONTENT_TYPE_LABELS = {
    "countdown": "Countdown",
    "early_bird": "Early Bird",
    "selling_fast": "Selling Fast",
    "sponsor_spotlight": "Sponsor Spotlight",
    "food_stall": "Food Stalls",
    "sponsorship_open": "Become A Sponsor",
    "artist": "Live In Concert",
    "venue": "The Venue",
}

dashboard_app = FastAPI(title="Garba Promo Review Dashboard")
dashboard_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your dashboard origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Auth: simple shared token for a small team ----
def require_token(authorization: str = Header(default="")):
    expected = os.environ.get("DASHBOARD_TOKEN")
    if not expected:
        return  # auth disabled if no token configured (e.g. private network)
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Invalid or missing dashboard token")


# ---- Models ----
class ManualPost(BaseModel):
    content_type: str = "countdown"
    city: str = ""
    platform: str = "facebook"
    media_file: str = "GENERATE"
    background: str = ""
    headline: str = ""
    subtext: str = ""
    caption: str = ""
    scheduled_for: str = ""


class EditPost(BaseModel):
    headline: str | None = None
    subtext: str | None = None
    caption: str | None = None
    background: str | None = None


# ---- Preview generation ----
def _generate_preview(item: dict) -> str:
    """Render (or copy) the preview image for an item, return web path."""
    os.makedirs(GENERATED_DIR, exist_ok=True)
    out_path = os.path.join(GENERATED_DIR, f"{item['id']}.jpg")

    if str(item.get("media_file", "")).upper() == "GENERATE":
        label = CONTENT_TYPE_LABELS.get(item["content_type"], item["content_type"].replace("_", " ").title())
        bg = item.get("background", "")
        bg_path = os.path.join(MEDIA_DIR, bg) if bg else None
        footer = EVENT_FOOTER
        image_overlay.render_post_image(
            label=label,
            big_text=item.get("headline") or label,
            subtext=item.get("subtext", ""),
            footer=footer,
            output_path=out_path,
            background_photo=bg_path,
        )
    else:
        # Real media file — preview is the file itself (or a URL passed through)
        mf = item["media_file"]
        if mf.startswith("http"):
            return mf
        src = os.path.join(MEDIA_DIR, mf)
        if os.path.isfile(src) and src.lower().endswith((".jpg", ".jpeg", ".png")):
            from shutil import copyfile
            copyfile(src, out_path)
        else:
            return f"/media/{mf}"  # video or other — served raw
    return f"/previews/{item['id']}.jpg"


# ---- API ----
@dashboard_app.get("/api/queue")
def list_queue(status: str = None, _=Depends(require_token)):
    return queue_store.get_queue(status)


@dashboard_app.post("/api/queue/refresh")
def refresh_queue(_=Depends(require_token)):
    added = queue_store.enqueue_due_from_schedule()
    return {"added": len(added), "items": added}


@dashboard_app.post("/api/queue/manual")
def create_manual(post: ManualPost, _=Depends(require_token)):
    item = queue_store.add_manual_item(post.dict())
    item["preview_path"] = _generate_preview(item)
    queue_store.update_item(item["id"], {"preview_path": item["preview_path"]})
    return item


@dashboard_app.post("/api/queue/{item_id}/preview")
def regenerate_preview(item_id: str, _=Depends(require_token)):
    item = queue_store.get_item(item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    preview = _generate_preview(item)
    queue_store.update_item(item_id, {"preview_path": preview})
    return {"preview_path": preview}


@dashboard_app.patch("/api/queue/{item_id}")
def edit_item(item_id: str, edit: EditPost, _=Depends(require_token)):
    item = queue_store.get_item(item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    updates = {k: v for k, v in edit.dict().items() if v is not None}
    updated = queue_store.update_item(item_id, updates)
    updated["preview_path"] = _generate_preview(updated)
    queue_store.update_item(item_id, {"preview_path": updated["preview_path"]})
    return updated


@dashboard_app.get("/api/backgrounds")
def list_backgrounds(_=Depends(require_token)):
    """List available photos in content/media for the background swapper."""
    if not os.path.isdir(MEDIA_DIR):
        return []
    return [
        f for f in os.listdir(MEDIA_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]


@dashboard_app.post("/api/upload")
async def upload_media(file: UploadFile = File(...), _=Depends(require_token)):
    os.makedirs(MEDIA_DIR, exist_ok=True)
    dest = os.path.join(MEDIA_DIR, file.filename)
    with open(dest, "wb") as f:
        f.write(await file.read())
    return {"filename": file.filename}


@dashboard_app.post("/api/queue/{item_id}/reject")
def reject_item(item_id: str, _=Depends(require_token)):
    return queue_store.mark_status(item_id, "rejected")


@dashboard_app.post("/api/queue/{item_id}/approve")
def approve_and_post(item_id: str, _=Depends(require_token)):
    item = queue_store.get_item(item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    if item["status"] == "posted":
        raise HTTPException(400, "Already posted")

    page_id = os.environ.get("FB_PAGE_ID")
    token = os.environ.get("FB_PAGE_ACCESS_TOKEN")
    if not page_id or not token:
        raise HTTPException(500, "FB_PAGE_ID / FB_PAGE_ACCESS_TOKEN not configured on server")

    # Resolve the actual file to post
    if str(item.get("media_file", "")).upper() == "GENERATE":
        media_path = os.path.join(GENERATED_DIR, f"{item['id']}.jpg")
        if not os.path.isfile(media_path):
            _generate_preview(item)
    elif item["media_file"].startswith("http"):
        media_path = item["media_file"]
    else:
        media_path = os.path.join(MEDIA_DIR, item["media_file"])

    try:
        facebook_api.post_to_facebook(page_id, token, media_path, item["caption"])
    except Exception as e:
        queue_store.mark_status(item_id, "error", note=str(e))
        raise HTTPException(502, f"Facebook post failed: {e}")

    return queue_store.mark_status(item_id, "posted", posted_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


# ---- Static file serving ----
@dashboard_app.get("/previews/{filename}")
def serve_preview(filename: str):
    path = os.path.join(GENERATED_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(404, "Preview not found")
    return FileResponse(path)


@dashboard_app.get("/media/{filename}")
def serve_media(filename: str):
    path = os.path.join(MEDIA_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(404, "Media not found")
    return FileResponse(path)


# Serve the built React app at the base path (single-origin deploy). Mounted
# last so it doesn't shadow the API routes above.
if os.path.isdir(FRONTEND_DIST):
    dashboard_app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")


# ---------------------------------------------------------------------------
# Base-path wrapper.
#
# The whole dashboard is mounted under BASE_PATH (default "/dashboard") so the
# public URL matches http://<vps>:<port>/dashboard. Everything inside
# dashboard_app uses relative paths, so changing BASE_PATH here (or via the
# .env DASHBOARD_BASE_PATH) moves the entire app — API, previews, and UI —
# together, with no other edits needed.
# ---------------------------------------------------------------------------
BASE_PATH = os.environ.get("DASHBOARD_BASE_PATH", "/dashboard").rstrip("/")

app = FastAPI()

# Redirect the bare root to the dashboard so visiting http://<vps>:<port>/
# lands somewhere useful instead of a 404.
from fastapi.responses import RedirectResponse  # noqa: E402


@app.get("/")
def _root_redirect():
    return RedirectResponse(url=BASE_PATH + "/")


if BASE_PATH:
    app.mount(BASE_PATH, dashboard_app)
else:
    # If BASE_PATH is empty, serve everything at root.
    app = dashboard_app
