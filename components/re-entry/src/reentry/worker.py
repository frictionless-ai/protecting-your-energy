from __future__ import annotations

import argparse
import os
import sys
import tomllib
from pathlib import Path

from .cli import register

HINT = "no pool configured: see docs/compute.md"
NOT_IMPLEMENTED = "pool configured but worker loop is not implemented: see docs/compute.md"


class PoolError(Exception):
    pass


def _pool() -> dict | None:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    path = Path(os.environ.get("REENTRY_POOL") or config_home / "reentry/pool.toml").expanduser()
    try:
        with path.open("rb") as fh:
            queue = tomllib.load(fh).get("queue")
    except FileNotFoundError:
        return None
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise PoolError(f"pool file unreadable: {path}: {exc}") from exc
    if not isinstance(queue, dict) or not queue.get("endpoint"):
        return None
    queues = queue.get("queues", [])
    if not isinstance(queues, list) or not all(isinstance(q, str) for q in queues):
        raise PoolError("pool file invalid: queues must be a list")
    return queue


def _worker_args(parser: argparse.ArgumentParser) -> None:
    pass


def _run_worker(args: argparse.Namespace) -> int:
    try:
        queue = _pool()
    except PoolError as exc:
        print(exc, file=sys.stderr)
        return 2
    if queue is None:
        print(HINT, file=sys.stderr)
        return 2
    print(NOT_IMPLEMENTED, file=sys.stderr)
    return 3


def _pool_args(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="pool_command", metavar="<subcommand>", required=True)
    sub.add_parser("status")


def _run_pool(args: argparse.Namespace) -> int:
    try:
        queue = _pool()
    except PoolError as exc:
        print(exc, file=sys.stderr)
        return 2
    if queue is None:
        print("closed")
        print(HINT)
        return 0
    queues = queue.get("queues") or []
    print(f"endpoint: {queue['endpoint']}")
    print(f"queues: {', '.join(map(str, queues)) or 'none'}")
    print("worker: not implemented")
    return 0


register("worker", _worker_args, _run_worker, "run a pool worker")
register("pool", _pool_args, _run_pool, "show the worker pool queue")
