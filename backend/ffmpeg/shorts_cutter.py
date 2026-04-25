import asyncio
from pathlib import Path
import config

FFMPEG = config.FFMPEG_PATH

async def cut_short(source_video: Path, output_path: Path,
                     start_s: float, duration_s: float) -> Path:
    """Cut a clip and reformat to 9:16 vertical for Shorts."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Center-crop 1920x1080 to 1080x1920 (9:16)
    vf = (
        "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
    )
    cmd = [
        FFMPEG, "-y",
        "-ss", str(start_s),
        "-i", str(source_video),
        "-t", str(duration_s),
        "-vf", vf,
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path)
    ]
    await _run(cmd)
    return output_path

async def burn_captions(input_path: Path, output_path: Path, captions: list[dict]) -> Path:
    """
    Burn caption text onto a video.

    captions: list of {text: str, start: float, end: float}
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not captions:
        import shutil
        shutil.copy2(input_path, output_path)
        return output_path

    drawtext_filters = []
    for cap in captions:
        text = cap["text"].replace("'", "\\'").replace(":", "\\:")
        start = cap["start"]
        end = cap["end"]
        drawtext_filters.append(
            f"drawtext=text='{text}':"
            f"fontsize=52:fontcolor=white:bordercolor=black:borderw=3:"
            f"x=(w-text_w)/2:y=h*0.82:"
            f"enable='between(t,{start},{end})'"
        )

    vf = ",".join(drawtext_filters)
    cmd = [
        FFMPEG, "-y", "-i", str(input_path),
        "-vf", vf,
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "copy",
        str(output_path)
    ]
    await _run(cmd)
    return output_path

async def extract_shorts_from_episode(episode_video: Path, shorts_data: list,
                                       output_dir: Path) -> list[Path]:
    """
    Extract and format all Shorts from a finished episode video.

    shorts_data: list of Short objects from the shorts generation stage,
                 each must have: short_id, narration (for timing), duration_seconds
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    # For each short, we need start/end timecodes from the storyboard
    # If not provided, distribute evenly through the video
    total_duration = await _get_duration(episode_video)
    n = len(shorts_data)
    for i, short in enumerate(shorts_data):
        # Basic timecode distribution (will be replaced by storyboard markers in full impl)
        seg_duration = min(short.get("duration_seconds", 45), 59)
        start_s = (total_duration / max(n, 1)) * i
        start_s = min(start_s, total_duration - seg_duration - 1)
        short_id = short.get("short_id", f"short_{i}")
        raw_path = output_dir / f"{short_id}_raw.mp4"
        final_path = output_dir / f"{short_id}.mp4"
        await cut_short(episode_video, raw_path, start_s, seg_duration)
        # Burn captions if available
        captions = _build_captions(short.get("captions", []), seg_duration)
        await burn_captions(raw_path, final_path, captions)
        raw_path.unlink(missing_ok=True)
        results.append(final_path)
    return results

def _build_captions(caption_texts: list[str], total_duration: float) -> list[dict]:
    if not caption_texts:
        return []
    seg = total_duration / len(caption_texts)
    return [
        {"text": t, "start": round(i * seg, 2), "end": round((i + 1) * seg - 0.1, 2)}
        for i, t in enumerate(caption_texts)
    ]

async def _get_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return float(stdout.decode().strip() or "0")

async def _run(cmd: list):
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg shorts failed:\n{stderr.decode()[-2000:]}")
