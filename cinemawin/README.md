# CinemaWin — From Idea to Investor-Ready Film

A calm, guided workspace that takes a film from a one-line idea to a developed
story, a 100-point Story Score with a greenlight verdict, and a finance-ready
package (budget ceiling, 4-layer capital stack, 12-slide investor deck).

**You do not need to pay for anything to run this.** Several AI providers have
a free tier with no credit card, and the whole app deploys to GitHub Pages for
free. See [Put it online for free](#put-it-online-for-free).

This folder is a **self-contained component** of the ImaginariumOzone monorepo.
It shares nothing with the other components except git history.

```
cinemawin/
  doctrine.json   Shared doctrine constants, read by both Python and JavaScript
  src/            React 18 + Vite + Tailwind 3 frontend (JSX)
  backend/        FastAPI + SQLite backend (auth, projects, AI functions)
  backend/prompts/doctrine/   The five CinemaWin spec documents
  Dockerfile      The whole app in one container
  render.yaml     Free-tier deploy blueprint
  start.sh        Runs backend + frontend together for local development
  COOPERATION.md  The contract for anyone contributing code
```

## Two ways to run it

| | Browser-only | With a backend |
|---|---|---|
| **Setup** | None | A server, and a provider key |
| **Where projects live** | This browser's storage | A database |
| **AI output** | Sample text, same for every project | A real read of your story |
| **Accounts** | None — the browser is the account | Email and password |
| **Cost** | Free | Free on a free tier |

Browser-only is a real, working app: the full workflow, your own projects,
saved between visits. What it cannot do is analyse *your* story, because there
is no AI behind it. The UI says so on every screen that shows sample text.

---

## Put it online for free

### Step 1 — Publish the site (5 minutes, free, no account needed)

Pushing to `main` builds CinemaWin and publishes it with the repo's other
sites. The workflow is already configured.

Your URL will be:

```
https://<your-github-username>.github.io/ImaginariumOzone/cinemawin/
```

That is a complete, usable app in browser-only mode. Nothing else to do.

> If GitHub Pages is not on yet, the workflow enables it on its first run. Check
> **Actions → Deploy sites to GitHub Pages** for the deploy, and
> **Settings → Pages** for the live URL.

### Step 2 — Add real AI (20 minutes, free)

For CinemaWin to analyse your actual story it needs a backend holding a
provider key. A key in the browser would be visible to anyone who opened it, so
it lives on a server instead.

**2a. Get a free API key.** Any one of these:

| Provider | Free tier | Get a key |
|---|---|---|
| **Google Gemini** | Yes, no card. Best quality of the free options. | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| **Groq** | Yes, no card. Fastest. | [console.groq.com/keys](https://console.groq.com/keys) |
| **Cerebras** | Yes | [cloud.cerebras.ai](https://cloud.cerebras.ai/) |
| **Ollama** | Runs on your own Mac. Unlimited, no key, works offline. | [ollama.com/download](https://ollama.com/download) |

Free tiers are rate limited — Gemini around 10 requests per minute, Groq around
30. CinemaWin makes one request per button press, so for one person that is
plenty.

**2b. Deploy the backend.** [Render](https://render.com)'s free tier needs no
credit card, and `render.yaml` configures it for you:

1. Sign up at render.com and connect this GitHub repository.
2. **New → Blueprint**, pick this repo. Render reads `render.yaml`.
3. When it asks for `CINEMAWIN_LLM_API_KEY`, paste your key from 2a.
4. If you chose a provider other than Gemini, set `CINEMAWIN_LLM_PROVIDER` to
   match (`groq`, `cerebras`, `openrouter`, `anthropic`, `openai`).
5. Deploy. You get a URL like `https://cinemawin-api.onrender.com`.

Two things about the free tier, so nothing surprises you later:

- **It sleeps after ~15 minutes idle.** The first request after that takes
  30–60 seconds while it wakes. It is not broken.
- **The disk is wiped on every restart and deploy.** Accounts and projects do
  not survive. Fine for trying it out; not fine for real work. Work package P6
  in `COOPERATION.md` covers fixing this.

**2c. Connect them.** Open your Pages URL, go to **Settings**, paste the Render
URL, and press Connect. It checks the server and tells you which provider
answered.

### Alternative: run it entirely on your own machine

Free, unlimited, private, and nothing sleeps. Install
[Ollama](https://ollama.com/download), run `ollama pull llama3.1`, then set
`CINEMAWIN_LLM_PROVIDER=ollama` in `backend/.env` and start the app locally.
No key, no account, no internet needed after the model downloads.

---

## Run it locally

**Requirements:** Python 3.10+, Node 20.19+ (or 22.12+). Node 18 will not work —
Vite 8 requires 20.19 or newer.

```bash
cd cinemawin
./start.sh
```

The first run creates `backend/.env` from the template and stops. Open that
file, set a provider and key (see the table above), then run `./start.sh`
again. The app is at **http://localhost:5174**; the API docs at
http://localhost:8002/docs.

To explore with no key at all, set `CINEMAWIN_DEMO_MODE=1` in `backend/.env`.

### First run, end to end

1. `./start.sh` and open http://localhost:5174
2. **Start your project free** — walk the four-step intake
3. Create an account when prompted (email and password; with no SMTP configured
   the account is verified instantly)
4. Your developed story is waiting in the workspace

To see the paid features, give your account a plan:

```bash
cd cinemawin/backend
.venv/bin/python tools/set_plan.py you@example.com premium
```

Then reload the project page. Plans are `entry`, `starter`, `premium`. The
server must have run at least once (so the database exists) and the email must
belong to a registered account.

### Running the pieces separately

```bash
# backend
cd cinemawin/backend
cp .env.example .env          # required — without it every AI call returns 503
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --port 8002 --reload

# frontend (the dev server proxies /api to the backend)
cd cinemawin
npm install
npm run dev
```

---

## How a project moves through the app

| Step | Page | What happens |
|---|---|---|
| Intake | `/get-started` | Track → title + logline → genre → **developStory** surfaces premise, protagonist, deeper need, wound, central question, theme, and a recommended next step. No account needed yet; the result is parked and saved when you sign up. |
| Develop | `/project/:id/develop` | Edit the story fields; **buildStructure** produces an 8-sequence structure with the emotional turn of each. |
| Score | `/project/:id/score` | **scoreStory** runs the 100-point Greenlight Scorecard and returns the verdict plus three prioritised fixes. Entry-plan users see a blurred breakdown. |
| Fund | `/project/:id/fund` | **buildFinance** sets a budget ceiling against market comps, balances the capital stack, and drafts the 12-slide investor deck. The deck and waterfall are Premium. |

The four functions are prompted with the five doctrine documents in
`backend/prompts/doctrine/` as the system prompt, preceded by a short house-style
preamble defined in `backend/services/llm.py` (`HOUSE_STYLE_PREAMBLE`) — that
preamble is the one piece of editorial doctrine that lives in code rather than
in the doctrine files.

**The doctrine's hard rules are enforced in code, not trusted to the model.**
This is what makes the output safe to quote:

- The scorecard always has exactly 12 categories in spec order with the spec's
  maximum points; the total is recomputed as their sum; the verdict follows the
  spec thresholds (90+, 80+, 70+, 60+, below 60).
- The capital stack always has exactly 4 layers in spec order, rebalanced to sum
  to exactly 100% with the equity gap absorbing rounding, and the equity gap in
  dollars is computed from the ceiling.
- The budget tier is snapped to a spec tier, and the deck always has the 12 spec
  slide titles.

A model that returns nine categories or percentages summing to 115 still
produces a correct response. Those numbers live in `doctrine.json`, which both
the Python backend and the browser build read.

**Evidence tags.** Capital-stack layers and the assumptions list each carry an
evidence tag (`FACT`, `INDUSTRY RANGE`, `MODEL ASSUMPTION`, and the rest of the
Module 00 §V scale) so you can see how much weight a figure holds. The budget
ceiling, tier, and comps are not individually tagged.

---

## Plans and the paywall

There is no billing integration. Plans live on the user record:

| Plan | Story Score breakdown | Pitch deck | Investor waterfall |
|---|---|---|---|
| `entry` (default) | Blurred | First 6 slides blurred, rest withheld | Withheld |
| `starter` | Full | First 6 slides blurred, rest withheld | Withheld |
| `premium` | Full | Full | Full |

Locked content is withheld by the server, not merely blurred in CSS — it never
reaches the browser. New accounts get `CINEMAWIN_DEFAULT_PLAN` (default
`entry`). In browser-only mode you can switch plans freely from Settings to see
what each unlocks.

---

## Configuration (`backend/.env`)

Every variable is optional except a provider key (or demo mode).

| Variable | Default | Purpose |
|---|---|---|
| `CINEMAWIN_LLM_PROVIDER` | inferred from whichever key is set | `gemini`, `groq`, `openrouter`, `cerebras`, `ollama`, `anthropic`, `openai`, `together` |
| `CINEMAWIN_LLM_API_KEY` | — | Your provider key. You may instead set the provider's own variable (`GEMINI_API_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, …) and the provider is inferred. |
| `CINEMAWIN_MODEL_CRAFT` | provider default | Model for developStory / buildStructure |
| `CINEMAWIN_MODEL_JUDGE` | provider default | Model for scoreStory / buildFinance |
| `CINEMAWIN_LLM_BASE_URL` | provider default | Override for a self-hosted or proxied endpoint |
| `CINEMAWIN_LLM_MAX_TOKENS` | `8000` | Response ceiling |
| `CINEMAWIN_LLM_TIMEOUT_SEC` | `180` | Per-request timeout |
| `CINEMAWIN_REFUSAL_FALLBACKS` | `1` | Anthropic only: retry on another model if a request is declined |
| `CINEMAWIN_DEMO_MODE` | `0` | `1`/`true`/`yes`/`on` = always sample output. `auto` = sample only when no provider is configured. `0` = real calls only, 503 if unconfigured. |
| `CINEMAWIN_SECRET_KEY` | random each boot | Signs login tokens. **Set it**, or every restart logs everyone out. |
| `CINEMAWIN_DATABASE_PATH` | `./cinemawin.db` | Relative to `backend/`; absolute paths used as-is |
| `CINEMAWIN_PORT` | `8002` | Backend port. `start.sh` and the Vite dev proxy both read it. |
| `CINEMAWIN_DEFAULT_PLAN` | `entry` | Plan given to new accounts |
| `CINEMAWIN_CORS_ORIGINS` | `http://localhost:5174` | Comma-separated origins, or `*` when the frontend is hosted elsewhere |
| `CINEMAWIN_PUBLIC_URL` | `http://localhost:5174` | Used to build password-reset links |
| `CINEMAWIN_DEVELOP_RATE_LIMIT` | `10` | developStory calls per IP per hour (in-memory; resets on restart) |
| `SMTP_HOST` | empty | Set it and sign-up requires an emailed code and resets are emailed. Leave it empty and accounts verify instantly with reset links printed to the server console. `SMTP_PORT` defaults to `587`; `SMTP_HOST` alone switches email on. |

Frontend build variables: `CINEMAWIN_MODE=static` produces the browser-only
build, and `CINEMAWIN_BASE` sets the sub-path it is served from.

---

## Checks before committing

```bash
cd cinemawin
npm ci
npm run build
npm run build:static

cd backend
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -c "import main"
.venv/bin/python -m pytest -q tests
```

`requirements-dev.txt` is what provides pytest; `requirements.txt` alone will
not run the tests.

---

## Contributing

`COOPERATION.md` is the contract: architecture, hard rules, how to claim work
without colliding, the verification gate, and a prioritised backlog of work
packages. Read it before writing code.

---

## Not built yet

Deliberate gaps, so the UI does not promise what it cannot do:

- **Billing.** Plans are set by the operator; there is no checkout.
- **Exports.** Premium's deck and budget exports are work package P2.
- **The Plan module.** `"plan"` exists as a module with no screen (P3).
- **Clearance and risk audit.** Sold on Premium, not built (P4).
- **Production footprint overview.** Sold on Starter, not built (P3).
- **Deeper doctrine commands** — `DRAFT`, `PREP`, `DOOD`, `LOOKBOOK`, `RIGHTS`,
  `STRESS TEST`. The doctrine is loaded in full, but only `DEVELOP`, the
  8-sequence structure, `SCORE`, and `FINANCE`/`PACKAGE` have a user interface.
- **Maturity levels 2–7.** Defined in the doctrine; nothing raises a project
  past level 1 yet (P5).
