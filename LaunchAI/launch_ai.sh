#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# AI Stack Launcher
# Edit the CONFIG section to match your machine before first use.
# ─────────────────────────────────────────────────────────────────────────────

# ── CONFIG ────────────────────────────────────────────────────────────────────
COMFYUI_DIR="$HOME/ComfyUI"              # path to your ComfyUI folder
COMFYUI_PORT=8188                        # ComfyUI default port
COMFYUI_PYTHON="$COMFYUI_DIR/venv/bin/python"  # python inside ComfyUI venv
                                         # fallback: "python3"

OPEN_WEBUI_URL="http://localhost:3000"   # Open WebUI URL (with Qwen2.5 loaded)
COMFY_URL="http://localhost:$COMFYUI_PORT"

CLAUDE_APP="Claude"                      # name shown in /Applications
CHROME_APP="Google Chrome"

OLLAMA_STARTUP_WAIT=3                    # seconds to wait after starting Ollama
COMFY_STARTUP_WAIT=5                     # seconds to wait before opening browser
# ─────────────────────────────────────────────────────────────────────────────

log() { echo "[LaunchAI] $*"; }

# ── 1. Ollama ─────────────────────────────────────────────────────────────────
if pgrep -x "ollama" > /dev/null 2>&1; then
    log "Ollama already running."
else
    log "Starting Ollama..."
    if command -v ollama &>/dev/null; then
        nohup ollama serve > /tmp/ollama.log 2>&1 &
        sleep "$OLLAMA_STARTUP_WAIT"
        log "Ollama started."
    else
        log "WARNING: ollama not found in PATH — skipping."
    fi
fi

# ── 2. Pull Qwen2.5 if not present (non-blocking) ────────────────────────────
if command -v ollama &>/dev/null; then
    if ! ollama list 2>/dev/null | grep -q "qwen2.5"; then
        log "Pulling qwen2.5 model in background (this may take a while)..."
        nohup ollama pull qwen2.5 > /tmp/ollama_pull.log 2>&1 &
    fi
fi

# ── 3. ComfyUI ────────────────────────────────────────────────────────────────
if lsof -iTCP:"$COMFYUI_PORT" -sTCP:LISTEN -t &>/dev/null; then
    log "ComfyUI already running on port $COMFYUI_PORT."
else
    if [ -d "$COMFYUI_DIR" ]; then
        log "Starting ComfyUI..."
        PYTHON_BIN="$COMFYUI_PYTHON"
        [ ! -x "$PYTHON_BIN" ] && PYTHON_BIN="python3"
        nohup bash -c "cd '$COMFYUI_DIR' && '$PYTHON_BIN' main.py --port $COMFYUI_PORT" \
            > /tmp/comfyui.log 2>&1 &
        log "ComfyUI starting (waiting ${COMFY_STARTUP_WAIT}s)..."
        sleep "$COMFY_STARTUP_WAIT"
    else
        log "WARNING: ComfyUI directory not found at $COMFYUI_DIR — skipping."
        log "         Edit COMFYUI_DIR in launch_ai.sh to fix this."
    fi
fi

# ── 4. Claude desktop app ─────────────────────────────────────────────────────
if ! pgrep -x "Claude" > /dev/null 2>&1; then
    log "Opening Claude..."
    open -a "$CLAUDE_APP" 2>/dev/null || log "WARNING: Claude app not found."
else
    log "Claude already running."
fi

# ── 5. Chrome with Open WebUI + ComfyUI tabs ─────────────────────────────────
log "Opening Chrome tabs..."
open -a "$CHROME_APP" "$OPEN_WEBUI_URL" "$COMFY_URL" 2>/dev/null \
    || log "WARNING: Chrome not found or failed to open."

log "Done. Check /tmp/ollama.log and /tmp/comfyui.log for service output."
