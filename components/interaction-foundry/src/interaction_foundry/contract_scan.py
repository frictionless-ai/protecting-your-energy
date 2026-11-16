"""Import supported originals through contract-v1 adapters into a private ledger."""

import argparse
from collections import Counter
from functools import partial
import json
import os
from pathlib import Path

from .ai import iter_ai_jsonl
from .discord import iter_discord
from .ingestion import ingest
from .web_exports import iter_chatgpt_graph, iter_claude_web


FAMILIES = {
    "discord": ("*.json", iter_discord),
    "claude_code": ("*.jsonl", partial(iter_ai_jsonl, provider="claude_code_sessions")),
    "codex_cli": ("*.jsonl", partial(iter_ai_jsonl, provider="codex_sessions")),
    "cursor_agent": ("*.jsonl", partial(iter_ai_jsonl, provider="cursor_transcripts")),
    "gemini_antigravity": ("*.jsonl", partial(iter_ai_jsonl, provider="gemini_logs")),
    "chatgpt_export": ("*.json", iter_chatgpt_graph),
    "claude_ai_export": ("*.json", iter_claude_web),
}


def _private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)
    info = path.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("private output directory must be owner-private")


def _write_private_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")
    os.chmod(path, 0o600)


def scan(root: Path, output: Path, *, max_files: int | None = None,
         families: tuple[str, ...] | None = None) -> dict:
    """Scan only supported source families; JSON/JSONL parsing stays adapter-owned."""
    root, output = Path(root).resolve(), Path(output).resolve()
    if output == root or root in output.parents:
        raise ValueError("output must be outside source tree")
    selected = tuple(FAMILIES) if families is None else tuple(families)
    if not selected or any(family not in FAMILIES for family in selected) or len(set(selected)) != len(selected):
        raise ValueError("families must be unique supported family names")
    _private_directory(output)
    database = output / "contract-events.sqlite"
    seen, report = set(), {"status": "private_contract_ingestion", "families": {}, "unsupported_families": ["archives", "secondary_history_views"]}
    for family in selected:
        pattern, adapter = FAMILIES[family]
        stats = Counter()
        directory = root / family
        if not directory.is_dir():
            stats["missing_directory"] += 1
            report["families"][family] = dict(stats)
            continue
        for path in sorted(directory.rglob(pattern)):
            if path.is_symlink() or not path.is_file():
                continue
            info = path.stat()
            inode = (info.st_dev, info.st_ino)
            if inode in seen:
                stats["duplicate_inode"] += 1
                continue
            seen.add(inode)
            if max_files is not None and stats["attempted"] >= max_files:
                stats["deferred_limit"] += 1
                continue
            stats["attempted"] += 1
            try:
                stats.update(ingest(path, adapter, database))
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
                stats["failed_artifact"] += 1
                stats[f"error_{type(error).__name__}"] += 1
        report["families"][family] = dict(stats)
    _write_private_json(output / "contract-ingestion-report.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Read-only originals root")
    parser.add_argument("--output", type=Path, required=True, help="Ignored private output directory")
    parser.add_argument("--max-files", type=int, help="Per-family pilot limit")
    parser.add_argument("--family", action="append", choices=tuple(FAMILIES),
                        help="Repeat to import only selected supported families")
    args = parser.parse_args()
    if args.max_files is not None and args.max_files < 1:
        parser.error("--max-files must be positive")
    print(json.dumps(scan(args.root, args.output, max_files=args.max_files,
                         families=tuple(args.family) if args.family else None), indent=2))


if __name__ == "__main__":
    main()
