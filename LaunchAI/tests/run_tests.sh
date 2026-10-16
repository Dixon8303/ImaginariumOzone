#!/bin/bash
# Smoke tests for LaunchAI. They run the real launchai.sh and install.sh against stand-ins for the
# Mac tools (open, osascript, docker, ollama, curl, ...), so they work on any machine:
#
#     bash LaunchAI/tests/run_tests.sh
#
# Each scenario builds a fake home folder, fake services that "come up" when started, and then
# checks which commands the launcher ran. Nothing here touches the real system.

# The single-quoted strings below are the bodies of the stand-in tools; they must not expand until a stand-in runs.
# shellcheck disable=SC2016
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT
export W=""                      # the current scenario's folder, read by the stand-in tools
PASS=0; FAIL=0; N=0

mkstub() { printf '#!/bin/bash\n%s\n' "$2" >"$W/bin/$1"; chmod +x "$W/bin/$1"; }

world() {
    N=$((N + 1)); W="$ROOT/w$N"
    mkdir -p "$W"/{bin,up,logs,apps/Ollama.app,apps/Docker.app,bgf/backend,ComfyUI/comfy,ComfyUI/venv/bin,home/.launchai/run,home/Desktop}
    : >"$W/calls.log"; : >"$W/containers"
    echo '{"models":[{"name":"mistral:latest"},{"name":"qwen2.5:latest"}]}' >"$W/models"
    printf 'ANTHROPIC_API_KEY=FAKE-KEY-VALUE-123\nOLLAMA_MODEL=mistral\n' >"$W/bgf/backend/.env"
    touch "$W/bgf/backend/main.py" "$W/ComfyUI/main.py"
    printf '#!/bin/bash\necho "bgf start.sh" >>"$W/calls.log"\ntouch "$W/up/backend" "$W/up/frontend"\n' >"$W/bgf/start.sh"
    printf '#!/bin/bash\necho "comfy $*" >>"$W/calls.log"\ntouch "$W/up/comfy"\n' >"$W/ComfyUI/venv/bin/python"
    chmod +x "$W/ComfyUI/venv/bin/python"

    mkstub curl 'url=""; has_data=""
for a in "$@"; do case "$a" in http*) url=$a ;; -d) has_data=1 ;; esac; done
[ -n "$has_data" ] && echo "curl POST $url" >>"$W/calls.log"
up() { [ -e "$W/up/$1" ]; }
case "$url" in
  */api/version)        up ollama && { echo "{\"version\":\"0\"}"; exit 0; } ;;
  */api/tags)           up ollama && { cat "$W/models"; exit 0; } ;;
  */api/generate|*/api/pull) up ollama && exit 0 ;;
  *:8001/api/health)    up backend && { echo "{\"status\":\"ok\",\"service\":\"BGF Production OS v1.0\"}"; exit 0; } ;;
  *:5173/)              up frontend && exit 0 ;;
  *:8188/system_stats)  up comfy && { echo "{}"; exit 0; } ;;
  *:3000/health)        up webui && { echo "{\"status\":true}"; exit 0; } ;;
esac
exit 7'
    mkstub open 'echo "open $*" >>"$W/calls.log"
case "$*" in
  *"-a Ollama"*) touch "$W/up/ollama" ;;
  *"-a Docker"*) touch "$W/up/docker" ;;
  *"-a Claude"*) touch "$W/up/claude" ;;
  *"-a Google Chrome"*) [ -e "$W/no_chrome" ] && exit 1 ;;
esac
exit 0'
    mkstub osascript 'for a; do last=$a; done; echo "notify: $last" >>"$W/calls.log"'
    mkstub pgrep '[ "$1" = "-x" ] && [ -e "$W/up/$(echo "$2" | tr A-Z a-z)" ]'
    mkstub docker 'echo "docker $*" >>"$W/calls.log"
case "$1" in
  info)    [ -e "$W/up/docker" ] ;;
  ps)      cat "$W/containers" ;;
  inspect) [ -e "$W/up/webui" ] && echo true || echo false ;;
  start|run) touch "$W/up/webui" ;;
  stop)    rm -f "$W/up/webui" ;;
