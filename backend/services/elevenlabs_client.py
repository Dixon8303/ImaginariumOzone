"""
ElevenLabs TTS client — premium voiceover for P5.

Falls back gracefully: if ELEVENLABS_API_KEY is unset or the API call
fails, the caller (assembler.generate_narration) uses macOS `say`.
"""

import asyncio
from pathlib import Path
import config

try:
    import aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False

API_BASE = "https://api.elevenlabs.io/v1"

# Documentary narration settings — stability high for consistent tone,
# style low to avoid theatrical drift over long reads
VOICE_SETTINGS = {
    "stability": 0.65,
    "similarity_boost": 0.80,
    "style": 0.15,
    "use_speaker_boost": True,
}


def is_configured() -> bool:
    return bool(config.ELEVENLABS_API_KEY) and _AIOHTTP_AVAILABLE


async def synthesize(text: str, output_path: Path, voice_id: str = None) -> Path | None:
    """
    Generate speech via ElevenLabs. Returns the output path on success,
    None on any failure (caller falls back to macOS say).
    Output is MP3 44.1kHz 192kbps — same format the assembler expects.
    """
    if not is_configured():
        return None
    vid = voice_id or config.ELEVENLABS_VOICE_ID
    url = f"{API_BASE}/text-to-speech/{vid}"
    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": VOICE_SETTINGS,
        "output_format": "mp3_44100_192",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    return None
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(await resp.read())
                return output_path
    except Exception:
        return None


async def list_voices() -> list[dict]:
    """Return available voices [{voice_id, name, category}] or [] on failure."""
    if not is_configured():
        return []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE}/voices",
                headers={"xi-api-key": config.ELEVENLABS_API_KEY},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return [
                    {"voice_id": v["voice_id"], "name": v["name"],
                     "category": v.get("category", "")}
                    for v in data.get("voices", [])
                ]
    except Exception:
        return []
