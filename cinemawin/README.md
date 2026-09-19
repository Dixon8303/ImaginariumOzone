# CinemaWin — From Idea to Investor-Ready Film

A calm, guided workspace that takes a film from a one-line idea to a developed
story, a 100-point Story Score with a greenlight verdict, and a finance-ready
package (budget ceiling, 4-layer capital stack, 12-slide investor deck).

This folder is a **self-contained component** of the ImaginariumOzone monorepo.
It shares nothing with the other components except git history.

```
cinemawin/
  src/            React 18 + Vite + Tailwind 3 frontend (JSX)
  backend/        FastAPI + SQLite backend (auth, projects, LLM functions)
  backend/prompts/doctrine/   The five CinemaWin spec documents — the system prompt
  start.sh        Runs backend (8002) + frontend (5174) together
```

## Origin

The frontend was first built on the Base44 platform. This port keeps the UI
and copy intact and replaces the Base44 SDK (auth, `Project` entity, backend
functions, `InvokeLLM`) with a small FastAPI service that runs the four story
functions on the Anthropic API. The Base44-specific pieces (Google sign-in,
the MCP OAuth consent page, the admin 404 note) are gone; everything the user
sees is the same.

## Quick start

Requirements: Python 3.10+, Node 18+, an Anthropic API key.

```bash
cd cinemawin
./start.sh
```

The first run creates `backend/.env` from `backend/.env.example` and stops.
Open `backend/.env`, paste your key on the `ANTHROPIC_API_KEY=` line, then run
`./start.sh` again. The app is at **http://localhost:5174**; the API docs at
http://localhost:8002/docs.

### Try it with no API key (demo mode)

Set `CINEMAWIN_DEMO_MODE=1` in `backend/.env`. Every story, score, and finance
call returns deterministic sample output (in the voice of the sample project
*The Last Archivist*), so you can walk the whole product end to end for free.
The API's `/api/health` response reports `demo_mode: true` while this is on.

## How a project moves through the app

| Step | Page | What happens |
|---|---|---|
| Intake | `/get-started` | Track → title + logline → genre → **developStory** surfaces premise, protagonist, deeper need, wound, central question, theme, next step. No account needed yet; the result is parked and saved the moment you sign up or sign in. |
| Develop | `/project/:id/develop` | Edit the story fields; **buildStructure** produces an 8-sequence structure with the emotional turn of each. |
| Score | `/project/:id/score` | **scoreStory** runs the 100-point Greenlight Scorecard (12 categories) and returns the verdict. Entry-plan users see a blurred breakdown (soft paywall). |
| Fund | `/project/:id/fund` | **buildFinance** sets a budget ceiling against market comps, balances the 4-layer capital stack, and drafts the 12-slide investor deck. The deck is blurred until Premium. Every figure carries an evidence tag. |

The four functions are prompted with the five CinemaWin doctrine documents in
`backend/prompts/doctrine/` as the system prompt. The backend also enforces
the doctrine's hard rules in code, so the UI never depends on the model doing
arithmetic:

- Scorecard: exactly 12 categories in spec order with the spec's maximum
  points; the total is recomputed as the sum; the verdict and label follow the
  §II thresholds (90+/80+/70+/60+/<60).
- Capital stack: exactly 4 layers in spec order, re-balanced to sum to 100%
  with the Equity Gap absorbing rounding; the equity gap in dollars is
  computed from the ceiling.
- Budget tier snapped to the spec tiers; exactly 12 deck slides with the §V
  slide titles.

## Plans and the soft paywall

There is no billing integration yet. Plans live on the user record and gate
what the UI unlocks:

| Plan | Story Score breakdown | Pitch deck |
|---|---|---|
| `entry` (default) | blurred | blurred |
| `starter` | full | blurred |
| `premium` | full | full |

Change a user's plan from the command line (backend virtualenv active):

```bash
cd cinemawin/backend
.venv/bin/python tools/set_plan.py you@example.com premium
```

New accounts get `CINEMAWIN_DEFAULT_PLAN` (default `entry`).

## Configuration (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required** unless demo mode is on. Never commit it. |
| `CINEMAWIN_SECRET_KEY` | random per boot | Signs login tokens. Set it so sign-ins survive a restart. |
| `CINEMAWIN_DATABASE_PATH` | `./cinemawin.db` | SQLite file, relative to `backend/`. |
| `CINEMAWIN_PORT` | `8002` | Backend port. |
| `CINEMAWIN_DEMO_MODE` | `0` | `1` = canned output, no API key needed. `auto` = demo only when no key is set. |
| `CINEMAWIN_DEFAULT_PLAN` | `entry` | Plan given to new accounts. |
| `CINEMAWIN_MODEL_CRAFT` | `claude-opus-5` | Model for developStory / buildStructure. |
| `CINEMAWIN_MODEL_JUDGE` | `claude-opus-5` | Model for scoreStory / buildFinance. |
| `CINEMAWIN_REFUSAL_FALLBACKS` | `1` | Server-side fallback to another Claude model if a request is declined by safety classifiers. |
| `CINEMAWIN_CORS_ORIGINS` | `http://localhost:5174` | Comma-separated allowed origins. |
| `CINEMAWIN_PUBLIC_URL` | `http://localhost:5174` | Used to build password-reset links. |
| `CINEMAWIN_DEVELOP_RATE_LIMIT` | `10` | Unauthenticated developStory calls per IP per hour. |
| `SMTP_HOST` … `SMTP_FROM` | empty | When set, sign-up requires an emailed 6-digit code and password resets are emailed. When empty, accounts are verified instantly and reset links are printed to the server console. |

## Running the pieces separately

```bash
# backend
cd cinemawin/backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --port 8002 --reload

# frontend (dev server proxies /api to :8002)
cd cinemawin
npm install && npm run dev

# production build — the backend serves ./dist as the app
npm run build
```

## Checks before committing

```bash
cd cinemawin && npx vite build
cd backend && .venv/bin/python -c "import main" && .venv/bin/python -m pytest -q tests
```

## Not built yet (deliberately)

- **Billing.** Plans are set by the operator with `tools/set_plan.py`; Stripe
  is the obvious next step and the pricing page already carries the tiers.
- **Exports.** The Premium tier promises deck/budget exports; the deck and
  capital stack are rendered on screen today.
- **Deeper doctrine commands** (`DRAFT`, `PREP`, `DOOD`, `LOOKBOOK`, `RIGHTS`,
  `STRESS TEST`). The doctrine is loaded in full, but only `DEVELOP`, the
  8-sequence structure, `SCORE`, and `FINANCE`/`PACKAGE` have UI.
