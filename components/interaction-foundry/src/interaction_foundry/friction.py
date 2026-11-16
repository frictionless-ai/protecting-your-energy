"""Create private AI repair and stop-cause review packets from a legacy ledger."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3

from .focus import CONTINUE, friction_signals, stop_signal


def _private_path(path: Path) -> None:
    if "private" not in path.resolve().parts:
        raise ValueError("friction candidate output must remain under a private directory")


def _records(ledger_path: str | Path) -> list[dict]:
    with sqlite3.connect(Path(ledger_path)) as db:
        rows = db.execute(
            "SELECT event_id, version, data FROM events WHERE family != 'discord' "
            "ORDER BY family, conversation, json_extract(data, '$.ordinal')"
        ).fetchall()
    result = []
    for event_id, version, data in rows:
        record = json.loads(data)
        record["event_id"] = event_id
        record["version"] = version
        result.append(record)
    return result


def private_repair_candidates(ledger_path: str | Path) -> dict:
    """Return review-only correction and continuation-stop packets.

    Export order is retained as evidence but never presented as verified graph
    chronology. The records include private source material and must stay under
    ``private/``. They are not model inputs, learned rules, or outcome labels.
    """
    conversations: dict[tuple[str, str], list[dict]] = {}
    for record in _records(ledger_path):
        key = (record["family"], record["conversation_id"])
        conversations.setdefault(key, []).append(record)

    repairs, continuations, counts = [], [], Counter()
    for (family, conversation), sequence in conversations.items():
        for ordinal, record in enumerate(sequence):
            if record.get("role") != "user":
                continue
            text = record.get("text", "")
            previous = sequence[ordinal - 1] if ordinal else None
            following = sequence[ordinal + 1] if ordinal + 1 < len(sequence) else None
            if CONTINUE.fullmatch(text):
                if previous is not None and previous.get("role") == "assistant":
                    causes = stop_signal(previous.get("text", ""))
                    # Unknown alone does not establish a useful stop episode.
                    if causes != ["unknown"]:
                        continuations.append({
                            "kind": "continuation_after_possible_stop",
                            "family": family,
                            "conversation_id": conversation,
                            "previous_assistant": previous,
                            "continuation_request": record,
                            "stop_cause_candidates": causes,
                            "review_status": "pending_context_and_tool_evidence_review",
                        })
                continue
            signals = friction_signals(text)
            if not signals:
                continue
            for signal in signals:
                counts[signal] += 1
            repairs.append({
                "kind": "user_correction_candidate",
                "family": family,
                "conversation_id": conversation,
                "signals": signals,
                "previous_event": previous,
                "correction": record,
                "following_event": following,
                "ordering_basis": "export_order_not_verified_graph_chronology",
                "review_status": "pending_repair_and_outcome_review",
            })
    ranked = [
        {"signal": signal, "candidate_episodes": count}
        for signal, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    return {
        "schema": "interaction-foundry/private-repair-candidates/v1",
        "review_only": True,
        "candidate_counts": {
            "repair_episodes": len(repairs),
            "continuation_stop_episodes": len(continuations),
        },
        "signal_ranking": ranked,
        "repair_candidates": repairs,
        "continuation_stop_candidates": continuations,
        "limitations": [
            "Signal frequency is not incident frequency, annoyance, or causal evidence.",
            "Assistant completion claims are not verified outcomes.",
            "Export order requires branch/parent review before causal interpretation.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    _private_path(args.output)
    result = private_repair_candidates(args.ledger)
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"review_only": True, **result["candidate_counts"]}))


if __name__ == "__main__":
    main()
