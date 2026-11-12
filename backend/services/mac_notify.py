"""
Local macOS notifications for 'needs D' moments — CHECKPOINT gates,
HardHalts, and unexpected stage failures. Fired from the orchestrator
alongside the existing Mission Control sync.

Why not `osascript -e 'display notification'` (what n8n and LaunchAI's own
startup banner use today): AppleScript's notifier always posts under Script
Editor's identity and has no click target, so clicking it just raises Script
Editor — a dead end, not the decision screen. terminal-notifier posts under
its own identity and supports `-open <url>`, so clicking the notification
opens the Control Room page for that exact episode.

Degrades the same way every other optional integration in this file does:
if terminal-notifier isn't installed, this is a silent no-op. Nothing in the
pipeline depends on it. Install with `brew install terminal-notifier`.
"""

import asyncio
import shutil

import config

_BIN = shutil.which("terminal-notifier")


def is_configured() -> bool:
    return _BIN is not None


async def notify(episode_id: str, title: str, message: str, path: str = "control-room") -> None:
    """Fire a clickable local notification. No-op if terminal-notifier is absent."""
    if not is_configured():
        return
    url = f"{config.BGF_FRONTEND_URL}/episodes/{episode_id}/{path}"
    args = [
        _BIN,
        "-title", title,
        "-message", message,
        "-open", url,
        "-sender", "com.apple.Terminal",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
    except Exception:
        pass  # A notification must never take the pipeline down with it.
