"""vball 命令列入口。

結束代碼：0 成功；1 可預期錯誤（stderr 印出 [錯誤代碼] 訊息）；2 參數錯誤（argparse）。
"""

from __future__ import annotations

import argparse
import json
import sys

from vball import __version__
from vball.errors import VballError


def _cmd_probe(args: argparse.Namespace) -> int:
    from vball.video.probe import probe_video

    meta = probe_video(args.video)
    print(json.dumps(meta.to_dict(), ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vball", description="Volleyball AI Video Analysis System")
    parser.add_argument("--version", action="version", version=f"vball {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p_probe = sub.add_parser("probe", help="讀取影片 metadata，輸出 JSON")
    p_probe.add_argument("video", help="影片路徑")
    p_probe.set_defaults(func=_cmd_probe)
    return parser


def main(argv: list[str] | None = None) -> int:
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
