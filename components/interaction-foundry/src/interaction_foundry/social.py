"""Build private Discord reply/reaction review packets after explicit attribution.

This module deliberately creates *candidates*, not positive-reception labels.
It preserves the minimum surrounding evidence needed for a later independent
semantic review and keeps all native IDs and message text in private storage.
"""

import argparse
import json
from pathlib import Path
import sqlite3

from .focus import discord_in_period, social_signals
from .identity import load_verified_discord_accounts


def _private_path(path: Path) -> None:
    """Avoid an accidental export of raw Discord content through this CLI."""
    if "private" not in path.resolve().parts:
        raise ValueError("social candidate output must remain under a private directory")


def _discord_records(ledger_path: str | Path) -> list[dict]:
    with sqlite3.connect(Path(ledger_path)) as db:
        rows = db.execute(
            "SELECT event_id, version, data FROM events WHERE family = 'discord'"
        ).fetchall()
    records = []
    for event_id, version, data in rows:
        record = json.loads(data)
        record["event_id"] = event_id
        record["version"] = version
        records.append(record)
    return records


def private_social_candidates(ledger_path: str | Path, identity_path: str | Path) -> dict:
    """Return identity-gated private review packets from a completed legacy ledger.

    Replies must point to an in-period target message. Reaction counts are kept
    separate because their actors and timestamps may be absent from exports.
    No lexical pattern becomes a reception finding until a reviewer checks the
    paired messages and surrounding context.
    """
    target_accounts = load_verified_discord_accounts(identity_path)
    records = _discord_records(ledger_path)
    in_period = [record for record in records if discord_in_period(record.get("timestamp"))]
    target_by_source = {
        record["source_id"]: record
        for record in in_period
        if record.get("actor") in target_accounts
    }
    reply_candidates, reaction_candidates = [], []
    for record in in_period:
        if record.get("actor") in target_accounts:
            if (record.get("payload") or {}).get("reactions"):
                reaction_candidates.append({
                    "kind": "target_message_reactions_unattributed",
                    "target": record,
                    "review_status": "pending_reaction_actor_and_semantic_review",
                })
            continue
        parent = record.get("parent_id")
        target = target_by_source.get(parent)
        if target is None:
            continue
        # The legacy ledger stores normalized timing/actor fields alongside the
        # raw payload. Reconstruct only the view expected by the conservative
        # lexical screener; preserve the original record unchanged in output.
        signal_message = dict(record.get("payload") or {})
        signal_message["timestamp"] = record.get("timestamp")
        signal_message["author"] = {"id": record.get("actor")}
        signals = social_signals(signal_message, target_accounts)
        reply_candidates.append({
            "kind": "community_reply_to_target",
            "target": target,
            "reply": record,
            "lexical_review_signals": signals,
            "review_status": "pending_semantic_and_context_review",
        })
    return {
        "schema": "interaction-foundry/private-social-candidates/v1",
        "review_only": True,
        "target_account_count": len(target_accounts),
        "in_period_event_versions": len(in_period),
        "reply_candidates": reply_candidates,
        "reaction_candidates": reaction_candidates,
        "limitations": [
            "No candidate is a positive-reception or entertainment conclusion.",
            "Reaction actors and reaction times may be unavailable.",
            "Only direct native reply links are included; unlinked responses need separate review.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("identity", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    _private_path(args.output)
    result = private_social_candidates(args.ledger, args.identity)
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "review_only": True,
        "reply_candidates": len(result["reply_candidates"]),
        "reaction_candidates": len(result["reaction_candidates"]),
    }))


if __name__ == "__main__":
    main()