esac'
    mkstub ollama 'echo "ollama $*" >>"$W/calls.log"; [ "$1" = serve ] && touch "$W/up/ollama"; exit 0'
    mkstub sleep 'exec /bin/sleep 0.03'
    mkstub uname '[ "${1:-}" = "-m" ] && echo arm64 || echo Darwin'
    mkstub sw_vers 'echo 15.0'
    mkstub xattr 'exit 0'
    mkstub killall 'exit 0'
}

# launch [config lines…]  — runs launchai.sh with a fake home; LPATH overrides PATH, ARG is the sub-command.
launch() {
    printf '%s\n' "BGF_DIR=\"$W/bgf\"" "COMFYUI_DIR=\"$W/ComfyUI\"" "APP_DIRS=\"$W/apps\"" \
        "WAIT_OLLAMA=40; WAIT_COMFYUI=40; WAIT_BGF=40; WAIT_DOCKER=40; WAIT_OPEN_WEBUI=40" \
        "$@" >"$W/home/.launchai/config.sh"
    OUT=$(env HOME="$W/home" W="$W" LAUNCHAI_HOME="$W/home/.launchai" LAUNCHAI_LOG_DIR="$W/logs" \
        PATH="${LPATH:-$W/bin:$PATH}" bash "$HERE/launchai.sh" "${ARG:-}" 2>&1)
    /bin/sleep 0.3      # let background helpers (model preload) finish writing
}

ok()   { PASS=$((PASS + 1)); printf '  ok    %s\n' "$1"; }
bad()  {
    FAIL=$((FAIL + 1)); printf '  FAIL  %s\n' "$1"
    if [ -n "${TEST_DEBUG:-}" ]; then      # TEST_DEBUG=1 bash run_tests.sh  shows what the launcher did
        sed 's/^/        calls| /' "$W/calls.log"; sed 's/^/        log  | /' "$W/logs/launchai.log" 2>/dev/null
    fi
}
check() { if "${@:2}"; then ok "$1"; else bad "$1"; fi; }
called()    { grep -qF -- "$1" "$W/calls.log"; }
not_called(){ ! grep -qF -- "$1" "$W/calls.log"; }
notified()  { grep -F 'notify:' "$W/calls.log" | grep -qF -- "$1"; }
logged()    { grep -qF -- "$1" "$W/logs/launchai.log"; }
scenario()  { printf '\n%s\n' "$1"; world; }

# ── cold start ────────────────────────────────────────────────────────────────
scenario "Cold start: nothing is running"
launch
check "opens Ollama.app"                       called "open -g -a Ollama"
check "starts ComfyUI with its venv python"    called "comfy main.py --port 8188"
check "runs the BGF start.sh"                  called "bgf start.sh"
check "opens the Claude app"                   called "open -a Claude"
check "opens the dashboard and ComfyUI in Chrome" called "open -a Google Chrome http://localhost:5173/ http://localhost:8188/"
check "uses Chrome, not the fallback browser"  not_called "open http://localhost"
check "does not touch Docker (Open WebUI is off)" not_called "docker"
check "reports success"                        notified "Everything is up."

# ── already running ───────────────────────────────────────────────────────────
scenario "Warm start: everything is already up"
touch "$W"/up/{ollama,comfy,backend,frontend,claude}
launch
check "does not restart Ollama"                not_called "open -g -a Ollama"
check "does not restart ComfyUI"               not_called "comfy main.py"
check "does not run start.sh again"            not_called "bgf start.sh"
check "does not reopen Claude"                 not_called "open -a Claude"
check "still opens the Chrome tabs"            called "open -a Google Chrome http://localhost:5173/ http://localhost:8188/"

# ── setup problems are reported, the rest still works ─────────────────────────
scenario "BGF has no backend/.env yet"
rm "$W/bgf/backend/.env"
launch
check "does not run start.sh"                  not_called "bgf start.sh"
check "says what is missing"                   notified "backend/.env is missing"
check "still opens ComfyUI alone"              called "open -a Google Chrome http://localhost:8188/"

scenario "BGF's Ollama model isn't installed"
echo '{"models":[{"name":"llama3:latest"}]}' >"$W/models"
launch
check "tells you the pull command"             notified "ollama pull mistral"

