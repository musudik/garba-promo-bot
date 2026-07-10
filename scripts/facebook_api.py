"""
Thin wrapper around the Facebook Graph API for Page posting.

Requires a Page Access Token with pages_manage_posts + pages_read_engagement
permissions. See README.md for how to generate one.
"""
import os
import requests

GRAPH_API_VERSION = "v20.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class FacebookAPIError(Exception):
    pass


def _check(resp: requests.Response):
    if resp.status_code >= 400:
        raise FacebookAPIError(f"{resp.status_code}: {resp.text}")
    return resp.json()


def post_text(page_id: str, access_token: str, message: str) -> dict:
    url = f"{GRAPH_API_BASE}/{page_id}/feed"
    resp = requests.post(url, data={"message": message, "access_token": access_token})
    return _check(resp)


def post_photo(page_id: str, access_token: str, image_path: str, caption: str) -> dict:
    url = f"{GRAPH_API_BASE}/{page_id}/photos"
    with open(image_path, "rb") as f:
        files = {"source": f}
        data = {"caption": caption, "access_token": access_token}
        resp = requests.post(url, files=files, data=data)
    return _check(resp)


def post_video(page_id: str, access_token: str, video_path: str, caption: str) -> dict:
    url = f"{GRAPH_API_BASE}/{page_id}/videos"
    with open(video_path, "rb") as f:
        files = {"source": f}
        data = {"description": caption, "access_token": access_token}
        resp = requests.post(url, files=files, data=data)
    return _check(resp)


def post_to_facebook(page_id: str, access_token: str, media_path: str, caption: str) -> dict:
    """Dispatch to the right endpoint based on file extension. media_path may be empty for text-only posts."""
    if not media_path:
        return post_text(page_id, access_token, caption)
    ext = os.path.splitext(media_path)[1].lower()
    if ext in (".mp4", ".mov", ".m4v"):
        return post_video(page_id, access_token, media_path, caption)
    elif ext in (".jpg", ".jpeg", ".png", ".gif"):
        return post_photo(page_id, access_token, media_path, caption)
    else:
        raise FacebookAPIError(f"Unsupported media type: {ext}")
