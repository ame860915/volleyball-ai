"""Task 1.5 驗收：probe_video 與 vball probe（使用合成影片與真實影片）。"""

import json
import subprocess
import sys

import pytest

from vball.cli import main
from vball.errors import ProbeError
from vball.video.probe import probe_video

# 已在 2026-10-18 以 ffprobe 盤點確認的真實影片預期值（docs/ENVIRONMENT.md）
REAL_EXPECTED = {
    "20260719.mp4": {
        "duration_ms": 5935, "width": 872, "height": 490, "video_codec": "h264",
        "r_frame_rate": "30/1", "avg_frame_rate": "35400/1187", "fps_avg": 29.823,
        "is_vfr_suspected": False, "has_audio": True, "audio_codec": "aac",
        "size_bytes": 1628114,
    },
}


@pytest.mark.parametrize(
    "name, fps, has_audio, codec",
    [
        ("cfr30_audio.mp4", "30/1", True, "aac"),
        ("cfr60_audio.mp4", "60/1", True, "aac"),
        ("cfr30_noaudio.mp4", "30/1", False, None),
    ],
)
def test_cfr_metadata(videos, name, fps, has_audio, codec):
    m = probe_video(videos / name)
    assert m.duration_ms == pytest.approx(3000, abs=50)
    assert (m.width, m.height) == (320, 240)
    assert m.video_codec == "h264"
    assert m.r_frame_rate == fps
    assert m.avg_frame_rate == fps
    assert m.fps_avg == pytest.approx(float(fps.split("/")[0]))
    assert m.is_vfr_suspected is False
    assert m.has_audio is has_audio
    assert m.audio_codec == codec
    assert m.size_bytes == (videos / name).stat().st_size


def test_vfr_detected(videos):
    m = probe_video(videos / "vfr_mixed.mp4")
    assert m.is_vfr_suspected is True
    assert m.fps_avg == pytest.approx(20.0, abs=1.0)
    assert m.has_audio is False


@pytest.mark.parametrize("name", ["empty.mp4", "corrupt.mp4"])
def test_invalid_video(videos, name):
    with pytest.raises(ProbeError) as exc:
        probe_video(videos / name)
    assert exc.value.code == "INVALID_VIDEO"


def test_input_not_found(tmp_path):
    with pytest.raises(ProbeError) as exc:
        probe_video(tmp_path / "missing.mp4")
    assert exc.value.code == "INPUT_NOT_FOUND"


def test_directory_is_not_a_video(tmp_path):
    with pytest.raises(ProbeError) as exc:
        probe_video(tmp_path)
    assert exc.value.code == "INPUT_NOT_FOUND"


def test_unicode_path(videos, tmp_path):
    target = tmp_path / "排球 測試 🏐.mp4"
    target.write_bytes((videos / "cfr30_audio.mp4").read_bytes())
    assert probe_video(target).duration_ms == pytest.approx(3000, abs=50)


def test_cli_probe_full_json(videos, capsys):
    assert main(["probe", str(videos / "cfr30_audio.mp4")]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data == probe_video(videos / "cfr30_audio.mp4").to_dict()


def test_cli_probe_error_exit_code(tmp_path, capsys):
    assert main(["probe", str(tmp_path / "missing.mp4")]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "[INPUT_NOT_FOUND]" in captured.err


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "vball.cli", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def test_cli_process_success_stdout_only_json(videos):
    result = _run_cli("probe", str(videos / "cfr60_audio.mp4"))
    assert result.returncode == 0
    assert json.loads(result.stdout)["r_frame_rate"] == "60/1"
    assert result.stderr == ""


def test_cli_process_error_stderr_only(videos):
    result = _run_cli("probe", str(videos / "corrupt.mp4"))
    assert result.returncode == 1
    assert result.stdout == ""
    assert "[INVALID_VIDEO]" in result.stderr


@pytest.mark.real_video
def test_real_video(real_video):
    m = probe_video(real_video).to_dict()
    expected = REAL_EXPECTED.get(real_video.name)
    if expected is None:
        assert m["duration_ms"] > 0 and m["width"] > 0 and m["height"] > 0
        pytest.skip(f"{real_video.name} 沒有登錄預期值，只做基本檢查")
    for key, value in expected.items():
        assert m[key] == value, key
