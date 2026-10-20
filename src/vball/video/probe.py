"""以 FFprobe 讀取影片 metadata（Task 1.5）。

白話：像 AOI 取像前先讀相機的解析度與幀率，後續切片都以這份資訊驗證時間範圍。
時間一律以毫秒（int）表示；fps 只供參考，切片時以時間戳計算（影片可能為 VFR）。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path

from vball.errors import ProbeError

FFPROBE_TIMEOUT_S = 30
VFR_TOLERANCE = 0.01  # r_frame_rate 與 avg_frame_rate 相差超過 1% 視為疑似 VFR


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
    is_vfr_suspected: bool
    has_audio: bool
    audio_codec: str | None
    size_bytes: int

    def to_dict(self) -> dict:
        return asdict(self)


def _rate(value: str | None) -> float | None:
    """'30000/1001' → 29.97；'0/0' 或無效值 → None。"""
    if not value:
        return None
    try:
        frac = Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None
    return float(frac) if frac > 0 else None


def _duration_ms(fmt: dict, video: dict) -> int | None:
    for source in (fmt.get("duration"), video.get("duration")):
        try:
            seconds = float(source)
        except (TypeError, ValueError):
            continue
        if seconds > 0:
            return round(seconds * 1000)
    return None


def _run_ffprobe(path: Path) -> dict:
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
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "未知錯誤"
        raise ProbeError("INVALID_VIDEO", f"ffprobe 無法讀取影片：{detail}")
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ProbeError("FFPROBE_FAILED", "ffprobe 輸出不是有效 JSON") from exc


def probe_video(path: str | Path) -> VideoMetadata:
    """讀取影片 metadata。失敗時拋出帶錯誤代碼的 ProbeError。"""
    p = Path(path)
    if not p.is_file():
        raise ProbeError("INPUT_NOT_FOUND", f"找不到檔案：{p}")
    size = p.stat().st_size
    if size == 0:
        raise ProbeError("INVALID_VIDEO", f"檔案為 0 位元組：{p}")

    info = _run_ffprobe(p)
    streams = info.get("streams", [])
    fmt = info.get("format", {})
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if not videos:
        raise ProbeError("INVALID_VIDEO", f"沒有 video stream：{p}")
    video = videos[0]

    duration = _duration_ms(fmt, video)
    if duration is None:
        raise ProbeError("INVALID_VIDEO", f"無法取得有效長度（duration ≤ 0）：{p}")

    r_rate = video.get("r_frame_rate", "0/0")
    avg_rate = video.get("avg_frame_rate", "0/0")
    r, avg = _rate(r_rate), _rate(avg_rate)
    vfr = bool(r and avg and abs(r - avg) / r > VFR_TOLERANCE)

    return VideoMetadata(
        path=p.resolve().as_posix(),
        duration_ms=duration,
        width=int(video.get("width", 0)),
        height=int(video.get("height", 0)),
        video_codec=video.get("codec_name", "unknown"),
        r_frame_rate=r_rate,
        avg_frame_rate=avg_rate,
        fps_avg=round(avg, 3) if avg else None,
        is_vfr_suspected=vfr,
        has_audio=bool(audios),
        audio_codec=audios[0].get("codec_name") if audios else None,
        size_bytes=size,
    )
