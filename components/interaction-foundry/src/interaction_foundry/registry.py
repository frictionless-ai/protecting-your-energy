"""Versioned advisory rules. No registry operation grants execution authority."""
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import sqlite3
from urllib.parse import quote


class StaleRevision(ValueError):
    """The caller must reload before retrying its edit."""


@dataclass(frozen=True)
class Rule:
    id: str
    text: str
    provenance: tuple[str, ...]
    scope: str = "project"
    scope_id: str | None = None
    status: str = "candidate"
    applicability: tuple[str, ...] = ()
    exceptions: tuple[str, ...] = ()
    compatibility: tuple[str, ...] = ()
    preference_expression_evidence: tuple[str, ...] = ()
    effectiveness_evidence: tuple[str, ...] = ()
    expires_at: float | None = None
    reviewed: bool = False

    def __post_init__(self):
        for name in ("id", "text"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be nonempty text")
        for name in ("provenance", "applicability", "exceptions", "compatibility",
                     "preference_expression_evidence", "effectiveness_evidence"):
            values = getattr(self, name)
            if not isinstance(values, (tuple, list)) or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise ValueError(f"{name} must contain nonempty strings")
            object.__setattr__(self, name, tuple(values))
        if not self.provenance:
            raise ValueError("provenance is required")
        if self.scope not in ("project", "user", "global", "session"):
            raise ValueError("unknown scope")
        if self.scope == "global":
            if self.scope_id is not None:
                raise ValueError("global scope has no identifier")
        elif not isinstance(self.scope_id, str) or not self.scope_id.strip():
            raise ValueError("non-global scope requires scope_id")
        if self.status not in ("candidate", "active", "deprecated"):
            raise ValueError("unknown status")
        if type(self.reviewed) is not bool:
            raise ValueError("reviewed must be boolean")
        if self.status == "active" and not self.reviewed:
            raise ValueError("activation requires explicit review")
        if self.expires_at is not None and (
            isinstance(self.expires_at, bool) or not isinstance(self.expires_at, (int, float))
            or not math.isfinite(self.expires_at)
        ):
            raise ValueError("expires_at must be a finite Unix timestamp")


class Registry:
    """One SQLite writer at a time; callers supply the expected head revision."""

    def __init__(self, path: str = ":memory:", *, read_only: bool = False):
        if type(read_only) is not bool:
            raise ValueError("read_only must be boolean")
        if read_only:
            if path == ":memory:":
                raise ValueError("read_only requires an existing database path")
            database = Path(path).expanduser()
            if not database.is_file():
                raise FileNotFoundError(database)
            uri = f"file:{quote(str(database.resolve()), safe='/')}?mode=ro"
            self._db = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=5)
            return
        self._db = sqlite3.connect(path, isolation_level=None, timeout=5)
        self._db.executescript('''
            CREATE TABLE IF NOT EXISTS revisions (
                revision INTEGER PRIMARY KEY, rules TEXT NOT NULL, reason TEXT NOT NULL);
            INSERT OR IGNORE INTO revisions VALUES (0, '[]', 'initial');
            CREATE TABLE IF NOT EXISTS invalidated (id TEXT PRIMARY KEY);
        ''')

    def close(self):
        self._db.close()

    @property
    def revision(self) -> int:
        return self._db.execute("SELECT MAX(revision) FROM revisions").fetchone()[0]

    def snapshot(self, revision: int | None = None, *, audit: bool = False) -> tuple[Rule, ...]:
        """Exact historical rules with audit=True; otherwise honor permanent deletions."""
        if revision is not None and (type(revision) is not int or revision < 0):
            raise ValueError("revision must be a nonnegative integer")
        # One SELECT keeps snapshot and invalidations consistent across connections.
        rows = self._db.execute('''
            WITH selected AS (
                SELECT rules FROM revisions
                WHERE revision = COALESCE(?, (SELECT MAX(revision) FROM revisions))
            )
            SELECT rules, NULL FROM selected
            UNION ALL
            SELECT NULL, id FROM invalidated WHERE EXISTS (SELECT 1 FROM selected)
        ''', (revision,)).fetchall()
        if not rows:
            raise ValueError("unknown revision")
        invalidated = {row[1] for row in rows}
        payload = next(row[0] for row in rows if row[0] is not None)
        return tuple(Rule(**rule) for rule in json.loads(payload)
                     if audit or rule["id"] not in invalidated)

    def apply(self, *, expected_revision: int, upsert: tuple[Rule, ...] = (),
              delete: tuple[str, ...] = (), reason: str = "edit") -> int:
        """Atomically replace rules and permanently invalidate deleted identities."""
        return self._write(expected_revision, upsert, delete, reason, None)

    def rollback(self, target_revision: int, *, expected_revision: int) -> int:
        """Append a revision restoring the target except permanently deleted identities."""
        if type(target_revision) is not int or target_revision < 0:
            raise ValueError("target_revision must be a nonnegative integer")
        return self._write(expected_revision, (), (), f"rollback to {target_revision}", target_revision)

    def _write(self, expected, upsert, delete, reason, target):
        if type(expected) is not int or expected < 0:
            raise ValueError("expected_revision must be a nonnegative integer")
        if not isinstance(upsert, (tuple, list)) or not isinstance(delete, (tuple, list)):
            raise ValueError("upsert and delete must be sequences")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("reason is required")
        if any(not isinstance(rule, Rule) for rule in upsert):
            raise ValueError("upsert requires Rule values")
        if any(not isinstance(id_, str) or not id_.strip() for id_ in delete):
            raise ValueError("delete requires rule identifiers")
        ids = [rule.id for rule in upsert]
        if len(ids) != len(set(ids)) or set(ids).intersection(delete):
            raise ValueError("ambiguous rule mutation")
        self._db.execute("BEGIN IMMEDIATE")
        try:
            head = self.revision
            if expected != head:
                raise StaleRevision(f"expected {expected}, current {head}")
            rules = {rule.id: rule for rule in self.snapshot(head if target is None else target)}
            invalidated = {row[0] for row in self._db.execute("SELECT id FROM invalidated")}
            if invalidated.intersection(ids):
                raise ValueError("deleted identities cannot be reused")
            for rule in upsert:
                rules[rule.id] = rule
            for id_ in delete:
                rules.pop(id_, None)
                self._db.execute("INSERT OR IGNORE INTO invalidated VALUES (?)", (id_,))
            # ponytail: full snapshots cost O(history * rules); use deltas if storage matters.
            payload = json.dumps([asdict(rules[key]) for key in sorted(rules)], ensure_ascii=False)
            self._db.execute("INSERT INTO revisions VALUES (?, ?, ?)", (head + 1, payload, reason))
            self._db.execute("COMMIT")
            return head + 1
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
