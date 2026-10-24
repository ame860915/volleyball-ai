"""以 FFprobe 讀取影片 metadata（Task 1.5）。

白話：像 AOI 取像前先讀相機的解析度與幀率，後續切片都以這份資訊驗證時間範圍。
時間一律以毫秒（int）表示；fps 只供參考，切片時以時間戳計算（影片可能為 VFR）。

is_vfr_suspected 為啟發式判斷：只比較 r_frame_rate 與 avg_frame_rate，
無法偵測局部影格間隔變化（W3 再補時間戳分析）。rate 資訊不足時為 None（無法判斷）。
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from vball.errors import ProbeError

FFPROBE_TIMEOUT_S = 30
VFR_TOLERANCE = 0.01  # 相差超過 1% 視為疑似 VFR（初始值，未經大量手機影片驗證）


@dataclass(frozen=True)
class VideoMetadata:
    path: str
    duration_ms: int
    width: int
    height: int
    video_codec: str
    r_frame_rate: str
    avg_frame_rate: str
    fps_avg: float | None
    is_vfr_suspected: bool | None
    has_audio: bool
    audio_codec: str | None
    size_bytes: int

    def to_dict(self) -> dict:
        return asdict(self)


def _rate(value: Any) -> float | None:
    """'30000/1001' → 29.97；'0/0'、None 或無效值 → None。"""
    if not isinstance(value, str) or not value:
        return None
    try:
        frac = Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None
    return float(frac) if frac > 0 else None


def _vfr_suspected(r: float | None, avg: float | None) -> bool | None:
    if r is None or avg is None:
        return None
    return abs(r - avg) / r > VFR_TOLERANCE


def _duration_ms(*sources: Any) -> int | None:
    """依序嘗試各來源，回傳第一個有限且 > 0 毫秒的值。"""
    for source in sources:
        try:
            seconds = float(source)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(seconds):
            continue
        ms = round(seconds * 1000)
        if ms > 0:
            return ms
    return None


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value > 0 else None


def _run_ffprobe(path: Path) -> Any:
    exe = shutil.which("ffprobe")
    if not exe:
        raise ProbeError("FFPROBE_NOT_FOUND", "找不到 ffprobe，請確認在 (volleyball) 環境且 FFmpeg 在 PATH")
    cmd = [exe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=FFPROBE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProbeError("FFPROBE_FAILED", f"ffprobe 超過 {FFPROBE_TIMEOUT_S} 秒未完成") from exc
    except FileNotFoundError as exc:
        raise ProbeError("FFPROBE_NOT_FOUND", f"無法啟動 ffprobe：{exc}") from exc
    except OSError as exc:
        raise ProbeError("FFPROBE_FAILED", f"無法啟動 ffprobe：{exc}") from exc
    if result.returncode != 0:
        stderr = result.stderr.strip()
        detail = stderr.splitlines()[-1] if stderr else "未知錯誤"
        raise ProbeError("INVALID_VIDEO", f"ffprobe 無法讀取影片：{detail}")
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ProbeError("FFPROBE_FAILED", "ffprobe 輸出不是有效 JSON") from exc


def _parse(info: Any, p: Path, size: int) -> VideoMetadata:
    """把 ffprobe JSON 轉為 VideoMetadata；必要欄位缺失或型別錯誤一律 INVALID_VIDEO。"""
    def invalid(reason: str) -> ProbeError:
        return ProbeError("INVALID_VIDEO", f"{reason}：{p}")

    if not isinstance(info, dict):
        raise invalid("ffprobe 輸出格式異常")
    streams = info.get("streams")
    fmt = info.get("format")
    if not isinstance(streams, list):
        raise invalid("沒有 streams 資訊")
    if not isinstance(fmt, dict):
        fmt = {}
    streams = [s for s in streams if isinstance(s, dict)]
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if not videos:
        raise invalid("沒有 video stream")
    video = videos[0]

    width, height = _positive_int(video.get("width")), _positive_int(video.get("height"))
    if width is None or height is None:
        raise invalid("解析度缺失或無效")

    duration = _duration_ms(fmt.get("duration"), video.get("duration"))
    if duration is None:
        raise invalid("無法取得有效長度（duration ≤ 0 或非有限值）")

    r_rate = video.get("r_frame_rate") if isinstance(video.get("r_frame_rate"), str) else "0/0"
    avg_rate = video.get("avg_frame_rate") if isinstance(video.get("avg_frame_rate"), str) else "0/0"
    r, avg = _rate(r_rate), _rate(avg_rate)
    codec = video.get("codec_name")
    audio_codec = audios[0].get("codec_name") if audios else None

    return VideoMetadata(
        path=p.resolve().as_posix(),
        duration_ms=duration,
        width=width,
        height=height,
        video_codec=codec if isinstance(codec, str) and codec else "unknown",
        r_frame_rate=r_rate,
        avg_frame_rate=avg_rate,
        fps_avg=round(avg, 3) if avg else None,
        is_vfr_suspected=_vfr_suspected(r, avg),
        has_audio=bool(audios),
        audio_codec=audio_codec if isinstance(audio_codec, str) else None,
        size_bytes=size,
    )


def probe_video(path: str | Path) -> VideoMetadata:
    """讀取影片 metadata。失敗時拋出帶錯誤代碼的 ProbeError。"""
    p = Path(path)
    if not p.is_file():
        raise ProbeError("INPUT_NOT_FOUND", f"找不到檔案：{p}")
    size = p.stat().st_size
    if size == 0:
        raise ProbeError("INVALID_VIDEO", f"檔案為 0 位元組：{p}")
    return _parse(_run_ffprobe(p), p, size)
