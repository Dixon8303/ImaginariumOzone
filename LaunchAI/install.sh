#!/bin/bash
# LaunchAI installer — builds LaunchAI.app on your Desktop.
#
#     cd LaunchAI && bash install.sh
#
# Safe to run again at any time: it replaces the app, keeps your settings in
# ~/.launchai/config.sh and re-detects your folders. To point it at a particular
# BGF Production OS folder:   BGF_DIR=/path/to/ImaginariumOzone bash install.sh

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="LaunchAI"
DEST_DIR="${LAUNCHAI_DEST:-$HOME/Desktop}"
APP="$DEST_DIR/$APP_NAME.app"
LAUNCHAI_HOME="${LAUNCHAI_HOME:-$HOME/.launchai}"
CONFIG="$LAUNCHAI_HOME/config.sh"
ENVFILE="$LAUNCHAI_HOME/env.sh"

say()  { printf '%s\n' "$*"; }
ok()   { printf '  ✓ %s\n' "$*"; }
warn() { printf '  ! %s\n' "$*"; }
die()  { printf '\n✗ %s\n\n' "$*" >&2; exit 1; }

[ "$(uname)" = "Darwin" ] || die "LaunchAI is a Mac app — run this on your Mac."
for f in launchai.sh config.example.sh LaunchAI.icns; do
    [ -f "$HERE/$f" ] || die "$f is missing next to install.sh — run it from inside the LaunchAI folder."
done

say ""
say "Installing LaunchAI…"

# ── find your folders ─────────────────────────────────────────────────────────
abs()         { (cd "$1" 2>/dev/null && pwd); }
is_bgf()      { [ -f "$1/start.sh" ] && [ -f "$1/backend/main.py" ]; }
has_bgf_env() { is_bgf "$1" && [ -f "$1/backend/.env" ]; }   # .env is not in git, so only a real, set-up copy has it
is_comfy()    { [ -f "$1/main.py" ] && [ -d "$1/comfy" ]; }

mtime() {
    local m
    m=$(stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0)
    case "$m" in ''|*[!0-9]*) m=0 ;; esac
    echo "$m"
}

# The newest backend/.env under your home folder (skipping Library and hidden or heavy folders).
search_bgf() {
    local f d m best="" newest=-1
    while IFS= read -r f; do
        d="${f%/backend/.env}"
        is_bgf "$d" || continue
        m=$(mtime "$f")
        if [ "$m" -gt "$newest" ]; then newest=$m; best=$d; fi
    done < <(find "$HOME" -maxdepth 5 \( -type d \( -name Library -o -name Applications -o -name node_modules -o -name '.*' \) \) -prune \
                -o -path '*/backend/.env' -type f -print 2>/dev/null)
    [ -n "$best" ] && printf '%s\n' "$best"
}

find_bgf() {
    local c d
    if [ -n "${BGF_DIR:-}" ]; then
        if is_bgf "$BGF_DIR"; then abs "$BGF_DIR"; return 0; fi
        warn "BGF_DIR=$BGF_DIR has no start.sh and backend/main.py — ignoring it" >&2
    fi
    for c in "$HERE/.." "$HOME/Documents/ImaginariumOzone" "$HOME/ImaginariumOzone" "$HOME/Desktop/ImaginariumOzone" \
             "$HOME/Developer/ImaginariumOzone" "$HOME/Projects/ImaginariumOzone" "$HOME/Documents/GitHub/ImaginariumOzone" \
             "$HOME/GitHub/ImaginariumOzone" "$HOME/code/ImaginariumOzone" "$HOME/dev/ImaginariumOzone"; do
        if has_bgf_env "$c"; then abs "$c"; return 0; fi
    done
    d=$(search_bgf)
    [ -n "$d" ] && { printf '%s\n' "$d"; return 0; }
    return 1
}

find_comfy() {
    local c d
    for c in "$HOME/ComfyUI" "$HOME/Documents/ComfyUI" "$HOME/Documents/GitHub/ComfyUI" "$HOME/Developer/ComfyUI" \
             "$HOME/Projects/ComfyUI" "$HOME/code/ComfyUI" "$HOME/Desktop/ComfyUI" "$HOME/Applications/ComfyUI"; do
        if is_comfy "$c"; then abs "$c"; return 0; fi
    done
    d=$(find "$HOME" -maxdepth 4 \( -type d \( -name Library -o -name Applications -o -name node_modules -o -name '.*' \) \) -prune \
            -o -path '*/ComfyUI/main.py' -type f -print 2>/dev/null | head -n 1)
    d=${d%/main.py}
    [ -n "$d" ] && is_comfy "$d" && { printf '%s\n' "$d"; return 0; }
    return 1
}

BGF=$(find_bgf) || BGF=""
if [ -z "$BGF" ] && [ -t 0 ]; then
    say "  I couldn't find your BGF Production OS folder (the one with start.sh and backend/.env)."
    printf '  Drag that folder into this window and press Enter, or just press Enter to skip: '
    IFS= read -r ans
    ans=$(printf '%s' "$ans" | sed -e 's/\\\(.\)/\1/g' -e "s/^[\"']//" -e "s/[\"']\$//" -e 's/[[:space:]]*$//')
    if [ -n "$ans" ] && is_bgf "$ans"; then BGF=$(abs "$ans"); fi
fi
if [ -n "$BGF" ]; then
    ok "BGF Production OS: $BGF"
else
    warn "BGF Production OS folder not found. Re-run with:  BGF_DIR=/path/to/your/folder bash install.sh"
fi

COMFY=""
if ! is_comfy "$HOME/ComfyUI"; then COMFY=$(find_comfy) || COMFY=""; fi

