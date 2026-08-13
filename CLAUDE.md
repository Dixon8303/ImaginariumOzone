# ImaginariumOzone — System Constraints & Operating Guide

A multi-project repository. The components below are **independent** — they share a
git history and a Pages deploy, nothing else. Never wire one into another.

| # | Component | Path | What it is |
|---|-----------|------|-----------|
| 1 | **BGF Production OS** | `backend/`, `src/`, `start.sh` | The main system. Autonomous video-production pipeline for *The Black Genius Files*. Runs locally on the operator's Mac. |
| 2 | **Mission Control** | `docs/bgf/`, `status/` | Public read-only dashboard mirroring pipeline state. Static page on GitHub Pages. |
| 3 | **Published sites** | `docs/`, `site/`, `eatmedia/` | Three static sites deployed by one workflow. |
| 4 | **HoneyDrip Bot** | `honeydrip_bot/` | Python trading methodology framework. Live agentic trading via Robinhood Trading MCP — see Hard Rules. |
| 5 | **Marvel Release Tracker** | `marvel_tracker/` | Personal automation. Daily GitHub Actions cron watching TMDb. |
| 6 | **Circle of Morality / Screenplay Tracker** | `src/CircleOfMorality.jsx`, `src/ScreenplayTracker.jsx` | Earlier React features, preserved at `/circle` and `/tracker`. |
| 7 | **Dixon Grant Studio** | `dixon-grant-studio/` | Grant-writing pipeline and outreach assets. |
| 8 | **RS Options Risk Engine** | `rs_options/` | Research-stage risk engine for the RS Options spec. Pure Python, zero deps. **No live trading** — see `rs_options/README.md` boundaries. |

**Target platform:** macOS (Apple Silicon). `start.sh` uses BSD `sed -i ''`, narration
falls back to the macOS `say` command, and ComfyUI is tuned for MPS. Linux/CI runs of
the backend work for tests but not the full media pipeline.

---

## Hard Rules (Non-Negotiable)

### Trading — HoneyDrip

| Rule | Enforcement |
|------|-------------|
| `HONEYDRIP_MODE` controls execution | `"paper"` (default) → Alpaca paper endpoint; `"live_mcp"` → Robinhood Trading MCP |
| Abort if `HONEYDRIP_ARMED != "YES"` | Interlock in `config.py` + `engine.py` — required in every mode |
| Alpaca for paper mode only | `alpaca_client.py` hard-codes the paper endpoint |
| Robinhood via official Trading MCP | Authorized for agentic live execution via `https://agent.robinhood.com/mcp/trading` |
| Max position size: 5% of equity | Enforced in `risk_manager.py` |
| Max daily loss: 2% of equity | Hard stop in `risk_manager.py` — no further trades that session |
| All trades logged | `trade_logger.py` records every execution including result |
| Execution playbook | See `honeydrip_bot/robinhood_mcp_guide.md` |

### Secrets — all components

| Rule | Enforcement |
|------|-------------|
| API keys live in env vars only | Never write a key to a file, prompt, dossier, commit, or chat reply |
| `.env` is gitignored; `.env.example` holds empty keys only | Check before every commit that adds config |
| Nothing secret enters `status/production_status.json` | It is committed to a **public** repo — metadata only, never scripts, research text, or keys |

### Publishing

| Rule | Why |
|------|-----|
| Never link Mission Control (`docs/bgf/`) from a public page | It is deliberately unlisted (`noindex, nofollow`) |
| Never remove `rm -f _site/*/CNAME` from `pages.yml` | Custom domains only apply at the artifact root; leaving them breaks the deploy |
| Uploads to YouTube stay behind a human gate | No mode publishes without operator approval |

---

## 1. BGF Production OS

FastAPI backend (port **8001**) + Vite/React frontend (port **5173**), SQLite at
`backend/bgf.db`, media written to `OUTPUT_BASE_DIR`.

```bash
./start.sh          # creates venv, installs deps, runs both servers
```

First run copies `backend/.env.example` → `backend/.env` and exits, asking for
`ANTHROPIC_API_KEY`. That key is the only hard requirement; every other integration
degrades gracefully when unset.

