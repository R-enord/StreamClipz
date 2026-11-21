"""Moment scanner: candidates, silence, spacing and the file reader. Test audio is generated here."""

import shutil
import wave
from pathlib import Path

import numpy as np
import pytest

from core import moments
from core.media import MediaError

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is needed for these tests")


def write_wav(path: Path, samples: np.ndarray, rate: int = moments.SAMPLE_RATE) -> Path:
    pcm = np.clip(samples * 32767, -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())
    return path


def stream_with_bursts(seconds: int, bursts: list[int], burst_s: int = 25) -> np.ndarray:
    rng = np.random.default_rng(1)
    audio = rng.normal(0.0, 0.01, seconds * moments.SAMPLE_RATE)  # quiet background, about -40 dBFS
    t = np.arange(moments.SAMPLE_RATE) / moments.SAMPLE_RATE
    loud = 0.5 * np.sin(2 * np.pi * 440 * t)  # about -6 dBFS
    for start in bursts:
        for second in range(burst_s):
            begin = (start + second) * moments.SAMPLE_RATE
            audio[begin:begin + moments.SAMPLE_RATE] = loud
    return audio


@needs_ffmpeg
def test_scan_finds_the_loud_stretches_of_a_long_recording(tmp_path):
    wav = write_wav(tmp_path / "stream.wav", stream_with_bursts(600, [120, 300, 480]))
    result = moments.scan(wav, top=5)
    centres = [(c["start_s"] + c["end_s"]) / 2 for c in result["candidates"]]
    for burst in (120, 300, 480):
        assert any(abs(centre - (burst + 12.5)) <= 10 for centre in centres), (burst, centres)
    assert result["duration_s"] == 600.0
    assert result["method"] == moments.METHOD


def test_silence_gives_no_candidates():
    rms = np.full(300, moments.SILENCE_DB - 60)
    peak = np.full(300, -120.0)
    assert moments.find_candidates(rms, peak) == []


def test_candidates_are_spread_out_in_time():
    rms = np.full(400, -40.0)
    rms[100:125] = -6.0  # one loud stretch
    rms[140:165] = -6.0  # another, only 40 s later
    peak = np.full(400, -30.0)
    peak[100:125] = -3.0
    peak[140:165] = -3.0
    picks = moments.find_candidates(rms, peak, top=10, min_gap_s=60)
    assert len(picks) == 1  # the second stretch is too close to be a separate pick


def test_reasons_say_what_was_found():
    rms = np.full(200, -40.0)
    rms[50:90] = -6.0
    peak = np.full(200, -30.0)
    peak[50:90] = -1.0
    (pick,) = moments.find_candidates(rms, peak, top=1)
    assert "sustained loudness" in pick.reasons and "sharp peak" in pick.reasons


@needs_ffmpeg
def test_a_file_without_sound_is_refused_plainly(tmp_path):
    not_audio = tmp_path / "notes.txt"
    not_audio.write_text("this is not a recording")
    with pytest.raises(MediaError):
        moments.per_second_levels(not_audio)


def test_parts_each_get_their_own_candidates():
    rms = np.full(600, -40.0)
    rms[100:125] = -6.0
    rms[400:425] = -6.0
    peak = np.full(600, -30.0)
    peak[100:125] = -3.0
    peak[400:425] = -3.0
    picks = moments.candidates_for_levels(rms, peak, top=3, chunk_s=300)
    assert {pick["part"] for pick in picks} == {1, 2}
    assert moments.chunk_ranges(600, 300) == [(0, 300), (300, 600)]
    assert moments.chunk_ranges(600, None) == [(0, 600)]
