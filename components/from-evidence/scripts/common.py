"""Shared helpers for from-evidence scripts. Standard library only."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")).expanduser() / "from-evidence"
STATE_ROOT = Path(os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local/state")).expanduser() / "from-evidence"
DATASETS = Path(os.environ.get("FROM_EVIDENCE_DATASETS") or str(DATA_ROOT / "datasets")).expanduser()
TEMPLATES = ROOT / "templates"
GENERATED = Path(os.environ.get("FROM_EVIDENCE_GENERATED") or str(STATE_ROOT / "generated")).expanduser()
PLUGIN_JSON = ROOT / ".claude-plugin" / "plugin.json"
BUILD_JSON = Path(os.environ.get("FROM_EVIDENCE_BUILD") or str(DATA_ROOT / "build.json")).expanduser()

RECORD_FIELDS = {
    "id": str,
    "source": str,
    "medium": str,
    "partner": str,
    "ts": str,
    "topic": str,
    "turns": list,
    "moves": list,
    "outcome": str,
    "why_it_worked_or_failed": str,
    "quality": int,
}
TURN_FIELDS = {"ts": str, "author": str, "text": str}
MANIFEST_FIELDS = {
    "name": str,
    "version": str,
    "pattern": str,
    "sources": list,
    "record_count": int,
    "held_out_ids": list,
}
SOURCE_KINDS = {"discord", "chat-export", "notes", "email", "forum", "synthetic"}
OUTCOMES = {"conceded", "convinced", "redirected", "stalled", "escalated", "dropped"}
SUBJECT = "self"
QUOTABLE_QUALITY = 4

SPEC_SECTIONS = [
    "Identity",
    "Benefits",
    "Language",
    "Behaviour",
    "Communication style",
    "Demeanor",
    "Motivations",
    "Moves: opening",
    "Moves: escalation",
    "Moves: repair",
    "Moves: exit",
    "Phrase bank",
    "Anti-patterns",
    "Held-out exemplars",
]
# Optional. "Core rules": at most MAX_CORE_RULES ranked rules rendered at the top of
# SKILL.md (instruction adherence drops past ~5 constraints and mid-prompt content
# is lost). "Inline exemplars": up to MAX_INLINE_EXEMPLARS training record ids
# whose full turns are rendered inside SKILL.md (few-shot dialogue lines beat
# persona descriptions in every role-play study in the research notes).
# "Agent protocol": how a subagent built from this spec challenges another agent's
# claims (distinct opposer, external check before asserting fault, null move, round
# cap). Rendered by kind: subagent.
OPTIONAL_SPEC_SECTIONS = ["Core rules", "Inline exemplars", "Agent protocol"]
MAX_CORE_RULES = 6
MAX_INLINE_EXEMPLARS = 8
# Goal contract. Every generated artifact must say what it does (one_line), why it
# helps (why_it_helps: the mechanism, with the evidence it rests on), when to use it
# (trigger_description) and when not to (when_not_to_use). An artifact that cannot
# fill all four is not ready to forge.
IDENTITY_KEYS = ["skill_name", "one_line", "why_it_helps", "trigger_description", "when_not_to_use"]

KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
PHRASE_LINE = re.compile(r'^"(?P<phrase>.+)" \(n=(?P<n>\d+)(?:; (?P<ids>[^)]*))?\)$')
ANTI_LINE = re.compile(r"^never: (?P<desc>.+?)(?: \(markers: (?P<markers>.+)\))?$")
PLACEHOLDER = re.compile(r"\{\{([a-z0-9_]+)\}\}")


class ContractError(Exception):
    """A dataset, spec, manifest or template broke the contract."""


def read_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        raise ContractError(f"Cannot read configured JSON {path}: {exc}") from exc


def dump_json(data) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_records(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line.strip():
                raise ContractError(f"{path}:{lineno}: blank line in records.jsonl")
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ContractError(f"{path}:{lineno}: invalid JSON ({exc.msg})") from exc
    return records


def parse_frontmatter(text: str) -> dict | None:
    """Minimal YAML frontmatter reader: top-level `key: value` and `key: >-` blocks."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    body = text[4:end].split("\n")
    result: dict[str, str] = {}
    key = None
    block: list[str] = []
    for line in body:
        if line and not line.startswith((" ", "\t")):
            if key is not None:
                result[key] = "\n".join(block).strip()
            if ":" not in line:
                return None
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value in (">", ">-", "|", "|-"):
                block = []
            else:
                block = [value]
        elif key is not None:
            block.append(line.strip())
    if key is not None:
        result[key] = "\n".join(block).strip()
    return result


