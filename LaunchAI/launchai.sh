#!/bin/bash
# LaunchAI — one click brings up the BGF Production OS stack on this Mac.
#
#   launchai.sh            start everything and open Chrome   (what the Desktop app runs)
#   launchai.sh stop       stop what LaunchAI started
#   launchai.sh diagnose   print a health report you can paste to Claude
#
# Starts   Ollama · ComfyUI · BGF Production OS (through its own start.sh) · the Claude app
# Opens    the BGF dashboard and ComfyUI in Chrome
# Extra    Open WebUI with a local Qwen model — off by default (START_OPEN_WEBUI="yes")
#
# Your settings live in ~/.launchai/config.sh; anything not set there uses the defaults
# below. install.sh copies this file into LaunchAI.app and into ~/.launchai/launchai.
# Written for the bash 3.2 that ships with macOS.

VERSION="2.0"

# ── Defaults ──────────────────────────────────────────────────────────────────
BGF_DIR=""                              # the folder that holds start.sh (install.sh finds it)
START_BGF="yes"
BGF_BACKEND_PORT=8001
BGF_FRONTEND_PORT=5173

START_OLLAMA="yes"
OLLAMA_PORT=11434

START_COMFYUI="yes"
COMFYUI_DIR="$HOME/ComfyUI"
COMFYUI_PYTHON=""                       # blank = <COMFYUI_DIR>/venv/bin/python, else /usr/bin/python3
COMFYUI_PORT=8188
COMFYUI_ARGS=""                         # extra flags for ComfyUI, e.g. "--force-fp16"

START_CLAUDE="yes"
CLAUDE_APP="Claude"
CHROME_APP="Google Chrome"

# Optional extra: Open WebUI chat with a local Qwen model. The BGF Production OS does not use it.
START_OPEN_WEBUI="no"
OPEN_WEBUI_PORT=3000
OPEN_WEBUI_MODE="auto"                  # auto | docker | pip
OPEN_WEBUI_CONTAINER="open-webui"
OPEN_WEBUI_IMAGE="ghcr.io/open-webui/open-webui:main"
CHAT_MODEL="qwen2.5"
CHAT_MODEL_KEEP_ALIVE="30m"             # how long Ollama keeps it in memory after its last use
PRELOAD_CHAT_MODEL="yes"
AUTO_PULL_CHAT_MODEL="no"               # "yes" downloads it when missing (several GB)

TERMINAL_PATH=""                        # your Terminal's PATH, captured by install.sh
APP_DIRS="/Applications:$HOME/Applications"
WAIT_OLLAMA=45; WAIT_COMFYUI=90; WAIT_BGF=150; WAIT_DOCKER=120; WAIT_OPEN_WEBUI=180
POLL=2                                  # seconds between readiness checks

LAUNCHAI_HOME="${LAUNCHAI_HOME:-$HOME/.launchai}"
LOG_DIR="${LAUNCHAI_LOG_DIR:-$HOME/Library/Logs/LaunchAI}"
RUN_DIR="$LAUNCHAI_HOME/run"
LOG="$LOG_DIR/launchai.log"
mkdir -p "$LOG_DIR" "$RUN_DIR" 2>/dev/null

VERBOSE=""; [ -t 2 ] && VERBOSE=1       # echo progress when run from Terminal
log() {
    local line
    line="$(date '+%H:%M:%S')  $*"
    printf '%s\n' "$line" >>"$LOG"
    [ -n "$VERBOSE" ] && printf '%s\n' "$line" >&2
    return 0
}

# env.sh is written by install.sh (detected folders, Terminal PATH); config.sh is yours and wins.
for f in "$LAUNCHAI_HOME/env.sh" "$LAUNCHAI_HOME/config.sh"; do
    # shellcheck disable=SC1090
    [ -f "$f" ] && { . "$f" || log "WARNING: could not read $f"; }
done
[ -n "$COMFYUI_PYTHON" ] || COMFYUI_PYTHON="$COMFYUI_DIR/venv/bin/python"

# A Finder-launched app gets a bare PATH, so Homebrew tools (ollama, docker, node) are not found.
# Use the Terminal's PATH, keep the system dirs, and add the usual install locations last.
export PATH="${TERMINAL_PATH:+$TERMINAL_PATH:}$PATH:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$HOME/.docker/bin:$HOME/.orbstack/bin:/Applications/Docker.app/Contents/Resources/bin"
export LANG="${LANG:-en_US.UTF-8}"