scenario ".env written the other common way (export, spaces, quotes, comments)"
printf 'export ANTHROPIC_API_KEY = "FAKE-X"   # my key\nexport OLLAMA_MODEL = llama3   # chat\n' >"$W/bgf/backend/.env"
echo '{"models":[{"name":"llama3:8b"}]}' >"$W/models"
launch
check "still sees the key and starts BGF"      called "bgf start.sh"
check "reads the model name, ignoring the comment" bash -c "! grep -F 'notify:' '$W/calls.log' | grep -q 'ollama pull'"

scenario "ANTHROPIC_API_KEY really is empty"
printf 'ANTHROPIC_API_KEY=\n' >"$W/bgf/backend/.env"
launch
check "does not start BGF"                     not_called "bgf start.sh"
check "says why"                               notified "ANTHROPIC_API_KEY is empty"

scenario "ComfyUI folder is wrong"
launch "COMFYUI_DIR=\"$W/nowhere\""
check "reports it"                             notified "ComfyUI not found"
check "opens no ComfyUI tab"                   called "open -a Google Chrome http://localhost:5173/"

# ── how Ollama is started ─────────────────────────────────────────────────────
scenario "Ollama installed with Homebrew (no app)"
rm -rf "$W/apps/Ollama.app"
launch
check "runs 'ollama serve'"                    called "ollama serve"

scenario "Finder-style bare PATH (the old launcher's failure)"
rm -rf "$W/apps/Ollama.app"
LPATH="/usr/bin:/bin" launch "TERMINAL_PATH=\"$W/bin\""
unset LPATH
check "finds ollama through the saved Terminal PATH" called "ollama serve"

# ── Open WebUI extra ──────────────────────────────────────────────────────────
scenario "Open WebUI on: an existing container, whatever it is called"
echo 'adoring_hopper|ghcr.io/open-webui/open-webui:main' >"$W/containers"
launch 'START_OPEN_WEBUI="yes"'
check "starts Docker first"                    called "open -g -a Docker"
check "starts the existing container"          called "docker start adoring_hopper"
check "does not create a second one"           not_called "docker run"
check "pre-selects the Qwen model in the URL"  called "http://localhost:3000/?model=qwen2.5%3Alatest"
check "loads the model into memory"            called "curl POST http://localhost:11434/api/generate"
check "opens all three tabs, WebUI in the middle" called "open -a Google Chrome http://localhost:5173/ http://localhost:3000/?model=qwen2.5%3Alatest http://localhost:8188/"

scenario "Open WebUI on: no container yet"
launch 'START_OPEN_WEBUI="yes"'
check "creates it on port 3000"                called "docker run -d -p 3000:8080"
check "names it open-webui"                    called "--name open-webui"

scenario "Open WebUI on: a Pipelines container must not be mistaken for it"
echo 'pipes|ghcr.io/open-webui/pipelines:main' >"$W/containers"
launch 'START_OPEN_WEBUI="yes"'
check "creates a real one instead"             called "docker run -d"
check "leaves the pipelines container alone"   not_called "docker start pipes"

scenario "Open WebUI on, Qwen not installed"
echo '{"models":[{"name":"mistral:latest"}]}' >"$W/models"
launch 'START_OPEN_WEBUI="yes"'
check "tells you how to get it"                notified "ollama pull qwen2.5"
launch 'START_OPEN_WEBUI="yes"' 'AUTO_PULL_CHAT_MODEL="yes"'
check "downloads it when asked to"             called "curl POST http://localhost:11434/api/pull"

scenario "BGF's start.sh dies straight away"
printf '#!/bin/bash\necho "bgf start.sh" >>"$W/calls.log"\nexit 1\n' >"$W/bgf/start.sh"
launch
check "reports it without waiting out the clock" notified "BGF didn't come up"
check "still opens ComfyUI"                    called "open -a Google Chrome http://localhost:8188/"

scenario "Chrome isn't installed"
touch "$W/no_chrome"
launch
check "falls back to the default browser"      called "open http://localhost:5173/ http://localhost:8188/"

# ── guard rails ───────────────────────────────────────────────────────────────
scenario "A second click while the first run is still going"
/bin/bash -c 'exec -a LaunchAI-fake /bin/sleep 30' & PEER=$!
echo "$PEER" >"$W/home/.launchai/run/launcher.pid"
launch
kill "$PEER" 2>/dev/null
check "does nothing"                           not_called "open "
check "says why"                               logged "still going"

