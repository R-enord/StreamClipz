"""Render finished clips: 9:16 video, on-screen captions, a progress bar and even loudness.

Two styles are built first:

- keyword_punch: one or two big outlined words at a time. A word wrapped in *stars* is shown
  in colour. The picture is cut to 9:16 from the middle (or from a box you give).
- streamer_split: the streamer's face on top (40 percent of the frame), gameplay below
  (60 percent). Captions sit over the gameplay.

Everything runs through ffmpeg on this computer. Source files are never changed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .content import plan_caption_beats
from .media import MediaError, MediaToolMissing, probe

OUT_W, OUT_H = 1080, 1920
STYLES = ("keyword_punch", "streamer_split")
LOUDNESS = "loudnorm=I=-16:TP=-1.5:LRA=11"


@dataclass(frozen=True)
class Box:
    """A crop box as fractions of the source picture (0 to 1), so it works at any resolution."""

    x: float
    y: float
    w: float
    h: float

    def __post_init__(self) -> None:
        inside = 0 <= self.x < 1 and 0 <= self.y < 1
        fits = 0 < self.w <= 1 - self.x and 0 < self.h <= 1 - self.y
        if not (inside and fits):
            raise ValueError("a crop box must lie inside the picture, as fractions from 0 to 1")


@dataclass(frozen=True)
class CaptionLine:
    start_s: float
    end_s: float
    text: str


@dataclass(frozen=True)
class RenderSpec:
    source: Path
    start_s: float
    end_s: float
    style: str
    captions: list[CaptionLine]
    output: Path
    face_box: Box | None = None
    game_box: Box | None = None
    keyword_rgb: str = "FFE000"
    progress_rgb: str = "FF3EA5"


def _even(value: float) -> int:
    rounded = int(round(value))
    return rounded - (rounded % 2)


def crop_for_aspect(
    box: Box | None, src_w: int, src_h: int, out_w: int, out_h: int
) -> tuple[int, int, int, int]:
    """Pixel crop (width, height, x, y) inside the box, cut to the output's shape and centred."""
    if src_w <= 0 or src_h <= 0:
        raise ValueError("the source picture has no size")
    box = box or Box(0.0, 0.0, 1.0, 1.0)
    left, top = box.x * src_w, box.y * src_h
    width, height = box.w * src_w, box.h * src_h
    target = out_w / out_h
    if width / height > target:
        new_w, new_h = height * target, height
    else:
        new_w, new_h = width, width / target
    x = left + (width - new_w) / 2
    y = top + (height - new_h) / 2
    w, h = _even(new_w), _even(new_h)
    x = _even(min(max(x, 0), src_w - w))
    y = _even(min(max(y, 0), src_h - h))
    return w, h, x, y


def filtergraph(spec: RenderSpec, src_w: int, src_h: int) -> str:
    if spec.style not in STYLES:
        raise ValueError(f"unknown style {spec.style!r}; use one of: {', '.join(STYLES)}")
    length = spec.end_s - spec.start_s
    progress = (
        f"drawbox=x=0:y=ih-18:w=iw*t/{length:.3f}:h=18:color=0x{spec.progress_rgb}@0.95:t=fill"
    )
    if spec.style == "keyword_punch":
        w, h, x, y = crop_for_aspect(spec.game_box, src_w, src_h, OUT_W, OUT_H)
        video = (
            f"[0:v]crop={w}:{h}:{x}:{y},scale={OUT_W}:{OUT_H},setsar=1,"
            f"ass=captions.ass,{progress}[v]"
        )
    else:
        top_h = int(OUT_H * 0.4)
        bottom_h = OUT_H - top_h
        face = spec.face_box or Box(0.0, 0.0, 0.3, 0.3)
        fw, fh, fx, fy = crop_for_aspect(face, src_w, src_h, OUT_W, top_h)
        gw, gh, gx, gy = crop_for_aspect(spec.game_box, src_w, src_h, OUT_W, bottom_h)
        video = (
            "[0:v]split=2[face][game];"
            f"[face]crop={fw}:{fh}:{fx}:{fy},scale={OUT_W}:{top_h},setsar=1[top];"
            f"[game]crop={gw}:{gh}:{gx}:{gy},scale={OUT_W}:{bottom_h},setsar=1[bottom];"
            f"[top][bottom]vstack=inputs=2,ass=captions.ass,{progress}[v]"
        )
    return f"{video};[0:a]{LOUDNESS}[a]"