# ── helpers ───────────────────────────────────────────────────────────────────
PROBLEMS=""
problem() { log "PROBLEM: $*"; PROBLEMS="${PROBLEMS:+$PROBLEMS · }$*"; }

notify() {
    osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title "LaunchAI"' \
        -e 'end run' "$1" >/dev/null 2>&1 || true
}

http_ok()  { curl -fsS --max-time 3 -o /dev/null "$1" >/dev/null 2>&1; }
http_has() { curl -fsS --max-time 3 "$1" 2>/dev/null | grep -q "$2"; }

app_installed() {
    local d IFS=:
    for d in $APP_DIRS; do [ -d "$d/$1.app" ] && return 0; done
    return 1
}

trim_log() {   # trim_log <file> <max bytes> — moves an oversized log aside
    [ -f "$1" ] && [ "$(wc -c <"$1" | tr -d ' ')" -gt "$2" ] && mv -f "$1" "$1.old"
    return 0
}

pid_alive() {   # false for a missing pid, a dead process, and one that has exited but not been reaped (zombie)
    local pid
    pid=$(cat "$1" 2>/dev/null)
    { [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; } || return 1
    case "$(ps -p "$pid" -o stat= 2>/dev/null)" in Z*) return 1 ;; esac
    return 0
}

# wait_for <label> <seconds> <check-function> [pidfile]   — gives up early if the pidfile's process dies
wait_for() {
    local label=$1 limit=$2 check=$3 pidfile=${4:-} waited=0
    until "$check"; do
        if [ -n "$pidfile" ] && [ -f "$pidfile" ] && ! pid_alive "$pidfile"; then
            log "$label: its process exited before it was ready"
            return 1
        fi
        if [ "$waited" -ge "$limit" ]; then log "$label: not ready after ${limit}s"; return 1; fi
        sleep "$POLL"; waited=$((waited + POLL))
        if [ $((waited % 20)) -eq 0 ]; then log "$label: still waiting (${waited}s)"; fi
    done
    log "$label: ready"
}

# ── readiness checks ──────────────────────────────────────────────────────────
ollama_ok() { http_ok "http://localhost:$OLLAMA_PORT/api/version"; }
comfy_ok()  { http_ok "http://localhost:$COMFYUI_PORT/system_stats"; }
bgf_ok()    { http_has "http://localhost:$BGF_BACKEND_PORT/api/health" '"ok"' && http_ok "http://localhost:$BGF_FRONTEND_PORT/"; }
webui_ok()  { http_has "http://localhost:$OPEN_WEBUI_PORT/health" '"status"'; }
docker_ok() { docker info >/dev/null 2>&1; }

# ── Ollama ────────────────────────────────────────────────────────────────────
start_ollama() {
    [ "$START_OLLAMA" = "yes" ] || return 0
    if ollama_ok; then log "Ollama: already running"; OLLAMA_WAIT=1; return 0; fi
    if app_installed Ollama; then
        log "Ollama: opening Ollama.app"
        open -g -a Ollama 2>>"$LOG"
    elif command -v ollama >/dev/null 2>&1; then
        log "Ollama: starting 'ollama serve'"
        nohup ollama serve >>"$LOG_DIR/ollama.log" 2>&1 &
        echo $! >"$RUN_DIR/ollama.pid"
    else
        problem "Ollama isn't installed (brew install ollama)"
        return 1
    fi
    OLLAMA_WAIT=1
}

# Prints the first installed Ollama model whose name starts with $1.
installed_model() {
    curl -fsS --max-time 5 "http://localhost:$OLLAMA_PORT/api/tags" 2>/dev/null \
        | grep -o '"name":"[^"]*"' | cut -d'"' -f4 \
        | awk -v want="$1" 'index(tolower($0), tolower(want)) == 1 { print; exit }'
}

# backend/.env helpers. They answer yes/no or read one non-secret value; they never print the file.
# Tolerant of "export KEY=value", spaces around "=", quotes and trailing comments.
bgf_key_set() { grep -Eq '^[[:space:]]*(export[[:space:]]+)?ANTHROPIC_API_KEY[[:space:]]*=[[:space:]]*[^[:space:]#]' "$BGF_DIR/backend/.env" 2>/dev/null; }

