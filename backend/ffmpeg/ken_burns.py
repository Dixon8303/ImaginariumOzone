import asyncio
import subprocess
from pathlib import Path
import config

FFMPEG = config.FFMPEG_PATH

async def apply_ken_burns(input_path: Path, output_path: Path,
                           motion: str, duration_s: int) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fps = 24
    total_frames = duration_s * fps

    motion_map = {
        "zoom_in":    _zoom_in_filter,
        "zoom_out":   _zoom_out_filter,
        "pan_left":   _pan_left_filter,
        "pan_right":  _pan_right_filter,
        "slow_push":  _slow_push_filter,
        "static":     _static_filter,
    }
    vf = motion_map.get(motion, _static_filter)(total_frames)

    cmd = [
        FFMPEG, "-y",
        "-loop", "1",
        "-i", str(input_path),
        "-vf", vf,
        "-t", str(duration_s),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        str(output_path)
    ]
    await _run(cmd)
    return output_path

def _zoom_in_filter(total_frames: int) -> str:
    return (
        f"scale=8000:-1,"
        f"zoompan=z='if(lte(zoom,1.0),1.0,zoom-0.0015)':d={total_frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=24,"
        f"scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    )

def _zoom_out_filter(total_frames: int) -> str:
    return (
        f"scale=8000:-1,"
        f"zoompan=z='if(gte(zoom,1.3),1.3,zoom+0.001)':d={total_frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=24,"
        f"scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    )

def _pan_right_filter(total_frames: int) -> str:
    return (
        f"scale=8000:-1,"
        f"zoompan=z='1.1':x='(iw/2-(iw/zoom/2))*on/{total_frames}':"
        f"y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps=24,"
        f"scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    )

def _pan_left_filter(total_frames: int) -> str:
    return (
        f"scale=8000:-1,"
        f"zoompan=z='1.1':x='(iw/2-(iw/zoom/2))*(1-on/{total_frames})':"
        f"y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps=24,"
        f"scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    )

def _slow_push_filter(total_frames: int) -> str:
    return (
        f"scale=8000:-1,"
        f"zoompan=z='1.0+0.0005*on':d={total_frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=24,"
        f"scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    )

def _static_filter(_total_frames: int) -> str:
    return (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    )

async def _run(cmd: list):
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg ken_burns failed:\n{stderr.decode()[-2000:]}")
