"""Task 1.5 Review 修正：異常 metadata、ffprobe 失敗、VFR 邊界、主控台編碼（使用 mock）。"""

import io
import json
import subprocess
import sys

import pytest

import vball.video.probe as probe_mod
from vball.cli import _print_json
from vball.errors import ProbeError
from vball.video.probe import _duration_ms, _rate, _vfr_suspected, probe_video

GOOD_VIDEO = {
    "codec_type": "video", "codec_name": "h264", "width": 320, "height": 240,
    "r_frame_rate": "30/1", "avg_frame_rate": "30/1",
}
GOOD_INFO = {"streams": [GOOD_VIDEO], "format": {"duration": "3.0"}}


@pytest.fixture
def fake_file(tmp_path):
    f = tmp_path / "fake.mp4"
    f.write_bytes(b"x" * 10)
    return f


def _with_info(monkeypatch, info):
    monkeypatch.setattr(probe_mod, "_run_ffprobe", lambda p: info)


def test_mock_baseline_ok(monkeypatch, fake_file):
    _with_info(monkeypatch, GOOD_INFO)
    m = probe_video(fake_file)
    assert (m.duration_ms, m.width, m.height, m.is_vfr_suspected) == (3000, 320, 240, False)


@pytest.mark.parametrize(
    "info",
    [
        [],                                                        # 頂層不是 object
        "text",
        {"format": {"duration": "3"}},                             # 沒有 streams
        {"streams": None, "format": {"duration": "3"}},
        {"streams": ["bad", 1], "format": {"duration": "3"}},       # stream 元素不是 object
        {"streams": [{"codec_type": "audio"}], "format": {"duration": "3"}},  # 無 video
        {"streams": [{**GOOD_VIDEO, "width": None}], "format": {"duration": "3"}},
        {"streams": [{k: v for k, v in GOOD_VIDEO.items() if k != "width"}], "format": {"duration": "3"}},
        {"streams": [{**GOOD_VIDEO, "height": 0}], "format": {"duration": "3"}},
        {"streams": [{**GOOD_VIDEO, "width": "320"}], "format": {"duration": "3"}},
        {"streams": [{**GOOD_VIDEO, "width": True}], "format": {"duration": "3"}},
        {"streams": [GOOD_VIDEO], "format": {"duration": "inf"}},
        {"streams": [GOOD_VIDEO], "format": {"duration": "nan"}},
        {"streams": [GOOD_VIDEO], "format": {"duration": "0.0001"}},
        {"streams": [GOOD_VIDEO], "format": {"duration": None}},
        {"streams": [GOOD_VIDEO], "format": None},
    ],
)
def test_bad_metadata_is_invalid_video(monkeypatch, fake_file, info):
    _with_info(monkeypatch, info)
    with pytest.raises(ProbeError) as exc:
        probe_video(fake_file)
    assert exc.value.code == "INVALID_VIDEO"


def test_duration_falls_back_to_stream(monkeypatch, fake_file):
    _with_info(monkeypatch, {"streams": [{**GOOD_VIDEO, "duration": "2.5"}], "format": {"duration": "inf"}})
    assert probe_video(fake_file).duration_ms == 2500


def test_null_optional_fields_do_not_crash(monkeypatch, fake_file):
    video = {**GOOD_VIDEO, "codec_name": None, "r_frame_rate": None, "avg_frame_rate": None}
    _with_info(monkeypatch, {"streams": [video, {"codec_type": "audio", "codec_name": None}],
                             "format": {"duration": "3"}})
    m = probe_video(fake_file)
    assert m.video_codec == "unknown"
    assert m.fps_avg is None
    assert m.is_vfr_suspected is None
    assert m.has_audio is True and m.audio_codec is None


@pytest.mark.parametrize(
    "value, expected",
    [("30/1", 30.0), ("30000/1001", 29.97002997), ("0/0", None), ("abc", None), (None, None), ("", None)],
)
def test_rate(value, expected):
    assert _rate(value) == (pytest.approx(expected) if expected else None)


@pytest.mark.parametrize(
    "r, avg, expected",
    [
        (30.0, 30.0, False),
        (30.0, 29.71, False),   # 差 0.97%，低於門檻
        (30.0, 29.69, True),    # 差 1.03%，高於門檻
        (30.0, 20.0, True),
        (None, 30.0, None),
        (30.0, None, None),
    ],
)
def test_vfr_threshold(r, avg, expected):
    assert _vfr_suspected(r, avg) is expected


def test_duration_ms_rules():
    assert _duration_ms("inf", "-1", "0.0004", "1.234") == 1234
    assert _duration_ms(None, "abc") is None


# --- ffprobe 執行失敗 ---

def _ffprobe_present(monkeypatch):
    monkeypatch.setattr(probe_mod.shutil, "which", lambda name: "ffprobe")


def test_ffprobe_missing(monkeypatch, fake_file):
    monkeypatch.setattr(probe_mod.shutil, "which", lambda name: None)
    with pytest.raises(ProbeError) as exc:
        probe_video(fake_file)
    assert exc.value.code == "FFPROBE_NOT_FOUND"


@pytest.mark.parametrize(
    "error, code",
    [
        (FileNotFoundError("gone"), "FFPROBE_NOT_FOUND"),
        (PermissionError("denied"), "FFPROBE_FAILED"),
        (subprocess.TimeoutExpired("ffprobe", 30), "FFPROBE_FAILED"),
    ],
)
def test_ffprobe_launch_errors(monkeypatch, fake_file, error, code):
    _ffprobe_present(monkeypatch)

    def boom(*a, **k):
        raise error

    monkeypatch.setattr(probe_mod.subprocess, "run", boom)
    with pytest.raises(ProbeError) as exc:
        probe_video(fake_file)
    assert exc.value.code == code
    assert exc.value.__cause__ is error


def test_ffprobe_invalid_json(monkeypatch, fake_file):
    _ffprobe_present(monkeypatch)
    monkeypatch.setattr(
        probe_mod.subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="not json", stderr=""),
    )
    with pytest.raises(ProbeError) as exc:
        probe_video(fake_file)
    assert exc.value.code == "FFPROBE_FAILED"


# --- 主控台編碼（模擬 Windows cp950） ---

def _cp950_stream():
    return io.TextIOWrapper(io.BytesIO(), encoding="cp950", errors="strict")


def _read(stream) -> str:
    stream.flush()
    return stream.buffer.getvalue().decode("cp950")


def test_cp950_keeps_chinese_readable(monkeypatch):
    stream = _cp950_stream()
    monkeypatch.setattr(sys, "stdout", stream)
    data = {"path": "D:/排球/測試.mp4"}
    _print_json(data)
    out = _read(stream)
    assert "排球" in out
    assert json.loads(out) == data


def test_cp950_unencodable_falls_back_to_escaped_json(monkeypatch):
    stream = _cp950_stream()
    monkeypatch.setattr(sys, "stdout", stream)
    data = {"path": "D:/🏐/a.mp4"}
    _print_json(data)
    out = _read(stream)
    assert "\\ud83c\\udfd0" in out
    assert json.loads(out) == data


def test_cp950_stderr_does_not_crash(monkeypatch, tmp_path):
    from vball.cli import main

    raw = io.TextIOWrapper(io.BytesIO(), encoding="cp950", errors="strict")
    monkeypatch.setattr(sys, "stderr", raw)
    assert main(["probe", str(tmp_path / "🏐.mp4")]) == 1
    raw.flush()
    assert "[INPUT_NOT_FOUND]" in raw.buffer.getvalue().decode("cp950")
