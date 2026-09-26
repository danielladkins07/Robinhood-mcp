"""TikTok Content Posting API (official) - OAuth + Direct Post via file upload."""
import json
import math
import secrets
import time
import urllib.parse
from pathlib import Path

import requests

from . import config

API = "https://open.tiktokapis.com/v2"
AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
SCOPES = "user.info.basic,video.publish"


class TikTokError(RuntimeError):
    pass


# ---------------- OAuth ----------------

def authorize_url(state: str) -> str:
    q = {
        "client_key": config.TIKTOK_CLIENT_KEY,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": config.TIKTOK_REDIRECT_URI,
        "state": state,
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(q)


def _token_request(data: dict) -> dict:
    r = requests.post(
        f"{API}/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Cache-Control": "no-cache"},
        data={"client_key": config.TIKTOK_CLIENT_KEY, "client_secret": config.TIKTOK_CLIENT_SECRET, **data},
        timeout=30,
    )
    j = r.json()
    if "access_token" not in j:
        raise TikTokError(f"Token request failed: {j}")
    j["obtained_at"] = int(time.time())
    return j


def save_tokens(tokens: dict):
    config.TOKEN_FILE.write_text(json.dumps(tokens, indent=2))
    try:
        config.TOKEN_FILE.chmod(0o600)
    except Exception:
        pass


def exchange_code(code: str) -> dict:
    tokens = _token_request({
        "code": code, "grant_type": "authorization_code", "redirect_uri": config.TIKTOK_REDIRECT_URI,
    })
    save_tokens(tokens)
    return tokens


def get_access_token() -> str:
    """Refreshes the access token every run and stores any rotated refresh token."""
    refresh = None
    if config.TOKEN_FILE.exists():
        refresh = json.loads(config.TOKEN_FILE.read_text()).get("refresh_token")
    refresh = refresh or config.TIKTOK_REFRESH_TOKEN
    if not refresh:
        raise TikTokError("No refresh token. Run `python main.py auth` first.")
    tokens = _token_request({"grant_type": "refresh_token", "refresh_token": refresh})
    save_tokens(tokens)
    return tokens["access_token"]


# ---------------- Posting ----------------

def _post(token, path, body):
    r = requests.post(
        f"{API}{path}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"},
        json=body, timeout=60,
    )
    j = r.json()
    err = j.get("error", {})
    if err.get("code") not in (None, "ok"):
        raise TikTokError(f"{path}: {err.get('code')} - {err.get('message')}")
    return j.get("data", {})


def creator_info(token) -> dict:
    return _post(token, "/post/publish/creator_info/query/", {})


def _chunk_plan(size: int):
    # TikTok rules: chunks 5-64MB, final chunk may hold the remainder (up to 128MB);
    # files <= 64MB may go as a single chunk.
    MB = 1024 * 1024
    if size <= 64 * MB:
        return size, 1
    chunk = 10 * MB
    return chunk, math.floor(size / chunk)


def upload_video(token, path: Path, caption: str, ai_generated: bool, duration: float) -> str:
    info = creator_info(token)
    max_dur = info.get("max_video_post_duration_sec")
    if max_dur and duration > max_dur:
        raise TikTokError(f"Video is {duration:.0f}s but this account allows {max_dur}s max.")
    options = info.get("privacy_level_options", [])
    privacy = config.PRIVACY_LEVEL if config.PRIVACY_LEVEL in options else "SELF_ONLY"
    if privacy != config.PRIVACY_LEVEL:
        print(f"  note: {config.PRIVACY_LEVEL} not allowed for this app/account yet, posting as {privacy}")

    size = path.stat().st_size
    chunk, count = _chunk_plan(size)
    data = _post(token, "/post/publish/video/init/", {
        "post_info": {
            "title": caption[:2200],
            "privacy_level": privacy,
            "disable_comment": config.DISABLE_COMMENTS or bool(info.get("comment_disabled")),
            "disable_duet": bool(info.get("duet_disabled")),
            "disable_stitch": bool(info.get("stitch_disabled")),
            "video_cover_timestamp_ms": 500,
            "brand_content_toggle": False,
            "brand_organic_toggle": False,
            "is_aigc": ai_generated,
        },
        "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk,
                        "total_chunk_count": count},
    })
    publish_id, upload_url = data["publish_id"], data["upload_url"]

    with open(path, "rb") as f:
        for i in range(count):
            start = i * chunk
            end = size - 1 if i == count - 1 else start + chunk - 1
            f.seek(start)
            blob = f.read(end - start + 1)
            r = requests.put(upload_url, data=blob, timeout=600, headers={
                "Content-Type": "video/mp4",
                "Content-Length": str(len(blob)),
                "Content-Range": f"bytes {start}-{end}/{size}",
            })
            if r.status_code not in (200, 201, 206):
                raise TikTokError(f"Chunk {i + 1}/{count} upload failed: {r.status_code} {r.text[:300]}")
    return publish_id


def wait_for_publish(token, publish_id, timeout=300) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = _post(token, "/post/publish/status/fetch/", {"publish_id": publish_id})
        status = d.get("status")
        if status == "PUBLISH_COMPLETE":
            return d
        if status == "FAILED":
            raise TikTokError(f"TikTok rejected the post: {d.get('fail_reason')}")
        time.sleep(8)
    return {"status": "STILL_PROCESSING"}


def new_state() -> str:
    return secrets.token_urlsafe(16)
