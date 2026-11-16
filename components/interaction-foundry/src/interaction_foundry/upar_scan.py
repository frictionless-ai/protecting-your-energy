"""Sequential, resumable UPAR corpus scan for a remote high-I/O host."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import inspect
import json
import os
from pathlib import Path
import threading

try:
    import fcntl
except ImportError:  # pragma: no cover - Linux supplies fcntl
    fcntl = None

from .ingestion import ingest
from .io_policy import IoBudget, advise_drop_cache, advise_sequential
from .upar import DEFAULT_MAX_RECORD_BYTES, iter_upar_contract


_AI_PLATFORMS = {"chatgpt", "claude", "claude_code", "cursor", "gemini", "codex"}
_SOURCE_LOCKS: dict[str, threading.Lock] = {}
_SOURCE_LOCKS_GUARD = threading.Lock()


def _domain_from_partition(path: Path, root: Path) -> str | None:
    """Return a partition hint; explicit unknown platforms stay excluded."""
    for part in path.relative_to(root).parts:
        if not part.startswith("platform="):
            continue
        platform = part.partition("=")[2].casefold()
        if platform == "discord":
            return "discord"
        if platform in _AI_PLATFORMS:
            return "ai_conversation"
        return "other"
    return None


def _conversation_paths(root: Path, domain: str | None):
    """Yield the sorted conversation JSONL inputs selected for this scan."""
    for path in sorted(root.glob("kind=conversation/**/*.jsonl")):
        if not path.is_file() or path.is_symlink():
            continue
        if domain is not None and (_domain_from_partition(path, root) not in (None, domain)):
            continue
        yield path


def _accepts_io_budget() -> bool:
    """Detect the ingestion worker's optional keyword without probing it."""
    try:
        parameters = inspect.signature(ingest).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(parameter.name == "io_budget" or
               parameter.kind is inspect.Parameter.VAR_KEYWORD
               for parameter in parameters)


class _BudgetedReader:
    """Apply the shared byte budget to a binary reader without buffering it."""

    def __init__(self, stream, budget: IoBudget):
        self._stream, self._budget = stream, budget

    def read(self, size: int = -1):
        value = self._stream.read(size)
        self._budget.consume(len(value))
        return value


def _report_only(path: Path, domain: str | None, budget: IoBudget,
                 max_record_bytes: int) -> dict:
    """Count contract outcomes without snapshotting or storing raw events."""
    counts = Counter()
    with path.open("rb") as source:
        advise_sequential(source)
        try:
            for record in iter_upar_contract(_BudgetedReader(source, budget), domain=domain,
                                             max_record_bytes=max_record_bytes):
                counts[str(record.get("status", "invalid"))] += 1
        finally:
            advise_drop_cache(source)
    return dict(counts)


def _source_lock(root: Path):
    key = str(root)
    with _SOURCE_LOCKS_GUARD:
        lock = _SOURCE_LOCKS.setdefault(key, threading.Lock())
    return lock


@contextmanager
def _exclusive_source_scan(root: Path):
    """Serialize readers of one source tree across threads and processes."""
    with _source_lock(root):
        if fcntl is None:
            yield
            return
        lock_name = hashlib.sha256(str(root).encode()).hexdigest()
        lock_path = Path("/tmp") / f"interaction-foundry-upar-{lock_name}.lock"
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)


def scan(root: str | Path, output: str | Path, *, domain: str | None = None,
         max_files: int | None = None, io_rate: int = 8 * 1024 * 1024,
         io_burst: int = 512 * 1024,
         max_record_bytes: int = DEFAULT_MAX_RECORD_BYTES,
         report_only: bool = False) -> dict:
    if domain not in (None, "discord", "ai_conversation"):
        raise ValueError("unsupported UPAR domain")
    if max_files is not None and (type(max_files) is not int or max_files < 1):
        raise ValueError("max_files must be positive")
    if type(max_record_bytes) is not int or max_record_bytes < 1:
        raise ValueError("max_record_bytes must be positive")
    root, output = Path(root).resolve(), Path(output).resolve()
    if not root.is_dir() or root == output or root in output.parents:
        raise ValueError("UPAR root must be a directory and output must be outside it")
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    database = output / "events.sqlite"
    counts = Counter()
    budget = IoBudget(io_rate, io_burst)
    budgeted_ingest = _accepts_io_budget()
    with _exclusive_source_scan(root):
        for path in _conversation_paths(root, domain):
            if max_files is not None and counts["attempted"] >= max_files:
                counts["deferred_limit"] += 1
                continue
            counts["attempted"] += 1
            try:
                adapter = lambda stream: iter_upar_contract(
                    stream, domain=domain, max_record_bytes=max_record_bytes)
                if report_only:
                    result = _report_only(path, domain, budget, max_record_bytes)
                elif budgeted_ingest:
                    result = ingest(path, adapter, database, io_budget=budget)
                else:
                    result = ingest(path, adapter, database)
            except (OSError, UnicodeError, TypeError, ValueError, json.JSONDecodeError) as exc:
                counts["failed"] += 1
                with (output / "problems.jsonl").open("a", encoding="utf-8") as report:
                    report.write(json.dumps({"path": str(path), "error": type(exc).__name__}) + "\n")
                continue
            counts["parsed"] += 1
            counts.update(result)
            print(json.dumps({"path": str(path), "counts": result}), flush=True)
    report = {"status": "terminal", "mode": "report_only" if report_only else "ledger",
              "domain": domain, "root": str(root), "counts": dict(counts)}
    (output / "screening.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="archive/corpus/records directory")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--domain", choices=("discord", "ai_conversation"))
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--io-rate", type=int, default=8 * 1024 * 1024,
                        help="Shared read budget in bytes/sec; 0 disables throttling")
    parser.add_argument("--io-burst", type=int, default=512 * 1024,
                        help="Maximum uninterrupted read burst in bytes")
    parser.add_argument("--max-record-bytes", type=int, default=DEFAULT_MAX_RECORD_BYTES,
                        help="Maximum bytes in one JSONL record before quarantine")
    parser.add_argument("--report-only", action="store_true",
                        help="Count source contract outcomes without creating a raw-event SQLite mirror")
    args = parser.parse_args()
    if args.max_files is not None and args.max_files < 1:
        parser.error("max-files must be positive")
    print(json.dumps(scan(args.root, args.output, domain=args.domain,
                          max_files=args.max_files, io_rate=args.io_rate,
                          io_burst=args.io_burst, max_record_bytes=args.max_record_bytes,
                          report_only=args.report_only)))


if __name__ == "__main__":
    main()