# The model BGF asks Ollama for: OLLAMA_MODEL in backend/.env, default mistral.
bgf_model() {
    local m=""
    [ -f "$BGF_DIR/backend/.env" ] && m=$(grep -E '^[[:space:]]*(export[[:space:]]+)?OLLAMA_MODEL[[:space:]]*=' "$BGF_DIR/backend/.env" \
        | tail -n 1 | cut -d= -f2- | sed 's/[[:space:]]*#.*$//' | tr -d "\"' \r")
    echo "${m:-mistral}"
}

check_models() {
    local want
    if [ "$START_BGF" = "yes" ] && [ -n "$BGF_DIR" ]; then
        want=$(bgf_model)
        [ -n "$(installed_model "$want")" ] || problem "Ollama model '$want' isn't installed — run: ollama pull $want"
    fi
    [ "$START_OPEN_WEBUI" = "yes" ] || return 0
    CHAT_MODEL_FOUND=$(installed_model "$CHAT_MODEL")
    if [ -z "$CHAT_MODEL_FOUND" ]; then
        if [ "$AUTO_PULL_CHAT_MODEL" = "yes" ]; then
            log "Ollama: downloading $CHAT_MODEL in the background"
            notify "Downloading $CHAT_MODEL (several GB). Chat works once it finishes."
            nohup curl -fsS -d "{\"model\":\"$CHAT_MODEL\",\"stream\":false}" \
                "http://localhost:$OLLAMA_PORT/api/pull" >>"$LOG_DIR/ollama-pull.log" 2>&1 &
        else
            problem "Chat model '$CHAT_MODEL' isn't installed — run: ollama pull $CHAT_MODEL"
        fi
    elif [ "$PRELOAD_CHAT_MODEL" = "yes" ]; then
        log "Ollama: loading $CHAT_MODEL_FOUND into memory"
        # An empty prompt loads the model without generating anything.
        ( curl -fsS --max-time 300 \
            -d "{\"model\":\"$CHAT_MODEL_FOUND\",\"keep_alive\":\"$CHAT_MODEL_KEEP_ALIVE\"}" \
            "http://localhost:$OLLAMA_PORT/api/generate" >/dev/null 2>&1 & )
    fi
}

# ── ComfyUI ───────────────────────────────────────────────────────────────────
start_comfyui() {
    [ "$START_COMFYUI" = "yes" ] || return 0
    if comfy_ok; then log "ComfyUI: already running"; COMFY_TAB=1; return 0; fi
    if [ ! -f "$COMFYUI_DIR/main.py" ]; then
        problem "ComfyUI not found at $COMFYUI_DIR (set COMFYUI_DIR in ~/.launchai/config.sh)"
        return 1
    fi
    local py=$COMFYUI_PYTHON
    [ -x "$py" ] || py=/usr/bin/python3
    log "ComfyUI: starting with $py"
    rm -f "$RUN_DIR/comfyui.pid"; trim_log "$LOG_DIR/comfyui.log" 5000000
    (
        cd "$COMFYUI_DIR" || exit 1
        # shellcheck disable=SC2086
        nohup "$py" main.py --port "$COMFYUI_PORT" $COMFYUI_ARGS >>"$LOG_DIR/comfyui.log" 2>&1 &
        echo $! >"$RUN_DIR/comfyui.pid"
    )
    COMFY_TAB=1; COMFY_WAIT=1
}

# ── BGF Production OS ─────────────────────────────────────────────────────────
start_bgf() {
    [ "$START_BGF" = "yes" ] || return 0
    if bgf_ok; then log "BGF: already running"; BGF_TAB=1; return 0; fi
    if [ ! -f "$BGF_DIR/start.sh" ]; then
        problem "Can't read the BGF folder (${BGF_DIR:-not set}). Re-run install.sh, or allow LaunchAI under System Settings → Privacy & Security → Files and Folders"
        return 1
    fi
    if [ ! -f "$BGF_DIR/backend/.env" ]; then
        problem "BGF isn't set up yet: backend/.env is missing (see BGF_USER_GUIDE.md §1)"
        return 1
    fi
    if ! bgf_key_set; then
        problem "ANTHROPIC_API_KEY is empty in BGF's backend/.env"
        return 1
    fi
    log "BGF: running start.sh in $BGF_DIR"
    rm -f "$RUN_DIR/bgf.pid"; trim_log "$LOG_DIR/bgf.log" 5000000
    (
        cd "$BGF_DIR" || exit 1
        nohup bash ./start.sh >>"$LOG_DIR/bgf.log" 2>&1 &
        echo $! >"$RUN_DIR/bgf.pid"
    )
    BGF_TAB=1; BGF_WAIT=1
}

