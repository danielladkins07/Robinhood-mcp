"""All settings come from environment variables (or a .env file next to main.py)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv():
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


# --- TikTok app credentials (from developers.tiktok.com) ---
TIKTOK_CLIENT_KEY = env("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = env("TIKTOK_CLIENT_SECRET")
TIKTOK_REDIRECT_URI = env("TIKTOK_REDIRECT_URI")
# Refresh token from `python main.py auth`. tokens.json takes priority if present.
TIKTOK_REFRESH_TOKEN = env("TIKTOK_REFRESH_TOKEN")
TOKEN_FILE = Path(env("TOKEN_FILE", ROOT / "tokens.json"))

# PUBLIC_TO_EVERYONE / MUTUAL_FOLLOW_FRIENDS / FOLLOWER_OF_CREATOR / SELF_ONLY
# Unaudited TikTok apps can only use SELF_ONLY; the bot falls back automatically.
PRIVACY_LEVEL = env("PRIVACY_LEVEL", "PUBLIC_TO_EVERYONE")
HASHTAGS = env("HASHTAGS", "#storytime #reddit #redditstories #fyp")
DISABLE_COMMENTS = env("DISABLE_COMMENTS", "false").lower() == "true"

# --- Story source ---
# "queue": use text files in stories/   "ai": write a new original story with Claude
# "auto": use the queue first, fall back to AI when it's empty
STORY_SOURCE = env("STORY_SOURCE", "auto")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = env("ANTHROPIC_MODEL", "claude-sonnet-5")
STORY_THEMES = env(
    "STORY_THEMES",
    "AITA workplace drama|petty revenge on a neighbor|wedding drama|roommate from hell|"
    "entitled customer|family inheritance fight|malicious compliance at work",
)

# --- Voice / video ---
TTS_VOICE = env("TTS_VOICE", "en-US-ChristopherNeural")
TTS_RATE = env("TTS_RATE", "+12%")
FONT_NAME = env("FONT_NAME", "DejaVu Sans")
FONT_DIR = env("FONT_DIR", str(ROOT / "fonts"))
MAX_SECONDS = int(env("MAX_SECONDS", "170"))

STORIES_DIR = ROOT / "stories"
DONE_DIR = STORIES_DIR / "done"
BACKGROUNDS_DIR = ROOT / "backgrounds"
OUTPUT_DIR = ROOT / "output"