### The 15-stage pipeline (Order v2)

Defined in `backend/pipeline/orchestrator.py` — the `stages` list is execution
order, `ROUTING` is the tier map. Doctrine lives in `BGF_PROMPT_STACK.md`
(stage contracts) and `BGF_PACING_CONSTITUTION.md` (§3 pacing, §6 Flux specs,
§14 gates). Both must stay in sync with `STAGE_ORDER` in
`backend/services/status_sync.py` and the `STAGES` array in `docs/bgf/index.html`.

Three things define v2: storyboard is pulled ahead of voiceover so ComfyUI
starts days earlier; QA gates the master **before** Shorts extraction so a
re-render never forces a 13-clip re-extract; and G0.25/G0.5 size the shot list
against measured VO duration instead of an estimate.

| # | Stage key | Spec | Tier | Pre-work | Autonomy |
|---|-----------|------|------|----------|----------|
| 1 | `batch_primer` | P0.5 Cluster Primer | Opus 4.8 | — | AUTO |
| 2 | `topic_scoring` | P1 Ideation/Score | Opus 4.8 | Ollama titles | CHECKPOINT |
| 3 | `research` | P2 Research | **Fable 5** | — | AUTO |
| 4 | `outline` | P3 Outline | Opus 4.8 | — | AUTO |
| 5 | `script` | P4 Script | Opus 4.8 | — | AUTO_REVIEW |
| 6 | `storyboard` | P6 Storyboard · runs G0.25 + G0.5 | Sonnet 4.6 | Ollama shots | AUTO |
| 7 | `generation` | Asset generation | ComfyUI (Flux Dev) | — | AUTO |
| 8 | `ken_burns` | Motion pass | ffmpeg | — | AUTO |
| 9 | `voice_ssml` | P5 Voiceover | Sonnet 4.6 | — | AUTO |
| 10 | `audio_prod` | P5.5 Audio Production | ffmpeg | — | AUTO |
| 11 | `titles_seo` | P7a Titles + P8 SEO | Haiku 4.5 | Ollama tags | AUTO |
| 12 | `assembly` | Episode assembly | ffmpeg | — | AUTO |
| 13 | `qa_gates` | P10 QA + G3–G5 | Opus 4.8 | code checks | CHECKPOINT |
| 14 | `shorts` | P9b Shorts (post-QA) | Sonnet 4.6 | Ollama captions | AUTO |
| 15 | `upload` | P10.5 Upload / release | YouTube | — | CHECKPOINT |

Steps 6–8 are Track A (visual), 9–10 Track B (audio), 11 Track C (metadata).
Execution is currently sequential in that order; the outputs are identical
either way, so true concurrency is an optimization, not a correctness fix.

Model IDs are centralized in `backend/config.py` (`MODEL_FABLE`, `MODEL_OPUS`,
`MODEL_SONNET`, `MODEL_HAIKU`), and the constitution's constants — word rate,
buffer multipliers, FLEX share, ASL-per-phase, Flux dimensions — live there too
as `BGF_*`. Never hard-code a model string or a doctrine number in a service.

**Tier discipline:** the tier assignment is the product, not an implementation
detail. Research goes to Fable because claim verification is the highest-stakes
step; titles+SEO go to Haiku because they are mechanical. Do not "upgrade" a
stage to a larger model to fix a bad output — fix the prompt in
`backend/prompts/` first.

### Gates G0.25 – G5

G0.25 and G0.5 are computed in the orchestrator; G1–G5 are judged by Opus in
`backend/services/claude_client.py`. All persist to `gate_decisions`. A FAIL raises `HardHalt`, writes a remediation row, and stops the
pipeline — it never silently continues.

