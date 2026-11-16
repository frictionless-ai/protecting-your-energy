from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Callable

from . import __version__

AddParser = Callable[[argparse.ArgumentParser], None]
RunFn = Callable[[argparse.Namespace], int]

COMMANDS: dict[str, tuple[AddParser, RunFn, str]] = {}
COMMAND_MODULES = ("reentry.tools", "reentry.doctor", "reentry.setup_cmd", "reentry.worker")


def register(name: str, add_parser: AddParser, run: RunFn, help: str = "") -> None:
    if name in COMMANDS:
        raise ValueError(f"command already registered: {name}")
    COMMANDS[name] = (add_parser, run, help)


def _load_commands() -> None:
    for mod in COMMAND_MODULES:
        try:
            importlib.import_module(mod)
        except ModuleNotFoundError as exc:
            if exc.name != mod:
                raise


def build_parser() -> argparse.ArgumentParser:
    _load_commands()
    parser = argparse.ArgumentParser(prog="reentry")
    parser.add_argument("--version", action="version", version=f"reentry {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    for name, (add_parser, _, help) in COMMANDS.items():
        add_parser(sub.add_parser(name, help=help))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return COMMANDS[args.command][1](args)


if __name__ == "__main__":
    # Command modules register with the canonical package module. Use that
    # registry when invoked with python -m as well as the installed entrypoint.
    from reentry.cli import main as package_main

    sys.exit(package_main())
