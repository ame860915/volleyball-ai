"""Task 1.5 驗收：probe_video 與 vball probe。"""

import json

import pytest

from vball.cli import main
from vball.errors import ProbeError
from vball.video.probe import probe_video


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
    assert m.is_vfr_suspected is False
    assert m.has_audio is has_audio
    assert m.audio_codec == codec
    assert m.size_bytes > 0


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


def test_cli_probe_outputs_json(videos, capsys):
    assert main(["probe", str(videos / "cfr30_audio.mp4")]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["r_frame_rate"] == "30/1"
    assert data["has_audio"] is True


def test_cli_probe_error_exit_code(tmp_path, capsys):
    assert main(["probe", str(tmp_path / "missing.mp4")]) == 1
    assert "[INPUT_NOT_FOUND]" in capsys.readouterr().err


@pytest.mark.real_video
def test_real_video(real_video):
    m = probe_video(real_video)
    assert m.duration_ms > 0
    assert m.width > 0 and m.height > 0
