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

OPEN_WEBUI_PORT=3000                     # Open WebUI port
OPEN_WEBUI_URL="http://localhost:$OPEN_WEBUI_PORT"
COMFY_URL="http://localhost:$COMFYUI_PORT"

# How Open WebUI is installed on your machine — set ONE of these:
#   "docker"  — started via Docker container named "open-webui"
#   "pip"     — installed via  pip install open-webui  (runs: open-webui serve)
#   "none"    — already running / managed externally (script just opens the tab)
OPEN_WEBUI_MODE="docker"
OPEN_WEBUI_DOCKER_IMAGE="ghcr.io/open-webui/open-webui:main"  # only used first run

CLAUDE_APP="Claude"                      # name shown in /Applications
CHROME_APP="Google Chrome"

OLLAMA_STARTUP_WAIT=3                    # seconds to wait after starting Ollama
WEBUI_STARTUP_TIMEOUT=60                 # max seconds to wait for WebUI to be ready
# ─────────────────────────────────────────────────────────────────────────────

log() { echo "[LaunchAI] $*"; }

# Wait until a TCP port accepts connections (max $2 seconds)
wait_for_port() {
    local port=$1 timeout=$2 elapsed=0
    while ! lsof -iTCP:"$port" -sTCP:LISTEN -t &>/dev/null; do
        if [ "$elapsed" -ge "$timeout" ]; then
            log "WARNING: port $port not ready after ${timeout}s — opening browser anyway."
            return 1
        fi
        sleep 2; elapsed=$((elapsed + 2))
        log "  waiting for port $port … (${elapsed}s)"
    done
    log "  port $port ready."
}

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

# ── 3. Open WebUI ────────────────────────────────────────────────────────────
if lsof -iTCP:"$OPEN_WEBUI_PORT" -sTCP:LISTEN -t &>/dev/null; then
    log "Open WebUI already running on port $OPEN_WEBUI_PORT."
else
    case "$OPEN_WEBUI_MODE" in
        docker)
            if command -v docker &>/dev/null; then
                # Try to restart an existing stopped container first
                if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^open-webui$"; then
                    log "Starting existing open-webui Docker container..."
                    docker start open-webui > /tmp/openwebui.log 2>&1
                else
                    log "Creating open-webui Docker container (first run)..."
                    docker run -d \
                        -p "$OPEN_WEBUI_PORT:8080" \
                        --add-host=host.docker.internal:host-gateway \
                        -v open-webui:/app/backend/data \
                        -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
                        --name open-webui \
                        --restart unless-stopped \
                        "$OPEN_WEBUI_DOCKER_IMAGE" > /tmp/openwebui.log 2>&1
                fi
                log "Open WebUI starting via Docker..."
                wait_for_port "$OPEN_WEBUI_PORT" "$WEBUI_STARTUP_TIMEOUT"
            else
                log "WARNING: Docker not found. Set OPEN_WEBUI_MODE to 'pip' or 'none'."
            fi
            ;;
        pip)
            if command -v open-webui &>/dev/null; then
                log "Starting Open WebUI (pip)..."
                nohup open-webui serve --port "$OPEN_WEBUI_PORT" \
                    > /tmp/openwebui.log 2>&1 &
                wait_for_port "$OPEN_WEBUI_PORT" "$WEBUI_STARTUP_TIMEOUT"
            else
                log "WARNING: open-webui command not found."
                log "         Install it with:  pip install open-webui"
            fi
            ;;
        none)
            log "Open WebUI mode is 'none' — assuming it is managed externally."
            ;;
        *)
            log "WARNING: Unknown OPEN_WEBUI_MODE '$OPEN_WEBUI_MODE'. Use docker, pip, or none."
            ;;
    esac
fi

# ── 4. ComfyUI ────────────────────────────────────────────────────────────────
if lsof -iTCP:"$COMFYUI_PORT" -sTCP:LISTEN -t &>/dev/null; then
    log "ComfyUI already running on port $COMFYUI_PORT."
else
    if [ -d "$COMFYUI_DIR" ]; then
        log "Starting ComfyUI..."
        PYTHON_BIN="$COMFYUI_PYTHON"
        [ ! -x "$PYTHON_BIN" ] && PYTHON_BIN="python3"
        nohup bash -c "cd '$COMFYUI_DIR' && '$PYTHON_BIN' main.py --port $COMFYUI_PORT" \
            > /tmp/comfyui.log 2>&1 &
        log "ComfyUI starting..."
        wait_for_port "$COMFYUI_PORT" 60
    else
        log "WARNING: ComfyUI directory not found at $COMFYUI_DIR — skipping."
        log "         Edit COMFYUI_DIR in launch_ai.sh to fix this."
    fi
fi

# ── 5. Claude desktop app ─────────────────────────────────────────────────────
if ! pgrep -x "Claude" > /dev/null 2>&1; then
    log "Opening Claude..."
    open -a "$CLAUDE_APP" 2>/dev/null || log "WARNING: Claude app not found."
else
    log "Claude already running."
fi

# ── 6. Chrome with Open WebUI + ComfyUI tabs ─────────────────────────────────
log "Opening Chrome tabs..."
open -a "$CHROME_APP" "$OPEN_WEBUI_URL" "$COMFY_URL" 2>/dev/null \
    || log "WARNING: Chrome not found or failed to open."

log "Done."
log "Logs: /tmp/ollama.log | /tmp/openwebui.log | /tmp/comfyui.log"
