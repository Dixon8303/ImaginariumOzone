"""
CinemaWin backend configuration — single source of truth.

Every environment variable, model ID, and doctrine constant used by the
backend is defined here. Services import from this module; nothing else
hard-codes a model string or a spec number.

Paths are resolved relative to this file's directory (cinemawin/backend/).
"""

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


# ── Core ────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PORT = int(os.getenv("CINEMAWIN_PORT", "8002"))
DATABASE_PATH = _resolve(os.getenv("CINEMAWIN_DATABASE_PATH", "./cinemawin.db"))
PUBLIC_URL = os.getenv("CINEMAWIN_PUBLIC_URL", "http://localhost:5174").rstrip("/")
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CINEMAWIN_CORS_ORIGINS", "http://localhost:5174").split(",")
    if o.strip()
]
DEFAULT_PLAN = os.getenv("CINEMAWIN_DEFAULT_PLAN", "entry").strip().lower() or "entry"
DEVELOP_RATE_LIMIT = int(os.getenv("CINEMAWIN_DEVELOP_RATE_LIMIT", "10"))
DEVELOP_RATE_WINDOW_SEC = 3600

# ── Secret key (JWT signing) ────────────────────────────────────────────────
SECRET_KEY = os.getenv("CINEMAWIN_SECRET_KEY", "")
SECRET_KEY_EPHEMERAL = False
if not SECRET_KEY:
    # main.py logs the warning at startup (keeps CLI tools like set_plan.py quiet).
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

# ── Demo mode ───────────────────────────────────────────────────────────────
_demo_raw = os.getenv("CINEMAWIN_DEMO_MODE", "0").strip().lower()
if _demo_raw == "auto":
    DEMO_MODE = not bool(ANTHROPIC_API_KEY)
else:
    DEMO_MODE = _truthy(_demo_raw)

LLM_CONFIGURED = bool(ANTHROPIC_API_KEY)

# ── Model routing ───────────────────────────────────────────────────────────
# Craft = develop/structure. Judge = score/finance. Both default to Opus 5.
MODEL_CRAFT = os.getenv("CINEMAWIN_MODEL_CRAFT", "claude-opus-5") or "claude-opus-5"
MODEL_JUDGE = os.getenv("CINEMAWIN_MODEL_JUDGE", "claude-opus-5") or "claude-opus-5"
LLM_MAX_TOKENS = 16000
LLM_MAX_ATTEMPTS = 3
REFUSAL_FALLBACKS = _truthy(os.getenv("CINEMAWIN_REFUSAL_FALLBACKS", "1"))
FALLBACK_BETA = "server-side-fallback-2026-07-01"

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

# ── App / plans ─────────────────────────────────────────────────────────────
APP_NAME = "CinemaWin"
PLANS = {"entry": {"price": 0}, "starter": {"price": 12}, "premium": {"price": 29}}
VALID_PLANS = tuple(PLANS.keys())
VALID_TRACKS = ("Writer", "Producer", "Both")
VALID_MODULES = ("develop", "plan", "score", "fund")

# ── Field limits (contract) ─────────────────────────────────────────────────
PROJECT_TEXT_MAX = 5000
PROJECT_TITLE_MAX = 200
FUNCTION_TEXT_MAX = 1500
FUNCTION_LOGLINE_MAX = 1000
FUNCTION_TITLE_MAX = 200

# ── Doctrine constants (Module 04 §II — 100-point Greenlight Scorecard) ─────
SCORE_CATEGORIES = [
    ("Premise & Hook", 10),
    ("Story Architecture", 10),
    ("Character & Voice", 10),
    ("Dialogue & Subtext", 5),
    ("Thematic Depth", 5),
    ("Cinematic Potential", 10),
    ("Marketability & Comps", 10),
    ("Castability", 10),
    ("Production Feasibility", 10),
    ("Financial Viability", 10),
    ("Packaging Potential", 5),
    ("Distribution Viability", 5),
]
SCORE_TOTAL_MAX = sum(m for _, m in SCORE_CATEGORIES)  # 100

