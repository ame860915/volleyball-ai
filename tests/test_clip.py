"""Task 2.1 驗收：vball clip（TEST_RULES.md 的 9 類案例 + 安全性與 CLI）。"""

import json
import subprocess
import sys

import pytest

import vball.video.clip as clip_mod
from vball.cli import main
from vball.errors import ClipError, ProbeError
from vball.video.clip import clip_video
from vball.video.probe import probe_video


def _sidecars(out):
    return out.with_suffix(".json"), out.with_suffix(".log")


# 1 + 6：正常區間、30 / 60 fps（accurate）
@pytest.mark.parametrize("name, frames", [("cfr30_audio.mp4", 30), ("cfr60_audio.mp4", 60)])
def test_accurate_normal(videos, tmp_path, name, frames):
    out = tmp_path / "clip.mp4"
    r = clip_video(videos / name, 1000, 2000, out, mode="accurate")
    assert r.status == "ok", r.warnings
    assert (r.actual_start_ms, r.actual_end_ms) == (1000, 2000)
    assert r.boundary_error_ms <= r.tolerance_ms
    assert r.frame_accurate is True
    m = probe_video(out)
    assert m.duration_ms == pytest.approx(1000, abs=50)
    assert m.has_audio is True


def test_accurate_no_audio(videos, tmp_path):
    out = tmp_path / "clip.mp4"
    r = clip_video(videos / "cfr30_noaudio.mp4", 500, 1500, out)
    assert r.frame_accurate is True
    assert probe_video(out).has_audio is False


# 1：copy 模式起點對齊 Keyframe（fixture GOP = 1 秒）
def test_copy_aligns_to_keyframe(videos, tmp_path):
    out = tmp_path / "clip.mp4"
    r = clip_video(videos / "cfr30_audio.mp4", 1500, 2500, out, mode="copy")
    assert r.actual_start_ms == 1000
    assert r.actual_end_ms == pytest.approx(2500, abs=40)
    assert r.boundary_error_ms == pytest.approx(500, abs=40)
    assert r.frame_accurate is False
    assert r.status == "warning"
    assert any("Keyframe" in w for w in r.warnings)


def test_copy_on_keyframe_is_exact(videos, tmp_path):
    r = clip_video(videos / "cfr30_audio.mp4", 1000, 2000, tmp_path / "c.mp4", mode="copy")
    assert r.actual_start_ms == 1000
    assert r.boundary_error_ms <= 40
    assert r.frame_accurate is False       # copy 模式一律不宣稱 Frame-accurate


# 7：VFR
def test_vfr_accurate(videos, tmp_path):
    r = clip_video(videos / "vfr_mixed.mp4", 1200, 2200, tmp_path / "v.mp4")
    assert r.input_vfr_suspected is True
    assert r.actual_start_ms == 1200
    assert r.boundary_error_ms is not None


# 2、3：時間範圍
@pytest.mark.parametrize("start, end", [(2000, 1000), (1000, 1000), (-1, 1000), (0, 3001), (0, 999999)])
def test_invalid_range(videos, tmp_path, start, end):
    out = tmp_path / "x.mp4"
    with pytest.raises(ClipError) as exc:
        clip_video(videos / "cfr30_audio.mp4", start, end, out)
    assert exc.value.code == "INVALID_RANGE"
    assert not out.exists()


def test_invalid_mode(videos, tmp_path):
    with pytest.raises(ClipError) as exc:
        clip_video(videos / "cfr30_audio.mp4", 0, 1000, tmp_path / "x.mp4", mode="fast")
    assert exc.value.code == "INVALID_RANGE"


# 4、5：輸入檔
def test_input_not_found(tmp_path):
    with pytest.raises(ProbeError) as exc:
        clip_video(tmp_path / "missing.mp4", 0, 1000, tmp_path / "x.mp4")
    assert exc.value.code == "INPUT_NOT_FOUND"


@pytest.mark.parametrize("name", ["empty.mp4", "corrupt.mp4"])
def test_invalid_input_video(videos, tmp_path, name):
    with pytest.raises(ProbeError) as exc:
        clip_video(videos / name, 0, 1000, tmp_path / "x.mp4")
    assert exc.value.code == "INVALID_VIDEO"


# 8：無法寫入（上層是檔案、輸出是資料夾、輸出等於輸入）
def test_output_parent_is_file(videos, tmp_path):
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("x")
    with pytest.raises(ClipError) as exc:
        clip_video(videos / "cfr30_audio.mp4", 0, 1000, blocker / "x.mp4")
    assert exc.value.code == "OUTPUT_NOT_WRITABLE"


def test_output_is_directory(videos, tmp_path):
    with pytest.raises(ClipError) as exc:
        clip_video(videos / "cfr30_audio.mp4", 0, 1000, tmp_path, overwrite=True)
    assert exc.value.code == "OUTPUT_NOT_WRITABLE"


