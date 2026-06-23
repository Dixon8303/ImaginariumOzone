# LaunchAI — One-Click AI Stack Launcher for macOS

Click the icon on your Desktop and it automatically:

1. **Starts Ollama** (if not already running)
2. **Pulls Qwen2.5** in the background if it isn't downloaded yet
3. **Starts ComfyUI** (if not already running)
4. **Opens Claude** desktop app
5. **Opens Chrome** with two tabs — Open WebUI (Qwen2.5) + ComfyUI

The icon is a shiny metallic-blue **AI** fused with a power-button ring.

---

## Quick Start

```bash
# 1. Clone / download this folder, then:
cd LaunchAI

# 2. Install Pillow (needed to generate the icon)
pip install Pillow

# 3. Build the app — puts LaunchAI.app on your Desktop
bash build_app.sh
```

**First launch:** right-click → **Open** (bypasses macOS Gatekeeper for
unsigned apps). After that, double-click works normally.

---

## Configuration

Open `launch_ai.sh` and edit the `CONFIG` block at the top:

| Variable | Default | What to change |
|---|---|---|
| `COMFYUI_DIR` | `~/ComfyUI` | Full path to your ComfyUI folder |
| `COMFYUI_PORT` | `8188` | ComfyUI port |
| `COMFYUI_PYTHON` | `~/ComfyUI/venv/bin/python` | Python binary inside ComfyUI's venv |
| `OPEN_WEBUI_URL` | `http://localhost:3000` | Open WebUI URL |
| `CLAUDE_APP` | `Claude` | Name of Claude in /Applications |

---

## Files

| File | Purpose |
|---|---|
| `launch_ai.sh` | Main launcher script |
| `create_icon.py` | Generates the metallic-blue AI power-button icon |
| `build_app.sh` | Assembles `LaunchAI.app` on your Desktop |

---

## Troubleshooting

- **Services don't start:** Check `/tmp/ollama.log` and `/tmp/comfyui.log`
- **Icon not showing:** Run `pip install Pillow` then re-run `build_app.sh`
- **Chrome opens wrong tab:** Edit `OPEN_WEBUI_URL` / `COMFY_URL` in `launch_ai.sh`
- **ComfyUI not found:** Set `COMFYUI_DIR` to the correct path
