import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
COMFYUI_BASE_URL = os.getenv("COMFYUI_BASE_URL", "http://localhost:8188")
OUTPUT_BASE_DIR = Path(os.getenv("OUTPUT_BASE_DIR", "./backend/outputs")).resolve()
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
YOUTUBE_CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "")
YOUTUBE_TOKEN_CACHE = os.getenv("YOUTUBE_TOKEN_CACHE", str(Path.home() / ".config/bgf/token.json"))
DATABASE_PATH = os.getenv("DATABASE_PATH", str(Path(__file__).parent / "bgf.db"))

CLAUDE_MODEL = "claude-sonnet-4-6"
PROMPTS_DIR = Path(__file__).parent / "prompts"
WORKFLOWS_DIR = Path(__file__).parent / "workflows"
MUSIC_DIR = Path(__file__).parent / "assets" / "music"

OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
