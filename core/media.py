"""Checks for media files: what is inside a file, and whether it is fit for a social post.

These checks call ffprobe and ffmpeg, which must be installed. If they are missing, the
functions raise MediaToolMissing with a plain message.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Defaults for short vertical video. These are conventions we chose, not platform rules.
TARGET_ASPECT = 9 / 16
TARGET_WIDTH, TARGET_HEIGHT = 1080, 1920
TARGET_LUFS = -16.0

_LUFS_SUMMARY = re.compile(r"I:\s+(-?\d+(?:\.\d+)?)\s+LUFS")


class MediaError(Exception):
    """The file could not be read or measured."""


class MediaToolMissing(MediaError):
    """ffprobe or ffmpeg is not installed or not on PATH."""


@dataclass(frozen=True)
class MediaInfo:
    duration_s: float
    width: int
    height: int
    fps: float
    has_video: bool
    has_audio: bool
    video_codec: str | None
    audio_codec: str | None

    @property
    def aspect(self) -> float:
        return self.width / self.height if self.height else 0.0

    @property
    def is_9_16(self) -> bool:
        return abs(self.aspect - TARGET_ASPECT) < 0.01


@dataclass
class ReviewResult:
    blocking: list[str] = field(default_factory=list)  # must be fixed before the clip is used
    notes: list[str] = field(default_factory=list)  # shown to the reviewer, not blocking

    @property
    def ok(self) -> bool:
        return not self.blocking


def _tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise MediaToolMissing(f"{name} is not installed or not on PATH. Install ffmpeg and try again.")
    return path


def _parse_fps(value: str | None) -> float:
    if not value or "/" not in value:
        return 0.0
    numerator, denominator = value.split("/", 1)
    try:
        return float(numerator) / float(denominator) if float(denominator) else 0.0
    except ValueError:
        return 0.0


def display_size(stream: dict[str, Any]) -> tuple[int, int]:
    """Width and height as people see them. Phones store a rotation, which swaps the two."""
    width, height = int(stream.get("width") or 0), int(stream.get("height") or 0)
    rotations = [str((stream.get("tags") or {}).get("rotate", "0"))]
    rotations += [str(item.get("rotation", "0")) for item in stream.get("side_data_list", [])]
    if any(abs(int(float(r))) % 180 == 90 for r in rotations if _is_number(r)):
        width, height = height, width
    return width, height


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def probe(path: Path) -> MediaInfo:
    ffprobe = _tool("ffprobe")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise MediaError(f"ffprobe could not read {path.name}: {result.stderr.strip()[:300]}")
    data = json.loads(result.stdout or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is None and audio is None:
        raise MediaError(f"{path.name} has no video or audio streams")
    duration = float((data.get("format") or {}).get("duration") or 0.0)
    if duration == 0.0 and video is not None:
        duration = float(video.get("duration") or 0.0)
    width, height = display_size(video) if video else (0, 0)
    return MediaInfo(
        duration_s=round(duration, 3),
        width=width,
        height=height,
        fps=round(_parse_fps((video or {}).get("avg_frame_rate")), 3),
        has_video=video is not None,
        has_audio=audio is not None,
        video_codec=(video or {}).get("codec_name"),
        audio_codec=(audio or {}).get("codec_name"),
    )


def integrated_loudness(path: Path) -> float:
    """Integrated loudness in LUFS (EBU R128). Raises MediaError if no audio can be measured."""
    ffmpeg = _tool("ffmpeg")
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True,
        text=True,
        timeout=600,
    )
    values = _LUFS_SUMMARY.findall(result.stderr)
    if not values:
        raise MediaError(f"could not measure loudness of {path.name} (no audio?)")
    return float(values[-1])


def review_for_social(
    info: MediaInfo, *, min_seconds: float = 3.0, max_seconds: float = 180.0
) -> ReviewResult:
    """What must be fixed, and what the reviewer should know, before a clip from this file is used."""
    result = ReviewResult()
    if not info.has_video:
        result.blocking.append("the file has no picture")
    if not info.has_audio:
        result.blocking.append("the file has no sound: add the audio file as well")
    if info.duration_s < min_seconds:
        result.blocking.append(f"the file is only {info.duration_s:.1f} s long (minimum {min_seconds:.0f} s)")
    if info.duration_s > max_seconds:
        result.notes.append(f"the file is {info.duration_s / 60:.0f} minutes long: cut moments from it")
    if info.has_video and not info.is_9_16:
        result.notes.append(
            f"the picture is {info.width}x{info.height}; clips will be reframed to 9:16"
        )
    return result
