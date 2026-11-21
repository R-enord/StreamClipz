"""Caption and layout rules, plus real renders of short synthetic clips."""

import shutil
import subprocess
from pathlib import Path

import pytest

from core import render
from core.media import integrated_loudness, probe

needs_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg and ffprobe are needed for these tests",
)


def spec_for(style="keyword_punch", **overrides):
    values = dict(
        source=Path("in.mp4"),
        start_s=0.0,
        end_s=10.0,
        style=style,
        captions=[render.CaptionLine(0.0, 5.0, "TRAILER. *GAME*. REACTION.")],
        output=Path("out.mp4"),
    )
    values.update(overrides)
    return render.RenderSpec(**values)


def make_source(path: Path, seconds: int = 12) -> Path:
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"testsrc=size=1920x1080:rate=30:duration={seconds}",
         "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={seconds}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)],
        check=True, capture_output=True,
    )
    return path


def test_crop_matches_the_output_shape_and_stays_inside_the_picture():
    w, h, x, y = render.crop_for_aspect(None, 1920, 1080, 1080, 1920)
    assert h == 1080 and abs(w / h - 9 / 16) < 0.01
    assert w % 2 == 0 and h % 2 == 0 and x + w <= 1920 and y + h <= 1080
    w2, h2, x2, y2 = render.crop_for_aspect(render.Box(0.0, 0.0, 0.3, 0.3), 1920, 1080, 1080, 768)
    assert x2 + w2 <= 576 and y2 + h2 <= 324


def test_a_box_outside_the_picture_is_refused():
    with pytest.raises(ValueError):
        render.Box(0.9, 0.0, 0.5, 1.0)


def test_keyword_punch_graph_has_captions_progress_bar_and_loudness():
    graph = render.filtergraph(spec_for("keyword_punch"), 1920, 1080)
    assert "scale=1080:1920" in graph
    assert "ass=captions.ass" in graph
    assert "drawbox" in graph
    assert "loudnorm=I=-16" in graph
    assert "vstack" not in graph


def test_streamer_split_stacks_face_above_gameplay():
    graph = render.filtergraph(spec_for("streamer_split"), 1920, 1080)
    assert "vstack=inputs=2" in graph
    assert "scale=1080:768" in graph and "scale=1080:1152" in graph


def test_starred_words_are_coloured_and_the_colour_is_reset():
    text = render.ass_document(spec_for())
    expected = (
        "Dialogue: 0,0:00:00.00,0:00:05.00,Caption,,0,0,0,,"
        "TRAILER. {\\c&H00E0FF&}GAME{\\c&HFFFFFF&}. REACTION."
    )
    assert expected in text


def test_unknown_style_is_refused():
    with pytest.raises(ValueError):
        render.filtergraph(spec_for("glitter"), 1920, 1080)


@needs_ffmpeg
def test_keyword_punch_makes_a_nine_by_sixteen_clip(tmp_path):
    source = make_source(tmp_path / "source.mp4")
    out = tmp_path / "punch.mp4"
    spec = render.RenderSpec(
        source=source, start_s=2.0, end_s=10.0, style="keyword_punch",
        captions=[render.CaptionLine(0.0, 4.0, "TRAILER. *GAME*. REACTION."),
                  render.CaptionLine(4.0, 8.0, "CLIP THAT.")],
        output=out,
    )
    render.render(spec)
    info = probe(out)
    assert (info.width, info.height) == (1080, 1920)
    assert abs(info.duration_s - 8.0) < 0.3 and info.has_audio
    assert abs(integrated_loudness(out) + 16.0) < 2.0


@needs_ffmpeg
def test_streamer_split_makes_a_nine_by_sixteen_clip(tmp_path):
    source = make_source(tmp_path / "source.mp4")
    out = tmp_path / "split.mp4"
    spec = render.RenderSpec(
        source=source, start_s=1.0, end_s=7.0, style="streamer_split",
        captions=[render.CaptionLine(0.0, 3.0, "PUNCH INTO *THE REACTION*."),
                  render.CaptionLine(3.0, 6.0, "READY TO DROP.")],
        output=out,
        face_box=render.Box(0.0, 0.0, 0.3, 0.3),
    )
    render.render(spec)
    info = probe(out)
    assert (info.width, info.height) == (1080, 1920)
    assert info.has_audio


@needs_ffmpeg
def test_a_clip_past_the_end_of_the_file_is_refused(tmp_path):
    source = make_source(tmp_path / "source.mp4", seconds=6)
    with pytest.raises(ValueError):
        render.render(spec_for(source=source, start_s=2.0, end_s=20.0, output=tmp_path / "x.mp4"))
