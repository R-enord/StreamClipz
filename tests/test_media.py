"""Media checks. Clips are generated with ffmpeg here, so no real footage is stored in the repo."""

import shutil
import subprocess
from pathlib import Path

import pytest

from core import media


def make_clip(path: Path, width: int, height: int, seconds: float, audio: bool) -> Path:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-f", "lavfi", "-i", f"testsrc=size={width}x{height}:rate=30:duration={seconds}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={seconds}"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    cmd += ["-c:a", "aac", "-shortest"] if audio else ["-an"]
    cmd.append(str(path))
    subprocess.run(cmd, check=True, capture_output=True)
    return path


needs_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg and ffprobe are needed for these tests",
)


@needs_ffmpeg
def test_probe_reads_size_duration_and_audio(tmp_path):
    clip = make_clip(tmp_path / "clip.mp4", 720, 900, 3.0, audio=True)
    info = media.probe(clip)
    assert (info.width, info.height) == (720, 900)
    assert 2.5 < info.duration_s < 3.5
    assert info.has_video and info.has_audio
    assert info.audio_codec == "aac"
    assert not info.is_9_16  # 4:5 is not the 9:16 output we make


@needs_ffmpeg
def test_review_blocks_a_file_with_no_sound(tmp_path):
    clip = make_clip(tmp_path / "silent.mp4", 720, 1280, 4.0, audio=False)
    review = media.review_for_social(media.probe(clip))
    assert not review.ok
    assert any("no sound" in problem for problem in review.blocking)


@needs_ffmpeg
def test_loudness_is_measured_in_lufs(tmp_path):
    clip = make_clip(tmp_path / "tone.mp4", 720, 1280, 4.0, audio=True)
    loudness = media.integrated_loudness(clip)
    assert -70.0 < loudness < 0.0


@needs_ffmpeg
def test_probe_rejects_a_file_that_is_not_media(tmp_path):
    fake = tmp_path / "not-a-video.mp4"
    fake.write_text("this is text, not a video")
    with pytest.raises(media.MediaError):
        media.probe(fake)


def test_missing_ffprobe_gives_a_plain_message(tmp_path, monkeypatch):
    monkeypatch.setattr(media.shutil, "which", lambda name: None)
    with pytest.raises(media.MediaToolMissing, match="ffmpeg"):
        media.probe(tmp_path / "anything.mp4")


def test_rotation_swaps_width_and_height():
    phone_video = {"width": 1920, "height": 1080, "tags": {"rotate": "90"}}
    assert media.display_size(phone_video) == (1080, 1920)
    flat = {"width": 720, "height": 900}
    assert media.display_size(flat) == (720, 900)


def test_review_flags_short_and_non_916_pictures():
    info = media.MediaInfo(duration_s=2.0, width=720, height=900, fps=60.0, has_video=True,
                           has_audio=True, video_codec="h264", audio_codec="aac")
    review = media.review_for_social(info)
    assert any("only 2.0 s" in problem for problem in review.blocking)
    assert any("reframed to 9:16" in note for note in review.notes)
