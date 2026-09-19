"""
CinemaWin backend configuration — single source of truth.

Every environment variable and model default used by the backend is defined
here. Doctrine constants (scorecard categories, capital layers, deck slides,
tiers) are loaded from ../doctrine.json so the Python backend and the browser
build read the same numbers.

Paths resolve relative to this file's directory (cinemawin/backend/).
"""

import json
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (BASE_DIR / p).resolve()


# ── Doctrine constants (shared with the frontend) ───────────────────────────
# Looked up next to the project root first, then inside backend/, so a
# container that copies only backend/ still works.
_DOCTRINE_CANDIDATES = [
    BASE_DIR.parent / "doctrine.json",
    BASE_DIR / "doctrine.json",
]
DOCTRINE_FILE = next((p for p in _DOCTRINE_CANDIDATES if p.is_file()), None)
if DOCTRINE_FILE is None:
    raise RuntimeError(
        "doctrine.json not found. Looked in: "
        + ", ".join(str(p) for p in _DOCTRINE_CANDIDATES)
    )
_D = json.loads(DOCTRINE_FILE.read_text(encoding="utf-8"))

SCORE_CATEGORIES = [(name, int(points)) for name, points in _D["score_categories"]]
SCORE_TOTAL_MAX = sum(p for _, p in SCORE_CATEGORIES)  # 100
VERDICT_THRESHOLDS = [(int(m), v, label) for m, v, label in _D["verdict_thresholds"]]
MATURITY_LABELS = {int(k): v for k, v in _D["maturity_labels"].items()}
CAPITAL_LAYERS = list(_D["capital_layers"])
EQUITY_GAP_LAYER = _D["equity_gap_layer"]
CAPITAL_LAYER_RANGES = {k: tuple(v) for k, v in _D["capital_layer_ranges"].items()}
BUDGET_CEILING_MIN = int(_D["budget_ceiling_min"])
BUDGET_CEILING_MAX = int(_D["budget_ceiling_max"])
BUDGET_TIERS = [(None if b is None else int(b), t) for b, t in _D["budget_tiers"]]
DECK_SLIDE_TITLES = list(_D["deck_slide_titles"])
DECK_SLIDE_COUNT = len(DECK_SLIDE_TITLES)  # 12
DECK_PLACEHOLDER_CONTENT = _D["deck_placeholder_content"]
WATERFALL_STEPS = list(_D["waterfall_steps"])
EVIDENCE_TAGS = list(_D["evidence_tags"])
STRUCTURE_SEQUENCE_COUNT = int(_D["structure_sequence_count"])
COMPS_MIN = int(_D["comps_min"])
COMPS_MAX = int(_D["comps_max"])
TOP_FIXES_COUNT = int(_D["top_fixes_count"])
VALID_TRACKS = tuple(_D["tracks"])
VALID_MODULES = tuple(_D["modules"])
PLANS = dict(_D["plans"])
VALID_PLANS = tuple(PLANS.keys())

# ── Core ────────────────────────────────────────────────────────────────────
PORT = int(os.getenv("CINEMAWIN_PORT", "8002"))
DATABASE_PATH = _resolve(os.getenv("CINEMAWIN_DATABASE_PATH", "./cinemawin.db"))
PUBLIC_URL = os.getenv("CINEMAWIN_PUBLIC_URL", "http://localhost:5174").rstrip("/")
DEFAULT_PLAN = os.getenv("CINEMAWIN_DEFAULT_PLAN", "entry").strip().lower() or "entry"
DEVELOP_RATE_LIMIT = int(os.getenv("CINEMAWIN_DEVELOP_RATE_LIMIT", "10"))
DEVELOP_RATE_WINDOW_SEC = 3600
APP_NAME = "CinemaWin"

# CORS. "*" is accepted for the common case of a static frontend on GitHub
# Pages calling a backend on another host; credentials are not used, so this
# is safe (auth rides on an Authorization header the browser only sends when
# our own frontend code sets it).
_cors_raw = os.getenv("CINEMAWIN_CORS_ORIGINS", "http://localhost:5174").strip()
CORS_ALLOW_ALL = _cors_raw == "*"
CORS_ORIGINS = [] if CORS_ALLOW_ALL else [o.strip() for o in _cors_raw.split(",") if o.strip()]