# ── carry over settings from the previous LaunchAI ────────────────────────────
OLD=""
for c in "$APP/Contents/MacOS/$APP_NAME" "$HOME/Applications/$APP_NAME.app/Contents/MacOS/$APP_NAME" \
         "/Applications/$APP_NAME.app/Contents/MacOS/$APP_NAME"; do
    [ -f "$c" ] && { OLD=$c; break; }
done

old_value() {   # the value of VAR="…" in the old launcher, with comment and quotes removed
    grep -m1 "^$1=" "$OLD" 2>/dev/null | sed -e 's/^[A-Z_]*=//' -e 's/[[:space:]]*#.*$//' -e 's/^"//' -e 's/"$//'
}

expand() {      # resolve the few variables the old launcher used in its values
    local v=$1
    v=${v//\$\{HOME\}/$HOME}; v=${v//\$HOME/$HOME}; v=${v//\$COMFYUI_DIR/${OLD_COMFY:-$HOME/ComfyUI}}
    printf '%s' "$v"
}

carried_settings() {   # prints VAR=value lines for anything you had changed from the old defaults
    local pair var default val
    [ -n "$OLD" ] || return 0
    OLD_COMFY=$(expand "$(old_value COMFYUI_DIR)")
    for pair in "COMFYUI_DIR|$HOME/ComfyUI" "COMFYUI_PORT|8188" "COMFYUI_PYTHON|${OLD_COMFY:-$HOME/ComfyUI}/venv/bin/python" \
                "CLAUDE_APP|Claude" "CHROME_APP|Google Chrome" "OPEN_WEBUI_PORT|3000"; do
        var=${pair%%|*}; default=${pair#*|}
        val=$(expand "$(old_value "$var")")
        if [ -n "$val" ] && [ "$val" != "$default" ]; then printf '%s=%q\n' "$var" "$val"; fi
    done
}

# ── settings files ────────────────────────────────────────────────────────────
mkdir -p "$LAUNCHAI_HOME/run"
if [ -f "$CONFIG" ]; then
    ok "Kept your settings: $CONFIG"
else
    cp "$HERE/config.example.sh" "$CONFIG"
    carried=$(carried_settings)
    if [ -n "$carried" ]; then
        { printf '\n# ── Carried over from your previous LaunchAI ──\n'; printf '%s\n' "$carried"; } >>"$CONFIG"
        ok "Carried over from your old LaunchAI: $(printf '%s\n' "$carried" | cut -d= -f1 | tr '\n' ' ')"
    fi
    ok "Settings file: $CONFIG"
fi

{   # what this installer detected — rewritten every run; your edits belong in config.sh, which wins
    echo "# Written by install.sh and re-created every time it runs. Put your own changes in config.sh."
    printf 'BGF_DIR=%q\n' "$BGF"
    [ -n "$COMFY" ] && printf 'COMFYUI_DIR=%q\n' "$COMFY"
    # A Finder-launched app starts with a bare PATH. Keep the one your Terminal has, so node, python and ollama resolve.
    printf 'TERMINAL_PATH=%q\n' "$PATH"
} >"$ENVFILE"
[ -n "$COMFY" ] && ok "ComfyUI: $COMFY"

for t in node npm python3; do
    command -v "$t" >/dev/null 2>&1 || warn "$t isn't on your Terminal's PATH — the BGF dashboard needs node and python (see BGF_USER_GUIDE.md §1)"
done

# ── build the app ─────────────────────────────────────────────────────────────
rm -rf "$APP"      # replaces the previous version
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" "$DEST_DIR"
cp "$HERE/launchai.sh" "$APP/Contents/MacOS/$APP_NAME"
chmod +x "$APP/Contents/MacOS/$APP_NAME"
cp "$HERE/LaunchAI.icns" "$APP/Contents/Resources/$APP_NAME.icns"
cat >"$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>               <string>$APP_NAME</string>
  <key>CFBundleDisplayName</key>        <string>$APP_NAME</string>
  <key>CFBundleIdentifier</key>         <string>com.local.launchai</string>
  <key>CFBundleVersion</key>            <string>2.0</string>
  <key>CFBundleShortVersionString</key> <string>2.0</string>
  <key>CFBundleExecutable</key>         <string>$APP_NAME</string>
  <key>CFBundleIconFile</key>           <string>$APP_NAME</string>
  <key>CFBundlePackageType</key>        <string>APPL</string>
  <key>NSHighResolutionCapable</key>    <true/>
</dict>
</plist>
PLIST
ok "Built $APP"

# The same script, for the command line:  ~/.launchai/launchai stop  |  ~/.launchai/launchai diagnose
cp "$HERE/launchai.sh" "$LAUNCHAI_HOME/launchai"
chmod +x "$LAUNCHAI_HOME/launchai"

# Make Finder pick up the new icon.
xattr -cr "$APP" 2>/dev/null || true
touch "$APP"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP" >/dev/null 2>&1 || true
killall Finder 2>/dev/null || true

for other in "$HOME/Applications/$APP_NAME.app" "/Applications/$APP_NAME.app"; do
    [ -d "$other" ] && warn "There is another copy at $other — delete it if you don't use it."
done

cat <<DONE

Done. LaunchAI is on your Desktop.

  Click it to start: Ollama, ComfyUI, the BGF Production OS and Claude, with the
  BGF dashboard and ComfyUI opened in Chrome. A notification tells you when it is up.

  The first time, macOS may ask whether LaunchAI can access your Documents folder or
  show notifications. Click Allow — the BGF folder lives there.

  Stop everything it started:   ~/.launchai/launchai stop
  Something not working?        ~/.launchai/launchai diagnose | pbcopy     (then paste it to Claude)
  Change settings:              open -e ~/.launchai/config.sh

DONE
