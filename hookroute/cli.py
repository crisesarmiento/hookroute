"""Read one event and report a decision; this entry point never sends."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .core import InputError, decide
from .parsing import parse_event, parse_routes


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise InputError("invalid arguments; see hookroute --help")


def _read(path: str | None, message: str) -> str:
    try:
        if path is None:
            return sys.stdin.read()
        file = Path(path)
        if ".ssh" in file.parts or file.name.startswith(".env") or file.name in {
            "auth.json", "service.json"
        }:
            raise InputError(message)
        return file.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError):
        raise InputError(message) from None


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="hookroute", allow_abbrev=False, description="Decide locally; never send.")
    commands = parser.add_subparsers(dest="command", required=True)
    event = commands.add_parser("event", allow_abbrev=False, help="route one JSON event")
    event.add_argument("--dry-run", action="store_true", help="show the decision (both modes send nothing)")
    event.add_argument("--routes", default="routes.toml", metavar="PATH", help="TOML route file")
    event.add_argument("--file", metavar="PATH", help="JSON event file (default: stdin)")
    try:
        args = parser.parse_args(argv)
        routes = parse_routes(_read(args.routes, "could not read routes"))
        decision = decide(parse_event(_read(args.file, "could not read event")), routes)
    except InputError as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps({**asdict(decision), "sent": False}))
    return 0
