"""Validate reviewed deidentified episodes before building an upload allowlist.

Review assertions are trusted-caller attestations, not automatic anonymization.
This module never receives original events and never uploads files.
"""
import hashlib
import json
from pathlib import Path
import re
from .privacy import PrivacyRedactor

FIELDS = {"case_id", "group_id", "domain", "split", "input", "rubric", "provenance_kind", "review"}
METADATA_FIELDS = {"task_label"}
LOCAL_ACTOR = re.compile(r"actor-[a-z0-9-]{1,80}")
LOCAL_MESSAGE = re.compile(r"message-[a-f0-9]{20}")
MESSAGE_FIELDS = {
    "role", "content", "speaker", "actor", "reply_to_actor", "quote_actor",
    "message_id", "reply_to_message", "quote_message",
}
RELATION_FIELDS = ("reply_to_actor", "quote_actor")
MESSAGE_REFERENCE_FIELDS = ("message_id", "reply_to_message", "quote_message")


def content_digest(case):
    payload = {key: value for key, value in case.items() if key != "review"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_case(case, deny_terms=()):
    allowed_fields = (FIELDS, FIELDS | {"metadata"})
    if not isinstance(case, dict) or set(case) not in allowed_fields:
        raise ValueError("Unexpected case fields")
    for key in ("case_id", "group_id"):
        if not isinstance(case[key], str) or not re.fullmatch(r"[a-z][a-z0-9-]{3,80}", case[key]):
            raise ValueError("Invalid opaque identifier")
    if case["domain"] not in ("discord", "ai_conversation") or case["split"] not in ("development", "validation", "test"):
        raise ValueError("Unknown domain or split")
    if case["provenance_kind"] not in {"deidentified_real_episode", "generalized_real_episode"}:
        raise ValueError("Release requires a reviewed real-episode provenance kind")
    inp, rubric, review = case["input"], case["rubric"], case["review"]
    if "metadata" in case:
        metadata = case["metadata"]
        if not isinstance(metadata, dict) or set(metadata) != METADATA_FIELDS or not isinstance(metadata["task_label"], str) or not metadata["task_label"].strip():
            raise ValueError("Invalid task metadata")
    if not isinstance(inp, dict) or set(inp) != {"messages", "context"} or not isinstance(inp["context"], str):
        raise ValueError("Invalid model input")
    if not isinstance(inp["messages"], list) or not inp["messages"]:
        raise ValueError("Missing messages")
    for message in inp["messages"]:
        fields = set(message) if isinstance(message, dict) else set()
        if (not isinstance(message, dict) or not {"role", "content"}.issubset(fields)
                or not fields.issubset(MESSAGE_FIELDS) or message["role"] not in ("system", "user", "assistant", "tool")):
            raise ValueError("Invalid message")
        if "speaker" in message and message["speaker"] not in ("self", "other"):
            raise ValueError("Invalid speaker attribution")
        if "actor" in message and (not isinstance(message["actor"], str) or not LOCAL_ACTOR.fullmatch(message["actor"])):
            raise ValueError("Invalid local actor attribution")
        for field in RELATION_FIELDS:
            if field in message and (not isinstance(message[field], str) or not LOCAL_ACTOR.fullmatch(message[field])):
                raise ValueError("Invalid local actor relation")
        for field in MESSAGE_REFERENCE_FIELDS:
            if field in message and (not isinstance(message[field], str) or not LOCAL_MESSAGE.fullmatch(message[field])):
                raise ValueError("Invalid local message relation")
        if not isinstance(message["content"], str) or not message["content"].strip():
            raise ValueError("Empty message")
    if not isinstance(rubric, dict) or set(rubric) != {"required", "forbidden", "outcome_status"}:
        raise ValueError("Invalid rubric")
    for key in ("required", "forbidden"):
        if not isinstance(rubric[key], list) or not rubric[key] or any(not isinstance(x, str) or not x.strip() for x in rubric[key]):
            raise ValueError("Rubric needs observable criteria")
    if rubric["outcome_status"] not in ("unknown", "user_confirmed", "tool_verified", "contradicted"):
        raise ValueError("Unsupported outcome evidence")
    if not isinstance(review, dict) or set(review) != {"privacy", "fidelity"}:
        raise ValueError("Invalid review")
    digest = content_digest(case)
    reviewers = []
    for kind in ("privacy", "fidelity"):
        decision = review[kind]
        if not isinstance(decision, dict) or set(decision) != {"status", "reviewer", "reviewed_content_sha256"}:
            raise ValueError("Invalid review decision")
        if decision["status"] != "approved" or not isinstance(decision["reviewer"], str) or not decision["reviewer"].strip():
            raise ValueError("Review incomplete")
        if decision["reviewed_content_sha256"] != digest:
            raise ValueError("Case changed after review")
        reviewers.append(decision["reviewer"])
    if reviewers[0] == reviewers[1]:
        raise ValueError("Privacy and fidelity reviews must be independent")
    redactor = PrivacyRedactor(deny_terms)
    # Scan actual field values: JSON escaping can conceal Windows paths, and
    # the review digest is an intentional artifact hash, not a source locator.
    def check(value, field=None):
        if field in MESSAGE_REFERENCE_FIELDS and isinstance(value, str) and LOCAL_MESSAGE.fullmatch(value):
            return
        if isinstance(value, str) and redactor.screen(value):
            raise ValueError("Potential private identifier requires review")
        if isinstance(value, list):
            for item in value:
                check(item)
        if isinstance(value, dict):
            for key, item in value.items():
                check(item, key)
    check({key: value for key, value in case.items() if key != "review"})
    for reviewer in reviewers:
        check(reviewer)


def build_release(cases, destination, *, deny_terms=(), private_provenance=None):
    cases = list(cases)
    if not cases:
        raise ValueError("No reviewed cases")
    groups, ids, payloads = {}, set(), {}
    for case in cases:
        validate_case(case, deny_terms)
        if case["case_id"] in ids:
            raise ValueError("Duplicate case identifier")
        ids.add(case["case_id"])
        group, split = case["group_id"], case["split"]
        if groups.setdefault(group, split) != split:
            raise ValueError("Conversation group crosses splits")
        payload = json.dumps(case["input"], sort_keys=True)
        if payloads.setdefault(payload, split) != split:
            raise ValueError("Identical input crosses splits")
    if private_provenance is not None:
        from .provenance import validate_private_provenance
        validate_private_provenance(private_provenance, cases)
    destination = Path(destination)
    if any(path.is_symlink() for path in (destination, *destination.parents)):
        raise ValueError("Release path cannot use symlinks")
    if destination.exists():
        raise ValueError("Release destination must be new")
    destination.mkdir(parents=True, mode=0o700)
    files = []
    for split in ("development", "validation", "test"):
        selected = [case for case in cases if case["split"] == split]
        if selected:
            name = f"{split}.jsonl"
            (destination / name).write_text("".join(json.dumps(case, ensure_ascii=False) + "\n" for case in selected))
            files.append(name)
    card = """---
language: en
task_categories:
- text-generation
tags:
- evaluation
---
# Interaction Foundry evaluation pilot

Reviewed deidentified real interaction episodes. Private release.
Original conversations and provenance mappings are intentionally excluded.
Model input is the `input` field only; `rubric` is evaluator-only information.
Privacy and fidelity approval records identify review roles, not a claim of human certification.
Pattern screening cannot guarantee anonymity; contextual review remains required.
This pilot does not establish population representativeness or model effectiveness.
No redistribution license is assigned pending source-rights review.
"""
    (destination / "README.md").write_text(card)
    files.append("README.md")
    manifest = {name: hashlib.sha256((destination / name).read_bytes()).hexdigest() for name in files}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