def parse_spec(path: Path) -> dict:
    """Parse spec.md into {section: [lines]} plus identity dict, phrases, anti-patterns."""
    text = path.read_text(encoding="utf-8")
    sections: dict[str, list[str]] = {}
    current = None
    for raw in text.split("\n"):
        if raw.startswith("## "):
            current = raw[3:].strip()
            if current in sections:
                raise ContractError(f"{path}: duplicate section '{current}'")
            sections[current] = []
        elif current is not None and raw.startswith("- "):
            sections[current].append(raw[2:].strip())
    missing = [s for s in SPEC_SECTIONS if s not in sections]
    if missing:
        raise ContractError(f"{path}: missing sections {missing}")
    unknown = [s for s in sections if s not in SPEC_SECTIONS + OPTIONAL_SPEC_SECTIONS]
    if unknown:
        raise ContractError(f"{path}: unknown sections {unknown}")
    empty = [s for s in SPEC_SECTIONS if not sections[s]]
    if empty:
        raise ContractError(f"{path}: empty sections {empty}")
    for opt in OPTIONAL_SPEC_SECTIONS:
        sections.setdefault(opt, [])
    if len(sections["Core rules"]) > MAX_CORE_RULES:
        raise ContractError(f"{path}: Core rules has {len(sections['Core rules'])} lines; max {MAX_CORE_RULES}")
    if len(sections["Inline exemplars"]) > MAX_INLINE_EXEMPLARS:
        raise ContractError(f"{path}: Inline exemplars has {len(sections['Inline exemplars'])} ids; max {MAX_INLINE_EXEMPLARS}")

    identity: dict[str, str] = {}
    for line in sections["Identity"]:
        key, sep, value = line.partition(":")
        if not sep:
            raise ContractError(f"{path}: Identity line without 'key: value': {line}")
        identity[key.strip()] = value.strip()
    for key in IDENTITY_KEYS:
        if not identity.get(key):
            raise ContractError(f"{path}: Identity missing '{key}'")
    if not KEBAB.match(identity["skill_name"]):
        raise ContractError(f"{path}: skill_name must be kebab-case")

    phrases = []
    for line in sections["Phrase bank"]:
        m = PHRASE_LINE.match(line)
        if not m:
            raise ContractError(
                f"{path}: phrase bank line must look like "
                f'"phrase" (n=2; r-001, r-002): {line}'
            )
        ids = [i.strip() for i in (m.group("ids") or "").split(",") if i.strip()]
        phrases.append({"phrase": m.group("phrase"), "n": int(m.group("n")), "ids": ids})

    def _norm_name(x: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", x.lower()).strip("-")

    name_norm = _norm_name(identity["skill_name"])
    for ph in phrases:
        if _norm_name(ph["phrase"]) == name_norm:
            raise ContractError(
                f"{path}: skill_name '{identity['skill_name']}' is a phrase-bank catchphrase; "
                f"name the skill for what it does to the user or the work (verb + object), not for a line the subject says"
            )

    antis = []
    for line in sections["Anti-patterns"]:
        m = ANTI_LINE.match(line)
        if not m:
            raise ContractError(
                f"{path}: anti-pattern line must look like "
                f'never: <what> (markers: "a", "b"): {line}'
            )
        markers = re.findall(r'"([^"]+)"', m.group("markers") or "")
        antis.append({"description": m.group("desc").strip(), "markers": markers})

    return {
        "sections": sections,
        "identity": identity,
        "phrases": phrases,
        "anti_patterns": antis,
        "held_out": sections["Held-out exemplars"],
        "core_rules": sections["Core rules"],
        "inline_exemplars": sections["Inline exemplars"],
        "agent_protocol": sections["Agent protocol"],
        "benefits": sections["Benefits"],
    }


def validate_dataset(dataset_dir: Path) -> tuple[dict, list[dict]]:
    """Check a dataset directory against the contract. Return (manifest, records)."""
    if not dataset_dir.is_dir():
        raise ContractError(f"{dataset_dir}: not a directory")
    for name in ("dataset.json", "records.jsonl", "digest.md", "spec.md"):
        if not (dataset_dir / name).is_file():
            raise ContractError(f"{dataset_dir}: missing {name}")

    manifest = read_json(dataset_dir / "dataset.json")
    for key, typ in MANIFEST_FIELDS.items():
        if key not in manifest:
            raise ContractError(f"{dataset_dir}/dataset.json: missing '{key}'")
        if not isinstance(manifest[key], typ):
            raise ContractError(f"{dataset_dir}/dataset.json: '{key}' must be {typ.__name__}")
    if manifest["name"] != dataset_dir.name:
        raise ContractError(f"{dataset_dir}/dataset.json: name must equal directory name")
    if not (KEBAB.match(manifest["name"]) or KEBAB.match(manifest["name"].lstrip("_"))):
        raise ContractError(f"{dataset_dir}/dataset.json: name must be kebab-case")
    if not SEMVER.match(manifest["version"]):
        raise ContractError(f"{dataset_dir}/dataset.json: version must be semver")
    if not manifest["sources"]:
        raise ContractError(f"{dataset_dir}/dataset.json: sources[] is empty")
    for src in manifest["sources"]:
        if not isinstance(src, dict) or not {"kind", "path", "note"} <= set(src):
            raise ContractError(f"{dataset_dir}/dataset.json: each source needs kind, path, note")
        if src["kind"] not in SOURCE_KINDS:
            raise ContractError(f"{dataset_dir}/dataset.json: source kind '{src['kind']}' not in {sorted(SOURCE_KINDS)}")

    records = read_records(dataset_dir / "records.jsonl")
    if manifest["record_count"] != len(records):
        raise ContractError(
            f"{dataset_dir}/dataset.json: record_count={manifest['record_count']} "
            f"but records.jsonl has {len(records)} lines"
        )
    seen: set[str] = set()
    source_kinds = {s["kind"] for s in manifest["sources"]}
    for rec in records:
        for key, typ in RECORD_FIELDS.items():
            if key not in rec:
                raise ContractError(f"record {rec.get('id', '?')}: missing '{key}'")
            if not isinstance(rec[key], typ) or (typ is int and isinstance(rec[key], bool)):
                raise ContractError(f"record {rec.get('id', '?')}: '{key}' must be {typ.__name__}")
        extra = set(rec) - set(RECORD_FIELDS)
        if extra:
            raise ContractError(f"record {rec['id']}: unknown fields {sorted(extra)}")
        if rec["id"] in seen:
            raise ContractError(f"record {rec['id']}: duplicate id")
        seen.add(rec["id"])
        if rec["source"] not in source_kinds:
            raise ContractError(f"record {rec['id']}: source '{rec['source']}' not declared in manifest sources")
        if rec["outcome"] not in OUTCOMES:
            raise ContractError(f"record {rec['id']}: outcome '{rec['outcome']}' not in {sorted(OUTCOMES)}")
        if not 1 <= rec["quality"] <= 5:
            raise ContractError(f"record {rec['id']}: quality must be 1..5")
        if not rec["turns"]:
            raise ContractError(f"record {rec['id']}: turns[] is empty")
        authors = set()
        for i, turn in enumerate(rec["turns"]):
            for key, typ in TURN_FIELDS.items():
                if key not in turn or not isinstance(turn[key], typ):
                    raise ContractError(f"record {rec['id']} turn {i}: '{key}' must be {typ.__name__}")
            authors.add(turn["author"])
        if SUBJECT not in authors:
            raise ContractError(f"record {rec['id']}: no turn authored by '{SUBJECT}'")
        if not rec["moves"] or not all(isinstance(m, str) and re.match(r"^[a-z0-9_]+$", m) for m in rec["moves"]):
            raise ContractError(f"record {rec['id']}: moves[] must be non-empty snake_case strings")
    for hid in manifest["held_out_ids"]:
        if hid not in seen:
            raise ContractError(f"{dataset_dir}/dataset.json: held_out id '{hid}' not in records.jsonl")
    if len(manifest["held_out_ids"]) >= len(records):
        raise ContractError(f"{dataset_dir}/dataset.json: every record is held out; nothing to build from")

    spec = parse_spec(dataset_dir / "spec.md")
    if set(spec["held_out"]) != set(manifest["held_out_ids"]):
        raise ContractError(
            f"{dataset_dir}: spec.md held-out ids {sorted(spec['held_out'])} "
            f"differ from dataset.json {sorted(manifest['held_out_ids'])}"
        )
    held = set(manifest["held_out_ids"])
    for ph in spec["phrases"]:
        for rid in ph["ids"]:
            if rid not in seen:
                raise ContractError(f"{dataset_dir}/spec.md: phrase cites unknown record {rid}")
            if rid in held:
                raise ContractError(f"{dataset_dir}/spec.md: phrase cites held-out record {rid}")
    return manifest, records


def split_records(manifest: dict, records: list[dict]) -> tuple[list[dict], list[dict]]:
    held = set(manifest["held_out_ids"])
    training = [r for r in records if r["id"] not in held]
    held_out = [r for r in records if r["id"] in held]
    return training, held_out


def render(template: str, values: dict[str, str], where: str) -> str:
    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key not in values:
            raise ContractError(f"{where}: no value for placeholder {{{{{key}}}}}")
        return values[key]

    out = PLACEHOLDER.sub(sub, template)
    left = PLACEHOLDER.findall(out)
    if left:
        raise ContractError(f"{where}: placeholders survived rendering: {sorted(set(left))}")
    return out
