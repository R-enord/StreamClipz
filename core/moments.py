"""Find candidate moments in long recordings. Runs on the computer that holds the files.

The scan reads only the audio, one second at a time, so a long stream never has to fit in
memory. It writes a short JSON list of time ranges for a person to review. Nothing is published,
and no video is re-encoded unless you ask for previews.

    python -m core.moments "D:\\streams\\stream.mkv" --out stream-moments.json --previews 5
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .media import MediaError, MediaToolMissing

SAMPLE_RATE = 8000  # enough for loudness; keeps the scan small and fast
SILENCE_DB = -60.0
METHOD = "audio-loudness v1"


@dataclass(frozen=True)
class Candidate:
    start_s: float
    end_s: float
    score: float
    mean_db: float
    peak_db: float
    reasons: list[str]


def _read_seconds(path: Path):
    """Yield the audio one second at a time as 16-bit mono samples."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise MediaToolMissing("ffmpeg is not installed or not on PATH. Install ffmpeg and try again.")
    command = [
        ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    bytes_per_second = SAMPLE_RATE * 2
    try:
        while True:
            chunk = process.stdout.read(bytes_per_second)
            if len(chunk) < 2:
                break
            usable = len(chunk) - (len(chunk) % 2)
            yield np.frombuffer(chunk[:usable], dtype=np.int16)
    finally:
        process.stdout.close()
        error = process.stderr.read().decode(errors="replace")
        code = process.wait()
    if code != 0:
        raise MediaError(
            f"could not read the audio of {path.name} (is there sound?): {error.strip()[:300]}"
        )


def per_second_levels(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Loudness (RMS, dBFS) and peak (dBFS) for every second of the file."""
    rms_db: list[float] = []
    peak_db: list[float] = []
    for samples in _read_seconds(path):
        x = samples.astype(np.float32) / 32768.0
        rms = float(np.sqrt(np.mean(x * x)))
        peak = float(np.max(np.abs(x)))
        rms_db.append(20 * math.log10(max(rms, 1e-6)))
        peak_db.append(20 * math.log10(max(peak, 1e-6)))
    if not rms_db:
        raise MediaError(f"{path.name} has no audio to scan")
    return np.array(rms_db), np.array(peak_db)


def find_candidates(
    rms_db: np.ndarray,
    peak_db: np.ndarray,
    *,
    window_s: int = 30,
    top: int = 20,
    min_gap_s: float = 60.0,  # extra space between picks, on top of the window length
    min_db_over_baseline: float = 6.0,
) -> list[Candidate]:
    """Pick the loudest sustained windows that are clearly above the stream's usual level."""
    n = len(rms_db)
    if n < window_s:
        return []
    active = rms_db > SILENCE_DB
    if active.any():
        baseline = float(np.median(rms_db[active]))
        spread = 1.4826 * float(np.median(np.abs(rms_db[active] - baseline)))
    else:
        baseline, spread = SILENCE_DB, 1.0
    spread = max(spread, 1.0)
    z = (rms_db - baseline) / spread

    kernel = np.ones(window_s) / window_s
    mean_z = np.convolve(z, kernel, mode="valid")
    mean_db = np.convolve(rms_db, kernel, mode="valid")
    silent_share = np.convolve((~active).astype(float), kernel, mode="valid")
    peak_window = np.array([peak_db[i:i + window_s].max() for i in range(n - window_s + 1)])

    chosen: list[Candidate] = []
    for i in np.argsort(-mean_z):
        if len(chosen) >= top:
            break
        if silent_share[i] > 0.5 or mean_db[i] - baseline < min_db_over_baseline:
            continue
        centre = i + window_s / 2
        # Two picks must be a whole window plus the gap apart, so they never share a moment.
        if any(abs(centre - (c.start_s + c.end_s) / 2) < window_s + min_gap_s for c in chosen):
            continue
        reasons = []
        if mean_z[i] >= 1.0:
            reasons.append("sustained loudness")
        if peak_window[i] - baseline >= 12.0:
            reasons.append("sharp peak")
        chosen.append(
            Candidate(
                start_s=float(i),
                end_s=float(i + window_s),
                score=round(float(mean_z[i]), 2),
                mean_db=round(float(mean_db[i]), 1),
                peak_db=round(float(peak_window[i]), 1),
                reasons=reasons or ["above the usual level"],
            )
        )
    return chosen


def chunk_ranges(total_s: int, chunk_s: int | None) -> list[tuple[int, int]]:
    """Split the timeline into parts of chunk_s seconds, or keep one part when chunk_s is None."""
    if not chunk_s:
        return [(0, total_s)]
    return [(start, min(start + chunk_s, total_s)) for start in range(0, total_s, chunk_s)]


def candidates_for_levels(
    rms_db: np.ndarray, peak_db: np.ndarray, *, top: int = 20, chunk_s: int | None = None
) -> list[dict]:
    """Candidates for each part of the timeline. Times are counted from the start of the file."""
    result: list[dict] = []
    for number, (start, end) in enumerate(chunk_ranges(len(rms_db), chunk_s), start=1):
        for pick in find_candidates(rms_db[start:end], peak_db[start:end], top=top):
            row = asdict(pick)
            row["start_s"] += start
            row["end_s"] += start
            row["part"] = number if chunk_s else None
            result.append(row)
    return result


def scan(path: Path, *, top: int = 20, chunk_s: int | None = None) -> dict:
    rms_db, peak_db = per_second_levels(path)
    return {
        "file": path.name,
        "duration_s": float(len(rms_db)),
        "method": METHOD,
        "parts": len(chunk_ranges(len(rms_db), chunk_s)),
        "note": "Candidates are starting points for review, not finished cuts.",
        "candidates": candidates_for_levels(rms_db, peak_db, top=top, chunk_s=chunk_s),
    }


def write_previews(
    path: Path, candidates: list[dict], out_dir: Path, count: int, height: int = 360
) -> list[Path]:
    """Short low-resolution previews of the top candidates, for review on a phone or in chat."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise MediaToolMissing("ffmpeg is not installed or not on PATH. Install ffmpeg and try again.")
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for rank, cand in enumerate(candidates[:count], start=1):
        target = out_dir / f"{rank:02d}_{int(cand['start_s'])}s.mp4"
        subprocess.run(
            [
                ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", str(cand["start_s"]), "-i", str(path), "-t", str(cand["end_s"] - cand["start_s"]),
                "-vf", f"scale=-2:{height}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                "-c:a", "aac", "-b:a", "96k", str(target),
            ],
            check=True,
        )
        written.append(target)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m core.moments", description=__doc__.split("\n")[0])
    parser.add_argument("video", type=Path, help="the recording to scan")
    parser.add_argument("--out", type=Path, required=True, help="where to write the JSON list")
    parser.add_argument("--top", type=int, default=20, help="how many candidates to keep")
    parser.add_argument("--previews", type=int, default=0, help="also write this many short previews")
    parser.add_argument("--chunk-hours", type=float, default=None, help="scan in parts this many hours long")
    args = parser.parse_args(argv)

    chunk_s = int(args.chunk_hours * 3600) if args.chunk_hours else None
    result = scan(args.video, top=args.top, chunk_s=chunk_s)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Found {len(result['candidates'])} candidates in {result['duration_s'] / 3600:.2f} h of audio.")
    print(f"List written to {args.out}")
    if args.previews:
        previews = write_previews(
            args.video, result["candidates"], args.out.with_suffix("") / "previews", args.previews
        )
        print(f"Wrote {len(previews)} previews to {args.out.with_suffix('') / 'previews'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