# ── Secret key (JWT signing) ────────────────────────────────────────────────
SECRET_KEY = os.getenv("CINEMAWIN_SECRET_KEY", "")
SECRET_KEY_EPHEMERAL = False
if not SECRET_KEY:
    # main.py logs the warning at startup (keeps CLI tools like set_plan quiet).
    SECRET_KEY = secrets.token_hex(32)
    SECRET_KEY_EPHEMERAL = True

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30

# ── Password hashing ────────────────────────────────────────────────────────
PBKDF2_ITERATIONS = 600_000
PASSWORD_MIN_LENGTH = 8

# ── OTP / reset tokens ──────────────────────────────────────────────────────
OTP_EXPIRY_MINUTES = 10
RESET_TOKEN_EXPIRY_MINUTES = 60

# ── LLM provider ────────────────────────────────────────────────────────────
# CinemaWin works with any provider (see services/providers.py). Several have
# a free tier, so no paid account is required.
#
# Resolution order for the provider:
#   1. CINEMAWIN_LLM_PROVIDER, if set.
#   2. Inferred from whichever provider key is present.
#   3. Unset -> not configured (functions return 503 unless demo mode is on).
_PROVIDER_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "together": "TOGETHER_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "openai": "OPENAI_API_KEY",
    "ollama": "",  # no key needed
}
# Checked in this order when inferring, so a free provider wins over a paid
# one if someone has several keys in their environment.
_INFER_ORDER = ("anthropic", "gemini", "groq", "openrouter", "cerebras", "together", "openai")

LLM_PROVIDER = os.getenv("CINEMAWIN_LLM_PROVIDER", "").strip().lower()
LLM_API_KEY = os.getenv("CINEMAWIN_LLM_API_KEY", "").strip()

if not LLM_PROVIDER:
    for _name in _INFER_ORDER:
        if os.getenv(_PROVIDER_KEY_ENV[_name], "").strip():
            LLM_PROVIDER = _name
            break

if LLM_PROVIDER and not LLM_API_KEY:
    LLM_API_KEY = os.getenv(_PROVIDER_KEY_ENV.get(LLM_PROVIDER, ""), "").strip()

LLM_BASE_URL = os.getenv("CINEMAWIN_LLM_BASE_URL", "").strip()
MODEL_CRAFT = os.getenv("CINEMAWIN_MODEL_CRAFT", "").strip()
MODEL_JUDGE = os.getenv("CINEMAWIN_MODEL_JUDGE", "").strip()
LLM_MAX_TOKENS = int(os.getenv("CINEMAWIN_LLM_MAX_TOKENS", "8000"))
LLM_MAX_ATTEMPTS = 3
LLM_TIMEOUT_SEC = float(os.getenv("CINEMAWIN_LLM_TIMEOUT_SEC", "180"))
REFUSAL_FALLBACKS = _truthy(os.getenv("CINEMAWIN_REFUSAL_FALLBACKS", "1"))
FALLBACK_BETA = "server-side-fallback-2026-07-01"

# Backwards compatibility: earlier builds read ANTHROPIC_API_KEY directly.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_CONFIGURED = bool(LLM_API_KEY) or LLM_PROVIDER == "ollama"

# ── Demo mode ───────────────────────────────────────────────────────────────
# "1" forces canned output; "auto" uses it only when no provider is configured.
_demo_raw = os.getenv("CINEMAWIN_DEMO_MODE", "0").strip().lower()
if _demo_raw == "auto":
    DEMO_MODE = not LLM_CONFIGURED
else:
    DEMO_MODE = _truthy(_demo_raw)

# ── SMTP (email verification / reset). Unset → console logging. ────────────
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587") or "587")
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "") or SMTP_USER
SMTP_CONFIGURED = bool(SMTP_HOST)
EMAIL_VERIFICATION_REQUIRED = SMTP_CONFIGURED

# ── Paths ───────────────────────────────────────────────────────────────────
PROMPTS_DIR = BASE_DIR / "prompts"
DOCTRINE_DIR = PROMPTS_DIR / "doctrine"
DIST_DIR = (BASE_DIR.parent / "dist").resolve()

# ── Field limits ────────────────────────────────────────────────────────────
PROJECT_TEXT_MAX = 5000
PROJECT_TITLE_MAX = 200
FUNCTION_TEXT_MAX = 1500
FUNCTION_LOGLINE_MAX = 1000
FUNCTION_TITLE_MAX = 200
