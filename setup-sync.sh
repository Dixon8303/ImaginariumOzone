#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# BGF Mission Control — one-command sync setup
#
#   ./setup-sync.sh
#
# Paste your GitHub token when asked. This script then:
#   1. Checks the token is real and reaches the right repository
#   2. Confirms it has write permission (the #1 cause of a silent dead dashboard)
#   3. Writes it into backend/.env correctly
#   4. Runs a live test sync and tells you to go look at the dashboard
#
# The token is never displayed, never logged, and never committed.
# ─────────────────────────────────────────────────────────────────────────────

set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
ENV_FILE="$BACKEND/.env"
REPO="Dixon8303/ImaginariumOzone"
DASHBOARD="https://dixon8303.github.io/ImaginariumOzone/bgf/"

bold=$(printf '\033[1m'); dim=$(printf '\033[2m')
red=$(printf '\033[31m'); grn=$(printf '\033[32m')
ylw=$(printf '\033[33m'); rst=$(printf '\033[0m')

say()  { printf "%s\n" "$*"; }
ok()   { printf "  ${grn}✓${rst} %s\n" "$*"; }
bad()  { printf "  ${red}✗${rst} %s\n" "$*"; }
warn() { printf "  ${ylw}!${rst} %s\n" "$*"; }

say ""
say "${bold}BGF MISSION CONTROL — SYNC SETUP${rst}"
say "${dim}Connects the studio app on this Mac to your dashboard on the web.${rst}"
say ""

# ── Step 0: where do I get a token? ──────────────────────────────────────────
if [ ! -d "$BACKEND" ]; then
  bad "Can't find the backend folder."
  say ""
  say "  Run this from inside the project folder, like so:"
  say "    ${bold}cd ~/Documents/ImaginariumOzone && ./setup-sync.sh${rst}"
  say ""
  exit 1
fi

say "${bold}Need a token first?${rst} Open this page while signed in to GitHub:"
say "  ${bold}https://github.com/settings/personal-access-tokens/new${rst}"
say ""
say "  Fill it in exactly like this:"
say "    Token name ............ ${bold}bgf-sync${rst}"
say "    Expiration ............ ${bold}1 year${rst} (or custom — just remember the date)"
say "    Repository access ..... ${bold}Only select repositories${rst} → ${bold}ImaginariumOzone${rst}"
say "    Permissions ........... Repository permissions → ${bold}Contents${rst} → ${bold}Read and write${rst}"
say "                            ${dim}(leave every other permission on 'No access')${rst}"
say ""
say "  Click ${bold}Generate token${rst} at the bottom, then copy what it shows you."
say "  ${dim}It starts with github_pat_ and is only shown once.${rst}"
say ""

# ── Step 1: take the token, hidden ───────────────────────────────────────────
printf "${bold}Paste your token here and press Enter${rst} ${dim}(it stays hidden as you paste)${rst}: "
IFS= read -r -s TOKEN
printf "\n\n"

# Trim stray whitespace from copy/paste
TOKEN="$(printf '%s' "$TOKEN" | tr -d '[:space:]')"

if [ -z "$TOKEN" ]; then
  bad "Nothing was pasted. Run the script again when you have the token."
  exit 1
fi

case "$TOKEN" in
  github_pat_*) ;;
  ghp_*)
    warn "That looks like a ${bold}classic${rst} token, not a fine-grained one."
    warn "It may still work, but the fine-grained kind is safer. Continuing…"
    ;;
  *)
    bad "That doesn't look like a GitHub token — it should start with github_pat_"
    say "  Nothing was saved. Run the script again with the full token."
    exit 1
    ;;
esac

say "${bold}Checking the token…${rst}"

# ── Step 2: validate against the real API ────────────────────────────────────
API="https://api.github.com/repos/$REPO"
RESP="$(curl -sS -w $'\n%{http_code}' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  --max-time 30 "$API" 2>/dev/null)"

CODE="$(printf '%s' "$RESP" | tail -n1)"
BODY="$(printf '%s' "$RESP" | sed '$d')"

case "$CODE" in
  200) ok "Token is valid and can see $REPO" ;;
  401)
    bad "GitHub rejected the token (401 Unauthorized)."
    say "  Most likely it was copied incompletely, or it's already expired."
    say "  Generate a fresh one and run this again. Nothing was saved."
    exit 1
    ;;
  404)
    bad "Token works, but it can't see $REPO (404)."
    say "  On the token page, 'Repository access' must be set to"
    say "  ${bold}Only select repositories${rst} → ${bold}ImaginariumOzone${rst}."
    say "  Fix that on the token (or make a new one) and run this again."
    exit 1
    ;;
  "")
    bad "Couldn't reach GitHub at all — check this Mac's internet connection."
    exit 1
    ;;
  *)
    bad "GitHub returned an unexpected response (HTTP $CODE)."
    printf '%s\n' "$BODY" | head -5
    exit 1
    ;;
esac

# Fine-grained token with Contents:write reports push=true here.
if printf '%s' "$BODY" | grep -q '"push"[[:space:]]*:[[:space:]]*true'; then
  ok "Token has write permission"
