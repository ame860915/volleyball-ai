"""vball 命令列入口。

結束代碼：0 成功；1 可預期錯誤（stderr 印出 [錯誤代碼] 訊息）；2 參數錯誤（argparse）。
輸出契約：stdout 只輸出 JSON；主控台編碼（如 cp950）無法表示的字元改以 \\uXXXX 跳脫，
JSON 仍然有效。stderr 遇到無法表示的字元以 ? 取代，不會讓錯誤訊息本身失敗。
"""

from __future__ import annotations

import argparse
import json
import sys

from vball import __version__
from vball.errors import VballError


def _print_json(data: dict) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    try:
        print(text)
    except UnicodeEncodeError:
        print(json.dumps(data, ensure_ascii=True, indent=2))


def _cmd_probe(args: argparse.Namespace) -> int:
    from vball.video.probe import probe_video

    _print_json(probe_video(args.video).to_dict())
    return 0


def _cmd_clip(args: argparse.Namespace) -> int:
    from vball.video.clip import clip_video

    result = clip_video(args.video, args.start_ms, args.end_ms, args.out,
                        mode=args.mode, overwrite=args.overwrite)
    _print_json(result.to_dict())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vball", description="Volleyball AI Video Analysis System")
    parser.add_argument("--version", action="version", version=f"vball {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p_probe = sub.add_parser("probe", help="讀取影片 metadata，輸出 JSON")
    p_probe.add_argument("video", help="影片路徑")
    p_probe.set_defaults(func=_cmd_probe)

    p_clip = sub.add_parser("clip", help="切出影片片段為 MP4，並寫出 .json 與 .log")
    p_clip.add_argument("video", help="輸入影片路徑")
    p_clip.add_argument("--start-ms", type=int, required=True, help="起點（毫秒）")
    p_clip.add_argument("--end-ms", type=int, required=True, help="終點（毫秒）")
    p_clip.add_argument("--out", required=True, help="輸出 MP4 路徑")
    p_clip.add_argument("--mode", choices=["accurate", "copy"], default="accurate",
                        help="accurate：重新編碼、精準（預設）；copy：快，起點對齊 Keyframe")
    p_clip.add_argument("--overwrite", action="store_true", help="輸出已存在時覆蓋")
    p_clip.set_defaults(func=_cmd_clip)
    return parser


def _safe_stderr() -> None:
    reconfigure = getattr(sys.stderr, "reconfigure", None)
    if reconfigure:
        try:
            reconfigure(errors="replace")
        except (ValueError, OSError):
            pass


def main(argv: list[str] | None = None) -> int:
    _safe_stderr()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except VballError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
