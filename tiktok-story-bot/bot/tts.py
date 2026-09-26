"""Text-to-speech with word timings (Microsoft Edge neural voices via edge-tts, free)."""
import asyncio
import re
import subprocess
from pathlib import Path


def audio_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def estimate_word_timings(text: str, duration: float) -> list[tuple[str, float, float]]:
    """Fallback when the TTS engine gives no timings: spread words by length, pausing at punctuation."""
    words = text.split()
    weights = []
    for w in words:
        wt = len(re.sub(r"\W", "", w)) + 2
        if re.search(r"[.!?]$", w):
            wt += 6
        elif re.search(r"[,;:]$", w):
            wt += 3
        weights.append(wt)
    total = sum(weights) or 1
    t, out = 0.0, []
    for w, wt in zip(words, weights):
        d = duration * wt / total
        out.append((w, t, t + d * 0.9))
        t += d
    return out


async def _edge(text, voice, rate, mp3_path):
    import edge_tts

    try:
        comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    except TypeError:  # older edge-tts versions always send word boundaries
        comm = edge_tts.Communicate(text, voice, rate=rate)
    words = []
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                end = start + chunk["duration"] / 1e7
                words.append((chunk["text"], start, end))
    return words


def synthesize(text: str, voice: str, rate: str, mp3_path: Path):
    """
    Returns (duration_seconds, [(word, start, end), ...]).

    Uses Microsoft's free Edge TTS service via edge-tts library.
    Install: pip install edge-tts
    Voices: en-US-ChristopherNeural, en-US-AriaNeural, en-GB-RyanNeural, etc.
    """
    try:
        words = asyncio.run(_edge(text, voice, rate, mp3_path))
    except ImportError:
        raise RuntimeError(
            "edge-tts is not installed. Install it with: pip install edge-tts\n"
            "Or, for testing without voice: python main.py make --offline-voice"
        )
    dur = audio_duration(mp3_path)
    if not words:
        words = estimate_word_timings(text, dur)
    return dur, words
