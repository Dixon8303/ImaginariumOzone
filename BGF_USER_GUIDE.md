# BGF Production OS — User Guide

**The Black Genius Files · Narrative Production Operating System v1.0**
E.A.T. Media · Boombox Pictures

---

## Table of Contents

1. [First-Time Setup](#1-first-time-setup)
2. [Starting the App](#2-starting-the-app)
3. [The Production Dashboard](#3-the-production-dashboard)
4. [Creating an Episode](#4-creating-an-episode)
5. [Pipeline Monitor — Live Status](#5-pipeline-monitor--live-status)
6. [What Each Stage Does](#6-what-each-stage-does)
7. [Human Gates — When You're Called In](#7-human-gates--when-youre-called-in)
   - [Gate A: Script Review](#gate-a-script-review)
   - [Gate B: Asset Review](#gate-b-asset-review)
   - [Gate C: Video Preview](#gate-c-video-preview)
   - [Gate D: QA Gates P10](#gate-d-qa-gates-p10)
8. [Control Room — Gate Decisions & Audit](#8-control-room--gate-decisions--audit)
9. [Upload Panel](#9-upload-panel)
10. [War Room — Analytics & Decisions](#10-war-room--analytics--decisions)
11. [Discovery Feed — What to Make Next](#11-discovery-feed--what-to-make-next)
12. [Operating Modes Explained](#12-operating-modes-explained)
13. [What the AI Tiers Mean](#13-what-the-ai-tiers-mean)
14. [When Something Fails](#14-when-something-fails)
15. [Frequently Asked Questions](#15-frequently-asked-questions)
16. [Mission Control — Your Dashboard on the Internet](#16-mission-control--your-dashboard-on-the-internet)

---

## 1. First-Time Setup

### Requirements

| Software | Purpose | Install |
|----------|---------|---------|
| Node.js ≥18 | Frontend | `brew install node` |
| Python 3.11+ | Backend | `brew install python` |
| ffmpeg | Video assembly | `brew install ffmpeg` |
| ComfyUI | Image/video generation | Optional — skip if not generating assets |
| Ollama | Free local pre-work | Optional — `brew install ollama` |

### Configuration

1. **Copy the environment file:**
   ```
   cp backend/.env.example backend/.env
   ```

2. **Open `backend/.env` and fill in:**
   ```
   ANTHROPIC_API_KEY=sk-ant-...        ← required — get from console.anthropic.com
   FFMPEG_PATH=/opt/homebrew/bin/ffmpeg ← your ffmpeg path
   OUTPUT_BASE_DIR=/path/to/outputs     ← where videos/assets are saved
   ```

3. **Optional services** (leave blank to disable gracefully):
   ```
   COMFYUI_BASE_URL=http://localhost:8188   ← if ComfyUI is running
   ELEVENLABS_API_KEY=...                    ← premium voiceover (falls back to macOS say)
   OLLAMA_BASE_URL=http://localhost:11434    ← local $0 title/caption drafts
   OLLAMA_MODEL=mistral                      ← any model you've pulled
   VIDIQ_API_KEY=...                         ← real YouTube keyword/CTR data (vidiq.com)
   YOUTUBE_CHANNEL_ID=UC...                  ← your channel, for War Room analytics pull
   ```

   **What vidIQ unlocks when connected:**
   - P1 topic scoring uses *real* search volume + competition instead of AI estimates
   - Title candidates get CTR-predictive scores (visible in Control Room → Title Variants)
   - The G4 predictive gate is primed with the real title score
   - The Discover page shows breakout videos in the BGF content space
   - The War Room can pull live channel metrics with one click

4. **YouTube upload** (optional — required only for `Upload to YouTube`):
   ```
   YOUTUBE_CLIENT_SECRETS=/path/to/client_secrets.json
   ```
   Get credentials from Google Cloud Console → YouTube Data API v3 → OAuth 2.0.

---

## 2. Starting the App

Run one command from the project root:

```bash
./start.sh
```

This automatically:
- Creates a Python virtual environment (first run only)
- Installs all Python dependencies
- Starts the backend API on **http://localhost:8001**
- Starts the frontend on **http://localhost:5173**

Open your browser to **http://localhost:5173**.

Press `Ctrl+C` in the terminal to stop everything.

> **Troubleshooting:** If the backend fails to start, check that `ANTHROPIC_API_KEY` is set in `backend/.env`. The key must begin with `sk-ant-`.

---

## 3. The Production Dashboard

**URL: `http://localhost:5173/`**

The home screen. Every episode you've ever created appears here as a row.

### Reading the dashboard

Each row shows:
- **Colored dot** — pipeline state at a glance
  - Pulsing amber = running right now
  - Solid amber = waiting for your review
  - Green = published
  - Red = something failed
- **Topic** — what you typed when creating the episode
- **Score/100** — Opus 4.8's topic virality/retention score from P1
- **Primary keyword** — the main SEO keyword Opus chose
- **Mode** — ASSISTED / SEMI_AUTO / FULL_AUTO
- **Status badge** — current stage label
- **REVIEW NEEDED** (animated) — pipeline is paused and waiting for you

### Navigation from the dashboard

- **Click any row** — goes directly to whatever requires attention:
  - If running → Pipeline Monitor
  - If at a review gate → the relevant review screen (Script / Assets / Video)
  - If ready to upload → Upload Panel
- **+ New Episode** button (top right) → create a new production
- **War Room →** link → analytics view
- **Discover** (nav bar) → topic ideas and breakout signals ([section 11](#11-discovery-feed--what-to-make-next))
- **× (delete)** — appears on hover, permanently removes the episode and all assets

---

## 4. Creating an Episode

**URL: `http://localhost:5173/new`**

### Step 1 — Write the topic

Be specific. Name real people, institutions, events, and eras. The AI scores better and researches more accurately when the topic is concrete.

**Good examples:**
```
Garrett Morgan and the invention of the automatic traffic signal — 
and how patent records show he was systematically erased from credit

The Freedmen's Bureau banking system 1865–1874: the first Black 
financial infrastructure in the United States

Madam C.J. Walker's manufacturing operation and how she built the 
first Black female-owned factory in the US
```

**Weak examples (too vague):**
```
Black inventors
Civil rights leaders
Slavery history
```

### Step 2 — Add production notes (optional)

Tell the system what to emphasize: era, angle, tone, what to avoid. This goes into the research and script prompts.

```
Focus on the 1920s–1940s. Emphasize the commercial scale — she had 
over 40,000 sales agents. The "lone genius" framing is a distraction; 
frame through her organizational system.
```

### Step 3 — Choose an operating mode

| Mode | What it does | Best for |
|------|-------------|---------|
| **ASSISTED** | Pauses at script, assets, and video review | Your first 5–10 episodes; maximum editorial control |
| **SEMI_AUTO** | Pauses only before upload | Once you trust the script and generation quality |
| **FULL_AUTO** | Runs end-to-end; pauses only before upload | High-volume production; established topics |

> **Recommendation:** Start with ASSISTED until you've approved at least 3 scripts and confirmed the asset quality matches your standards.

### Step 4 — Click "Begin Production"

The system creates the episode in the database and immediately starts the pipeline. You're taken to the Pipeline Monitor automatically.

---

## 5. Pipeline Monitor — Live Status

**URL: `http://localhost:5173/episodes/{id}/pipeline`**

This screen updates in real time via a live connection to the server. You don't need to refresh.

### Reading the stage list

Each row represents one pipeline stage. The small dot on the left shows status:

| Dot | Meaning |
|----|---------|
| Dim gray | Not yet reached |
| Pulsing amber | Running right now |
| Green | Completed |
| Red | Failed |
| Orange | Halted (gate failed) |

The two-letter code on the right side of each row shows **which AI tier is handling that stage**:

| Code | Model | Work |
|------|-------|------|
| **F5** | Fable 5 | Research — reads PDFs, verifies claims |
| **OP** | Opus 4.8 | Ideation, script, outline, all gate decisions |
| **SN** | Sonnet 4.6 | SSML/voice, storyboard, shorts |
| **HK** | Haiku 4.5 | SEO metadata and tags |
| **CUI** | ComfyUI | Local image/video generation |
| **FFM** | ffmpeg | Ken Burns effects, assembly |

### The live connection indicator

Top right: **LIVE** (green) = connected and receiving real-time updates. **OFFLINE** = the connection dropped; refresh the page to reconnect.

### Control Room link

Top right also shows **Control Room →** — click this at any time to see gate decisions, tier routing details, and the full audit log for this episode.

### What happens when it pauses

When a stage finishes and the pipeline hits a human gate, a panel appears at the bottom of the screen. This panel tells you:
- What gate was reached
- What to do next (review link or approve button)

The pipeline will not advance until you take action.

---

## 6. What Each Stage Does

| # | Stage | Model | What it produces | Time |
|---|-------|-------|-----------------|------|
| P1 | **Topic Score + G1/G2** | Opus 4.8 (+ Ollama pre-work) | Editorial gate check, 100-pt score, keyword, title candidates | 30–60s |
| P2 | **Research** | Fable 5 | Deep research brief with per-claim source verification, bibliography | 2–5 min |
| P3 | **Outline** | Opus 4.8 | 6–8 beat structure with curiosity loops, arc notes | 45s |
| P4 | **Script** | Opus 4.8 | Full narration scenes with visual direction per scene | 60–90s |
| P8 | **SEO** | Haiku 4.5 (+ Ollama tags) | YouTube title/description/tags package | 20s |
| P5 | **Voice & SSML** | Sonnet 4.6 | Narration markup for TTS pacing and emphasis | 30s |
| P6 | **Storyboard** | Sonnet 4.6 (+ Ollama shots) | Asset spec per scene with ComfyUI prompts | 45s |
| — | **Generation** | ComfyUI | AI images/videos for each scene | 5–20 min |
| — | **Ken Burns** | ffmpeg | Pan/zoom motion applied to still images | 1–2 min |
| — | **Assembly** | ffmpeg | Full episode assembled with narration, music, transitions | 2–5 min |
| P9 | **Shorts** | Sonnet 4.6 (+ Ollama captions) | YouTube Shorts cut from episode, 9:16 reformat | 2–3 min |
| P10 | **QA Gates G3–G5** | Opus 4.8 | Hook diagnostic, predictive performance, monetization/ethics | 60s |

---

## 7. Human Gates — When You're Called In

In ASSISTED mode, the pipeline pauses three times before QA and once after. Each pause presents you with a specific review task.

---

### Gate A: Script Review

**Reached after: P4 Script**
**Status shown:** "Script Review" (amber, pulsing REVIEW NEEDED)

The pipeline has generated the full narration script. You decide if the writing is right before any assets are made.

**How to access:** Click the episode on the dashboard → taken directly to Script Editor.

**URL:** `/episodes/{id}/script`

#### What you'll see

Scene cards, one per episode beat. Each card has:
- **Scene number** and duration estimate
- **Narration text** — what the narrator says (editable)
- **Visual direction** — what should appear on screen (not editable here)
- Editable **episode title** at the top

#### What to do

1. **Read every scene.** Check for: historical accuracy, narrative flow, hook strength in scene 1, the curiosity loop resolution in the final scene.
2. **Edit narration** directly in the text areas if needed. Click outside the box to save.
3. **Edit the title** by clicking the title at the top.
4. When satisfied: click **"Approve & Generate"** → pipeline resumes from the SEO stage and continues through asset generation.

> **You cannot un-approve.** If you realize after approving that a scene needs a rewrite, navigate back to `/episodes/{id}/script`, make edits, and the changes will be picked up if you re-run the relevant stages.

---

### Gate B: Asset Review

**Reached after: Generation**
**Status shown:** "Asset Review" (amber, pulsing REVIEW NEEDED)

ComfyUI has generated images/videos for each scene. You approve or reject them before Ken Burns effects and assembly.

**How to access:** Click the episode on the dashboard → taken directly to Asset Gallery.

**URL:** `/episodes/{id}/assets`

#### What you'll see

A grid of generated assets. Each card shows:
- Scene number and asset type (ai_image / ai_video)
- The asset itself (images shown directly; videos play on hover)
- Status indicator (done / failed / approved / rejected)
- Three action buttons: **Approve**, **Reject**, **Regenerate**

The gallery auto-refreshes every 8 seconds while generation is in progress.

#### What to do

For each asset:
- **Approve** — marks it for assembly
- **Reject** — excludes it from assembly (that scene may be skipped or use a placeholder)
- **Regenerate** — queues a new generation attempt with a different random seed

When you're satisfied with the set (not all assets need to be approved — the assembly stage handles gaps gracefully):

Click **"Proceed to Assembly"** → pipeline resumes from the Ken Burns stage.

> **Tip:** Focus on scene 1 and the final scene — they carry the most visual weight. Interior scenes with minor quality issues will be less noticeable in the final cut.

---

### Gate C: Video Preview

**Reached after: Assembly**
**Status shown:** "Video Review" (amber, pulsing REVIEW NEEDED)

The full episode has been assembled. You watch it and decide whether to continue to Shorts and upload.

**How to access:** Click the episode on the dashboard → taken directly to Video Preview.

**URL:** `/episodes/{id}/preview`

#### What you'll see

- **Video player** — the full assembled episode at 1920×1080
- **Thumbnail** extracted from the video (first meaningful frame)
- **SEO preview** — title, description, tags as they'll appear on YouTube
- **Approve** button

#### What to do

1. Watch the full episode, or scrub through key sections.
2. Check: narration pacing, visual-audio sync, transitions, opening hook, closing.
3. Check the SEO panel — edit title/description/tags in the Upload Panel if needed.
4. Click **"Approve"** → pipeline continues to Shorts extraction.

> If you want to re-cut or re-assemble, navigate back to the Pipeline Monitor and use "Retry from Failed Stage" or contact the developer to re-run specific stages.

---

### Gate D: QA Gates P10

**Reached after: Shorts**
**Status shown:** "QA Gates Complete — Operator Review"

Opus 4.8 has run three structured quality gates on the finished episode. You review the scores before upload.

**How to access:** Click "View Gates" in the gate panel on the Pipeline Monitor, or navigate to the Control Room.

**URL:** `/episodes/{id}/control-room`

#### What you'll see

G3, G4, and G5 decisions with scores and Opus's rationale. See the [Control Room section](#8-control-room--gate-decisions--audit) for full detail.

If all three gates passed, a **Resume** button appears on the Pipeline Monitor → advances to the Upload Panel.

If any gate failed, the pipeline is in HARD HALT. See [When Something Fails](#14-when-something-fails).

---

## 8. Control Room — Gate Decisions & Audit

**URL:** `/episodes/{id}/control-room`

Accessible at any time from the "Control Room →" link on the Pipeline Monitor, or from the nav bar.

### Tabs

#### Gates G1–G5

One card per gate. Each shows:

| Field | Meaning |
|-------|---------|
| Gate ID | G1 through G5 |
| Gate name | What it evaluates |
| Score | Numeric score where applicable (e.g. G3: /50, G5: /50) |
| PASS / FAIL badge | Green or red |
| Rationale | Opus's reasoning in prose |
| Remediation alert | Red box appears if the gate failed and a remediation task was created |

**G1 – Editorial Perspective** (binary PASS/FAIL)
- Does the topic name a real institution or documented individual?
- Does it frame through systems, not exceptional-individual narrative?
- Is it reconstructable from primary sources?
- Does it extend the BGF thesis?

**G2 – 100-pt Score** (PASS ≥70 / REVISE 60–69 / KILL <60)
- Virality (30), Retention Potential (20), Emotional Impact (20), Monetization Safety (15), Brand Alignment (15)

**G3 – Hook Diagnostic** (/50, need ≥28)
- B1 Cold open hook (/15) — **auto-fail if ≤4**
- B2 First question posed (/10)
- B3 Stakes established (/10)
- B4 Visual hook clarity (/15)

**G4 – Predictive Performance** (PASS/FAIL)
- CTR likelihood vs. 6% threshold
- Retention likelihood vs. 30%/70% benchmarks

**G5 – Monetization + Ethics** (/50, need ≥36)
- Advertiser safety score
- Ethics flags (sensitive content, historical accuracy risk, exploitative framing)

#### Operator Override

If a gate failed and you disagree with the AI's decision (or have made edits that resolve the issue), you can override it:

1. Click **"Operator Override →"** under the failed gate
2. Write your rationale (required — this is logged in the audit trail)
3. Click **"Override → Pass"**
4. Return to the Pipeline Monitor and resume

This is an **operator power** — use it when you have editorial knowledge the AI lacked, not to skip real quality problems.

#### Stage Runs tab

A table of every stage execution, showing:
- Which stage ran
- Which model tier handled it (Fable/Opus/Sonnet/Haiku)
- Autonomy mode (AUTO / AUTO_REVIEW / CHECKPOINT)
- Status (COMPLETED / FAILED / RUNNING)
- Duration in seconds

Useful for diagnosing performance bottlenecks or understanding costs.

#### Title Variants tab

All title candidates generated during the production:
- **Ollama pool** — 8 candidates drafted locally by the Ollama model (free, runs before Opus)
- **Opus variants** — 3 refined titles scored by Opus 4.8

The selected title (used in SEO and upload) is highlighted.

#### Mutation Log tab

Every database write made during this episode's production — what table was written, what operation, which stage triggered it, and when. Full audit trail. Most useful for debugging or compliance review.

---

## 9. Upload Panel

**URL:** `/episodes/{id}/upload`

**How to reach it:** Dashboard click when status is "Ready to Upload", or Pipeline Monitor after all gates pass.

### What you'll see

- **Editable title** — pre-filled from the SEO package; override if needed
- **Editable description** — pre-filled with the YouTube description
- **Editable tags** — comma-separated tag list
- **Privacy selector** — Private / Unlisted / Public
  - **Start with Private** for your first few uploads to check quality on YouTube before public release
- **Upload button**

### Upload flow

1. Review and edit title/description/tags
2. Select privacy level (default: Private)
3. Click **"Upload to YouTube"**
4. A live progress bar appears — do not close the tab while uploading
5. When complete: a success state appears with the YouTube URL

### First YouTube upload — OAuth

The first time you upload from a machine, a browser window opens for Google OAuth authorization. Sign in with the Google account that owns the channel. The token is saved locally and reused for subsequent uploads.

---

## 10. War Room — Analytics & Decisions

**URL:** `/war-room`

The performance intelligence layer. Use this after your episode has been live for 24–48 hours.

### 4 metric cards (top)

| Metric | Green threshold | What it means |
|--------|----------------|--------------|
| CTR · Avg | ≥6% | Average click-through rate across all episodes |
| Retention · Avg | ≥35% | Average audience retention percentage |
| Session Depth | ≥1.5 | How many BGF videos viewers watch per session |
| Episodes Total | — | Total in the system |

### Episode table

Lists all episodes with live CTR and retention data. Click **"Metrics"** on any row to open the metrics input panel for that episode.

### Logging performance metrics

**Fastest path — Pull from vidIQ:** If `VIDIQ_API_KEY` is set, click the violet **"⇣ Pull from vidIQ"** button at the top of the metrics panel. It fetches your live channel CTR, retention, and average watch time and fills the form automatically. Review the numbers, add anything missing (Shorts views, session depth), then run the decision engine.

**Manual path:** After an episode has been live for 24–48 hours, pull the numbers from YouTube Studio and enter them:

| Field | Where to find it in YouTube Studio |
|-------|-----------------------------------|
| CTR 24h % | Analytics → Reach → CTR (filter: last 24 hours) |
| CTR 48h % | Analytics → Reach → CTR (filter: last 48 hours) |
| Retention 30% mark | Analytics → Engagement → Audience retention curve |
| Retention 70% mark | Analytics → Engagement → Audience retention curve |
| Avg Watch Time (sec) | Analytics → Overview → Average view duration |
| Session Depth | Analytics → Reach → Traffic source (calculate: BGF views / unique viewers) |
| Shorts Views (best) | Analytics → Content → Shorts → Views |

Enter the numbers and click **"Run Decision Engine"**.

### Decision Engine output

The engine applies the NPOS §III·02 intervention logic and returns prioritized actions:

| Priority color | Meaning | Act within |
|---------------|---------|-----------|
| Red — IMMEDIATE | Critical performance failure, major structural issue | 24 hours |
| Amber — STRUCTURAL | Pattern-level problem needing a production change | This week |
| Green — MONITOR | Within acceptable range; continue tracking | No action needed |

Examples of what it might surface:
- "CTR 48h at 4.2% — below 6% threshold. Action: A/B test thumbnail concept B, deploy to 30% of traffic"
- "Retention drops below 30% at the 4:20 mark — investigate the scene 3 transition"
- "Shorts at 18k views — velocity is strong. Action: Push to 3 more platform clips from the B-roll"

---

## 11. Discovery Feed — What to Make Next

**URL:** `/discover` (also "Discover" in the nav bar)

The topic-sourcing layer. Use it when you're deciding what to produce next — before you ever open the New Episode form.

### Topic Candidates (top section)

Six episode ideas generated fresh on every visit, shaped by the BGF editorial doctrine:
- Each names a **real institution or documented individual** (never an archetype)
- Each frames through **systems**, not lone-genius narrative
- Each is **reconstructable from primary sources** — so it can survive the G1 gate

Every candidate card shows the topic, a one-sentence hook, the era, and a suggested primary keyword.

**Click "Produce →"** on any candidate — you're taken to the New Episode form with the topic pre-filled. Add production notes, pick a mode, and begin.

> These candidates always work — they only need your `ANTHROPIC_API_KEY`. They're generated by Haiku (the fast, cheap tier) so browsing the feed costs almost nothing.

### Breakout Signals (bottom section)

*Requires `VIDIQ_API_KEY`.*

A table of **outlier videos** — videos from small channels that dramatically over-performed on BGF-adjacent topics ("black history documentary", "black wall street", "freedmen's bureau", and similar seed queries).

| Column | What it tells you |
|--------|------------------|
| Video | The breakout video's title — study what framing worked |
| Channel | Who made it |
| Views | Total views |
| Subs | The channel's subscriber count |
| Multiplier | Views ÷ typical performance — **≥10× (green) means proven audience demand** |

**Why outliers matter more than trending:** A big channel getting big views proves nothing — that's their baseline. A 2,000-subscriber channel getting 400,000 views on a Freedmen's Bureau video proves *the topic itself* pulls an audience. That's the signal to produce your own, better-researched version.

**Workflow:** Scan the multiplier column for green entries → read those titles for framing cues → find (or write) a matching topic candidate → Produce.

---

## 12. Operating Modes Explained

| Mode | Pauses at | Good for |
|------|-----------|---------|
| **ASSISTED** | P4 Script → P6 Generation → Assembly → P10 QA | Full editorial control. Every piece reviewed before the next step consumes compute. |
| **SEMI_AUTO** | Assembly → P10 QA | Trust the script and generation; review only the finished video before upload. |
| **FULL_AUTO** | P10 QA only | Maximum throughput. The AI writes, generates, and assembles. You review gates and approve before publish. |

**You can't change mode mid-pipeline.** If you want to switch modes for an episode already running, delete it and recreate it with the new mode.

Gate G1/G2 (topic editorial check + score) always runs regardless of mode — a KILL decision (<60/100) always halts the pipeline. This is not overrideable from the UI in the normal flow; use the Control Room operator override if you're running a deliberate experiment.

---

## 13. What the AI Tiers Mean

The orchestrator routes each task to the cheapest model that can do it correctly. You don't need to manage this — it's automatic. But understanding the tiers helps you set expectations:

### Fable 5 — Research & Evidence

Used for: **P2 Research** only.

Fable 5 has a 1 million token context window and can read PDFs natively. It's the only model that can handle a full Freedmen's Bureau archive or a congressional record as a single context. It also runs multi-hour autonomous tasks — if research takes 5 minutes, that's normal. It verifies each factual claim against sources before returning the brief.

**Expect:** Very long completion time (2–8 min), very high factual density in the research output.

### Opus 4.8 — Judgment & Script

Used for: **P1 ideation + G1/G2 gates, P3 outline, P4 script, P10 gates G3–G5**.

Opus is the editorial spine. Every decision that could affect the channel's voice, monetization, or historical integrity goes through Opus. The gate evaluations (G1–G5) are Opus's structured judgment calls — they're not heuristics, they're deliberate evaluation prompts.

**Expect:** 30–90 second completion times, high-quality narrative writing, detailed gate rationales.

### Sonnet 4.6 — Structured Transforms

Used for: **P5 SSML, P6 Storyboard, P9 Shorts**.

Sonnet handles well-defined transforms with clear rules — converting narration text to SSML markup, turning script beats into ComfyUI visual prompts, cutting the episode into Shorts specs. It has enough judgment for rule-bound work but doesn't carry the cost of Opus.

**Expect:** Fast (20–45s), reliable structured output.

### Haiku 4.5 — SEO & Volume

Used for: **P8 SEO metadata**.

Haiku handles high-volume, low-judgment work. SEO tags, keyword expansion, metadata packaging — these are pattern-matching tasks where speed and cost matter more than nuanced reasoning.

**Expect:** Very fast (<20s), competent tag generation, may need occasional title cleanup.

### Ollama — Local, Free, Pre-work

Used for: **Candidate title generation (before Opus P1), shot row drafts (before Sonnet P6), caption drafts (P9), SEO tag pools (P8)**.

Ollama runs on your machine with no API cost. It generates rough candidate pools that the Claude models then refine and score. If Ollama isn't running, these pre-work steps are simply skipped — the pipeline continues without them, relying solely on the Claude tier.

**To activate Ollama:**
```bash
# Install
brew install ollama

# Pull a model (first time only)
ollama pull mistral

# Ollama runs automatically in the background after install
```

---

## 14. When Something Fails

### Regular stage failure (red dot)

A stage threw an error — API timeout, ComfyUI offline, ffmpeg crash, etc.

**On the Pipeline Monitor:** A red "Pipeline Failed" panel appears at the bottom with the error message.

**What to do:**
1. Read the error message
2. Fix the underlying issue (restart ComfyUI, check the API key, etc.)
3. Click **"Retry from Failed Stage"** — resumes from exactly where it failed

### HARD HALT (orange dot — Gate Failed)

A G1, G2, G3, G4, or G5 gate returned FAIL. This is not an error — it's the quality control system working.

**On the Pipeline Monitor:** An orange "Pipeline Halted — Gate Failed" panel appears. Click **"View Gate Details"** to go to the Control Room.

**What to do in the Control Room:**
1. Read the gate's rationale carefully
2. Determine if the failure is:
   - **Legitimate** — the episode genuinely has the problem Opus flagged. Fix the root cause (rewrite the script, choose a different topic angle).
   - **Contestable** — you have editorial knowledge that overrides the flag (e.g. you know the source material, the topic is safe but Opus flagged it due to surface keywords).
3. If contestable:
   - Click **"Operator Override →"** on the failed gate
   - Write a clear rationale (this goes in the permanent audit log)
   - Click **"Override → Pass"**
   - Return to Pipeline Monitor → Resume

**Remediation task:** A red box in the gate card describes what needs to be fixed before the pipeline is safe to continue. This is advisory — operator override bypasses it.

### G2 KILL (<60/100)

The topic scored below 60. The system decided the episode isn't worth producing.

**Options:**
1. **Delete the episode** and create a new one with a refined topic angle (recommended)
2. **Override the gate** with rationale — useful if you're running a deliberate experiment or the topic is strategically necessary despite low virality score

---

## 15. Frequently Asked Questions

**Q: How long does a full pipeline take?**

End-to-end (FULL_AUTO, assuming ComfyUI is running and responsive):
- Topic → Script: ~5–8 minutes (Opus on P1/P3/P4, Fable on P2)
- Generation (8 scenes): 20–40 minutes on M1 Max 64GB
- Assembly + Shorts: ~5 minutes
- Total with gates: ~35–55 minutes per episode

**Q: Can I run multiple episodes at once?**

Yes. Create multiple episodes and they'll queue. The backend handles concurrent pipeline runs. Note that ComfyUI asset generation is limited to 2 concurrent jobs (to stay within M1 Max memory limits) — episodes will queue behind each other at the generation stage.

**Q: What if ComfyUI isn't running?**

The generation stage will fail. The pipeline halts. You can:
- Start ComfyUI, then retry from the generation stage
- Skip generation by resuming from `ken_burns` with no approved assets (the assembly will use placeholders or skip affected scenes)

**Q: Can I edit the script after approving it?**

Yes — navigate to `/episodes/{id}/script` at any time. Edits are saved in the database. However, if generation has already started, the visual assets won't reflect script changes. You'd need to reject and regenerate affected assets.

**Q: What does "Ollama not running" mean in practice?**

The title candidate pool will be empty (Opus still generates 3 title variants on its own). Shot row drafts won't be pre-populated (Sonnet generates storyboard specs from scratch). Caption drafts won't be pre-generated. Everything still works — you just lose the $0 pre-work layer that enriches Opus/Sonnet's input.

**Q: How do I change the voice?**

Without ElevenLabs: the macOS `say` command is used. You can change the voice by editing `backend/ffmpeg/assembler.py` → the `generate_narration` function → add `-v VoiceName` to the `say` command. Available voices: run `say -v ?` in Terminal.

With ElevenLabs: set `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` in `.env`. The voice_ssml stage will use the ElevenLabs API automatically.

**Q: Where are the output files?**

All outputs are in `OUTPUT_BASE_DIR/{episode_id}/`:
```
{episode_id}/
  research.json       ← Fable research brief
  outline.json        ← Opus outline + beats
  script.json         ← full scene-by-scene script
  seo.json            ← YouTube metadata package
  voice_ssml.txt      ← SSML-marked narration
  asset_plan.json     ← ComfyUI prompt specs
  assets/             ← generated images/videos
  ken_burns/          ← pan/zoom clips
  audio/              ← narration MP3s per scene
  final/
    episode.mp4       ← assembled episode (1920×1080)
    thumbnail.jpg     ← extracted thumbnail
  shorts/             ← 9:16 Shorts clips
```

**Q: What's the Circle of Morality?**

A separate feature from an earlier build — accessible at `/circle` in the nav. It's preserved as-is alongside the Production OS.

**Q: How do I know which model actually ran for a stage?**

Two places:
1. **Pipeline Monitor** — the two-letter tier code (F5 / OP / SN / HK) appears on each stage row after it runs
2. **Control Room → Stage Runs tab** — full table with exact model ID, autonomy mode, and duration for every stage

---


---

## 16. Mission Control — Your Dashboard on the Internet

**URL:** `https://dixon8303.github.io/ImaginariumOzone/bgf/`

A read-only mirror of the production floor you can open from **any device, anywhere** — phone, another computer, anywhere with a browser. It shows every episode's stage-by-stage progress, gate verdicts, and topic scores, plus the pipeline map and recent build activity.

The page is **unlisted**: search engines are told not to index it, and it's linked from nowhere public. Anyone with the exact address could view it, but it contains only production progress — never scripts, research, or keys.

### One-time setup (~5 minutes)

The dashboard gets its data from your Mac. Whenever the pipeline advances, the app publishes a small status file to GitHub. To allow that, it needs a GitHub token — a kind of app password.

**Run the setup helper. It does everything except the part only you can do:**

```bash
cd ~/Documents/ImaginariumOzone
./setup-sync.sh
```

It prints the exact link and settings for creating the token, waits while you make it, then checks the token, saves it in the right place, and runs a live test so you know it worked before you walk away.

**Creating the token** (the script shows this too). Open
**https://github.com/settings/personal-access-tokens/new** while signed in to GitHub, and fill in:

| Field | Value |
|-------|-------|
| Token name | `bgf-sync` |
| Expiration | 1 year |
| Repository access | **Only select repositories** → `ImaginariumOzone` |
| Permissions → Repository permissions → **Contents** | **Read and write** |

Leave every other permission on "No access." Click **Generate token** at the bottom, copy what it shows you (it starts with `github_pat_` and is shown only once), and paste it into the script when it asks. Your typing stays hidden — that's normal.

> **Why "Read and write" matters:** with Contents set to "Read" only, everything *appears* to work but the dashboard never updates, with no error anywhere. The script catches this specific mistake and tells you, rather than letting you discover it days later.

That's it. From then on every stage completion, gate decision, and status change syncs to the dashboard within seconds. Without a token the app runs exactly as before — the dashboard just shows its last-known state.

**If you'd rather do it by hand:** open `backend/.env`, add the line `GITHUB_SYNC_TOKEN=github_pat_...`, save, and restart the app with `./start.sh`.

**Keeping the token safe:** it lives only in `backend/.env` on your Mac, which is excluded from GitHub so it can never be uploaded by accident. Never paste it into a chat, an email, or a website. If it's ever exposed, delete it at **github.com → Settings → Developer settings → Fine-grained tokens → `bgf-sync` → Delete**, then run `./setup-sync.sh` again with a fresh one.

### Reading the sync light

| Chip color | Meaning |
|-----------|---------|
| **Green (pulsing)** | Studio live — synced within the last 10 minutes |
| **Amber** | Last sync within 24 hours |
| **Gray** | Studio offline — showing the last state it reported |

### Reading the stage bar

Each episode card has a 12-segment bar, one segment per pipeline stage (hover or tap a segment for its name and AI tier):

| Look | Meaning |
|------|---------|
| Solid green | Stage complete |
| Pulsing amber | Running right now |
| Dim outline | Not reached yet |
| Orange with ❚❚ | Halted at a gate — needs your decision in the app |
| Red striped | Failed — check the Pipeline Monitor on the Mac |

Gate chips below the bar show G1–G5 verdicts (✓ pass / ✕ fail) with scores where applicable.

> **Remember:** Mission Control is a mirror, not a remote control. To approve gates, review scripts, or restart stages, use the app on the Mac.

---

*BGF Production OS · v1.0 · E.A.T. Media · Boombox Pictures*
*Truth · Tension · Transmission · Transformation*
