#!/usr/bin/env python3
"""
TikTok story bot.

  python main.py auth           one-time: connect your TikTok account
  python main.py make           generate a video into output/ (no upload)
  python main.py post           generate a video and upload it to TikTok
  python main.py upload FILE    upload an existing video (caption from FILE.txt if present)

Add --offline-voice to make/post to test without the TTS service (robot tone, estimated timings).
"""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

from bot import config, render, stories, tiktok, tts


def _slug(s, n=40):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:n] or "story"


def _offline_tts(text, mp3):
    words = len(text.split())
    dur = max(2.0, words / 2.9)  # ~175 wpm
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"sine=frequency=220:duration={dur:.2f}", "-af", "volume=0.05", str(mp3)], check=True)
    return dur, tts.estimate_word_timings(text, dur)


def make_video(offline=False):
    story = stories.get_story()
    print(f"Story: {story.title}  ({'AI-written' if story.ai_generated else 'from queue'})")
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = config.OUTPUT_DIR / f"{stamp}-{_slug(story.title)}.mp4"

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        speak = _offline_tts if offline else (lambda t, p: tts.synthesize(t, config.TTS_VOICE, config.TTS_RATE, p))
        print("  voicing title + story...")
        title_dur, _ = speak(story.title, td / "title.mp3")
        body_dur, body_words = speak(story.body, td / "body.mp3")
        gap = 0.35
        est = title_dur + gap + body_dur
        if est > config.MAX_SECONDS:
            raise SystemExit(f"Narration is {est:.0f}s, over MAX_SECONDS={config.MAX_SECONDS}. Shorten the story.")
        render.concat_audio(td / "title.mp3", td / "body.mp3", td / "voice.m4a", gap=gap)
        card_h = render.title_card(story.title, td / "card.png")
        title_end = title_dur + gap
        render.captions_ass(body_words, offset=title_end, out=td / "caps.ass")
        print("  rendering video...")
        duration = render.render(td / "card.png", card_h, title_end, td / "caps.ass", td / "voice.m4a", out)

    caption = f"{story.title} {config.HASHTAGS}".strip()
    meta = {"caption": caption, "ai_generated": story.ai_generated, "duration": round(duration, 2)}
    out.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    stories.mark_done(story)
    print(f"  saved {out} ({duration:.0f}s)")
    return out, meta


def upload(path: Path, meta: dict):
    print("Uploading to TikTok...")
    token = tiktok.get_access_token()
    pid = tiktok.upload_video(token, path, meta["caption"], meta["ai_generated"], meta["duration"])
    print(f"  upload sent (publish_id={pid}), waiting for TikTok to process...")
    status = tiktok.wait_for_publish(token, pid)
    print(f"  status: {status.get('status')}")
    ids = status.get("publicaly_available_post_id") or status.get("publicly_available_post_id")
    if ids:
        print(f"  post id: {ids}")


def cmd_auth():
    missing = [n for n in ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REDIRECT_URI")
               if not getattr(config, n)]
    if missing:
        sys.exit(f"Set these in .env first: {', '.join(missing)}")
    state = tiktok.new_state()
    print("1) Open this link, log in to TikTok and approve:\n")
    print("   " + tiktok.authorize_url(state) + "\n")
    print("2) You'll land on your redirect URL (the page may not load - that's fine).")
    pasted = input("   Paste the FULL address from the browser bar here: ").strip()
    q = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query)
    code = (q.get("code") or [pasted])[0]
    if q.get("state") and q["state"][0] != state:
        sys.exit("State mismatch - start over.")
    tokens = tiktok.exchange_code(code)
    print(f"\nConnected. Tokens saved to {config.TOKEN_FILE}")
    print("For GitHub Actions / servers without that file, set this secret:")
    print(f"TIKTOK_REFRESH_TOKEN={tokens['refresh_token']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["auth", "make", "post", "upload"])
    ap.add_argument("file", nargs="?")
    ap.add_argument("--offline-voice", action="store_true")
    a = ap.parse_args()

    if a.command == "auth":
        cmd_auth()
    elif a.command == "make":
        make_video(a.offline_voice)
    elif a.command == "post":
        path, meta = make_video(a.offline_voice)
        upload(path, meta)
    elif a.command == "upload":
        if not a.file:
            sys.exit("Usage: python main.py upload output/video.mp4")
        p = Path(a.file)
        mj = p.with_suffix(".json")
        if mj.exists():
            meta = json.loads(mj.read_text())
        else:
            meta = {"caption": config.HASHTAGS, "ai_generated": False,
                    "duration": tts.audio_duration(p)}
        upload(p, meta)


if __name__ == "__main__":
    main()