else
  bad "Token can read the repo, but ${bold}cannot write${rst} to it."
  say ""
  say "  This is the most common mistake, and it fails silently —"
  say "  the app would run fine but your dashboard would never update."
  say ""
  say "  Fix: on the token page, under ${bold}Permissions → Repository permissions${rst},"
  say "  set ${bold}Contents${rst} to ${bold}Read and write${rst} (not just Read)."
  say "  Then run this script again. Nothing was saved."
  exit 1
fi

# ── Step 3: write it into backend/.env ───────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  if [ -f "$BACKEND/.env.example" ]; then
    cp "$BACKEND/.env.example" "$ENV_FILE"
    ok "Created backend/.env from the template"
  else
    : > "$ENV_FILE"
    ok "Created backend/.env"
  fi
fi

# Rewrite without the old token line, then append the new one.
TMP="$ENV_FILE.tmp.$$"
grep -v '^[[:space:]]*GITHUB_SYNC_TOKEN[[:space:]]*=' "$ENV_FILE" > "$TMP" 2>/dev/null || : > "$TMP"

# Keep exactly one trailing newline before appending
if [ -s "$TMP" ]; then
  printf '%s\n' "$(cat "$TMP")" > "$TMP"
fi

printf 'GITHUB_SYNC_TOKEN=%s\n' "$TOKEN" >> "$TMP"

if ! grep -q '^[[:space:]]*GITHUB_SYNC_REPO[[:space:]]*=' "$TMP"; then
  printf 'GITHUB_SYNC_REPO=%s\n' "$REPO" >> "$TMP"
fi

mv "$TMP" "$ENV_FILE"
chmod 600 "$ENV_FILE"
ok "Saved to backend/.env ${dim}(readable only by you)${rst}"

# Safety net: .env must never be committed.
if git -C "$ROOT" check-ignore -q backend/.env 2>/dev/null; then
  ok "Confirmed backend/.env is gitignored — your token can't be committed"
else
  warn "backend/.env is NOT gitignored. Do not commit it. Tell Claude about this."
fi

unset TOKEN

# ── Step 4: prove it end-to-end with a real sync ─────────────────────────────
say ""
say "${bold}Running a live test sync…${rst}"

if [ ! -x "$BACKEND/.venv/bin/python" ]; then
  warn "The app's Python environment isn't built yet, so I can't test right now."
  say ""
  say "  That's fine — setup is complete. Just start the app:"
  say "    ${bold}./start.sh${rst}"
  say "  It will sync automatically the first time the pipeline does anything."
  say ""
  exit 0
fi

cd "$BACKEND" || exit 1
PY="$BACKEND/.venv/bin/python"

# The sync layer needs aiohttp. If it's absent every integration turns itself
# off silently, so install it rather than reporting a mystery failure.
if ! "$PY" -c "import aiohttp" >/dev/null 2>&1; then
  say "  ${dim}Installing a missing component (aiohttp)…${rst}"
  if "$BACKEND/.venv/bin/pip" install -q aiohttp >/dev/null 2>&1; then
    ok "Installed aiohttp"
  else
    bad "Couldn't install aiohttp — the sync can't run without it."
    say "  Try:  ${bold}cd backend && .venv/bin/pip install aiohttp${rst}"
    exit 1
  fi
fi

SYNC_OUT="$("$PY" -c "
import asyncio, sys, traceback
sys.path.insert(0, '.')
try:
    import database as db
    from services import status_sync
except Exception:
    traceback.print_exc(); print('IMPORT_ERROR'); raise SystemExit

async def main():
    await db.init_db()
    if not status_sync.is_configured():
        print('NOT_CONFIGURED'); return
    print('OK' if await status_sync.sync_now() else 'SYNC_FAILED')

try:
    asyncio.run(main())
except Exception:
    traceback.print_exc(); print('CRASHED')
" 2>&1)"

case "$SYNC_OUT" in
  *OK*)
    ok "Test sync succeeded — the studio is now connected"
    say ""
    say "  ${bold}Open your dashboard:${rst}"
    say "  $DASHBOARD"
    say ""
    say "  ${dim}The chip under the title should read 'Studio live — synced just now'.${rst}"
    say "  ${dim}Episodes appear on the Production Floor as you run them.${rst}"
    say ""
    ;;
  *NOT_CONFIGURED*)
    bad "The app couldn't read the token back from backend/.env."
    say "  The token is saved, but something about the file is off."
    say "  Send Claude this line — it's safe, it hides the token itself:"
    say "    ${bold}grep -c GITHUB_SYNC_TOKEN backend/.env${rst}"
    ;;
  *SYNC_FAILED*)
    warn "Token works, but GitHub refused the upload."
    say "  Usually a brief network problem. The app retries automatically —"
    say "  start it with ${bold}./start.sh${rst} and check the dashboard after a stage runs."
    ;;
  *)
    warn "The test didn't finish. Details below — this is safe to share, it"
    warn "contains no token:"
    say ""
    printf '%s\n' "$SYNC_OUT" | tail -12 | sed 's/^/    /'
    say ""
    say "  Your token is saved either way. Start the app with ${bold}./start.sh${rst};"
    say "  if the dashboard stays gray after running an episode, send Claude the above."
    ;;
esac
