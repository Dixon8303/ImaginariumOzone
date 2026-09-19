# CinemaWin — Cooperation Brief for Contributing Agents

This document is the contract for anyone — human or agent — building on
CinemaWin. Read it before writing code. It exists so several people can work
in parallel without colliding, and so nothing ships that quietly breaks the
product's promises.

**Repository:** `Dixon8303/ImaginariumOzone`
**Component path:** `cinemawin/` (everything you touch lives here)
**Owner / final approver:** D. Antione Dixon

---

## 1. What CinemaWin is

A film development workspace. A filmmaker brings a one-line idea and leaves
with a developed story, a 100-point Greenlight Scorecard verdict, and a
finance-ready package (budget ceiling, 4-layer capital stack, 12-slide investor
deck).

It is not a chatbot with a film theme. The product is the **doctrine**: five
specification documents in `backend/prompts/doctrine/` that define how a film
is analysed, scored, and financed. The software's job is to apply that doctrine
faithfully and to make its output trustworthy.

**The single most important thing to understand:** the model is not trusted
with arithmetic or structure. `backend/services/postprocess.py` deterministically
forces the 12 scorecard categories, recomputes totals, rebalances the capital
stack to exactly 100%, and pads the deck to 12 spec slides. If you add a feature
where a model produces numbers, you add the enforcement alongside it. This is
not optional and it is not negotiable.

---

## 2. Architecture in one screen

```
cinemawin/
  doctrine.json          Shared constants (categories, tiers, layers, slides).
                         Read by BOTH Python and JavaScript. One source of truth.
  src/                   React 18 + Vite + Tailwind 3. JSX only, no TypeScript.
    api/client.js        The ONLY place that talks to the backend. Two drivers:
                         "server" (FastAPI) and "local" (browser-only).
    lib/                 doctrine.js, demoData.js, localStore.js, AuthContext.
    pages/               One file per route.
    components/ui/       shadcn components. Standard output, do not restyle.
  backend/               FastAPI + SQLite.
    config.py            ALL env vars + doctrine loading. Single source of truth.
    services/providers.py  Talks to any AI provider (Anthropic or OpenAI-compatible).
    services/llm.py      Doctrine system prompt, JSON schemas, per-function calls.
    services/postprocess.py  Deterministic enforcement. The trust boundary.
    routers/             auth, projects, functions, app.
    prompts/             Per-stage user prompts + the five doctrine documents.
  Dockerfile             Whole app in one container.
  render.yaml            Free-tier deploy blueprint.
```

**Two run modes, one codebase.**

| Mode | How | Storage | AI |
|---|---|---|---|
| Server | `./start.sh`, or the Docker image | SQLite, real accounts | Real provider |
| Static | `npm run build:static` → any static host | Browser localStorage | Sample output until the user connects a backend |

The static build is what deploys to GitHub Pages. It uses **hash routing**
because a static host cannot rewrite deep links. If you add a route, it works
in both modes automatically — but never introduce code that assumes
`window.location.pathname` is the route.

---

## 3. Hard rules

Breaking one of these is grounds for rejecting the PR outright, however good
the rest of it is.

1. **Never commit a secret.** Not in code, not in a test fixture, not in
   `.env.example`, not in a comment, not in a PR description. `.env` is
   gitignored; keep it that way.
2. **Never put doctrine numbers in code.** Scorecard maximums, verdict
   thresholds, capital-stack ranges, budget tiers, slide titles — all of it
   lives in `doctrine.json`. If you need a new constant, add it there.
3. **Never trust model output for shape or arithmetic.** Everything a model
   returns passes through `postprocess.py` (server) or arrives pre-shaped from
   `demoData.js` (browser). Add enforcement with every new model-backed field.
4. **Never gate paid content in CSS alone.** A blurred div still ships the text
   to the browser. Withhold it server-side, as `pad_deck_slides` does. This was
   a real bug once; do not reintroduce it.
5. **Never present sample output as real analysis.** Any demo response carries
   `demo: true` and the UI must render `<SampleNotice />`. A user must never
   believe canned text is a reading of their film.
