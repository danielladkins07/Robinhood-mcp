"""Get the next story: from the stories/ queue, or a freshly written one from Claude."""
import random
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import requests

from . import config


@dataclass
class Story:
    title: str
    body: str
    ai_generated: bool = False
    source_file: Path | None = None

    @property
    def narration(self) -> str:
        return f"{self.title}\n\n{self.body}"


def _parse(text: str) -> tuple[str, str]:
    lines = [l.rstrip() for l in text.strip().splitlines()]
    title = lines[0].lstrip("#").strip()
    body = "\n".join(lines[1:]).strip()
    return title, body


def next_from_queue() -> Story | None:
    files = sorted(p for p in config.STORIES_DIR.glob("*.txt") if p.is_file())
    if not files:
        return None
    f = files[0]
    title, body = _parse(f.read_text(encoding="utf-8"))
    # A queued file can opt into the AI label by including a line "#ai"
    ai = bool(re.search(r"^#ai\s*$", body, re.M))
    body = re.sub(r"^#ai\s*$", "", body, flags=re.M).strip()
    return Story(title, body, ai_generated=ai, source_file=f)


def mark_done(story: Story):
    if story.source_file and story.source_file.exists():
        config.DONE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(story.source_file), config.DONE_DIR / story.source_file.name)


PROMPT = """Write an ORIGINAL, fictional first-person story in the style of a viral Reddit post \
(think r/AmItheAsshole, r/pettyrevenge, r/MaliciousCompliance). Theme: {theme}.

Rules:
- 180 to 260 words for the body, so it narrates in about 75-100 seconds.
- Hook in the first sentence. Short punchy sentences. Clear twist or payoff at the end.
- Casual spoken tone, no emojis, no hashtags, no profanity stronger than "damn".
- Invent all names; don't reference real people, brands, or actual Reddit users.

Reply in exactly this format and nothing else:
TITLE: <a Reddit-style post title, under 90 characters>
BODY:
<the story>"""


def generate_with_claude() -> Story:
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("stories/ is empty and ANTHROPIC_API_KEY isn't set - add a story file or a key.")
    theme = random.choice(config.STORY_THEMES.split("|")).strip()
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": config.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": config.ANTHROPIC_MODEL,
            "max_tokens": 1200,
            "messages": [{"role": "user", "content": PROMPT.format(theme=theme)}],
        },
        timeout=120,
    )
    r.raise_for_status()
    text = "".join(b.get("text", "") for b in r.json()["content"])
    m = re.search(r"TITLE:\s*(.+?)\s*BODY:\s*(.+)", text, re.S)
    if not m:
        raise RuntimeError(f"Unexpected story format from Claude:\n{text[:500]}")
    return Story(m.group(1).strip(), m.group(2).strip(), ai_generated=True)


def get_story() -> Story:
    src = config.STORY_SOURCE
    if src in ("queue", "auto"):
        s = next_from_queue()
        if s:
            return s
        if src == "queue":
            raise RuntimeError("No .txt files left in stories/.")
    return generate_with_claude()
