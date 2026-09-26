"""Build the 1080x1920 video: background footage + title card + narration + word captions."""
import random
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config
from .tts import audio_duration

W, H = 1080, 1920


def _font(size, bold=True):
    candidates = []
    fd = Path(config.FONT_DIR)
    if fd.exists():
        candidates += sorted(fd.glob("*.ttf")) + sorted(fd.glob("*.otf"))
    candidates += [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/Library/Fonts/Arial Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    ]
    for c in candidates:
        if c.exists():
            return ImageFont.truetype(str(c), size)
    return ImageFont.load_default(size)


def title_card(title: str, out: Path, username="u/throwaway_story"):
    """A generic 'forum post' card (no real brand logos)."""
    pad, card_w = 48, 940
    tf = _font(58)
    lines, cur = [], ""
    for word in title.split():
        trial = f"{cur} {word}".strip()
        if cur and tf.getlength(trial) > card_w - 2 * pad:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    line_h = 72
    card_h = 150 + line_h * len(lines) + 110
    img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=36, fill=(255, 255, 255, 255))
    # avatar + username
    d.ellipse([pad, 40, pad + 76, 116], fill=(255, 87, 34))
    d.text((pad + 38, 78), "S", font=_font(44), fill="white", anchor="mm")
    d.text((pad + 96, 50), username, font=_font(34), fill=(30, 30, 30))
    d.text((pad + 96, 90), "Posted a story", font=_font(26, bold=False), fill=(120, 120, 120))
    y = 150
    for ln in lines:
        d.text((pad, y), ln, font=tf, fill=(20, 20, 20))
        y += line_h
    # footer "likes / comments"
    fy = card_h - 80
    grey = (110, 110, 110)
    d.polygon([(pad, fy + 30), (pad + 18, fy + 4), (pad + 36, fy + 30)], fill=grey)
    d.text((pad + 52, fy), "99+", font=_font(32), fill=grey)
    d.rounded_rectangle([pad + 170, fy + 2, pad + 210, fy + 34], radius=8, outline=grey, width=4)
    d.text((pad + 226, fy), "99+", font=_font(32), fill=grey)
    img.save(out)
    return card_h


def _ass_time(t):
    t = max(t, 0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def captions_ass(words, offset: float, out: Path, max_words=3):
    """Big centered captions, 1-3 words at a time, with a small pop-in."""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{config.FONT_NAME},104,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,9,4,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or re.search(r"[.!?,;:]$", w[0]):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)

    events = []
    for i, g in enumerate(groups):
        start = g[0][1] + offset
        end = g[-1][2] + offset
        if i + 1 < len(groups):  # hold until the next group starts, avoids flicker
            end = max(end, groups[i + 1][0][1] + offset - 0.02)
        text = " ".join(w[0] for w in g).upper().replace("{", "(").replace("}", ")")
        pop = r"{\fscx80\fscy80\t(0,90,\fscx100\fscy100)}"
        events.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Cap,,0,0,0,,{pop}{text}")
    out.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def concat_audio(title_mp3: Path, body_mp3: Path, out: Path, gap=0.35):
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(title_mp3), "-i", str(body_mp3),
        "-filter_complex",
        f"[0:a]aresample=44100,apad=pad_dur={gap}[a0];[1:a]aresample=44100[a1];[a0][a1]concat=n=2:v=0:a=1[a]",
        "-map", "[a]", "-c:a", "aac", "-b:a", "192k", str(out),
    ], check=True)


def _pick_background(duration: float):
    vids = [p for p in config.BACKGROUNDS_DIR.iterdir()
            if p.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm")] if config.BACKGROUNDS_DIR.exists() else []
    if not vids:
        return None, None
    v = random.choice(vids)
    try:
        vd = audio_duration(v)
    except Exception:
        vd = 0
    start = random.uniform(0, vd - duration - 1) if vd > duration + 2 else 0
    return v, start


def render(title_png: Path, card_h: int, title_end: float, ass: Path, audio: Path, out: Path):
    total = audio_duration(audio) + 0.6
    bg, start = _pick_background(total)
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    if bg:
        cmd += ["-stream_loop", "-1", "-ss", f"{start:.2f}", "-i", str(bg)]
    else:  # no footage supplied: animated gradient
        cmd += ["-f", "lavfi", "-i", f"gradients=s={W}x{H}:c0=0x1a1a2e:c1=0x16213e:c2=0x0f3460:c3=0x533483:n=4:speed=0.015:r=30"]
    cmd += ["-i", str(audio), "-loop", "1", "-i", str(title_png)]
    ass_path = str(ass).replace("\\", "/").replace(":", r"\:")
    fonts = str(config.FONT_DIR).replace("\\", "/").replace(":", r"\:")
    card_y = (H - card_h) // 2
    fc = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=30,"
        f"eq=brightness=-0.06[bg];"
        f"[2:v]format=rgba,fade=t=out:st={max(title_end - 0.25, 0):.2f}:d=0.25:alpha=1[card];"
        f"[bg][card]overlay=(W-w)/2:{card_y}:enable='lte(t,{title_end:.2f})'[v1];"
        f"[v1]ass='{ass_path}':fontsdir='{fonts}'[v]"
    )
    cmd += [
        "-filter_complex", fc, "-map", "[v]", "-map", "1:a",
        "-t", f"{total:.2f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
    ]
    subprocess.run(cmd, check=True)
    return total
