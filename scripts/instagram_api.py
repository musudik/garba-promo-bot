"""
Instagram Graph API posting (optional — requires an Instagram Business/Creator
account linked to your Facebook Page).

IMPORTANT LIMITATION: unlike Facebook, Instagram's API does not accept direct
file uploads. It needs a publicly reachable URL for the image/video. The
simplest way to get one: keep this repo PUBLIC on GitHub, and this script
will build a raw.githubusercontent.com URL automatically from GITHUB_REPO.
If your repo is private, host the media elsewhere (e.g. an S3 bucket) and
put the public URL directly in schedule.csv's media_file column instead of
a local path.
"""
import os
import time
import requests

GRAPH_API_VERSION = "v20.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class InstagramAPIError(Exception):
    pass


def _check(resp: requests.Response):
    if resp.status_code >= 400:
        raise InstagramAPIError(f"{resp.status_code}: {resp.text}")
    return resp.json()


def _public_url_for(media_path: str) -> str:
    if media_path.startswith("http://") or media_path.startswith("https://"):
        return media_path
    repo = os.environ.get("GITHUB_REPO")  # e.g. "yourname/garba-promo-bot"
    branch = os.environ.get("GITHUB_BRANCH", "main")
    if not repo:
        raise InstagramAPIError(
            "media_file is a local path but GITHUB_REPO env var is not set, "
            "so a public URL can't be constructed for Instagram."
        )
    rel_path = media_path.replace("content/media/", "content/media/")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{rel_path}"


def post_to_instagram(ig_user_id: str, access_token: str, media_path: str, caption: str) -> dict:
    is_video = os.path.splitext(media_path)[1].lower() in (".mp4", ".mov", ".m4v")
    public_url = _public_url_for(media_path)

    create_url = f"{GRAPH_API_BASE}/{ig_user_id}/media"
    data = {"caption": caption, "access_token": access_token}
    data["video_url" if is_video else "image_url"] = public_url
    if is_video:
        data["media_type"] = "VIDEO"

    container = _check(requests.post(create_url, data=data))
    container_id = container["id"]

    # Video containers need time to process before publishing.
    if is_video:
        status_url = f"{GRAPH_API_BASE}/{container_id}"
        for _ in range(20):
            status = _check(
                requests.get(status_url, params={"fields": "status_code", "access_token": access_token})
            )
            if status.get("status_code") == "FINISHED":
                break
            time.sleep(15)

    publish_url = f"{GRAPH_API_BASE}/{ig_user_id}/media_publish"
    return _check(
        requests.post(publish_url, data={"creation_id": container_id, "access_token": access_token})
    )
