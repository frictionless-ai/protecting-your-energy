"""Private, source-preserving ingestion core for contract-v1 adapters."""
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from .io_policy import IoBudget, advise_drop_cache, advise_sequential


_CHUNK_SIZE = 1024 * 1024


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode()).hexdigest()


def _stream_digest(stream, io_budget: IoBudget | None = None):
    digest = sha256()
    advise_sequential(stream)
    try:
        for chunk in iter(lambda: stream.read(_CHUNK_SIZE), b""):
            if io_budget is not None:
                io_budget.consume(len(chunk))
            digest.update(chunk)
    finally:
        advise_drop_cache(stream)
    return digest.hexdigest()


def _file_digest(path, io_budget: IoBudget | None = None):
    with Path(path).open("rb") as stream:
        return _stream_digest(stream, io_budget)


def _private_file(path: Path) -> None:
    """Create/check a ledger artifact without inheriting a permissive umask."""
    if path.exists():
        mode = path.stat().st_mode
        if path.stat().st_uid != os.getuid() or mode & 0o077:
            raise ValueError("private ledger artifact must be owner-private")
        return
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)


def _snapshot(path: Path, directory: Path, io_budget: IoBudget | None = None) -> tuple[Path, str]:
    """Copy bytes once before hashing/parsing so artifact identity is immutable."""
    digest = sha256()
    handle = tempfile.NamedTemporaryFile(mode="w+b", dir=directory, delete=False)
    snapshot = Path(handle.name)
    try:
        os.chmod(snapshot, 0o600)
        with handle:
            with path.open("rb") as source:
                advise_sequential(source)
                try:
                    for chunk in iter(lambda: source.read(_CHUNK_SIZE), b""):
                        if io_budget is not None:
                            io_budget.consume(len(chunk))
                        digest.update(chunk)
                        handle.write(chunk)
                finally:
                    advise_drop_cache(source)
        return snapshot, digest.hexdigest()
    except BaseException:
        snapshot.unlink(missing_ok=True)
        raise


def _identity(event, artifact_digest, position):
    provider = event["provider"]
    native_id, conversation = event.get("native_id"), event.get("conversation")
    if native_id and conversation:
        return "native", _digest([provider, conversation, native_id])
    return "artifact_position", _digest([provider, artifact_digest, position])


def _semantic_event(event):
    event = dict(event)
    extra = dict(event.get("extra", {}))
    extra.pop("reactions", None)
    event["extra"] = extra
    return event


def _connect(database_path):
    _private_file(Path(database_path))
    db = sqlite3.connect(database_path)
    db.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS artifacts (
            digest TEXT PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS artifact_locators (
            artifact_digest TEXT NOT NULL, locator TEXT NOT NULL,
            PRIMARY KEY (artifact_digest, locator),
            FOREIGN KEY(artifact_digest) REFERENCES artifacts(digest)
        );
        CREATE TABLE IF NOT EXISTS events (
            identity TEXT PRIMARY KEY, identity_basis TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS versions (
            identity TEXT NOT NULL, digest TEXT NOT NULL, event TEXT NOT NULL,
            PRIMARY KEY (identity, digest), FOREIGN KEY(identity) REFERENCES events(identity)
        );
        CREATE TABLE IF NOT EXISTS observations (
            artifact_digest TEXT NOT NULL, position INTEGER NOT NULL,
            identity TEXT, status TEXT NOT NULL, reason TEXT NOT NULL, record TEXT NOT NULL,
            PRIMARY KEY (artifact_digest, position), FOREIGN KEY(identity) REFERENCES events(identity)
        );
    """)
    return db


def _record_locator_if_imported(database_path: Path, artifact_digest: str, locator: str) -> bool:
    """Check a digest while holding only the short SQLite metadata transaction."""
    db = _connect(database_path)
    try:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM artifacts WHERE digest = ?", (artifact_digest,)).fetchone():
            db.execute("INSERT OR IGNORE INTO artifact_locators VALUES (?, ?)",
                       (artifact_digest, locator))
            db.execute("COMMIT")
            return True
        db.execute("ROLLBACK")
        return False
    finally:
        db.close()


def ingest(path, adapter, database_path, *, io_budget: IoBudget | None = None):
    """Ingest one read-only artifact atomically and return aggregate status counts.

    `adapter` receives a fresh UTF-8 stream and yields contract-v1 records. It may
    report per-record quarantine/unsupported results; an iterator exception rolls
    back every row for this artifact.
    """
    path = Path(path)
    database_path = Path(database_path)
    locator = str(path)
    # Probe the source bytes before allocating a private snapshot.  Duplicate
    # artifacts therefore incur one sequential read but no temporary copy.
    artifact_digest = _file_digest(path, io_budget)
    if _record_locator_if_imported(database_path, artifact_digest, locator):
        return {"already_imported": 1}

    # New or changed bytes are copied before parsing.  The second digest is
    # authoritative if the source changes between the probe and this copy.
    snapshot, artifact_digest = _snapshot(path, database_path.parent, io_budget)
    db, counts = None, Counter()
    try:
        db = _connect(database_path)
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM artifacts WHERE digest = ?", (artifact_digest,)).fetchone():
            db.execute("INSERT OR IGNORE INTO artifact_locators VALUES (?, ?)",
                       (artifact_digest, locator))
            db.execute("COMMIT")
            return {"already_imported": 1}
        with snapshot.open(encoding="utf-8") as stream:
            for record in adapter(stream):
                position = record.get("position")
                status, reason = record.get("status"), record.get("reason")
                if type(position) is not int or position < 1 or status not in {
                    "accepted", "excluded", "quarantined", "unsupported"
                } or not isinstance(reason, str):
                    raise ValueError("invalid adapter record")
                identity = None
                if status == "accepted":
                    event = record.get("event")
                    required = ("provider", "kind", "actor", "parent_ids", "extra")
                    if not isinstance(event, dict) or any(not event.get(key) for key in ("provider", "kind")) \
                            or any(key not in event for key in required) or not isinstance(event["actor"], dict) \
                            or not isinstance(event["parent_ids"], list) or not isinstance(event["extra"], dict):
                        raise ValueError("invalid accepted event")
                    basis, identity = _identity(event, artifact_digest, position)
                    version = _digest(_semantic_event(event))
                    db.execute("INSERT OR IGNORE INTO events VALUES (?, ?)", (identity, basis))
                    db.execute("INSERT OR IGNORE INTO versions VALUES (?, ?, ?)",
                               (identity, version, json.dumps(event, ensure_ascii=False)))
                db.execute("INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?)",
                           (artifact_digest, position, identity, status, reason,
                            json.dumps(record, ensure_ascii=False)))
                counts[status] += 1
        db.execute("INSERT INTO artifacts VALUES (?)", (artifact_digest,))
        db.execute("INSERT OR IGNORE INTO artifact_locators VALUES (?, ?)",
                   (artifact_digest, locator))
        db.execute("COMMIT")
        return dict(counts)
    except BaseException:
        # SQLite can roll a transaction back implicitly after an I/O failure
        # (for example, ENOSPC).  Preserve the original exception instead of
        # replacing it with "cannot rollback - no transaction is active".
        if db is not None and db.in_transaction:
            db.execute("ROLLBACK")
        raise
    finally:
        if db is not None:
            db.close()
        snapshot.unlink(missing_ok=True)