| Gate | Stage | Criteria | Pass condition |
|------|-------|----------|----------------|
| **G0.25** VO Pilot | P6 | Renders ~250 words, measures real duration, derives `pilot_scale_factor` and `calibrated_VO_sec` | closes on write; blocks ComfyUI until then |
| **G0.5** Visual Budget | P6 | Per-phase min visual events x buffer (1.20 piloted / 1.25 not); FLEX = last 15–20% | closes when the budget doc exists |
| **G1** Editorial Perspective | P1 | Real institution/person, systems framing, primary-source reconstructable, extends the BGF thesis | binary PASS |
| **G2** Topic Score | P1 | Virality 30 · Retention 20 · Emotional 20 · Monetization safety 15 · Brand 15 | ≥70 PRODUCE · 60–69 REVISE · <60 KILL |
| **G3** Hook Diagnostic | P10 | Cold open /15 · question posed /10 · stakes /10 · visual hook /15 | ≥28/50; auto-fail if cold open ≤4 |
| **G4** Predictive | P10 | CTR + retention likelihood vs. benchmarks (CTR ≥6%, retention ≥45% AVD) | Opus verdict |
| **G5** Monetization + Ethics | P10 | Advertiser safety /50, sensitive content, accuracy risk, exploitative framing | ≥36/50 and ethics clear |

The operator can override a halt from the Control Room. Overrides are recorded — never
add a code path that clears a gate without writing to `mutation_log`.

### Operating modes

Human review pauses, from `human_gates` in the orchestrator:

| Mode | Pauses after |
|------|-------------|
| `ASSISTED` | script · generation · assembly · qa_gates · upload |
| `SEMI_AUTO` | assembly · qa_gates · upload |
| `FULL_AUTO` | qa_gates · upload |

`upload` (P10.5) is a CHECKPOINT in every mode — it assembles the release
package and stops. There is no unattended-publish path.

### Backend layout

```
backend/
  main.py            FastAPI app; routers mounted here
  config.py          all env config + model IDs (single source of truth)
  database.py        schema + async SQLite helpers
  pipeline/          orchestrator.py — stages, routing, gates, SSE events
  services/          claude_client · ollama_client · comfyui_client
                     elevenlabs_client · vidiq_client · status_sync
  routers/           episodes · pipeline · assets · analytics · discovery
  prompts/           production_bible.txt + per-stage prompt templates
  ffmpeg/            assembler.py — narration, Ken Burns, xfade, shorts
  youtube/           resumable upload client
```

**Conventions:**
- Every external service exposes `is_configured()` and returns `None`/`[]` on failure.
  A missing key must degrade the feature, never crash the pipeline.
- `production_bible.txt` is the system prompt for every Claude call. Editorial doctrine
  changes belong there, not in Python string literals.
- State changes emit SSE via `orchestrator.emit()` — which also triggers Mission Control
  sync. Any new state transition should go through it.

### Frontend routes (`src/App.jsx`)

`/` dashboard · `/new` create · `/discover` topic feed · `/war-room` analytics ·
`/episodes/:id/{pipeline,script,assets,preview,upload,control-room}` ·
`/circle` · `/tracker`

Production UI lives in `src/components/production/`; the API client is
`src/components/production/api/client.js` — add endpoints there, not inline in components.

---

## 2. Mission Control (public dashboard)

**URL:** `https://dixon8303.github.io/ImaginariumOzone/bgf/` — unlisted, `noindex`.

```
Mac (pipeline runs) ──debounced 5s──▶ status/production_status.json (Contents API)
                                              │
docs/bgf/index.html ──pages.yml──▶ GitHub Pages ──fetched client-side──▶ any browser
```

- `backend/services/status_sync.py` commits the status file when
  `GITHUB_SYNC_TOKEN` is set (fine-grained PAT, Contents R/W, this repo only).
  Unset → silent no-op.
- The page fetches the Contents API (fresh) with a raw.githubusercontent fallback
  (~5 min CDN cache) and localStorage as last resort; refreshes every 60 s.
- `docs/bgf/index.html` is intentionally **self-contained** — no build step, no
  external JS. Keep it that way so it can never break the Pages deploy.
- Payload is metadata only. Adding a field means checking it is safe to publish.

---

## 3. Published sites

One workflow, `.github/workflows/pages.yml`, triggered by pushes to `docs/**`,
`site/**`, `eatmedia/**`:

| Source | Deployed to | Site |
|--------|-------------|------|
| `docs/` | `/` | The Genius Index (assessment) |
| `site/` | `/book/` | Book promo — CNAME `blackgeniusfiles.com` |
| `eatmedia/` | `/eatmedia/` | Company site — CNAME `eatmediatv.com` |
| `docs/bgf/` | `/bgf/` | Mission Control (unlisted) |

