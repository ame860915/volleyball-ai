"""Task 2.1 驗收：vball clip（TEST_RULES.md 9 類案例 + Codex Review 修正項目）。"""

import json
import os
import shutil
import subprocess
import sys

import pytest

import vball.video.clip as clip_mod
from vball.cli import main
from vball.errors import ClipError, ProbeError
from vball.video.clip import RUN_LOG_NAME, clip_video
from vball.video.probe import probe_video

SRC30 = "cfr30_audio.mp4"


def _ffmpeg(*args):
    subprocess.run([shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def _files(folder):
    return sorted(p.name for p in folder.iterdir() if p.name != RUN_LOG_NAME)


def _run_log(folder):
    return [json.loads(line) for line in (folder / RUN_LOG_NAME).read_text(encoding="utf-8").splitlines()]


@pytest.fixture(scope="module")
def offset_video(videos, tmp_path_factory):
    """時間戳不從 0 開始的影片（format.start_time ≈ 0.478）。"""
    out = tmp_path_factory.mktemp("offset") / "offset.mp4"
    _ffmpeg("-i", str(videos / SRC30), "-c", "copy", "-output_ts_offset", "0.5", str(out))
    return out


@pytest.fixture(scope="module")
def static_video(tmp_path_factory):
    """畫面完全不動的影片：畫面比對無法確定起點。"""
    out = tmp_path_factory.mktemp("static") / "static.mp4"
    _ffmpeg("-f", "lavfi", "-i", "color=c=gray:size=320x240:rate=30:duration=3",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(out))
    return out


# ---------- 1 + 6：正常區間、30 / 60 fps、無音訊 ----------

@pytest.mark.parametrize("name", [SRC30, "cfr60_audio.mp4"])
def test_accurate_normal_is_measured(videos, tmp_path, name):
    out = tmp_path / "clip.mp4"
    r = clip_video(videos / name, 1000, 2000, out)
    assert r.status == "ok", r.warnings
    assert r.start_basis == "measured"
    assert (r.actual_start_ms, r.actual_end_ms) == (1000, 2000)
    assert r.start_error_ms == 0 and r.end_error_ms == 0
    assert r.frame_accurate is True
    assert probe_video(out).has_audio is True


def test_accurate_unaligned_start(videos, tmp_path):
    r = clip_video(videos / "cfr30_noaudio.mp4", 517, 1733, tmp_path / "c.mp4")
    assert r.start_basis == "measured"
    assert r.actual_start_ms == 533                   # 517 之後的第一格
    assert r.boundary_error_ms <= r.tolerance_ms
    assert probe_video(tmp_path / "c.mp4").has_audio is False


# ---------- copy 模式 ----------

def test_copy_aligns_to_keyframe(videos, tmp_path):
    r = clip_video(videos / SRC30, 1500, 2500, tmp_path / "c.mp4", mode="copy")
    assert r.start_basis == "measured"
    assert r.actual_start_ms == 1000
    assert r.start_error_ms == 500
    assert r.end_error_ms <= 40
    assert r.frame_accurate is False
    assert any("起點誤差 500" in w for w in r.warnings)
    assert not any("終點" in w and "500" in w for w in r.warnings)


def test_copy_on_keyframe(videos, tmp_path):
    r = clip_video(videos / SRC30, 1000, 2000, tmp_path / "c.mp4", mode="copy")
    assert r.actual_start_ms == 1000
    assert r.frame_accurate is False                   # copy 一律不宣稱 Frame-accurate


def _relative_packets(path):
    """以 ffprobe 直接讀出 (pts − format.start_time 毫秒, 是否 Keyframe)；期望值不寫死，避免 FFmpeg 版本差異。"""
    def probe(*args):
        return subprocess.run([shutil.which("ffprobe"), "-v", "error", *args, str(path)],
                              capture_output=True, text=True, check=True).stdout
    off = float(json.loads(probe("-show_entries", "format=start_time", "-of", "json"))["format"]["start_time"])
    rows = probe("-select_streams", "v:0", "-show_entries", "packet=pts_time,flags", "-of", "csv=p=0")
    pkts = [(round((float(t) - off) * 1000), "K" in f) for t, f in (ln.split(",")[:2] for ln in rows.split())]
    return off, sorted(pkts)


def test_start_time_offset(offset_video, tmp_path):
    """format.start_time ≠ 0 時，時間軸以 pts − start_time 計算。"""
    off, pkts = _relative_packets(offset_video)
    assert off > 0.4                                   # fixture 確實有 start_time 位移
    r = clip_video(offset_video, 1000, 2000, tmp_path / "a.mp4")
    assert r.start_basis == "measured"
    assert r.actual_start_ms == min(t for t, _ in pkts if t >= 1000)      # 第一格 ≥ 1000 ms
    assert r.frame_accurate is True
    c = clip_video(offset_video, 1000, 2000, tmp_path / "c.mp4", mode="copy")
    assert c.start_basis == "measured"
    assert c.actual_start_ms == max(t for t, k in pkts if k and t <= 1000)  # 起點前最近的 Keyframe


# ---------- Review #6：無法量測時不宣稱精準 ----------

def test_static_video_is_estimated_not_accurate(static_video, tmp_path):
    r = clip_video(static_video, 1000, 2000, tmp_path / "s.mp4")
    assert r.start_basis == "estimated"
    assert r.match["result"] == "ambiguous"
    assert r.frame_accurate is False
    assert r.status == "warning"


# ---------- 7：VFR ----------

def test_vfr_accurate(videos, tmp_path):
    r = clip_video(videos / "vfr_mixed.mp4", 1200, 2200, tmp_path / "v.mp4")
    assert r.input_vfr_suspected is True
    assert r.start_basis == "measured"
    assert r.actual_start_ms == 1200


# ---------- 2、3：參數 ----------

@pytest.mark.parametrize("start, end", [(2000, 1000), (1000, 1000), (-1, 1000), (0, 3001), (0, 999999)])
def test_invalid_range(videos, tmp_path, start, end):
    with pytest.raises(ClipError) as exc:
        clip_video(videos / SRC30, start, end, tmp_path / "x.mp4")
    assert exc.value.code == "INVALID_RANGE"
    assert _files(tmp_path) == []


def test_invalid_mode(videos, tmp_path):
    with pytest.raises(ClipError) as exc:
        clip_video(videos / SRC30, 0, 1000, tmp_path / "x.mp4", mode="fast")
    assert exc.value.code == "INVALID_ARGUMENT"


# ---------- 4、5：輸入 ----------

def test_input_not_found(tmp_path):
    with pytest.raises(ProbeError) as exc:
        clip_video(tmp_path / "missing.mp4", 0, 1000, tmp_path / "x.mp4")
    assert exc.value.code == "INPUT_NOT_FOUND"


@pytest.mark.parametrize("name", ["empty.mp4", "corrupt.mp4"])
def test_invalid_input_video(videos, tmp_path, name):
    with pytest.raises(ProbeError) as exc:
        clip_video(videos / name, 0, 1000, tmp_path / "x.mp4")
    assert exc.value.code == "INVALID_VIDEO"


# ---------- 8：輸出目的地 ----------

def test_output_parent_is_file(videos, tmp_path):
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("x")
    with pytest.raises(ClipError) as exc:
        clip_video(videos / SRC30, 0, 1000, blocker / "x.mp4")
    assert exc.value.code == "OUTPUT_NOT_WRITABLE"


def test_output_is_directory(videos, tmp_path):
    (tmp_path / "d.mp4").mkdir()
    with pytest.raises(ClipError) as exc:
        clip_video(videos / SRC30, 0, 1000, tmp_path / "d.mp4", overwrite=True)
    assert exc.value.code == "OUTPUT_NOT_WRITABLE"


@pytest.mark.parametrize("name", ["clip.json", "clip.log", "clip.mov", "clip"])
def test_output_must_be_mp4(videos, tmp_path, name):
    with pytest.raises(ClipError) as exc:
        clip_video(videos / SRC30, 0, 1000, tmp_path / name)
    assert exc.value.code == "INVALID_OUTPUT"
    assert _files(tmp_path) == []


def test_output_equals_input(videos, tmp_path):
    src = tmp_path / "src.mp4"
    shutil.copy(videos / SRC30, src)
    with pytest.raises(ClipError) as exc:
        clip_video(src, 0, 1000, src, overwrite=True)
    assert exc.value.code == "INVALID_OUTPUT"
    assert probe_video(src).duration_ms == pytest.approx(3000, abs=50)


def test_sidecar_target_equals_input(videos, tmp_path):
    """輸入叫 c.json，輸出 c.mp4 → c.json 會覆蓋輸入，必須拒絕。"""
    src = tmp_path / "c.json"
    shutil.copy(videos / SRC30, src)
    before = src.read_bytes()
    with pytest.raises(ClipError) as exc:
        clip_video(src, 0, 1000, tmp_path / "c.mp4", overwrite=True)
    assert exc.value.code == "INVALID_OUTPUT"
    assert src.read_bytes() == before


def test_creates_missing_output_folder(videos, tmp_path):
    out = tmp_path / "a" / "b" / "clip.mp4"
    clip_video(videos / SRC30, 0, 1000, out)
    assert out.is_file()


# ---------- Review #1（High）：暫存檔不可刪除輸入或他人檔案 ----------

def test_input_named_like_old_temp_survives(videos, tmp_path):
    src = tmp_path / "clip.tmp.mp4"
    shutil.copy(videos / SRC30, src)
    before = src.read_bytes()
    clip_video(src, 0, 1000, tmp_path / "clip.mp4")
    assert src.read_bytes() == before


def test_unrelated_tmp_file_untouched(videos, tmp_path):
    other = tmp_path / "clip.tmp.mp4"
    other.write_bytes(b"someone else's file")
    with pytest.raises(ClipError):
        clip_video(videos / SRC30, 2000, 1000, tmp_path / "clip.mp4")
    clip_video(videos / SRC30, 0, 1000, tmp_path / "clip.mp4")
    assert other.read_bytes() == b"someone else's file"


def test_temp_names_are_unique(videos, tmp_path):
    names = {clip_mod._new_temp(tmp_path / "c.mp4", ".tmp.mp4", videos / SRC30) for _ in range(20)}
    assert len(names) == 20


# ---------- 9 + Review #2（High）：重複執行與 sidecar 覆蓋 ----------

def test_repeat_requires_overwrite(videos, tmp_path):
    out = tmp_path / "clip.mp4"
    clip_video(videos / SRC30, 0, 1000, out)
    first = out.read_bytes()
    with pytest.raises(ClipError) as exc:
        clip_video(videos / SRC30, 1000, 2500, out)
    assert exc.value.code == "OUTPUT_EXISTS"
    assert out.read_bytes() == first
    r = clip_video(videos / SRC30, 1000, 2500, out, overwrite=True)
    assert r.requested_end_ms == 2500
    assert probe_video(out).duration_ms == pytest.approx(1500, abs=50)


@pytest.mark.parametrize("existing", ["clip.json", "clip.log"])
def test_existing_sidecar_protected(videos, tmp_path, existing):
    (tmp_path / existing).write_text("我的舊資料", encoding="utf-8")
    with pytest.raises(ClipError) as exc:
        clip_video(videos / SRC30, 0, 1000, tmp_path / "clip.mp4")
    assert exc.value.code == "OUTPUT_EXISTS"
    assert (tmp_path / existing).read_text(encoding="utf-8") == "我的舊資料"
    assert not (tmp_path / "clip.mp4").exists()


# ---------- Review #3：FFmpeg 成功但輸出無效 ----------

def _fake_ffmpeg(monkeypatch, write: bytes | None, returncode: int = 0, stderr: str = ""):
    real_run = clip_mod._run

    def fake_run(cmd, timeout):
        if "-map" in cmd and "0:a:0?" in cmd:          # 只攔截切片指令
            if write is not None:
                open(cmd[-1], "wb").write(write)
            return subprocess.CompletedProcess(cmd, returncode, stdout="", stderr=stderr)
        return real_run(cmd, timeout)

    monkeypatch.setattr(clip_mod, "_run", fake_run)


def test_ffmpeg_exit0_but_garbage_output(videos, tmp_path, monkeypatch):
    _fake_ffmpeg(monkeypatch, write=b"not a video" * 50)
    with pytest.raises(ClipError) as exc:
        clip_video(videos / SRC30, 0, 1000, tmp_path / "clip.mp4")
    assert exc.value.code == "OUTPUT_VERIFY_FAILED"
    assert _files(tmp_path) == []


def test_ffmpeg_failure_leaves_no_files(videos, tmp_path, monkeypatch):
    _fake_ffmpeg(monkeypatch, write=b"partial", returncode=1, stderr="boom: encoder error")
    with pytest.raises(ClipError) as exc:
        clip_video(videos / SRC30, 0, 1000, tmp_path / "clip.mp4")
    assert exc.value.code == "FFMPEG_FAILED"
    assert "encoder error" in exc.value.message
    assert _files(tmp_path) == []


def test_truncated_output_fails_verification(videos, tmp_path, monkeypatch):
    good = tmp_path / "good.mp4"
    clip_video(videos / SRC30, 0, 2000, good)
    data = good.read_bytes()
    _fake_ffmpeg(monkeypatch, write=data[: len(data) // 2])
    with pytest.raises(ClipError) as exc:
        clip_video(videos / SRC30, 0, 2000, tmp_path / "bad.mp4")
    assert exc.value.code == "OUTPUT_VERIFY_FAILED"
    assert not (tmp_path / "bad.mp4").exists()


def test_ffmpeg_missing(videos, tmp_path, monkeypatch):
    real_which = clip_mod.shutil.which
    monkeypatch.setattr(clip_mod.shutil, "which", lambda n: None if n == "ffmpeg" else real_which(n))
    with pytest.raises(ClipError) as exc:
        clip_video(videos / SRC30, 0, 1000, tmp_path / "x.mp4")
    assert exc.value.code == "FFMPEG_NOT_FOUND"


# ---------- Review #4：發布失敗（如 Windows 檔案被播放器鎖定） ----------

@pytest.mark.parametrize("locked", ["clip.mp4", "clip.json", "clip.log"])
def test_publish_failure_rolls_back(videos, tmp_path, monkeypatch, locked):
    real_replace = os.replace

    def fake_replace(a, b):
        if os.path.basename(b) == locked:
            raise PermissionError("檔案被其他程式使用中")
        return real_replace(a, b)

    monkeypatch.setattr(clip_mod.os, "replace", fake_replace)
    with pytest.raises(ClipError) as exc:
        clip_video(videos / SRC30, 0, 1000, tmp_path / "clip.mp4")
    assert exc.value.code == "OUTPUT_NOT_WRITABLE"
    assert _files(tmp_path) == []


def test_publish_failure_cli_format(videos, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(clip_mod.os, "replace", lambda a, b: (_ for _ in ()).throw(PermissionError("locked")))
    code = main(["clip", str(videos / SRC30), "--start-ms", "0", "--end-ms", "1000", "--out", str(tmp_path / "c.mp4")])
    assert code == 1
    assert "[OUTPUT_NOT_WRITABLE]" in capsys.readouterr().err


# ---------- Review #5：每次執行都有紀錄 ----------

def test_run_log_success_and_failure(videos, tmp_path):
    clip_video(videos / SRC30, 0, 1000, tmp_path / "a.mp4")
    with pytest.raises(ClipError):
        clip_video(videos / SRC30, 0, 1000, tmp_path / "a.mp4")
    with pytest.raises(ClipError):
        clip_video(videos / SRC30, 2000, 1000, tmp_path / "b.mp4")
    log = _run_log(tmp_path)
    assert [r["status"] for r in log] == ["ok", "failed", "failed"]
    assert [r["code"] for r in log] == [None, "OUTPUT_EXISTS", "INVALID_RANGE"]
    assert all("elapsed_ms" in r for r in log)


def test_run_log_records_ffmpeg_stderr(videos, tmp_path, monkeypatch):
    _fake_ffmpeg(monkeypatch, write=None, returncode=1, stderr="boom: encoder error")
    with pytest.raises(ClipError):
        clip_video(videos / SRC30, 0, 1000, tmp_path / "clip.mp4")
    rec = _run_log(tmp_path)[-1]
    assert rec["code"] == "FFMPEG_FAILED"
    assert "encoder error" in rec["stderr"]
    assert rec["ffmpeg_cmd"]


def test_run_log_fallback_when_output_unwritable(videos, tmp_path, monkeypatch):
    fallback = tmp_path / "fallback"
    monkeypatch.setattr(clip_mod.tempfile, "gettempdir", lambda: str(fallback))
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("x")
    with pytest.raises(ClipError):
        clip_video(videos / SRC30, 0, 1000, blocker / "x.mp4")
    rec = _run_log(fallback / "vball")[-1]
    assert rec["code"] == "OUTPUT_NOT_WRITABLE"


# ---------- JSON 與 log ----------

def test_sidecar_json_and_log(videos, tmp_path):
    out = tmp_path / "clip.mp4"
    r = clip_video(videos / SRC30, 1500, 2500, out, mode="copy")
    data = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
    assert data == r.to_dict()
    for key in ("start_basis", "start_error_ms", "end_error_ms", "match", "frame_accurate"):
        assert key in data
    text = out.with_suffix(".log").read_text(encoding="utf-8")
    assert "mode      : copy" in text and "(measured)" in text
    assert _files(tmp_path) == ["clip.json", "clip.log", "clip.mp4"]


def test_unicode_paths(videos, tmp_path):
    src = tmp_path / "排球 原片.mp4"
    shutil.copy(videos / SRC30, src)
    out = tmp_path / "輸出 資料夾" / "片段 1.mp4"
    assert clip_video(src, 0, 1000, out).status == "ok"


# ---------- CLI ----------

def test_cli_clip(videos, tmp_path, capsys):
    out = tmp_path / "c.mp4"
    assert main(["clip", str(videos / SRC30), "--start-ms", "1000", "--end-ms", "2000", "--out", str(out)]) == 0
    assert json.loads(capsys.readouterr().out)["actual_start_ms"] == 1000


def test_cli_clip_error_process(videos, tmp_path):
    r = subprocess.run(
        [sys.executable, "-m", "vball.cli", "clip", str(videos / SRC30),
         "--start-ms", "2000", "--end-ms", "1000", "--out", str(tmp_path / "c.mp4")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert r.returncode == 1
    assert r.stdout == ""
    assert "[INVALID_RANGE]" in r.stderr


def test_cli_clip_bad_mode_is_argparse_error(videos, tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["clip", str(videos / SRC30), "--start-ms", "0", "--end-ms", "1",
              "--out", str(tmp_path / "c.mp4"), "--mode", "fast"])
    assert exc.value.code == 2


# ---------- 真實影片 ----------

@pytest.mark.real_video
@pytest.mark.parametrize("mode", ["accurate", "copy"])
def test_real_video_clip(real_video, tmp_path, mode):
    out = tmp_path / f"real_{mode}.mp4"
    r = clip_video(real_video, 1000, 4000, out, mode=mode)
    assert out.is_file()
    assert r.start_basis in ("measured", "estimated")
    if mode == "accurate" and r.start_basis == "measured":
        assert r.frame_accurate is True, r.warnings
    if mode == "copy":
        assert r.actual_start_ms is not None and r.actual_start_ms <= 1000
