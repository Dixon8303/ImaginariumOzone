# LaunchAI

One Desktop icon that starts your whole BGF Production OS setup on the Mac.

## What one click does

1. Starts **Ollama** — the Ollama app, or `ollama serve` if you installed it with Homebrew
2. Starts **ComfyUI**
3. Starts the **BGF Production OS** by running the project's own `start.sh` (backend on :8001, dashboard on :5173)
4. Opens the **Claude** app, unless it is already open
5. Opens **Chrome** with two tabs: the BGF dashboard and ComfyUI

Anything already running is left alone. A notification tells you when everything is up, or what is
missing and how to fix it.

## Install

Paste this into Terminal. It downloads only the four files the installer needs:

```bash
mkdir -p ~/launchai-install/LaunchAI && cd ~/launchai-install/LaunchAI
for f in install.sh launchai.sh config.example.sh LaunchAI.icns; do
  curl -fsSLO "https://raw.githubusercontent.com/Dixon8303/ImaginariumOzone/main/LaunchAI/$f"
done
bash install.sh
```

`LaunchAI.app` appears on your Desktop and replaces any older one. The installer finds your real BGF
folder by itself (the one that has `backend/.env`) and keeps your ComfyUI settings from the old launcher.
Run the same commands again to update — your settings are kept.

The first time you click it, macOS may ask whether LaunchAI can read your Documents folder and send
notifications. Click **Allow**.

## Everyday use

| | |
|---|---|
| Start | Click **LaunchAI** on the Desktop |
| Stop | `~/.launchai/launchai stop` — stops only what LaunchAI started; your Ollama, Claude and Docker apps stay open |
| Change settings | `open -e ~/.launchai/config.sh` — takes effect on the next click, nothing to rebuild |
| Remove | Drag **LaunchAI** to the Trash, then `rm -rf ~/.launchai` |

## If something doesn't work

Run this, then paste the result to Claude:

```bash
~/.launchai/launchai diagnose | pbcopy
```

It reports which folders and tools were found and which services answer, plus the last lines of each
log. It never prints your API keys. The logs live in `~/Library/Logs/LaunchAI/`.

| You see | Cause and fix |
|---|---|
| "backend/.env is missing" or "ANTHROPIC_API_KEY is empty" | BGF isn't configured yet — see `BGF_USER_GUIDE.md` §1 |
| "Can't read the BGF folder" | macOS blocked access: System Settings → Privacy & Security → Files and Folders → turn LaunchAI on |
| "Ollama model 'mistral' isn't installed" | `ollama pull mistral` (BGF skips its free pre-work steps without it) |
| "ComfyUI not found" | Put the folder's path in `COMFYUI_DIR` in `config.sh` |
| No notifications appear | System Settings → Notifications → Script Editor → allow |

## Open WebUI + Qwen (optional)

The BGF Production OS does not use Open WebUI, so it is **off** by default. To get it back as a third
Chrome tab, add this to `~/.launchai/config.sh`:

```bash
START_OPEN_WEBUI="yes"
```

LaunchAI then starts Docker if needed, starts (or reuses) your `open-webui` container, loads Qwen2.5
into memory and opens Open WebUI with that model already selected. If Qwen isn't installed it tells
you the `ollama pull` command; set `AUTO_PULL_CHAT_MODEL="yes"` to have it download automatically.

## For maintainers

| File | What it is |
|---|---|
| `launchai.sh` | The launcher. The Desktop app is a copy of it; `stop` and `diagnose` are sub-commands |
| `install.sh` | Builds the app, finds your folders, carries settings over from an older LaunchAI |
| `config.example.sh` | Template for `~/.launchai/config.sh` — settings live outside the repo and survive updates |
| `make_icon.py` | Draws `LaunchAI.png` and `LaunchAI.icns` in E.A.T. Media blue (needs Pillow and the Inter font). `--text AI` gives the earlier AI version. The Mac never runs it |
| `tests/run_tests.sh` | `bash LaunchAI/tests/run_tests.sh` — runs both scripts against stand-ins for `open`, `docker`, `ollama`, … |

- **Why it keeps your Terminal's PATH.** An app started from Finder gets a bare `PATH`, so `ollama`,
  `docker` and `node` were "not found". `install.sh` saves the PATH your Terminal has and the launcher uses it.
- **Components stay independent.** LaunchAI only runs each tool's normal start command (`start.sh`,
  ComfyUI's `main.py`, `open -a`). It never edits, imports or reconfigures another component.
- **Secrets.** It only checks that `ANTHROPIC_API_KEY` is non-empty and reads `OLLAMA_MODEL`; it never
  prints `backend/.env`, and `diagnose` hides any log line that looks like a key.
- **Targets the macOS system bash (3.2)** — no associative arrays, `mapfile` or `${var,,}`.
- Run the tests and `shellcheck LaunchAI/*.sh LaunchAI/tests/run_tests.sh` before committing a change.