`site/404.html` is copied to the artifact root; it is the only 404.

---

## 4. HoneyDrip Bot

Live agentic trading via Robinhood's official Trading MCP. Signal generation and risk gating run in Python; Claude Code executes approved signals via the MCP.

### Execution modes

| Mode | `HONEYDRIP_MODE` | Platform | Use |
|------|-----------------|----------|-----|
| Paper | `paper` (default) | Alpaca paper endpoint | Backtesting, methodology validation |
| Live MCP | `live_mcp` | Robinhood Trading MCP | Live agentic execution |

### Running — paper mode
```bash
export APCA_API_KEY_ID=your_paper_key
export APCA_API_SECRET_KEY=your_paper_secret
export HONEYDRIP_ARMED=YES
pip install -r honeydrip_bot/requirements.txt
python -m honeydrip_bot.engine
```

### Running — live MCP mode
```bash
export HONEYDRIP_MODE=live_mcp
export HONEYDRIP_ARMED=YES
export HONEYDRIP_EQUITY_ESTIMATE=<your account equity>
pip install -r honeydrip_bot/requirements.txt
python -m honeydrip_bot.engine
# Engine writes approved signals to honeydrip_bot/pending_signals.json
# Then ask Claude Code (with Robinhood MCP connected) to execute them
# See honeydrip_bot/robinhood_mcp_guide.md for the full playbook
```

### One-time MCP setup (on your local machine)
```bash
claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
# Then: /mcp → select robinhood-trading → authenticate
```

Without `HONEYDRIP_ARMED=YES` the engine aborts immediately in any mode.

---

## 5. Marvel Release Tracker

Watches TMDb for new/changed Marvel Studios releases, syncs a dedicated iCloud
calendar, sends push/SMS. Runs daily at 13:00 UTC via
`.github/workflows/marvel_tracker.yml`. Setup in `marvel_tracker/README.md`.

---

## Credentials

| Variable | Component | Notes |
|----------|-----------|-------|
| `ANTHROPIC_API_KEY` | BGF | **Required.** Everything else is optional. |
| `GITHUB_SYNC_TOKEN` | Mission Control | Fine-grained PAT, Contents R/W, this repo only |
| `ELEVENLABS_API_KEY` | BGF voiceover | Falls back to macOS `say` |
| `VIDIQ_API_KEY` | BGF intelligence | Falls back to model estimates |
| `COMFYUI_BASE_URL` / `OLLAMA_BASE_URL` | BGF | Local services; skipped if down |
| `YOUTUBE_CLIENT_SECRETS` | BGF upload | OAuth client JSON path |
| `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` | HoneyDrip | Paper keys only, never committed |
| `HONEYDRIP_ARMED` | HoneyDrip | `YES` only in a confirmed paper environment |

Copy `backend/.env.example` → `backend/.env` and `honeydrip_bot/.env.example` →
`honeydrip_bot/.env` locally. Both `.env` files are gitignored.

---

## Working in this repo

- **Verify before you claim.** `cd backend && .venv/bin/python -c "import main"` and
  `npx vite build` both pass before any commit touching those trees. The frontend build
  has broken twice from merges — always run it.
- **Keep the four stage lists in sync** (orchestrator `stages`, orchestrator `ROUTING`,
  `status_sync.STAGE_ORDER`, dashboard `STAGES`). Changing the pipeline means changing
  all four plus `BGF_USER_GUIDE.md` and this file. A mismatch is silent: the dashboard
  renders segments that never light up and drops stages it doesn't recognize.
- **Doctrine lives in `BGF_PACING_CONSTITUTION.md` and `BGF_PROMPT_STACK.md`.** Pacing
  numbers, buffers, and Flux specs belong in `config.py` as `BGF_*` constants sourced
  from those docs — never inline in a stage function.
- **The operator is non-technical.** `BGF_USER_GUIDE.md` is the user-facing manual —
  update it whenever behavior the operator sees changes, in plain language, and give
  exact commands rather than describing them.
- **Never commit a secret**, including in an example file or a test fixture.