6. **Never import from another component of this monorepo.** `cinemawin/` shares
   git history with `backend/`, `deos/`, `site/` and the rest — nothing else.
   It must stay extractable into its own repository.
7. **Never break the Pages deploy.** Do not remove the `rm -f _site/*/CNAME`
   lines in `.github/workflows/pages.yml`. Custom domains only apply at the
   artifact root, and leaving those files in place breaks the whole deploy for
   every site in the repo, not just CinemaWin.
8. **Never widen a PR beyond its work package.** Drive-by refactors make review
   impossible and cause the merge conflicts this document exists to prevent.

---

## 4. How to claim work without colliding

Work is organised into **packages** (section 7). Each package names the files it
owns. The rule is simple:

> **One agent per package. An agent edits only the files its package lists.**

If your package needs a change in a file another package owns, do not make it.
Open an issue describing the change you need, reference it in your PR, and work
around it or wait. A shared file edited by two agents in parallel is the single
most likely way this effort wastes a day.

Files that are **shared by everything** and need an issue before anyone touches
them:

- `doctrine.json`
- `backend/config.py`
- `src/api/client.js`
- `backend/services/postprocess.py`
- `.github/workflows/pages.yml`

### Branch and PR conventions

- Branch from the latest `main`: `git fetch origin main && git checkout -B <branch> origin/main`
- Branch name: `cinemawin/<package-id>-<short-slug>` — e.g. `cinemawin/P3-export-pdf`
- One package per PR. Open it as a **draft** until your verification passes.
- PR title: `CinemaWin: <what changed>`
- PR body must contain, in this order:
  1. What changed and why, in plain sentences.
  2. The package ID you claimed.
  3. The exact verification commands you ran **and their real output**. Not
     "tests pass" — paste the summary line.
  4. Anything you could not verify, and why.
- Never force-push a branch someone else may have checked out. Merge `main` in
  rather than rebasing if your PR is already open for review.

---

## 5. Verification gate

Every PR must pass all of these locally before it leaves draft. A PR whose
author did not run them will be sent back unread.

```bash
# Frontend — both builds, because a change can break one and not the other
cd cinemawin
npm ci
npm run build
npm run build:static

# Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -c "import main"
.venv/bin/python -m pytest -q tests
```

**If you changed anything a user touches**, also run the app and use it:
`./start.sh`, then walk the path your change affects. A green test suite is not
evidence that a screen works.

**If you changed the static build**, verify a deep link survives a reload — that
is the failure mode GitHub Pages punishes and unit tests never catch.

### Writing tests

- Backend tests live in `backend/tests/`, run under pytest, and must not need
  network or an API key.
- Test the enforcement, not the model. `postprocess.py` and `providers.py` are
  pure and fully testable; assert on boundaries (a score of 59 vs 60, a stack
  summing to 95 vs 115, a deck with 3 slides vs 20).
- Any bug you fix gets a test that fails before your fix and passes after.

---

## 6. Things that look like bugs and are not

Read this before "fixing" them.

- **Google sign-in is disabled, not missing.** The backend reports
  `google_oauth_enabled: false`. The button and icon are intentionally kept so
  turning it on later is a server change, not a UI rewrite.
- **There is no billing.** Plans are set by the operator with
  `backend/tools/set_plan.py`, or from the Settings page in browser-only mode.
  The pricing page is real copy for a real intent; the checkout is simply not
  built yet. Do not wire a payment provider without asking.
- **The rate limiter is in-memory.** It resets on restart and is per-process.
  That is a deliberate simplification for a single-instance deployment, not an
  oversight. Replacing it means picking a datastore — open an issue first.
- **Demo output is identical for every project.** That is the point. It
  demonstrates the workflow without pretending to analyse anything.
- **`maturity_level` rarely moves past 1.** Levels 2–7 are defined in the
  doctrine but no stage raises them yet. That is package P5, not a bug.

---

## 7. Work packages

Ordered by value. Each lists the files it owns and what "done" means. Claim one
by opening a draft PR with the package ID in the branch name.

