"""Local corpus scan. Output contains private provenance; never upload this folder."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path

from .focus import CONTINUE, discord_in_period, friction_signals, stop_signal
from .ingest import Ledger, events
from .io_policy import IoBudget

FAMILIES = ("discord", "claude_code", "codex_cli", "cursor_agent", "chatgpt_export", "claude_ai_export")


def scan(root, output, *, max_files=None, max_json_bytes=256 * 1024 * 1024,
         io_rate=8 * 1024 * 1024, io_burst=512 * 1024):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output == root or root in output.parents:
        raise ValueError("Output must be outside the source tree")
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output, 0o700)
    ledger = Ledger(output / "events.sqlite")
    io_budget = IoBudget(io_rate, io_burst)
    counts, problems = {}, []
    seen = set()
    for family in FAMILIES:
        print(json.dumps({"phase": "family_start", "family": family}), flush=True)
        stats = Counter()
        directory = root / family
        if not directory.is_dir():
            problems.append({"family": family, "error": "missing_directory"})
            counts[family] = dict(stats)
            continue
        file_count = 0
        for path in sorted(directory.rglob("*")):
            if path.is_symlink() or path.suffix not in (".json", ".jsonl") or not path.is_file():
                continue
            stats["discovered"] += 1
            info = path.stat()
            key = (info.st_dev, info.st_ino)
            if key in seen:
                stats["duplicate_inode"] += 1
                continue
            seen.add(key)
            if max_files is not None and stats["attempted"] >= max_files:
                stats["deferred_limit"] += 1
                continue
            if path.suffix == ".json" and info.st_size > max_json_bytes:
                stats["deferred_size"] += 1
                continue
            stats["attempted"] += 1
            file_count += 1
            if file_count % 25 == 0:
                print(json.dumps({"phase": "family_ingest", "family": family,
                                  "attempted": stats["attempted"],
                                  "inserted": stats["inserted_versions"]}), flush=True)
            try:
                stats["inserted_versions"] += ledger.ingest(events(path, family, io_budget=io_budget))
                stats["parsed"] += 1
            except (ValueError, UnicodeError, OSError, TypeError, KeyError, AttributeError) as exc:
                stats["failed_or_unrecognized"] += 1
                problems.append({"family": family, "path": str(path), "error_type": type(exc).__name__})
        counts[family] = dict(stats)
        print(json.dumps({"family": family, "counts": dict(stats)}), flush=True)
    occurrences, groups = Counter(), {}
    continuation_causes = Counter()
    discord = Counter()
    # Native parent/order review is still needed for branched conversations.
    previous = {}
    for (data,) in ledger.db.execute("SELECT data FROM events ORDER BY family, conversation"):
        event = json.loads(data)
        if event["family"] == "discord":
            discord["event_versions"] += 1
            if discord_in_period(event["timestamp"]):
                discord["in_period_versions"] += 1
            continue
        group = (event["family"], event["conversation_id"])
        if event["role"] == "user":
            if CONTINUE.fullmatch(event["text"]):
                for cause in stop_signal(previous.get(group, "")):
                    continuation_causes[cause] += 1
            for signal in friction_signals(event["text"]):
                occurrences[signal] += 1
                groups.setdefault(signal, set()).add(group)
        elif event["role"] == "assistant":
            previous[group] = event["text"]
    ranking = sorted(({"signal": name, "candidate_event_versions": count,
                       "candidate_conversations": len(groups[name])} for name, count in occurrences.items()),
                     key=lambda row: (-row["candidate_conversations"], -row["candidate_event_versions"], row["signal"]))
    report = {"status": "screening_only_not_semantically_reviewed", "coverage": counts,
              "discord": dict(discord), "friction_candidates": ranking,
              "continuation_cause_candidates": dict(continuation_causes),
              "limitations": ["Target Discord account attribution not resolved", "Event versions are not unique incidents",
                              "Graph export order is not chronology; stop candidates require parent-edge review",
                              "No claims about annoyance, abandonment, medication or causal phrasing effects",
                              "Unsupported formats and archives not ingested", "No dataset release or model evaluation"]}
    (output / "screening.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "ingestion-problems.json").write_text(json.dumps(problems, indent=2) + "\n")
    ledger.close()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Originals directory, read only")
    parser.add_argument("--output", required=True, type=Path, help="Private local output directory")
    parser.add_argument("--max-files", type=int, help="Per-family pilot limit; omitted scans all supported files")
    parser.add_argument("--io-rate", type=int, default=8 * 1024 * 1024,
                        help="Per-process read budget in bytes/sec; 0 disables throttling")
    parser.add_argument("--io-burst", type=int, default=512 * 1024,
                        help="Maximum uninterrupted read burst in bytes")
    args = parser.parse_args()
    if args.max_files is not None and args.max_files < 1:
        parser.error("max-files must be positive")
    report = scan(args.root, args.output, max_files=args.max_files,
                  io_rate=args.io_rate, io_burst=args.io_burst)
    print(json.dumps({"status": report["status"], "discord": report["discord"],
                      "friction_candidates": report["friction_candidates"]}))


if __name__ == "__main__":
    main()