scenario "Stop"
/bin/bash -c 'exec -a "bash ./start.sh" /bin/sleep 30' & PEER=$!
echo "$PEER" >"$W/home/.launchai/run/bgf.pid"
ARG=stop launch
ARG=""
/bin/sleep 0.2
check "stops the BGF process it started"       bash -c "! kill -0 $PEER 2>/dev/null"
check "says so"                                bash -c "echo '$OUT' | grep -q 'BGF Production OS stopped'"
kill "$PEER" 2>/dev/null

scenario "Diagnose never prints secrets"
PFX="sk-"; PFX="${PFX}ant-"     # built here so no key-shaped text sits in the file
printf 'GET /x?foo=%sabc123leak 200\nretry with api_key=plain-value-777\nGET /health 200\n' "$PFX" >"$W/logs/bgf.log"
ARG=diagnose launch
ARG=""
check "reports the key as set"                 bash -c "echo '$OUT' | grep -q 'ANTHROPIC_API_KEY is set'"
check "does not print the key from .env"       bash -c "! echo '$OUT' | grep -q FAKE-KEY-VALUE-123"
check "hides a line holding a key-shaped value" bash -c "! echo '$OUT' | grep -q abc123leak"
check "hides a line that names an api key"     bash -c "! echo '$OUT' | grep -q plain-value-777"
check "still shows ordinary log lines"         bash -c "echo '$OUT' | grep -q 'GET /health 200'"

# ── installer ─────────────────────────────────────────────────────────────────
scenario "Installer: replaces the old app, keeps its ComfyUI settings, finds the real BGF folder"
H="$W/home"
mkdir -p "$H/Desktop/LaunchAI.app/Contents/MacOS" "$H/Documents/ImaginariumOzone/backend"
cat >"$H/Desktop/LaunchAI.app/Contents/MacOS/LaunchAI" <<'OLD'
#!/bin/bash
COMFYUI_DIR="$HOME/Studio/ComfyUI"              # path to your ComfyUI folder
COMFYUI_PORT=9999                        # ComfyUI default port
COMFYUI_PYTHON="$COMFYUI_DIR/venv/bin/python"  # python inside ComfyUI venv
CLAUDE_APP="Claude"                      # name shown in /Applications
CHROME_APP="Google Chrome"
OLD
touch "$H/Documents/ImaginariumOzone/start.sh" "$H/Documents/ImaginariumOzone/backend/main.py" "$H/Documents/ImaginariumOzone/backend/.env"
IOUT=$(env HOME="$H" W="$W" PATH="$W/bin:$PATH" LAUNCHAI_HOME="$H/.launchai" bash "$HERE/install.sh" </dev/null 2>&1)
APP="$H/Desktop/LaunchAI.app"
check "builds the app with an executable"      test -x "$APP/Contents/MacOS/LaunchAI"
check "installs the icon"                      test -s "$APP/Contents/Resources/LaunchAI.icns"
check "writes an Info.plist naming the icon"   grep -q '<string>LaunchAI</string>' "$APP/Contents/Info.plist"
check "the old app's script is gone"           bash -c "! grep -q 'Studio/ComfyUI' '$APP/Contents/MacOS/LaunchAI'"
check "carries over your ComfyUI folder"       grep -q "^COMFYUI_DIR=$H/Studio/ComfyUI" "$H/.launchai/config.sh"
check "carries over your ComfyUI port"         grep -q '^COMFYUI_PORT=9999' "$H/.launchai/config.sh"
check "does not pin settings you never changed" bash -c "! grep -q '^CLAUDE_APP=' '$H/.launchai/config.sh'"
check "finds the BGF folder that has a .env"   grep -q "^BGF_DIR=$H/Documents/ImaginariumOzone" "$H/.launchai/env.sh"
check "saves the Terminal PATH"                grep -q '^TERMINAL_PATH=' "$H/.launchai/env.sh"
check "installs the command-line copy"         test -x "$H/.launchai/launchai"
echo "my change" >>"$H/.launchai/config.sh"
env HOME="$H" W="$W" PATH="$W/bin:$PATH" LAUNCHAI_HOME="$H/.launchai" bash "$HERE/install.sh" </dev/null >/dev/null 2>&1
check "a second install keeps your settings"   grep -q '^my change' "$H/.launchai/config.sh"
check "prints how to stop and diagnose"        bash -c "echo '$IOUT' | grep -q 'launchai stop'"

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