# (min_inclusive, verdict, label) — checked top-down.
VERDICT_THRESHOLDS = [
    (90, "RECOMMEND", "RECOMMEND — Market-Ready / Exceptional"),
    (80, "RECOMMEND", "RECOMMEND — Strong / Packaging Candidate"),
    (70, "CONSIDER", "CONSIDER — Viable with Development"),
    (60, "CONSIDER", "CONSIDER — Major Revision Required"),
    (0, "PASS", "PASS — Not Ready"),
]

# ── Doctrine constants (Module 00 §II — maturity levels) ────────────────────
MATURITY_LABELS = {
    0: "LEVEL 0 (SPARK)",
    1: "LEVEL 1 (ARCHITECTURE)",
    2: "LEVEL 2 (SCREENPLAY MASTER)",
    3: "LEVEL 3 (REVISED MATERIAL)",
    4: "LEVEL 4 (PRODUCTION CANDIDATE)",
    5: "LEVEL 5 (FINANCING CANDIDATE)",
    6: "LEVEL 6 (PRODUCTION-READY PACKAGE)",
    7: "LEVEL 7 (MARKET / INVESTMENT OFFERING)",
}

# ── Doctrine constants (Module 03 §II — 4-layer capital stack) ─────────────
CAPITAL_LAYERS = [
    "Tax Incentives / Soft Money",
    "Foreign Pre-Sales & MGs",
    "Brand Integration & Grants",
    "Equity Gap",
]
EQUITY_GAP_LAYER = "Equity Gap"
# Industry ranges from Module 03 §II, used by demo mode and as prompt guidance.
CAPITAL_LAYER_RANGES = {
    "Tax Incentives / Soft Money": (20, 35),
    "Foreign Pre-Sales & MGs": (15, 30),
    "Brand Integration & Grants": (5, 10),
    "Equity Gap": (35, 50),
}

# ── Doctrine constants (Module 03 §I — budget tiers by ceiling) ─────────────
BUDGET_CEILING_MIN = 100_000
BUDGET_CEILING_MAX = 50_000_000
# (upper_exclusive_bound, tier) — checked in order; last is the catch-all.
BUDGET_TIERS = [
    (500_000, "Micro / Ultra-Low"),
    (3_500_000, "Contained Indie Tier"),
    (8_500_000, "Mid-Tier Indie / Streamer Buyout"),
    (None, "Studio Independent / Prestige"),
]

# ── Doctrine constants (Module 03 §V — 12-slide pitch deck) ─────────────────
DECK_SLIDE_TITLES = [
    "Title, Logline & Executive Financial Summary",
    "The Core Commercial Hook & Cultural Urgency",
    "World, Atmosphere & Cinematic Tone",
    "Character System & Ensemble Psychology",
    "Target Cast Attachments & Pre-Sales Value",
    "Physical Production Efficiency & Contained Footprint",
    "Market Comparables & Historic ROI Performance",
    "The 4-Layer Capital Stack & Soft-Money Breakdown",
    "Distribution Lane & Festival Premiere Strategy",
    "Step-by-Step Investor Recoupment Waterfall (115% Preferred Return)",
    "Institutional Risk Mitigation (Completion Bond, Escrow, E&O Insurance)",
    "Executive Production Leadership, Execution Timeline & Capital Call Subscription",
]
DECK_SLIDE_COUNT = len(DECK_SLIDE_TITLES)  # 12
DECK_PLACEHOLDER_CONTENT = "To be developed."

# ── Doctrine constants (Module 03 §III — investor waterfall) ───────────────
WATERFALL_STEPS = [
    "Gross Receipts",
    "International Sales Agent Commission (10%–25%) + approved delivery expenses",
    "Senior Debt & Tax Credit Bridge Loan payoff (+ accrued interest)",
    "Equity Investor Capital Recoupment + 110%–120% Preferred Return (pari-passu)",
    "Net Profits: 50% to Equity Investor Pool / 50% to Producer & Creative Talent Pool",
]

# ── Doctrine constants (Module 00 §V — evidence tags) ──────────────────────
EVIDENCE_TAGS = [
    "FACT",
    "VERIFIED CURRENT DATA",
    "INDUSTRY RANGE",
    "MODEL ASSUMPTION",
    "PROJECT-SPECIFIC ASSUMPTION",
    "SCENARIO",
    "UNKNOWN",
]

STRUCTURE_SEQUENCE_COUNT = 8
COMPS_MIN = 3
COMPS_MAX = 5
TOP_FIXES_COUNT = 3
