import asyncio
import json
import subprocess
from pathlib import Path
from typing import Optional
import config

FFMPEG = config.FFMPEG_PATH

async def upscale_clip(input_path: Path, output_path: Path) -> Path:
    """Upscale Wan2.2 832x480 output to 1920x1080 with lanczos."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG, "-y", "-i", str(input_path),
        "-vf", "scale=1920:1080:flags=lanczos",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        str(output_path)
    ]
    await _run(cmd)
    return output_path

async def generate_narration(text: str, output_path: Path, voice: str = "Alex", rate: int = 160) -> Path:
    """Generate TTS audio. Tries ElevenLabs first (if configured);
    falls back to macOS say."""
    from services import elevenlabs_client

    result = await elevenlabs_client.synthesize(text, output_path)
    if result is not None:
        return result

    output_path.parent.mkdir(parents=True, exist_ok=True)
    aiff_path = output_path.with_suffix(".aiff")
    say_cmd = ["say", "-v", voice, "-r", str(rate), "-o", str(aiff_path), text]
    proc = await asyncio.create_subprocess_exec(
        *say_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await proc.communicate()
    # Convert to mp3
    cmd = [
        FFMPEG, "-y", "-i", str(aiff_path),
        "-ar", "44100", "-ac", "2", "-ab", "192k",
        str(output_path)
    ]
    await _run(cmd)
    aiff_path.unlink(missing_ok=True)
    return output_path

async def master_narration(input_path: Path, output_path: Path,
                            drone_path: Optional[Path] = None) -> Path:
    """
    P5.5 BGF mastering chain (BGF_PROMPT_STACK.md).

    silenceremove (max 0.5s gap) -> optional D-minor drone bed at -20dB
    -> loudnorm -14 LUFS / -1 dBTP -> 48kHz 24-bit mono WAV.

    The -14 LUFS target is YouTube spec; -16 (the generic web value) leaves
    the episode quiet against the platform's normalization.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    trim = ("silenceremove=stop_periods=-1:stop_duration=0.5:stop_threshold=-50dB")
    loud = "loudnorm=I=-14:TP=-1:LRA=11"

    if drone_path and drone_path.exists():
        cmd = [
            FFMPEG, "-y", "-i", str(input_path), "-i", str(drone_path),
            "-filter_complex",
            f"[0:a]{trim}[vo];"
            f"[1:a]volume=-20dB,aloop=loop=-1:size=2e9[bed];"
            f"[vo][bed]amix=inputs=2:duration=first:dropout_transition=0,{loud}[out]",
            "-map", "[out]",
        ]
    else:
        cmd = [FFMPEG, "-y", "-i", str(input_path), "-af", f"{trim},{loud}"]

    cmd += ["-ar", "48000", "-ac", "1", "-c:a", "pcm_s24le", str(output_path)]
    await _run(cmd)
    return output_path


async def normalize_audio(input_path: Path, output_path: Path) -> Path:
    """EBU R128 loudness normalization."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG, "-y", "-i", str(input_path),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        str(output_path)
    ]
    await _run(cmd)
    return output_path

async def assemble_episode(scene_clips: list[Path], narration_clips: list[Path],
                            output_path: Path, music_path: Optional[Path] = None) -> Path:
    """
    Assemble final episode from ordered scene clips and narration audio.

    scene_clips: list of video file Paths (1920x1080, ordered by scene)
    narration_clips: list of audio file Paths (one per scene, synced)
    output_path: destination .mp4
    music_path: optional background music track
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_path.parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)

    # Step 1: Concat narration audio
    narration_concat = tmp_dir / "narration_concat.mp3"
    concat_list = tmp_dir / "narration_list.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in narration_clips))
    cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0",
           "-i", str(concat_list), "-c", "copy", str(narration_concat)]
    await _run(cmd)

    # Step 2: Build xfade filter_complex for video clips
    n = len(scene_clips)
    if n == 1:
        video_only = tmp_dir / "video_only.mp4"
        cmd = [FFMPEG, "-y", "-i", str(scene_clips[0]),
               "-c:v", "libx264", "-crf", "18", str(video_only)]
        await _run(cmd)
    else:
        # Calculate durations
        durations = [await get_duration(p) for p in scene_clips]
        video_only = await _xfade_concat(scene_clips, durations, tmp_dir)

    # Step 3: Mix audio and mux with video
    inputs = ["-i", str(video_only), "-i", str(narration_concat)]
    filter_parts = ["[1:a]volume=1.0[narration]"]
    map_args = ["-map", "0:v", "-map", "[aout]"]

    if music_path and music_path.exists():
        total_duration = await get_duration(video_only)
        fade_start = max(0, total_duration - 5)
        inputs += ["-i", str(music_path)]
        filter_parts.append(
            f"[2:a]volume=0.12,afade=t=in:ss=0:d=3,"
            f"afade=t=out:st={fade_start:.1f}:d=5[music]"
        )
        filter_parts.append("[narration][music]amix=inputs=2:duration=first:weights=1 0.12[aout]")
    else:
        filter_parts.append("[narration]acopy[aout]")

    cmd = ([FFMPEG, "-y"] + inputs +
           ["-filter_complex", ";".join(filter_parts)] +
           map_args +
           ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(output_path)])
    await _run(cmd)
    return output_path

async def _xfade_concat(clips: list[Path], durations: list[float], tmp_dir: Path) -> Path:
    n = len(clips)
    transition_duration = 0.5
    inputs = []
    for p in clips:
        inputs += ["-i", str(p)]
    filter_parts = []
    offsets = []
    cumulative = 0.0
    for i, d in enumerate(durations[:-1]):
        cumulative += d - transition_duration
        offsets.append(cumulative)
    # Build xfade chain
    prev = "0:v"
    for i in range(n - 1):
        out_label = f"[v{i+1}]" if i < n - 2 else "[vout]"
        filter_parts.append(
            f"[{prev}][{i+1}:v]xfade=transition=fade:"
            f"duration={transition_duration}:offset={offsets[i]:.3f}{out_label}"
        )
        prev = f"v{i+1}"

    out = tmp_dir / "video_only.mp4"
    cmd = ([FFMPEG, "-y"] + inputs +
           ["-filter_complex", ";".join(filter_parts),
            "-map", "[vout]",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-pix_fmt", "yuv420p", str(out)])
    await _run(cmd)
    return out

async def extract_thumbnail(video_path: Path, output_path: Path, timestamp: str = "00:00:05") -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG, "-y", "-ss", timestamp,
        "-i", str(video_path),
        "-vframes", "1", "-q:v", "2",
        str(output_path)
    ]
    await _run(cmd)
    return output_path

async def get_duration(path: Path) -> float:
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
    return float(stdout.decode().strip())

async def _run(cmd: list):
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed (code {proc.returncode}):\n{stderr.decode()[-2000:]}")