### P1 — CI for the component `[small, high value]`
**Owns:** `.github/workflows/cinemawin-ci.yml` (new file only)
Nothing currently re-runs the build or tests when `cinemawin/**` changes. Add a
workflow that, on pull requests touching `cinemawin/**`, runs both frontend
builds and the backend import + pytest. Must not touch `pages.yml`.
**Done when:** a PR that breaks a test shows a red check.

### P2 — Export the deck and the budget `[medium]`
**Owns:** `src/pages/FundPackage.jsx`, `src/lib/export/**` (new), `backend/routers/exports.py` (new)
Premium promises exports and they do not exist. Produce a PDF of the 12-slide
deck and a CSV or XLSX of the capital stack and budget. Client-side generation
is acceptable and avoids new server dependencies. Must respect the plan gate —
a non-premium user cannot export what the server withheld.
**Done when:** a premium user gets a file that opens correctly; a non-premium
user gets the upgrade prompt instead.

### P3 — The Plan module (production footprint) `[large]`
**Owns:** `src/pages/PlanProduction.jsx` (new), `backend/prompts/plan_production.txt` (new), a new function route
`"plan"` already exists in the module list with no screen behind it. Build the
Physical Production Breakdown from doctrine Module 02: scene parsing, element
tagging, the location footprint with the 75–85% cluster rule, and the
Day-out-of-Days matrix. Follow the existing function pattern exactly — prompt
file, JSON schema, deterministic post-processing.
**Done when:** a scored project produces a usable breakdown, and the numbers
are enforced in code rather than trusted to the model.

### P4 — Rights and clearance audit `[medium]`
**Owns:** `src/pages/Clearance.jsx` (new), `backend/prompts/clearance.txt` (new), a new function route
Doctrine Module 03 §VI. Scan the story material for trademarks, real people,
songs, and defamation risk; classify LOW/MEDIUM/HIGH/CRITICAL with a remedy for
each. Premium sells this today and it does not exist.
**Done when:** the risk register renders with severities and remedies, gated to
the plan that sells it.

### P5 — Maturity progression `[small]`
**Owns:** `backend/services/postprocess.py` (coordinate first), `src/pages/StoryDevelop.jsx`
Levels 2–7 are unreachable. Define what raises a project to each level and
apply it as stages complete.
**Done when:** finishing a stage visibly advances the level, and the rule for
each is documented.

### P6 — Real accounts on a free host `[medium]`
**Owns:** `render.yaml`, `Dockerfile`, `README.md` deployment section
The free tiers this ships with have ephemeral disks, so accounts vanish on
restart. Add an optional Postgres or Turso/libSQL path behind the existing
config so a free deploy can keep data.
**Done when:** a documented free deploy survives a restart with its accounts
intact, and SQLite remains the zero-config default.

### P7 — Accessibility and mobile pass `[small, high value]`
**Owns:** `src/components/**`, `src/pages/**` (visual only, no logic)
Keyboard navigation, focus states, contrast, and screen-reader labels have not
been audited. The paywall overlays and the OTP input are the likeliest problems.
**Done when:** every interactive element is reachable and labelled, and the
workspace is usable at 375px wide.

---

## 8. Style

- **Frontend:** JSX, function components, hooks. Tailwind utility classes using
  the theme tokens (`bg-card`, `text-muted-foreground`), never raw hex. Match
  the surrounding file; do not introduce a state library.
- **Backend:** Python 3.10+, type hints on function signatures, `async` for
  anything touching I/O. Every external service exposes `is_configured()` and
  degrades instead of crashing.
- **Comments** explain *why*, not *what*. If a line is surprising, say what
  breaks without it. Do not narrate the obvious.
- **Copy** is part of the product. It is plain, direct, and never oversells.
  Read the existing strings before writing new ones — if yours sound like
  marketing and theirs sound like a colleague, yours are wrong.

---

## 9. When to stop and ask

Open an issue and wait rather than guessing, if:

- The change touches a shared file from section 4.
- It adds a dependency, a service, or a recurring cost.
- It changes the doctrine, the scoring, or anything a user might quote to an
  investor.
- It handles payment, personal data, or authentication in a new way.
- It would make a claim in the UI that the code cannot currently back up.

Getting this wrong is expensive and quiet. Asking is cheap.
