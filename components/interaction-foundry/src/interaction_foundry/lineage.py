"""Build private connected-lineage groups from the legacy source ledger."""

import argparse
import json
from pathlib import Path
import sqlite3


class _Groups:
    def __init__(self):
        self.parents = {}

    def find(self, value):
        self.parents.setdefault(value, value)
        if self.parents[value] != value:
            self.parents[value] = self.find(self.parents[value])
        return self.parents[value]

    def union(self, left, right):
        left, right = self.find(left), self.find(right)
        if left != right:
            self.parents[right] = left


def build_lineage(ledger_path: str | Path, *, source_scan_complete: bool) -> dict:
    """Return private components; never expose this mapping in a release.

    Each conversation is a node. Shared source-event identities and source
    locators join nodes. `source_scan_complete` is intentionally caller
    supplied from the scanner's terminal coverage report: a partial scan must
    never claim that its connected groups are globally complete.
    """
    db = sqlite3.connect(ledger_path)
    try:
        rows = db.execute("""
            SELECT e.event_id, e.conversation, e.family, s.locator
            FROM events e JOIN sources s ON s.event_id = e.event_id AND s.version = e.version
            ORDER BY e.family, e.conversation, e.event_id, s.locator
        """).fetchall()
    finally:
        db.close()
    groups, by_event, by_locator, nodes = _Groups(), {}, {}, set()
    for event_id, conversation, family, locator in rows:
        node = json.dumps([family, conversation], ensure_ascii=False, separators=(",", ":"))
        nodes.add(node)
        if event_id in by_event:
            groups.union(node, by_event[event_id])
        else:
            by_event[event_id] = node
        if locator in by_locator:
            groups.union(node, by_locator[locator])
        else:
            by_locator[locator] = node
    components = {}
    for node in sorted(nodes):
        components.setdefault(groups.find(node), []).append(json.loads(node))
    result = []
    for ordinal, members in enumerate(sorted((sorted(value) for value in components.values()), key=lambda value: json.dumps(value)), 1):
        result.append({"private_group_id": f"lineage-{ordinal:06d}", "members": members,
                       "complete": bool(source_scan_complete)})
    return {"schema": "interaction-foundry/private-lineage/v1", "source_scan_complete": bool(source_scan_complete),
            "event_rows": len(rows), "groups": result}


def supported_scan_complete(report: dict) -> bool:
    """Conservatively assess the old scanner's terminal coverage report."""
    if not isinstance(report, dict) or report.get("status") != "screening_only_not_semantically_reviewed":
        return False
    coverage = report.get("coverage")
    if not isinstance(coverage, dict) or not coverage:
        return False
    for stats in coverage.values():
        if not isinstance(stats, dict):
            return False
        if any(key.startswith("deferred_") or key in {"failed_or_unrecognized", "missing_directory"}
               for key, value in stats.items() if value):
            return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path, help="Private legacy events.sqlite ledger")
    parser.add_argument("--scan-report", type=Path, required=True, help="Private terminal screening.json")
    parser.add_argument("--output", type=Path, required=True, help="New private lineage JSON")
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error("output must be a new real file")
    report = json.loads(args.scan_report.read_text())
    lineage = build_lineage(args.ledger, source_scan_complete=supported_scan_complete(report))
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(lineage, indent=2) + "\n")
    print(json.dumps({"groups": len(lineage["groups"]), "source_scan_complete": lineage["source_scan_complete"]}))


if __name__ == "__main__":
    main()
