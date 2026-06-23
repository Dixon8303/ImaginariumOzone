#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# build_app.sh — assembles LaunchAI.app and puts it on your Desktop
# Run this script once from the LaunchAI/ folder:
#   cd LaunchAI && bash build_app.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="LaunchAI"
DEST="$HOME/Desktop/$APP_NAME.app"

echo "==> Building $APP_NAME.app ..."

# ── 1. Create bundle structure ────────────────────────────────────────────────
rm -rf "$DEST"
mkdir -p "$DEST/Contents/MacOS"
mkdir -p "$DEST/Contents/Resources"

# ── 2. Copy launcher script as the executable ─────────────────────────────────
cp "$SCRIPT_DIR/launch_ai.sh" "$DEST/Contents/MacOS/$APP_NAME"
chmod +x "$DEST/Contents/MacOS/$APP_NAME"

# ── 3. Write Info.plist ───────────────────────────────────────────────────────
cat > "$DEST/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>            <string>$APP_NAME</string>
  <key>CFBundleDisplayName</key>     <string>Launch AI Stack</string>
  <key>CFBundleIdentifier</key>      <string>com.local.launchai</string>
  <key>CFBundleVersion</key>         <string>1.0</string>
  <key>CFBundleExecutable</key>      <string>$APP_NAME</string>
  <key>CFBundleIconFile</key>        <string>$APP_NAME</string>
  <key>CFBundlePackageType</key>     <string>APPL</string>
  <key>LSUIElement</key>             <false/>
  <key>NSHighResolutionCapable</key> <true/>
</dict>
</plist>
PLIST

# ── 4. Generate icon ──────────────────────────────────────────────────────────
echo "==> Generating icon (requires Pillow: pip install Pillow) ..."
cd "$SCRIPT_DIR"

if python3 -c "import PIL" 2>/dev/null; then
    python3 create_icon.py
    if [ -f "LaunchAI.icns" ]; then
        cp "LaunchAI.icns" "$DEST/Contents/Resources/$APP_NAME.icns"
        echo "    Icon installed."
    else
        echo "    WARNING: icon file not produced — app will use default icon."
    fi
else
    echo "    WARNING: Pillow not found. Skipping icon generation."
    echo "    Install it with:  pip install Pillow"
    echo "    Then re-run this script, or manually copy LaunchAI.icns to:"
    echo "    $DEST/Contents/Resources/"
fi

# ── 5. Refresh icon cache so Finder shows the new icon ────────────────────────
touch "$DEST"
if command -v killall &>/dev/null; then
    killall Finder 2>/dev/null || true
fi

echo ""
echo "==> Done!  LaunchAI.app is on your Desktop."
echo "    Double-click it to start your AI stack."
echo ""
echo "    First-time setup:"
echo "    1. Open LaunchAI.app/Contents/MacOS/launch_ai.sh"
echo "    2. Edit the CONFIG section at the top to match your paths."
echo "    3. Right-click → Open the first time to bypass Gatekeeper."
