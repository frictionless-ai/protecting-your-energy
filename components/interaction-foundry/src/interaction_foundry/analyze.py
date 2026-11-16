"""Run private post-ingestion analysis only after a legacy scan is terminal."""

import argparse
import json
from pathlib import Path

from .friction import private_repair_candidates
from .lineage import build_lineage, supported_scan_complete
from .social import private_social_candidates


def _terminal_report(path: Path) -> dict:
    report = json.loads(path.read_text())
    if not isinstance(report, dict) or report.get("status") != "screening_only_not_semantically_reviewed":
        raise ValueError("a terminal legacy screening report is required")
    return report


def analyze_completed_ledger(ledger: str | Path, screening: str | Path, output: str | Path,
                             *, identity: str | Path | None = None) -> dict:
    """Create fresh private derivative artifacts from a finished ledger.

    A terminal report is distinct from full source coverage. The lineage output
    records that distinction, and all candidates remain review-only regardless
    of source completeness.
    """
    ledger, screening, output = Path(ledger), Path(screening), Path(output)
    if not ledger.is_file():
        raise ValueError("ledger must be an existing private file")
    if "private" not in output.resolve().parts or output.exists() or output.is_symlink():
        raise ValueError("output must be a new directory under private")
    report = _terminal_report(screening)
    output.mkdir(parents=True, mode=0o700)
    friction = private_repair_candidates(ledger)
    lineage = build_lineage(ledger, source_scan_complete=supported_scan_complete(report))
    (output / "repair-candidates.json").write_text(json.dumps(friction, ensure_ascii=False, indent=2) + "\n")
    (output / "lineage.json").write_text(json.dumps(lineage, ensure_ascii=False, indent=2) + "\n")
    result = {
        "schema": "interaction-foundry/private-analysis-run/v1",
        "review_only": True,
        "source_scan_complete": lineage["source_scan_complete"],
        "repair_episodes": friction["candidate_counts"]["repair_episodes"],
        "continuation_stop_episodes": friction["candidate_counts"]["continuation_stop_episodes"],
        "lineage_groups": len(lineage["groups"]),
        "social_analysis": "not_run_no_identity_attestation",
    }
    if identity is not None:
        social = private_social_candidates(ledger, identity)
        (output / "social-candidates.json").write_text(json.dumps(social, ensure_ascii=False, indent=2) + "\n")
        result["social_analysis"] = "review_packets_written"
        result["social_reply_candidates"] = len(social["reply_candidates"])
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--screening", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--identity", type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze_completed_ledger(args.ledger, args.screening, args.output,
                                              identity=args.identity)))


if __name__ == "__main__":
    main()
