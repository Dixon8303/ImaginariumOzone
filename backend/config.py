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

# ── Model Tier Routing (BGF Orchestration Spec) ────────────────────────────
# Judgment + irreversible → Opus 4.8
# Long-horizon + vision + code → Fable 5
# Structured transform → Sonnet 4.6
# Volume + parse + draft → Haiku 4.5 / Ollama
MODEL_FABLE  = "claude-fable-5"
MODEL_OPUS   = "claude-opus-4-8"
MODEL_SONNET = "claude-sonnet-4-6"
MODEL_HAIKU  = "claude-haiku-4-5-20251001"

# Legacy alias — kept for any calls that pre-date tier routing
CLAUDE_MODEL = MODEL_SONNET

# ── Ollama (local, $0 marginal cost) ──────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "mistral")

# ── ElevenLabs (P5 voiceover; falls back to macOS say if key absent) ──────
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # Adam

# ── vidIQ (real YouTube intelligence; all features degrade if unset) ──────
VIDIQ_API_KEY = os.getenv("VIDIQ_API_KEY", "")
VIDIQ_BASE_URL = os.getenv("VIDIQ_BASE_URL", "https://api.vidiq.com")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")

PROMPTS_DIR  = Path(__file__).parent / "prompts"
WORKFLOWS_DIR = Path(__file__).parent / "workflows"
MUSIC_DIR    = Path(__file__).parent / "assets" / "music"

OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
