"""以 FFmpeg 切出影片片段（Task 2.1）。

兩種模式：
- accurate：重新編碼（libx264 + aac），起訖點精準到影格，較慢。
- copy：不重新編碼，速度快；起點會落在「要求起點之前最近的 Keyframe」，
  所以實際片段可能比要求長。JSON 會記錄實際起點，且 frame_accurate = false。

白話：copy 像直接剪下整段底片，只能從「完整畫面」的位置下刀；
accurate 像重新沖印，想從哪一格開始都可以，但比較花時間。

安全設計：先寫入 <名稱>.tmp.mp4，驗證成功後才以 os.replace 改名，
中途失敗不會留下看似成功的半成品。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from vball import __version__
from vball.errors import ClipError
from vball.video.probe import VideoMetadata, probe_video

Mode = Literal["copy", "accurate"]
MODES: tuple[str, ...] = ("copy", "accurate")
FFMPEG_TIMEOUT_S = 600
KEYFRAME_LOOKBACK_S = 60      # copy 模式往前找 Keyframe 的範圍
ACCURATE_TOLERANCE_FRAMES = 1.5


@dataclass
class ClipResult:
    input: str
    output: str
    mode: str
    requested_start_ms: int
    requested_end_ms: int
    actual_start_ms: int | None
    actual_end_ms: int | None
    boundary_error_ms: int | None
    tolerance_ms: int | None
    frame_accurate: bool
    input_vfr_suspected: bool | None
    status: str                       # ok | warning
    warnings: list[str] = field(default_factory=list)
    elapsed_ms: int = 0
    ffmpeg_cmd: list[str] = field(default_factory=list)
    vball_version: str = __version__
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------- 驗證 ----------

def _validate_range(meta: VideoMetadata, start_ms: int, end_ms: int) -> None:
    if not (isinstance(start_ms, int) and isinstance(end_ms, int)) or isinstance(start_ms, bool) or isinstance(end_ms, bool):
        raise ClipError("INVALID_RANGE", "start_ms 與 end_ms 必須是整數（毫秒）")
    if start_ms < 0:
        raise ClipError("INVALID_RANGE", f"start_ms 不可為負數：{start_ms}")
    if start_ms >= end_ms:
        raise ClipError("INVALID_RANGE", f"start_ms（{start_ms}）必須小於 end_ms（{end_ms}）")
    if end_ms > meta.duration_ms:
        raise ClipError("INVALID_RANGE", f"end_ms（{end_ms}）超過影片長度（{meta.duration_ms} ms）")


def _validate_output(input_path: Path, output: Path, overwrite: bool) -> None:
    if output.resolve() == input_path.resolve():
        raise ClipError("OUTPUT_NOT_WRITABLE", "輸出路徑不可與輸入影片相同")
    if output.exists():
        if output.is_dir():
            raise ClipError("OUTPUT_NOT_WRITABLE", f"輸出路徑是資料夾：{output}")
        if not overwrite:
            raise ClipError("OUTPUT_EXISTS", f"輸出已存在，要覆蓋請加 --overwrite：{output}")
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".vball_write_test_", delete=True):
            pass
    except OSError as exc:
        raise ClipError("OUTPUT_NOT_WRITABLE", f"輸出資料夾無法寫入：{output.parent}（{exc}）") from exc


# ---------- FFmpeg / FFprobe ----------

def _exe(name: str, code: str) -> str:
    exe = shutil.which(name)
    if not exe:
        raise ClipError(code, f"找不到 {name}，請確認在 (volleyball) 環境且 FFmpeg 在 PATH")
    return exe


def _sec(ms: int) -> str:
    return f"{ms / 1000:.3f}"


def build_ffmpeg_cmd(ffmpeg: str, src: Path, dst: Path, start_ms: int, end_ms: int, mode: str) -> list[str]:
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
           "-ss", _sec(start_ms), "-i", str(src), "-t", _sec(end_ms - start_ms),
           "-map", "0:v:0", "-map", "0:a:0?"]
    if mode == "copy":
        cmd += ["-c", "copy", "-avoid_negative_ts", "make_zero"]
    else:
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-movflags", "+faststart", "-f", "mp4", str(dst)]
    return cmd


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ClipError("FFMPEG_FAILED", f"FFmpeg 超過 {timeout} 秒未完成") from exc
    except OSError as exc:
        raise ClipError("FFMPEG_FAILED", f"無法啟動 FFmpeg：{exc}") from exc


def _video_duration_ms(path: Path) -> int | None:
    """輸出影片的 video stream 長度（不用 format duration，避免 AAC 前置延遲影響）。"""
    ffprobe = _exe("ffprobe", "FFMPEG_NOT_FOUND")
    r = _run([ffprobe, "-v", "error", "-select_streams", "v:0",
              "-show_entries", "stream=duration", "-of", "json", str(path)], 60)
    try:
        return round(float(json.loads(r.stdout)["streams"][0]["duration"]) * 1000)
    except (ValueError, KeyError, IndexError, TypeError):
        return None


def keyframe_at_or_before_ms(path: Path, start_ms: int) -> int | None:
    """找出 start_ms 當下或之前最近的 video Keyframe 時間（毫秒）。找不到回傳 None。"""
    ffprobe = _exe("ffprobe", "FFMPEG_NOT_FOUND")
    lo = max(0.0, start_ms / 1000 - KEYFRAME_LOOKBACK_S)
    r = _run([ffprobe, "-v", "error", "-select_streams", "v:0",
              "-read_intervals", f"{lo:.3f}%{start_ms / 1000 + 0.001:.3f}",
              "-show_entries", "packet=pts_time,flags", "-of", "csv=p=0", str(path)], 120)
    best: int | None = None
    for line in r.stdout.splitlines():
        parts = line.strip().split(",")
        if len(parts) < 2 or "K" not in parts[1]:
            continue
        try:
            t = round(float(parts[0]) * 1000)
        except ValueError:
            continue
        if t <= start_ms and (best is None or t > best):
            best = t
    return best


# ---------- 主流程 ----------

def _tmp_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.tmp.mp4")


def _write_sidecars(output: Path, result: ClipResult, stderr: str) -> None:
    output.with_suffix(".json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    log = [
        f"time      : {result.created_at}",
        f"vball     : {result.vball_version}",
        f"input     : {result.input}",
        f"output    : {result.output}",
        f"mode      : {result.mode}",
        f"requested : {result.requested_start_ms} - {result.requested_end_ms} ms",
        f"actual    : {result.actual_start_ms} - {result.actual_end_ms} ms",
        f"error     : {result.boundary_error_ms} ms (tolerance {result.tolerance_ms})",
        f"status    : {result.status} {result.warnings}",
        f"elapsed   : {result.elapsed_ms} ms",
        f"ffmpeg    : {subprocess.list2cmdline(result.ffmpeg_cmd)}",
        "stderr    :",
        stderr.strip() or "(none)",
    ]
    output.with_suffix(".log").write_text("\n".join(log) + "\n", encoding="utf-8")


def clip_video(
    input_path: str | Path,
    start_ms: int,
    end_ms: int,
    output: str | Path,
    mode: str = "accurate",
    overwrite: bool = False,
) -> ClipResult:
    """切出 [start_ms, end_ms) 片段為 MP4，並寫出同名 .json 與 .log。"""
    started = time.perf_counter()
    if mode not in MODES:
        raise ClipError("INVALID_RANGE", f"mode 必須是 {MODES}，收到：{mode}")
    src, dst = Path(input_path), Path(output)

    meta = probe_video(src)                     # INPUT_NOT_FOUND / INVALID_VIDEO
    _validate_range(meta, start_ms, end_ms)
    _validate_output(src, dst, overwrite)

    ffmpeg = _exe("ffmpeg", "FFMPEG_NOT_FOUND")
    tmp = _tmp_path(dst)
    cmd = build_ffmpeg_cmd(ffmpeg, src, tmp, start_ms, end_ms, mode)
    try:
        proc = _run(cmd, FFMPEG_TIMEOUT_S)
        if proc.returncode != 0 or not tmp.is_file() or tmp.stat().st_size == 0:
            lines = proc.stderr.strip().splitlines()
            raise ClipError("FFMPEG_FAILED", f"FFmpeg 執行失敗：{lines[-1] if lines else '沒有輸出檔'}")

        out_dur = _video_duration_ms(tmp)
        warnings: list[str] = []
        if mode == "copy":
            actual_start = keyframe_at_or_before_ms(src, start_ms)
            if actual_start is None:
                warnings.append("找不到起點前的 Keyframe，實際起點未知")
            tolerance = None
        else:
            actual_start = start_ms
            frame_ms = 1000 / meta.fps_avg if meta.fps_avg else 1000 / 30
            tolerance = round(frame_ms * ACCURATE_TOLERANCE_FRAMES)

        if out_dur is None:
            warnings.append("無法讀取輸出影片長度")
            actual_end = None
        else:
            actual_end = (actual_start if actual_start is not None else start_ms) + out_dur

        error = None
        if actual_start is not None and actual_end is not None:
            error = max(abs(actual_start - start_ms), abs(actual_end - end_ms))
        if mode == "copy" and error:
            warnings.append(f"copy 模式起點對齊 Keyframe，邊界誤差 {error} ms")
        if tolerance is not None and error is not None and error > tolerance:
            warnings.append(f"邊界誤差 {error} ms 超過容許值 {tolerance} ms")

        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink()

    result = ClipResult(
        input=src.resolve().as_posix(),
        output=dst.resolve().as_posix(),
        mode=mode,
        requested_start_ms=start_ms,
        requested_end_ms=end_ms,
        actual_start_ms=actual_start,
        actual_end_ms=actual_end,
        boundary_error_ms=error,
        tolerance_ms=tolerance,
        frame_accurate=(mode == "accurate" and error is not None and tolerance is not None and error <= tolerance),
        input_vfr_suspected=meta.is_vfr_suspected,
        status="warning" if warnings else "ok",
        warnings=warnings,
        elapsed_ms=round((time.perf_counter() - started) * 1000),
        ffmpeg_cmd=cmd,
        created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
    )
    _write_sidecars(dst, result, proc.stderr)
    return result