def ass_colour(rgb: str) -> str:
    """'FFE000' (red, green, blue) becomes '&H00E0FF&', because ASS stores blue first."""
    rgb = rgb.upper()
    if len(rgb) != 6:
        raise ValueError(f"a colour is six hex digits, for example FFE000; got {rgb!r}")
    return f"&H{rgb[4:6]}{rgb[2:4]}{rgb[0:2]}&"


def _ass_time(seconds: float) -> str:
    centiseconds = int(round(seconds * 100))
    hours, rest = divmod(centiseconds, 360000)
    minutes, rest = divmod(rest, 6000)
    secs, cs = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def _ass_text(text: str, keyword_rgb: str) -> str:
    safe = text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ").strip()
    highlight = ass_colour(keyword_rgb)
    pieces = []
    for index, part in enumerate(safe.split("*")):
        if index % 2 == 1 and part:
            pieces.append("{\\c" + highlight + "}" + part + "{\\c&HFFFFFF&}")
        else:
            pieces.append(part)
    return "".join(pieces)


def ass_document(spec: RenderSpec) -> str:
    margin = 560 if spec.style == "keyword_punch" else 330
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {OUT_W}\n"
        f"PlayResY: {OUT_H}\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Caption,Arial,96,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,"
        f"1,8,3,2,60,60,{margin},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events = [
        f"Dialogue: 0,{_ass_time(line.start_s)},{_ass_time(line.end_s)},Caption,,0,0,0,,"
        f"{_ass_text(line.text, spec.keyword_rgb)}"
        for line in spec.captions
    ]
    return header + "\n".join(events) + "\n"


def render(spec: RenderSpec) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise MediaToolMissing("ffmpeg is not installed or not on PATH. Install ffmpeg and try again.")
    if spec.style not in STYLES:
        raise ValueError(f"unknown style {spec.style!r}; use one of: {', '.join(STYLES)}")
    if spec.start_s < 0 or spec.end_s <= spec.start_s:
        raise ValueError("the clip must end after it starts")
    if not spec.captions:
        raise ValueError("add at least one caption")
    info = probe(spec.source)
    if not info.has_video:
        raise MediaError("the source has no picture")
    if not info.has_audio:
        raise MediaError("the source has no sound: add the audio file first")
    if spec.end_s > info.duration_s + 0.05:
        raise ValueError(f"the clip ends at {spec.end_s:.1f} s but the file is {info.duration_s:.1f} s long")

    length = spec.end_s - spec.start_s
    spec.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        workdir = Path(work)
        (workdir / "captions.ass").write_text(ass_document(spec), encoding="utf-8")
        command = [
            ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{spec.start_s:.3f}", "-i", str(spec.source), "-t", f"{length:.3f}",
            "-filter_complex", filtergraph(spec, info.width, info.height),
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(spec.output),
        ]
        result = subprocess.run(command, cwd=workdir, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0:
        raise MediaError(f"rendering failed: {result.stderr.strip()[-400:]}")
    return spec.output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m core.render", description="Render one clip with captions."
    )
    parser.add_argument("source", type=Path, help="the recording to cut from")
    parser.add_argument("--start", type=float, required=True, help="start, in seconds")
    parser.add_argument("--end", type=float, required=True, help="end, in seconds")
    parser.add_argument("--style", choices=STYLES, default="keyword_punch")
    parser.add_argument(
        "--captions", nargs="+", required=True,
        help='caption phrases, in order, e.g. "TRAILER. *GAME*." "CLIP THAT."',
    )
    parser.add_argument("--face", type=float, nargs=4, metavar=("X", "Y", "W", "H"),
                        help="streamer_split: where the face is, as fractions, e.g. 0 0 0.3 0.3")
    parser.add_argument("--out", type=Path, required=True, help="the finished MP4 to write")
    args = parser.parse_args(argv)

    beats = plan_caption_beats(args.end - args.start, args.captions)
    spec = RenderSpec(
        source=args.source,
        start_s=args.start,
        end_s=args.end,
        style=args.style,
        captions=[CaptionLine(beat.start_s, beat.end_s, beat.text) for beat in beats],
        output=args.out,
        face_box=Box(*args.face) if args.face else None,
    )
    render(spec)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
