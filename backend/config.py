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

# ── Mission Control cloud sync (public dashboard; no-op if token unset) ───
GITHUB_SYNC_TOKEN = os.getenv("GITHUB_SYNC_TOKEN", "")
GITHUB_SYNC_REPO = os.getenv("GITHUB_SYNC_REPO", "Dixon8303/ImaginariumOzone")

# ── Pacing Constitution constants (BGF_PACING_CONSTITUTION.md §14, §3) ───
# Single source of truth for the G0.25/G0.5 math. Changing the doctrine means
# changing it here, not in a stage function.

# §14 "Calibrated rate: 75 words/minute (1.25 words/second)" — verified against
# EP40 (1,254 words → 991.76s) and EP38. NOTE: the doc writes the formula as
# `estimated_seg_sec = seg_word_count ÷ 75`, which yields MINUTES, not seconds.
# We use words ÷ 1.25 (= words × 0.8), the only reading consistent with both
# the stated 1.25 words/sec and the EP40 measurement.
BGF_WORDS_PER_SECOND = 1.25

# §14 image buffer — non-negotiable. 1.20× with a pilot render, 1.25× without.
BGF_BUFFER_WITH_PILOT = 1.20
BGF_BUFFER_NO_PILOT   = 1.25

# §14 FLEX shots: last 15–20% of each chapter's AI shots. Midpoint.
BGF_FLEX_PCT = 0.175

# §14 archival floor: portraits ≥2, primary event, geographic, institutional,
# liberation context.
BGF_ARCHIVAL_MINIMUM = 15

# §3 pacing curve. pct = share of the 13:30 master runtime; asl = midpoint of
# the phase's master-target ASL band, used as the visual-event divisor.
BGF_PHASES = [
    {"name": "hook",       "pct": 0.0185, "asl": 1.5},
    {"name": "setup",      "pct": 0.0926, "asl": 2.4},
    {"name": "body_i",     "pct": 0.2593, "asl": 3.75},
    {"name": "body_ii",    "pct": 0.3704, "asl": 4.75},
    {"name": "climax",     "pct": 0.2222, "asl": 2.5},
    {"name": "resolution", "pct": 0.0370, "asl": 5.0},
]

# §14 G0.25 pilot sample size (hook + chapter 1 opening ≈ 200–300 words).
BGF_PILOT_WORD_TARGET = 250

# §6 Flux Dev 1 image standard — 1344×768 for ALL shots including hero.
BGF_IMAGE_WIDTH  = 1344
BGF_IMAGE_HEIGHT = 768
BGF_FLUX_STEPS       = 28
BGF_FLUX_STEPS_HERO  = 32   # §P6: hero shots cap at 32, never higher
BGF_FLUX_CFG         = 3.5  # §6.2: Flux Dev collapses at SD-style CFG 7–12

PROMPTS_DIR  = Path(__file__).parent / "prompts"
WORKFLOWS_DIR = Path(__file__).parent / "workflows"
MUSIC_DIR    = Path(__file__).parent / "assets" / "music"

OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
