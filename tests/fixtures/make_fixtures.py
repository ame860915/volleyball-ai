"""用 FFmpeg 合成測試影片（Task 1.4）。

不依賴任何授權影片；產生的 .mp4 不進 Git，只有這支腳本進 Git。

用法（Windows PowerShell，volleyball 環境）：
    python tests/fixtures/make_fixtures.py
    python tests/fixtures/make_fixtures.py --out D:/tmp/fixtures --force
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_OUT = Path(__file__).resolve().parent / "videos"
SIZE = "320x240"


@dataclass(frozen=True)
class Fixture:
    """一支測試影片的規格與預期值（供 probe / clip 測試比對）。"""

    name: str
    description: str
    valid: bool                       # ffprobe 是否應能讀出影片
    duration_s: float | None = None   # 預期長度（秒）
    fps: str | None = None            # 預期 r_frame_rate
    has_audio: bool | None = None
    vfr: bool = False
    gop: int | None = None            # Keyframe 間隔（影格數）


FIXTURES: list[Fixture] = [
    Fixture("cfr30_audio.mp4", "30fps 固定幀率，含音訊，3 秒", True, 3.0, "30/1", True, gop=30),
    Fixture("cfr60_audio.mp4", "60fps 固定幀率，含音訊，3 秒", True, 3.0, "60/1", True, gop=60),
    Fixture("vfr_mixed.mp4", "可變幀率：前 1 秒 30fps，後 2 秒 15fps，無音訊", True, 3.0, None, False, vfr=True),
    Fixture("cfr30_noaudio.mp4", "30fps，無音訊，3 秒", True, 3.0, "30/1", False, gop=30),
    Fixture("empty.mp4", "0 位元組的空檔案", False),
    Fixture("corrupt.mp4", "副檔名為 .mp4 的非影片內容", False),
]


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        sys.exit("找不到 ffmpeg，請確認在 (volleyball) 環境且 FFmpeg 在 PATH")
    return exe


def _run(args: list[str]) -> None:
    cmd = [_ffmpeg(), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 失敗：{' '.join(cmd)}\n{result.stderr}")


def _video_in(fps: int, seconds: float) -> list[str]:
    return ["-f", "lavfi", "-i", f"testsrc2=size={SIZE}:rate={fps}:duration={seconds}"]


def _audio_in(seconds: float) -> list[str]:
    return ["-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={seconds}"]


def _x264(gop: int) -> list[str]:
    return [
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-g", str(gop), "-keyint_min", str(gop), "-sc_threshold", "0",
    ]


def build(fx: Fixture, path: Path) -> None:
    if fx.name == "cfr30_audio.mp4":
        _run([*_video_in(30, 3), *_audio_in(3), *_x264(30), "-c:a", "aac", "-shortest", str(path)])
    elif fx.name == "cfr60_audio.mp4":
        _run([*_video_in(60, 3), *_audio_in(3), *_x264(60), "-c:a", "aac", "-shortest", str(path)])
    elif fx.name == "cfr30_noaudio.mp4":
        _run([*_video_in(30, 3), *_x264(30), "-an", str(path)])
    elif fx.name == "vfr_mixed.mp4":
        # 30 + 30 影格；前 30 格間隔 1/30 秒，後 30 格間隔 1/15 秒 → 共 3 秒
        pts = "if(lt(N,30),N/30,1+(N-30)/15)/TB"
        _run([
            *_video_in(30, 2), "-vf", f"setpts='{pts}'",
            "-fps_mode", "vfr", *_x264(30), "-an", "-video_track_timescale", "90000", str(path),
        ])
    elif fx.name == "empty.mp4":
        path.write_bytes(b"")
    elif fx.name == "corrupt.mp4":
        path.write_bytes(b"this is not a video file\n" * 64)
    else:
        raise ValueError(f"未知 fixture：{fx.name}")


def make_all(out_dir: Path = DEFAULT_OUT, force: bool = False) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    made: list[Path] = []
    for fx in FIXTURES:
        path = out_dir / fx.name
        if path.exists() and not force:
            print(f"略過（已存在）：{path.name}")
        else:
            build(fx, path)
            print(f"已產生：{path.name}  {path.stat().st_size:,} bytes")
        made.append(path)
    manifest = out_dir / "manifest.json"
    manifest.write_text(
        json.dumps([asdict(f) for f in FIXTURES], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return made


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="產生測試影片")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="輸出資料夾")
    parser.add_argument("--force", action="store_true", help="已存在也重新產生")
    args = parser.parse_args(argv)
    make_all(args.out, args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
