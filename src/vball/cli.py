"""vball 命令列入口。子指令（probe、clip）在後續 Task 加入。"""

from __future__ import annotations

import argparse
import sys

from vball import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vball",
        description="Volleyball AI Video Analysis System",
    )
    parser.add_argument("--version", action="version", version=f"vball {__version__}")
    parser.add_subparsers(dest="command", metavar="<command>")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
