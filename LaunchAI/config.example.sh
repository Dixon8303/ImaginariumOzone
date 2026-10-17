# LaunchAI settings — your personal copy, never overwritten by install.sh.
#
# Every line below is a default and is commented out. To change one, remove the leading
# "#" and edit the value. Nothing needs rebuilding: the next click on LaunchAI uses it.
#
#   open -e ~/.launchai/config.sh        # edit this file in TextEdit

# ── What to start ─────────────────────────────────────────────────────────────
#START_BGF="yes"                 # BGF Production OS: backend :8001 + dashboard :5173
#START_OLLAMA="yes"
#START_COMFYUI="yes"
#START_CLAUDE="yes"
#START_OPEN_WEBUI="no"           # optional extra: Open WebUI chat with a local Qwen model (needs Docker)

# ── Where things live (install.sh detects BGF_DIR and, if needed, COMFYUI_DIR) ─
#BGF_DIR="$HOME/Documents/ImaginariumOzone"
#COMFYUI_DIR="$HOME/ComfyUI"
#COMFYUI_PYTHON=""               # blank = <COMFYUI_DIR>/venv/bin/python
#COMFYUI_ARGS=""                 # extra ComfyUI flags, e.g. "--force-fp16"

# ── Apps ──────────────────────────────────────────────────────────────────────
#CLAUDE_APP="Claude"
#CHROME_APP="Google Chrome"

# ── Ports ─────────────────────────────────────────────────────────────────────
#BGF_BACKEND_PORT=8001
#BGF_FRONTEND_PORT=5173
#COMFYUI_PORT=8188
#OLLAMA_PORT=11434

# ── Open WebUI extra (only used when START_OPEN_WEBUI="yes") ──────────────────
#OPEN_WEBUI_PORT=3000
#OPEN_WEBUI_MODE="auto"          # auto | docker | pip
#CHAT_MODEL="qwen2.5"
#PRELOAD_CHAT_MODEL="yes"        # load the model into memory at start so the first answer is quick
#AUTO_PULL_CHAT_MODEL="no"       # "yes" downloads the model when it is missing (several GB)

# ── Anything else ─────────────────────────────────────────────────────────────
# Whatever you export here reaches ComfyUI and the BGF Production OS, for example:
#export PYTORCH_ENABLE_MPS_FALLBACK=1
