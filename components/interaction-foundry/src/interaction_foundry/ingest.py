"""Read original exports into a private event ledger; never execute source content."""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from .io_policy import IoBudget, advise_drop_cache, advise_sequential


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def text_content(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(filter(None, (text_content(item) for item in value)))
    if isinstance(value, dict):
        return text_content(value.get("text", value.get("parts", "")))
    return ""


@dataclass
class Event:
    event_id: str
    conversation_id: str
    family: str
    ordinal: int
    actor: str
    role: str
    text: str
    timestamp: str | float | None
    parent_id: str | None
    source_id: str
    locator: str
    payload: dict


def events(path: Path, family: str, *, io_budget: IoBudget | None = None):
    """Identifiers and original payloads are PRIVATE, not dataset release records.

    JSONL is streamed; JSON exports are loaded as complete documents. ChatGPT
    graph ordinal means export order, not chronology. Parent edges preserve this.
    """
    artifact_hash = sha256()
    budget = io_budget or IoBudget()
    with path.open("rb") as stream:
        advise_sequential(stream)
        for chunk in iter(lambda: stream.read(256 * 1024), b""):
            budget.consume(len(chunk))
            artifact_hash.update(chunk)
        advise_drop_cache(stream)
    fallback = artifact_hash.hexdigest()

    def emit(row, index, conversation, role, body, actor=None, parent=None):
        native = row.get("id") or row.get("uuid") or f"ordinal:{index}"
        identity = digest([family, conversation, native])
        yield Event(identity, str(conversation), family, index, str(actor or role),
                    str(role), text_content(body), row.get("timestamp", row.get("created_at", row.get("create_time"))),
                    str(parent) if parent is not None else None, str(native),
                    str(path), row)

    if path.suffix == ".jsonl":
        conversation = fallback
        with path.open(encoding="utf-8", buffering=256 * 1024) as stream:
            advise_sequential(stream)
            for index, line in enumerate(stream):
                budget.consume(len(line.encode("utf-8", errors="replace")))
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("JSONL row must be an object")
                kind = row.get("type", "message")
                payload = row.get("payload", {})
                if kind == "session_meta":
                    conversation = payload.get("id", fallback)
                    continue
                conversation = row.get("sessionId", conversation)
                if family == "codex_cli":
                    # Keep response records, not duplicate user/assistant summaries.
                    if kind != "response_item":
                        continue
                    role = payload.get("role", "tool" if payload.get("type", "").startswith("function") else "unknown")
                    body = payload.get("content", payload.get("output", ""))
                else:
                    message = row.get("message", {})
                    if not isinstance(message, dict):
                        message = {"content": message}
                    role = row.get("role", message.get("role", kind if kind in ("user", "assistant") else "event"))
                    body = message.get("content", row.get("content", ""))
                yield from emit(row, index, conversation, role, body, parent=row.get("parentUuid"))
        return

    with path.open(encoding="utf-8", buffering=256 * 1024) as stream:
        advise_sequential(stream)
        chunks = []
        for chunk in iter(lambda: stream.read(256 * 1024), ""):
            budget.consume(len(chunk.encode("utf-8", errors="replace")))
            chunks.append(chunk)
        advise_drop_cache(stream)
    data = json.loads("".join(chunks))
    if family == "discord":
        if not isinstance(data, dict) or not isinstance(data.get("messages"), list) or "channel" not in data:
            raise ValueError("Not a DiscordChatExporter envelope")
        conversation = str(data["channel"].get("id", fallback))
        for index, row in enumerate(data["messages"]):
            author = row.get("author") or {}
            yield from emit(row, index, conversation, "community", row.get("content", ""),
                            actor=author.get("id", "unknown"), parent=(row.get("reference") or {}).get("messageId"))
    elif family == "chatgpt_export":
        conversations = data if isinstance(data, list) else [data]
        recognized = False
        for conv in conversations:
            if not isinstance(conv, dict) or not isinstance(conv.get("mapping"), dict):
                continue
            recognized = True
            conversation = conv.get("id", conv.get("conversation_id", fallback))
            for index, (node_id, node) in enumerate(conv["mapping"].items()):
                row = node.get("message")
                if not row:
                    continue
                row = dict(row, id=row.get("id", node_id))
                yield from emit(row, index, conversation, (row.get("author") or {}).get("role", "unknown"),
                                row.get("content", {}), parent=node.get("parent"))
        if not recognized:
            raise ValueError("Not a ChatGPT conversation graph")
    elif family == "claude_ai_export":
        conversations = data if isinstance(data, list) else [data]
        recognized = False
        for conv in conversations:
            if not isinstance(conv, dict) or "chat_messages" not in conv:
                continue
            recognized = True
            for index, row in enumerate(conv["chat_messages"]):
                role = {"human": "user"}.get(row.get("sender"), row.get("sender", "unknown"))
                yield from emit(row, index, conv.get("uuid", fallback), role, row.get("content") or row.get("text", ""))
        if not recognized:
            raise ValueError("Not a Claude conversation export")
    else:
        raise ValueError("Unsupported JSON family")


class Ledger:
    def __init__(self, path):
        # A bounded wait prevents competing readers/writers from spinning in
        # Python while still allowing short commit batches to drain.
        self.db = sqlite3.connect(path, timeout=30.0)
        self.db.execute("PRAGMA busy_timeout=30000")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS events (event_id TEXT, version TEXT, conversation TEXT, family TEXT, data TEXT, PRIMARY KEY(event_id,version))")
        self.db.execute("CREATE TABLE IF NOT EXISTS sources (event_id TEXT, version TEXT, locator TEXT, PRIMARY KEY(event_id,version,locator))")

    def ingest(self, records, *, batch_size: int = 128):
        count = 0
        batch = []
        for event in records:
            batch.append(event)
            if len(batch) >= batch_size:
                count += self._ingest_batch(batch)
                batch.clear()
        if batch:
            count += self._ingest_batch(batch)
        return count

    def _ingest_batch(self, records):
        count = 0
        with self.db:
            for event in records:
                record = asdict(event)
                locator = record.pop("locator")
                # Export position is provenance, not edit identity.
                version = digest(event.payload)
                cursor = self.db.execute("INSERT OR IGNORE INTO events VALUES (?,?,?,?,?)",
                                         (event.event_id, version, event.conversation_id, event.family, json.dumps(record)))
                count += cursor.rowcount
                self.db.execute("INSERT OR IGNORE INTO sources VALUES (?,?,?)", (event.event_id, version, locator))
        return count

    def close(self):
        self.db.close()
