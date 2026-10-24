"""以 FFmpeg 切出影片片段（Task 2.1，依 Codex Review 修正）。

兩種模式：
- accurate：重新編碼（libx264 + aac），起訖點精準到影格，較慢。
- copy：不重新編碼，速度快；起點會落在「要求起點之前最近的 Keyframe」。

白話：copy 像直接剪下整段底片，只能從「完整畫面」的位置下刀；
accurate 像重新沖印，想從哪一格開始都可以，但比較花時間。

時間軸：一律以「pts − format.start_time」為準（與 ffmpeg -ss 相同基準），單位毫秒。

實際起點的量測（start_basis）：
- measured：把輸出的第一格畫面縮小成灰階，和來源起點附近的每一格比對（平均絕對差），
  找到唯一明顯最像的一格（像 AOI 的 Template Matching）。
- estimated：比對結果不明確（畫面幾乎不動、相鄰格太像），只能用推估值
  （accurate = 要求起點；copy = 起點前最近的 Keyframe）。
- unknown：連推估都做不到。
只有 measured 且誤差在容許值內，frame_accurate 才會是 true；copy 模式一律 false。

安全設計：
- 輸出必須是 .mp4；mp4 / json / log 三個目的地都不可指向輸入，預設不覆蓋任何一個。
- 每次執行使用唯一暫存檔（mkstemp），只清理本次建立的檔案。
- 輸出必須通過 probe 與完整解碼檢查，才會發布（os.replace）。
- 發布中途失敗會移除本次已發布的檔案並回報 OUTPUT_NOT_WRITABLE。
  注意：使用 --overwrite 時，被覆蓋的舊檔無法還原。
- 每次執行（成功或失敗）都會在 vball_runs.jsonl 追加一筆紀錄。
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from vball import __version__
from vball.errors import ClipError, ProbeError, VballError
from vball.video.probe import VideoMetadata, probe_video

MODES: tuple[str, ...] = ("copy", "accurate")
FFMPEG_TIMEOUT_S = 600
KEYFRAME_LOOKBACK_S = 60          # copy 模式往前找 Keyframe 的範圍
ACCURATE_TOLERANCE_FRAMES = 1.5
MATCH_RADIUS_FRAMES = 4           # 比對候選：推估起點前後各 4 格
MATCH_SIZE = (64, 36)             # 比對用縮圖（灰階）
MATCH_MAX_MAD = 12.0              # 最佳候選的平均絕對差上限（0–255）
MATCH_MIN_RATIO = 3.0             # 次佳至少是最佳的 3 倍，且
MATCH_MIN_GAP = 0.5               # 至少差 0.5，才算「唯一明顯最像」
RUN_LOG_NAME = "vball_runs.jsonl"


@dataclass
class ClipResult:
    input: str
    output: str
    mode: str
    requested_start_ms: int
    requested_end_ms: int
    actual_start_ms: int | None
    actual_end_ms: int | None
    start_basis: str                  # measured | estimated | unknown
    start_error_ms: int | None
    end_error_ms: int | None
    boundary_error_ms: int | None
    tolerance_ms: int | None
    frame_accurate: bool
    input_vfr_suspected: bool | None
    status: str                       # ok | warning
    warnings: list[str] = field(default_factory=list)
    match: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: int = 0
    ffmpeg_cmd: list[str] = field(default_factory=list)
    vball_version: str = __version__
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------- 小工具 ----------

def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _sec(ms: float) -> str:
    return f"{ms / 1000:.3f}"


def _same_file(a: Path, b: Path) -> bool:
    try:
        if a.exists() and b.exists():
            return os.path.samefile(a, b)
    except OSError:
        pass
    return os.path.normcase(str(a.resolve())) == os.path.normcase(str(b.resolve()))


def _exe(name: str) -> str:
    exe = shutil.which(name)
    if not exe:
        raise ClipError("FFMPEG_NOT_FOUND", f"找不到 {name}，請確認在 (volleyball) 環境且 FFmpeg 在 PATH")
    return exe


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ClipError("FFMPEG_FAILED", f"FFmpeg 超過 {timeout} 秒未完成") from exc
    except OSError as exc:
        raise ClipError("FFMPEG_FAILED", f"無法啟動 FFmpeg：{exc}") from exc


def _run_bytes(cmd: list[str], timeout: int = 60) -> bytes | None:
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    return r.stdout if r.returncode == 0 else None


# ---------- 驗證輸入與輸出目的地 ----------

def _validate_range(meta: VideoMetadata, start_ms: Any, end_ms: Any) -> None:
    for v in (start_ms, end_ms):
        if isinstance(v, bool) or not isinstance(v, int):
            raise ClipError("INVALID_RANGE", "start_ms 與 end_ms 必須是整數（毫秒）")
    if start_ms < 0:
        raise ClipError("INVALID_RANGE", f"start_ms 不可為負數：{start_ms}")
    if start_ms >= end_ms:
        raise ClipError("INVALID_RANGE", f"start_ms（{start_ms}）必須小於 end_ms（{end_ms}）")
    if end_ms > meta.duration_ms:
        raise ClipError("INVALID_RANGE", f"end_ms（{end_ms}）超過影片長度（{meta.duration_ms} ms）")


def _targets(dst: Path) -> list[Path]:
    return [dst, dst.with_suffix(".json"), dst.with_suffix(".log")]


def _validate_output(src: Path, dst: Path, overwrite: bool) -> None:
    if dst.suffix.lower() != ".mp4":
        raise ClipError("INVALID_OUTPUT", f"輸出檔名必須是 .mp4：{dst}")
    for target in _targets(dst):
        if _same_file(target, src):
            raise ClipError("INVALID_OUTPUT", f"輸出（含 .json / .log）不可與輸入影片相同：{target}")
        if target.is_dir():
            raise ClipError("OUTPUT_NOT_WRITABLE", f"輸出路徑是資料夾：{target}")
        if target.exists() and not overwrite:
            raise ClipError("OUTPUT_EXISTS", f"已存在，要覆蓋請加 --overwrite：{target}")
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=dst.parent, prefix=".vball_write_test_"):
            pass
    except OSError as exc:
        raise ClipError("OUTPUT_NOT_WRITABLE", f"輸出資料夾無法寫入：{dst.parent}（{exc}）") from exc


def _new_temp(dst: Path, suffix: str, src: Path) -> Path:
    fd, name = tempfile.mkstemp(dir=dst.parent, prefix=f".{dst.stem}.", suffix=suffix)
    os.close(fd)
    tmp = Path(name)
    if _same_file(tmp, src):          # 理論上不會發生，保險起見
        raise ClipError("INVALID_OUTPUT", f"暫存檔與輸入相同：{tmp}")
    return tmp


# ---------- FFmpeg ----------

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


def _format_start_ms(path: Path) -> float:
    r = _run([_exe("ffprobe"), "-v", "error", "-show_entries", "format=start_time",
              "-of", "json", str(path)], 60)
    try:
        v = float(json.loads(r.stdout)["format"]["start_time"])
        return v * 1000 if math.isfinite(v) else 0.0
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return 0.0


def _video_packets(path: Path, lo_ms: float, hi_ms: float) -> list[tuple[int, bool]]:
    """[lo_ms, hi_ms] 內的 video packet（相對時間毫秒, 是否 Keyframe），依時間排序。"""
    off = _format_start_ms(path)
    a = max(0.0, (lo_ms + off) / 1000 - 1.0)
    b = (hi_ms + off) / 1000 + 1.0
    r = _run([_exe("ffprobe"), "-v", "error", "-select_streams", "v:0",
              "-read_intervals", f"{a:.3f}%{b:.3f}",
              "-show_entries", "packet=pts_time,flags", "-of", "csv=p=0", str(path)], 120)
    out: dict[int, bool] = {}
    for line in r.stdout.splitlines():
        parts = line.strip().split(",")
        if len(parts) < 2:
            continue
        try:
            t = float(parts[0]) * 1000 - off
        except ValueError:
            continue
        if math.isfinite(t) and lo_ms - 0.5 <= t <= hi_ms + 0.5:
            ms = round(t)
            out[ms] = out.get(ms, False) or ("K" in parts[1])
    return sorted(out.items())


def keyframe_at_or_before_ms(path: Path, start_ms: int) -> int | None:
    """start_ms 當下或之前最近的 video Keyframe（相對時間毫秒）。找不到回傳 None。"""
    lo = max(0.0, start_ms - KEYFRAME_LOOKBACK_S * 1000)
    keys = [t for t, k in _video_packets(path, lo, start_ms) if k and t <= start_ms]
    return max(keys) if keys else None


def _video_duration_ms(path: Path) -> int | None:
    r = _run([_exe("ffprobe"), "-v", "error", "-select_streams", "v:0",
              "-show_entries", "stream=duration", "-of", "json", str(path)], 60)
    if r.returncode != 0:
        return None
    try:
        sec = float(json.loads(r.stdout)["streams"][0]["duration"])
    except (ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None
    if not math.isfinite(sec):
        return None
    ms = round(sec * 1000)
    return ms if ms > 0 else None


def _verify_output(tmp: Path) -> int:
    """輸出必須可 probe、有 video、長度有效，且能完整解碼。回傳 video 長度（毫秒）。"""
    try:
        probe_video(tmp)
    except ProbeError as exc:
        raise ClipError("OUTPUT_VERIFY_FAILED", f"輸出影片無法讀取：{exc.message}") from exc
    dur = _video_duration_ms(tmp)
    if dur is None:
        raise ClipError("OUTPUT_VERIFY_FAILED", "輸出影片沒有有效的 video 長度")
    r = _run([_exe("ffmpeg"), "-hide_banner", "-nostdin", "-v", "error",
              "-i", str(tmp), "-map", "0:v:0", "-f", "null", "-"], FFMPEG_TIMEOUT_S)
    if r.returncode != 0 or r.stderr.strip():
        detail = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else f"exit {r.returncode}"
        raise ClipError("OUTPUT_VERIFY_FAILED", f"輸出影片解碼失敗：{detail}")
    return dur


# ---------- 起點量測（畫面比對） ----------

def _gray(args: list[str]) -> bytes | None:
    w, h = MATCH_SIZE
    data = _run_bytes([_exe("ffmpeg"), "-hide_banner", "-nostdin", "-v", "error", *args,
                       "-map", "0:v:0", "-frames:v", "1",
                       "-vf", f"scale={w}:{h}:flags=area,format=gray", "-f", "rawvideo", "-"])
    return data if data and len(data) == w * h else None


def _mad(a: bytes, b: bytes) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def measure_start_ms(src: Path, out: Path, estimate_ms: int, fps: float | None) -> tuple[int | None, dict]:
    """以畫面比對找出輸出第一格對應的來源時間。不夠確定時回傳 (None, 細節)。"""
    frame_ms = 1000 / fps if fps else 1000 / 30
    span = MATCH_RADIUS_FRAMES * frame_ms
    first = _gray(["-i", str(out)])
    if first is None:
        return None, {"method": "frame_match", "result": "no_output_frame"}
    scores: list[tuple[float, int]] = []
    for t, _ in _video_packets(src, max(0.0, estimate_ms - span), estimate_ms + span):
        frame = _gray(["-ss", _sec(max(0.0, t - 1)), "-i", str(src)])
        if frame is not None:
            scores.append((_mad(first, frame), t))
    if len(scores) < 2:
        return None, {"method": "frame_match", "result": "too_few_candidates", "candidates": len(scores)}
    scores.sort()
    (best, best_t), (second, _) = scores[0], scores[1]
    info = {"method": "frame_match", "candidates": len(scores),
            "best_ms": best_t, "best_mad": round(best, 2), "second_mad": round(second, 2)}
    if best > MATCH_MAX_MAD:
        info["result"] = "no_good_match"
        return None, info
    if second < max(best * MATCH_MIN_RATIO, best + MATCH_MIN_GAP):
        info["result"] = "ambiguous"
        return None, info
    info["result"] = "matched"
    return best_t, info


# ---------- sidecar 與執行紀錄 ----------

def _render_log(result: ClipResult, stderr: str) -> str:
    lines = [
        f"time      : {result.created_at}",
        f"vball     : {result.vball_version}",
        f"input     : {result.input}",
        f"output    : {result.output}",
        f"mode      : {result.mode}",
        f"requested : {result.requested_start_ms} - {result.requested_end_ms} ms",
        f"actual    : {result.actual_start_ms} - {result.actual_end_ms} ms ({result.start_basis})",
        f"error     : start {result.start_error_ms} / end {result.end_error_ms} ms (tolerance {result.tolerance_ms})",
        f"match     : {result.match}",
        f"status    : {result.status} {result.warnings}",
        f"elapsed   : {result.elapsed_ms} ms",
        f"ffmpeg    : {subprocess.list2cmdline(result.ffmpeg_cmd)}",
        "stderr    :",
        stderr.strip() or "(none)",
    ]
    return "\n".join(lines) + "\n"


def run_log_path(dst: Path) -> Path:
    """執行紀錄位置：輸出資料夾可寫就放那裡，否則放系統暫存資料夾。"""
    parent = dst.parent
    if parent.is_dir() and os.access(parent, os.W_OK):
        return parent / RUN_LOG_NAME
    fallback = Path(tempfile.gettempdir()) / "vball"
    return fallback / RUN_LOG_NAME


def _append_run_log(dst: Path, record: dict) -> None:
    line = json.dumps(record, ensure_ascii=False) + "\n"
    for path in (run_log_path(dst), Path(tempfile.gettempdir()) / "vball" / RUN_LOG_NAME):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(line)
            return
        except OSError:
            continue                  # 紀錄失敗不可掩蓋原本的結果或錯誤


# ---------- 主流程 ----------

def _clip(src: Path, start_ms: int, end_ms: int, dst: Path, mode: str,
          overwrite: bool, trace: dict, started: float) -> ClipResult:
    if mode not in MODES:
        raise ClipError("INVALID_ARGUMENT", f"mode 必須是 {MODES}，收到：{mode}")
    if dst.suffix.lower() != ".mp4":
        raise ClipError("INVALID_OUTPUT", f"輸出檔名必須是 .mp4：{dst}")

    meta = probe_video(src)                     # INPUT_NOT_FOUND / INVALID_VIDEO
    _validate_range(meta, start_ms, end_ms)
    _validate_output(src, dst, overwrite)
    ffmpeg = _exe("ffmpeg")

    temps: list[Path] = []
    published: list[Path] = []
    try:
        tmp_mp4 = _new_temp(dst, ".tmp.mp4", src)
        temps.append(tmp_mp4)
        cmd = build_ffmpeg_cmd(ffmpeg, src, tmp_mp4, start_ms, end_ms, mode)
        trace["ffmpeg_cmd"] = cmd
        proc = _run(cmd, FFMPEG_TIMEOUT_S)
        trace["stderr"] = proc.stderr[-2000:]
        if proc.returncode != 0 or tmp_mp4.stat().st_size == 0:
            lines = proc.stderr.strip().splitlines()
            raise ClipError("FFMPEG_FAILED", f"FFmpeg 執行失敗：{lines[-1] if lines else '沒有輸出內容'}")

        out_dur = _verify_output(tmp_mp4)       # OUTPUT_VERIFY_FAILED

        # 起點：先推估，再以畫面比對量測
        warnings: list[str] = []
        estimate = keyframe_at_or_before_ms(src, start_ms) if mode == "copy" else start_ms
        measured, match = (None, {"result": "skipped"})
        if estimate is not None:
            measured, match = measure_start_ms(src, tmp_mp4, estimate, meta.fps_avg)
        if measured is not None:
            actual_start, basis = measured, "measured"
        elif estimate is not None:
            actual_start, basis = estimate, "estimated"
            warnings.append(f"起點無法以畫面比對確認（{match.get('result')}），使用推估值")
        else:
            actual_start, basis = None, "unknown"
            warnings.append("找不到起點前的 Keyframe，實際起點未知")

        actual_end = actual_start + out_dur if actual_start is not None else None
        start_err = abs(actual_start - start_ms) if actual_start is not None else None
        end_err = abs(actual_end - end_ms) if actual_end is not None else None
        errors = [e for e in (start_err, end_err) if e is not None]
        boundary = max(errors) if len(errors) == 2 else None

        tolerance = None
        if mode == "accurate":
            frame_ms = 1000 / meta.fps_avg if meta.fps_avg else 1000 / 30
            tolerance = round(frame_ms * ACCURATE_TOLERANCE_FRAMES)
            if start_err is not None and start_err > tolerance:
                warnings.append(f"起點誤差 {start_err} ms 超過容許值 {tolerance} ms")
            if end_err is not None and end_err > tolerance:
                warnings.append(f"終點誤差 {end_err} ms 超過容許值 {tolerance} ms")
        else:
            if start_err:
                warnings.append(f"copy 模式起點對齊 Keyframe，起點誤差 {start_err} ms")
            if end_err:
                warnings.append(f"copy 模式終點誤差 {end_err} ms")

        frame_accurate = (mode == "accurate" and basis == "measured" and boundary is not None
                          and tolerance is not None and boundary <= tolerance)

        result = ClipResult(
            input=src.resolve().as_posix(),
            output=dst.resolve().as_posix(),
            mode=mode,
            requested_start_ms=start_ms,
            requested_end_ms=end_ms,
            actual_start_ms=actual_start,
            actual_end_ms=actual_end,
            start_basis=basis,
            start_error_ms=start_err,
            end_error_ms=end_err,
            boundary_error_ms=boundary,
            tolerance_ms=tolerance,
            frame_accurate=frame_accurate,
            input_vfr_suspected=meta.is_vfr_suspected,
            status="warning" if warnings else "ok",
            warnings=warnings,
            match=match,
            elapsed_ms=round((time.perf_counter() - started) * 1000),
            ffmpeg_cmd=cmd,
            created_at=_now(),
        )

        # 先把 sidecar 寫成暫存檔，再依序發布 mp4 → json → log
        tmp_json = _new_temp(dst, ".tmp.json", src)
        temps.append(tmp_json)
        tmp_log = _new_temp(dst, ".tmp.log", src)
        temps.append(tmp_log)
        try:
            tmp_json.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_log.write_text(_render_log(result, proc.stderr), encoding="utf-8")
            for tmp, target in zip((tmp_mp4, tmp_json, tmp_log), _targets(dst)):
                os.replace(tmp, target)
                published.append(target)
        except OSError as exc:
            for target in published:            # 只移除本次已發布的檔案
                try:
                    target.unlink()
                except OSError:
                    pass
            raise ClipError("OUTPUT_NOT_WRITABLE",
                            f"發布輸出失敗（檔案可能被其他程式開啟）：{exc}") from exc
        return result
    except OSError as exc:
        raise ClipError("OUTPUT_NOT_WRITABLE", f"寫入暫存檔失敗：{exc}") from exc
    finally:
        for tmp in temps:                       # 只清理本次建立的暫存檔
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass


def clip_video(
    input_path: str | Path,
    start_ms: int,
    end_ms: int,
    output: str | Path,
    mode: str = "accurate",
    overwrite: bool = False,
) -> ClipResult:
    """切出 [start_ms, end_ms) 片段為 MP4，並寫出同名 .json 與 .log。

    成功或失敗都會在 vball_runs.jsonl 追加一筆執行紀錄。
    """
    started = time.perf_counter()
    src, dst = Path(input_path), Path(output)
    trace: dict = {}
    record = {
        "time": _now(), "vball": __version__, "input": str(src), "output": str(dst),
        "mode": mode, "requested_start_ms": start_ms, "requested_end_ms": end_ms,
        "overwrite": overwrite,
    }
    try:
        result = _clip(src, start_ms, end_ms, dst, mode, overwrite, trace, started)
    except VballError as exc:
        record.update(status="failed", code=exc.code, message=exc.message,
                      elapsed_ms=round((time.perf_counter() - started) * 1000), **trace)
        _append_run_log(dst, record)
        raise
    record.update(status=result.status, code=None, elapsed_ms=result.elapsed_ms,
                  start_basis=result.start_basis, boundary_error_ms=result.boundary_error_ms,
                  warnings=result.warnings)
    _append_run_log(dst, record)
    return result