# ── Claude app ────────────────────────────────────────────────────────────────
start_claude() {
    [ "$START_CLAUDE" = "yes" ] || return 0
    if pgrep -x "$CLAUDE_APP" >/dev/null 2>&1; then log "Claude: already running"; return 0; fi
    log "Claude: opening"
    open -a "$CLAUDE_APP" 2>>"$LOG" || problem "Couldn't open the $CLAUDE_APP app"
}

# ── Open WebUI (optional extra) ───────────────────────────────────────────────
docker_app() {
    local a
    for a in Docker OrbStack; do app_installed "$a" && { echo "$a"; return 0; }; done
    return 1
}

# Wake Docker early: it is the slowest thing to start, and nothing else has to wait for it.
kick_docker() {
    local app
    [ "$START_OPEN_WEBUI" = "yes" ] && [ "$OPEN_WEBUI_MODE" != "pip" ] || return 0
    command -v docker >/dev/null 2>&1 || return 0
    docker_ok && return 0
    app=$(docker_app) || return 0
    log "Docker: opening $app"
    open -g -a "$app" 2>>"$LOG"
}

start_webui_docker() {
    local name
    if ! docker_ok; then
        wait_for "Docker" "$WAIT_DOCKER" docker_ok || { problem "Docker didn't start"; return 1; }
    fi
    # Reuse whichever Open WebUI container already exists (and so its chats and settings).
    name=$(docker ps -a --format '{{.Names}}|{{.Image}}' 2>/dev/null \
        | awk -F'|' -v c="$OPEN_WEBUI_CONTAINER" '$1 == c || $2 ~ /open-webui(:|$)/ { print $1; exit }')
    if [ -n "$name" ]; then
        if [ "$(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null)" = "true" ]; then
            log "Open WebUI: container $name is already running (still starting)"
        else
            log "Open WebUI: starting container $name"
            docker start "$name" >>"$LOG_DIR/openwebui.log" 2>&1 \
                || { problem "Couldn't start the $name container (see openwebui.log)"; return 1; }
        fi
    else
        name=$OPEN_WEBUI_CONTAINER
        log "Open WebUI: creating container $name (first run)"
        docker run -d -p "$OPEN_WEBUI_PORT:8080" --add-host=host.docker.internal:host-gateway \
            -v open-webui:/app/backend/data \
            -e OLLAMA_BASE_URL="http://host.docker.internal:$OLLAMA_PORT" \
            --name "$name" --restart unless-stopped "$OPEN_WEBUI_IMAGE" >>"$LOG_DIR/openwebui.log" 2>&1 \
            || { problem "Couldn't create the Open WebUI container (see openwebui.log)"; return 1; }
    fi
    echo "$name" >"$RUN_DIR/openwebui.container"
    WEBUI_TAB=1; WEBUI_WAIT=1
}

start_openwebui() {
    [ "$START_OPEN_WEBUI" = "yes" ] || return 0
    if webui_ok; then log "Open WebUI: already running"; WEBUI_TAB=1; return 0; fi
    case "$OPEN_WEBUI_MODE" in
        auto|docker)
            if command -v docker >/dev/null 2>&1; then start_webui_docker; return; fi
            if [ "$OPEN_WEBUI_MODE" = "docker" ]; then problem "Docker isn't installed (Open WebUI needs it)"; return 1; fi ;;
    esac
    case "$OPEN_WEBUI_MODE" in
        auto|pip)
            if command -v open-webui >/dev/null 2>&1; then
                log "Open WebUI: starting 'open-webui serve'"
                nohup open-webui serve --port "$OPEN_WEBUI_PORT" >>"$LOG_DIR/openwebui.log" 2>&1 &
                echo $! >"$RUN_DIR/openwebui.pid"
                WEBUI_TAB=1; WEBUI_WAIT=1; return 0
            fi ;;
    esac
    problem "Open WebUI isn't installed (needs Docker, or: pip install open-webui)"
    return 1
}

