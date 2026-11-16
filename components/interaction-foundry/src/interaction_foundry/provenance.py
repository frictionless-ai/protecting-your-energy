"""Validate private event-boundary evidence before a public-shaped release."""


def validate_private_provenance(mapping: dict, cases: list[dict]) -> None:
    """Require a complete, ordered partition of input and grading evidence.

    The mapping stays in ignored private storage. This checks structural
    isolation; it cannot determine whether a natural-language generalization
    faithfully represents those events, so independent fidelity review remains
    required.
    """
    if not isinstance(mapping, dict) or mapping.get("schema") != "interaction-foundry/private-provenance/v1":
        raise ValueError("unsupported private provenance mapping")
    entries = mapping.get("cases")
    if not isinstance(entries, list) or len(entries) != len(cases):
        raise ValueError("private provenance must cover every case exactly once")
    by_id = {}
    for entry in entries:
        required = {"case_id", "group_id", "lineage_complete", "source_artifacts", "decision_boundary", "input_event_ordinals", "grading_event_ordinals"}
        if not isinstance(entry, dict) or set(entry) != required:
            raise ValueError("invalid private provenance entry")
        case_id, group_id = entry["case_id"], entry["group_id"]
        if not isinstance(case_id, str) or case_id in by_id or not isinstance(group_id, str):
            raise ValueError("private provenance identifiers must be unique")
        if entry["lineage_complete"] is not True:
            raise ValueError("lineage grouping is incomplete")
        if not isinstance(entry["source_artifacts"], list) or not entry["source_artifacts"] or any(not isinstance(x, str) or not x for x in entry["source_artifacts"]):
            raise ValueError("private source artifacts are required")
        boundary = entry["decision_boundary"]
        before, after = entry["input_event_ordinals"], entry["grading_event_ordinals"]
        if type(boundary) is not int or boundary < 0 or not isinstance(before, list) or not before or not isinstance(after, list) or not after:
            raise ValueError("decision boundary and evidence partitions are required")
        if any(type(x) is not int or x < 0 for x in before + after):
            raise ValueError("event ordinals must be nonnegative integers")
        if any(x > boundary for x in before) or any(x <= boundary for x in after) or set(before).intersection(after):
            raise ValueError("input and grading evidence cross the decision boundary")
        by_id[case_id] = entry
    for case in cases:
        entry = by_id.get(case["case_id"])
        if entry is None or entry["group_id"] != case["group_id"]:
            raise ValueError("case and private provenance group mismatch")