def test_output_equals_input(videos, tmp_path):
    src = tmp_path / "src.mp4"
    src.write_bytes((videos / "cfr30_audio.mp4").read_bytes())
    with pytest.raises(ClipError) as exc:
        clip_video(src, 0, 1000, src, overwrite=True)
    assert exc.value.code == "OUTPUT_NOT_WRITABLE"
    assert probe_video(src).duration_ms == pytest.approx(3000, abs=50)


def test_creates_missing_output_folder(videos, tmp_path):
    out = tmp_path / "a" / "b" / "clip.mp4"
    clip_video(videos / "cfr30_audio.mp4", 0, 1000, out)
    assert out.is_file()


# 9：重複執行
def test_repeat_requires_overwrite(videos, tmp_path):
    out = tmp_path / "clip.mp4"
    clip_video(videos / "cfr30_audio.mp4", 0, 1000, out)
    first = out.read_bytes()
    with pytest.raises(ClipError) as exc:
        clip_video(videos / "cfr30_audio.mp4", 1000, 2500, out)
    assert exc.value.code == "OUTPUT_EXISTS"
    assert out.read_bytes() == first
    r = clip_video(videos / "cfr30_audio.mp4", 1000, 2500, out, overwrite=True)
    assert r.requested_end_ms == 2500
    assert probe_video(out).duration_ms == pytest.approx(1500, abs=50)


# 安全性：失敗不留半成品
def test_ffmpeg_failure_leaves_no_files(videos, tmp_path, monkeypatch):
    out = tmp_path / "clip.mp4"
    real_run = clip_mod._run

    def fake_run(cmd, timeout):
        if "ffmpeg" in cmd[0].lower() and "ffprobe" not in cmd[0].lower():
            clip_mod._tmp_path(out).write_bytes(b"partial")
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom: encoder error")
        return real_run(cmd, timeout)

    monkeypatch.setattr(clip_mod, "_run", fake_run)
    with pytest.raises(ClipError) as exc:
        clip_video(videos / "cfr30_audio.mp4", 0, 1000, out)
    assert exc.value.code == "FFMPEG_FAILED"
    assert "encoder error" in exc.value.message
    assert list(tmp_path.iterdir()) == []


def test_ffmpeg_missing(videos, tmp_path, monkeypatch):
    real_which = clip_mod.shutil.which
    monkeypatch.setattr(clip_mod.shutil, "which", lambda n: None if n == "ffmpeg" else real_which(n))
    with pytest.raises(ClipError) as exc:
        clip_video(videos / "cfr30_audio.mp4", 0, 1000, tmp_path / "x.mp4")
    assert exc.value.code == "FFMPEG_NOT_FOUND"


# JSON 與 log
def test_sidecar_json_and_log(videos, tmp_path):
    out = tmp_path / "clip.mp4"
    r = clip_video(videos / "cfr30_audio.mp4", 1500, 2500, out, mode="copy")
    j, log = _sidecars(out)
    data = json.loads(j.read_text(encoding="utf-8"))
    assert data == r.to_dict()
    for key in ("requested_start_ms", "actual_start_ms", "boundary_error_ms", "frame_accurate", "ffmpeg_cmd"):
        assert key in data
    text = log.read_text(encoding="utf-8")
    assert "mode      : copy" in text and "ffmpeg    :" in text
    assert not any(p.name.endswith(".tmp.mp4") for p in tmp_path.iterdir())


def test_unicode_paths(videos, tmp_path):
    src = tmp_path / "排球 原片.mp4"
    src.write_bytes((videos / "cfr30_audio.mp4").read_bytes())
    out = tmp_path / "輸出 資料夾" / "片段 1.mp4"
    assert clip_video(src, 0, 1000, out).status == "ok"


# CLI
def test_cli_clip(videos, tmp_path, capsys):
    out = tmp_path / "c.mp4"
    code = main(["clip", str(videos / "cfr30_audio.mp4"), "--start-ms", "1000", "--end-ms", "2000", "--out", str(out)])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["actual_start_ms"] == 1000


def test_cli_clip_error_process(videos, tmp_path):
    r = subprocess.run(
        [sys.executable, "-m", "vball.cli", "clip", str(videos / "cfr30_audio.mp4"),
         "--start-ms", "2000", "--end-ms", "1000", "--out", str(tmp_path / "c.mp4")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert r.returncode == 1
    assert r.stdout == ""
    assert "[INVALID_RANGE]" in r.stderr


def test_cli_clip_bad_mode_is_argparse_error(videos, tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["clip", str(videos / "cfr30_audio.mp4"), "--start-ms", "0", "--end-ms", "1",
              "--out", str(tmp_path / "c.mp4"), "--mode", "fast"])
    assert exc.value.code == 2


@pytest.mark.real_video
@pytest.mark.parametrize("mode", ["accurate", "copy"])
def test_real_video_clip(real_video, tmp_path, mode):
    out = tmp_path / f"real_{mode}.mp4"
    r = clip_video(real_video, 1000, 4000, out, mode=mode)
    assert out.is_file()
    assert r.actual_end_ms is not None
    if mode == "accurate":
        assert r.frame_accurate is True, r.warnings
    else:
        assert r.actual_start_ms is not None and r.actual_start_ms <= 1000