# ── Chrome ────────────────────────────────────────────────────────────────────
open_tabs() {
    local urls=() u
    [ -n "$BGF_TAB" ] && urls+=("http://localhost:$BGF_FRONTEND_PORT/")
    if [ -n "$WEBUI_TAB" ]; then
        u="http://localhost:$OPEN_WEBUI_PORT/"
        [ -n "$CHAT_MODEL_FOUND" ] && u="$u?model=${CHAT_MODEL_FOUND//:/%3A}"   # pre-select the model
        urls+=("$u")
    fi
    [ -n "$COMFY_TAB" ] && urls+=("http://localhost:$COMFYUI_PORT/")
    if [ "${#urls[@]}" -eq 0 ]; then log "Chrome: nothing to open"; return 0; fi
    log "Chrome: opening ${urls[*]}"
    open -a "$CHROME_APP" "${urls[@]}" 2>>"$LOG" || {
        log "Chrome not found — using the default browser"
        open "${urls[@]}" 2>>"$LOG"
    }
}

# ── start ─────────────────────────────────────────────────────────────────────
cmd_start() {
    local old
    # One run at a time: a second click while the first is still waiting does nothing.
    if [ -f "$RUN_DIR/launcher.pid" ]; then
        old=$(cat "$RUN_DIR/launcher.pid" 2>/dev/null)
        if [ -n "$old" ] && ps -p "$old" -o command= 2>/dev/null | grep -qi launchai; then
            log "Another LaunchAI run (pid $old) is still going; leaving it to finish."
            return 0
        fi
    fi
    echo $$ >"$RUN_DIR/launcher.pid"
    trap 'rm -f "$RUN_DIR/launcher.pid"' EXIT
    trim_log "$LOG" 500000

    log "──── LaunchAI $VERSION ────"
    notify "Starting your AI stack…"

    # Start everything first (each start returns at once), then wait. The slow boots overlap.
    kick_docker
    start_ollama
    start_comfyui
    start_bgf
    start_claude

    if [ -n "$OLLAMA_WAIT" ]; then
        if wait_for "Ollama" "$WAIT_OLLAMA" ollama_ok "$RUN_DIR/ollama.pid"; then
            check_models
        else
            problem "Ollama didn't start"
        fi
    elif ollama_ok; then        # Ollama is switched off here but running anyway (started by hand)
        check_models
    fi

    start_openwebui

    if [ -n "$BGF_WAIT" ] && ! wait_for "BGF" "$WAIT_BGF" bgf_ok "$RUN_DIR/bgf.pid"; then
        problem "BGF didn't come up — see ~/Library/Logs/LaunchAI/bgf.log"
        pid_alive "$RUN_DIR/bgf.pid" || BGF_TAB=""      # dead, not just slow: don't open a tab that can't load
    fi
    if [ -n "$COMFY_WAIT" ] && ! wait_for "ComfyUI" "$WAIT_COMFYUI" comfy_ok "$RUN_DIR/comfyui.pid"; then
        problem "ComfyUI didn't come up — see comfyui.log"
        pid_alive "$RUN_DIR/comfyui.pid" || COMFY_TAB=""
    fi
    if [ -n "$WEBUI_WAIT" ]; then
        wait_for "Open WebUI" "$WAIT_OPEN_WEBUI" webui_ok || problem "Open WebUI isn't answering yet — see openwebui.log"
    fi

    open_tabs
    if [ -n "$PROBLEMS" ]; then notify "Up, but: $PROBLEMS"; else notify "Everything is up."; fi
    log "──── done ────"
}

# ── stop ──────────────────────────────────────────────────────────────────────
stop_pid() {   # stop_pid <label> <pidfile> <text the process command must contain>
    local label=$1 file=$2 want=$3 pid
    pid=$(cat "$file" 2>/dev/null)
    if [ -n "$pid" ] && ps -p "$pid" -o command= 2>/dev/null | grep -q "$want"; then
        kill "$pid" 2>/dev/null && echo "  ✓ $label stopped"
    else
        echo "  - $label: nothing of ours is running"
    fi
    rm -f "$file"
}

cmd_stop() {
    local c
    echo "Stopping what LaunchAI started…"
    stop_pid "BGF Production OS" "$RUN_DIR/bgf.pid" "start.sh"
    stop_pid "ComfyUI" "$RUN_DIR/comfyui.pid" "main.py"
    stop_pid "Ollama (ollama serve)" "$RUN_DIR/ollama.pid" "ollama"
    stop_pid "Open WebUI" "$RUN_DIR/openwebui.pid" "open-webui"
    if [ -f "$RUN_DIR/openwebui.container" ]; then
        c=$(cat "$RUN_DIR/openwebui.container")
        if docker stop "$c" >/dev/null 2>&1; then echo "  ✓ Open WebUI container stopped"; else echo "  - Open WebUI container $c: couldn't stop it"; fi
        rm -f "$RUN_DIR/openwebui.container"
    fi
    echo "Left alone: anything you started yourself, plus the Ollama, Claude and Docker apps."
}

# ── diagnose ──────────────────────────────────────────────────────────────────
mask() {   # hide any log line that might hold a secret
    awk 'tolower($0) ~ /sk-ant-|github_pat_|ghp_|api[_-]?key|secret|token|password/ { print "[line hidden: may contain a secret]"; next } { print }'
}

show() {   # show <label> <check-function> <detail>
    if "$2"; then printf '  ✓ %-14s %s\n' "$1" "$3"; else printf '  ✗ %-14s not answering (%s)\n' "$1" "$3"; fi
}

cmd_diagnose() {
    local f t port who
    echo "LaunchAI $VERSION diagnostic — $(date)"
    echo "macOS $(sw_vers -productVersion 2>/dev/null || echo '?') on $(uname -m)"
    echo
    echo "── Settings ──"
    for f in "$LAUNCHAI_HOME/env.sh" "$LAUNCHAI_HOME/config.sh"; do
        if [ -f "$f" ]; then
            echo "$f"
            grep -Ev '^[[:space:]]*(#|$)' "$f" | sed -E 's/^(TERMINAL_PATH)=.*/\1=(saved)/; s/^/  /'
        else
            echo "$f  (missing — run install.sh)"
        fi
    done
    echo
    echo "── BGF Production OS ──"
    if [ -z "$BGF_DIR" ]; then
        echo "  BGF_DIR is not set"
    else
        echo "  folder          $BGF_DIR"
        [ -f "$BGF_DIR/start.sh" ] && echo "  start.sh        found" || echo "  start.sh        MISSING"
        if [ -f "$BGF_DIR/backend/.env" ]; then
            if bgf_key_set; then
                echo "  backend/.env    found, ANTHROPIC_API_KEY is set"
            else
                echo "  backend/.env    found, ANTHROPIC_API_KEY is EMPTY"
            fi
            echo "  Ollama model    $(bgf_model)"
        else
            echo "  backend/.env    MISSING"
        fi
        [ -d "$BGF_DIR/backend/.venv" ] && echo "  backend/.venv   found" || echo "  backend/.venv   not created yet (start.sh makes it)"
        [ -d "$BGF_DIR/node_modules" ] && echo "  node_modules    found" || echo "  node_modules    not installed yet (start.sh installs them)"
    fi
    echo
    echo "── Tools ──"
    for t in node npm python3 ffmpeg ollama docker; do
        printf '  %-10s %s\n' "$t" "$(command -v "$t" || echo 'not found')"
    done
    echo
    echo "── Services ──"
    show "BGF backend" bgf_ok "http://localhost:$BGF_BACKEND_PORT/api/health + :$BGF_FRONTEND_PORT"
    show "ComfyUI" comfy_ok "http://localhost:$COMFYUI_PORT"
    show "Ollama" ollama_ok "http://localhost:$OLLAMA_PORT"
    if ollama_ok; then
        echo "      models: $(curl -fsS --max-time 5 "http://localhost:$OLLAMA_PORT/api/tags" 2>/dev/null | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | tr '\n' ' ')"
    fi
    show "Open WebUI" webui_ok "http://localhost:$OPEN_WEBUI_PORT (optional)"
    echo
    echo "── What is listening ──"
    if command -v lsof >/dev/null 2>&1; then
        for port in "$BGF_BACKEND_PORT" "$BGF_FRONTEND_PORT" "$COMFYUI_PORT" "$OLLAMA_PORT" "$OPEN_WEBUI_PORT"; do
            who=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | awk 'NR == 2 { print $1 " (pid " $2 ")" }')
            printf '  :%-6s %s\n' "$port" "${who:-nothing}"
        done
    fi
    echo
    for f in launchai.log bgf.log comfyui.log ollama.log openwebui.log; do
        if [ -f "$LOG_DIR/$f" ]; then
            echo "── $f (last 15 lines) ──"
            tail -n 15 "$LOG_DIR/$f" | mask
            echo
        fi
    done
}

case "${1:-start}" in
    stop)     cmd_stop ;;
    diagnose) cmd_diagnose ;;
    *)        cmd_start ;;     # also covers the extra arguments Finder can pass to an app
esac
