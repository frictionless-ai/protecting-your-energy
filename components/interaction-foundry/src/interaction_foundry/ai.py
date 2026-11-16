"""Bounded JSONL adapters for the supported AI session forms."""
import json

MAX_RECORD_BYTES = 1_048_576
SUPPORTED_PROVIDERS = {"claude_code_sessions", "codex_sessions", "cursor_transcripts", "gemini_logs"}


def _result(position, status, reason, event=None):
    result = {"position": position, "status": status, "reason": reason}
    if event is not None:
        result["event"] = event
    return result


def _content(value):
    if isinstance(value, list):
        return value
    return value if isinstance(value, (str, dict)) else None


def iter_ai_jsonl(stream, *, provider):
    """Yield contract-v1 records; line errors never include source text."""
    if provider not in SUPPORTED_PROVIDERS:
        yield _result(1, "unsupported", "unsupported_provider")
        return
    codex_session = None
    for position, line in enumerate(stream, 1):
        if len(line.encode("utf-8")) > MAX_RECORD_BYTES:
            yield _result(position, "quarantined", "record_too_large")
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            yield _result(position, "quarantined", "invalid_json")
            continue
        if not isinstance(row, dict):
            yield _result(position, "unsupported", "non_object_record")
            continue
        if provider == "codex_sessions":
            payload, kind = row.get("payload"), row.get("type")
            if not isinstance(payload, dict) or not isinstance(kind, str):
                yield _result(position, "unsupported", "unrecognized_record")
                continue
            if kind == "session_meta" and payload.get("id"):
                codex_session = payload["id"]
            conversation = payload.get("session_id") or row.get("session_id") or codex_session
            role, content = payload.get("role", "event"), payload.get("content")
            native_id, parents = payload.get("id"), []
            extra = {"source_type": kind, "tool_calls": payload.get("tool_calls"), "summary": payload.get("summary")}
            timestamp = payload.get("timestamp") or row.get("timestamp")
        elif provider == "cursor_transcripts":
            message, role = row.get("message"), row.get("role")
            if not isinstance(message, dict) or not isinstance(role, str):
                yield _result(position, "unsupported", "unrecognized_record")
                continue
            conversation = row.get("sessionId") or row.get("conversationId")
            content, native_id = message.get("content"), row.get("uuid") or row.get("messageId")
            parents, timestamp = [row["parentUuid"]] if row.get("parentUuid") else [], row.get("timestamp")
            kind = row.get("type", "message")
            if not isinstance(kind, str):
                yield _result(position, "unsupported", "unrecognized_record")
                continue
            extra = {"sidechain": row.get("isSidechain"), "source_type": kind}
        elif provider == "claude_code_sessions":
            message, kind = row.get("message"), row.get("type")
            if not isinstance(message, dict) or not isinstance(kind, str):
                yield _result(position, "unsupported", "unrecognized_record")
                continue
            conversation = row.get("sessionId")
            role, content = message.get("role", "event"), message.get("content")
            native_id = row.get("uuid") or row.get("messageId")
            parents, timestamp = [row["parentUuid"]] if row.get("parentUuid") else [], row.get("timestamp")
            extra = {"sidechain": row.get("isSidechain"), "source_type": kind, "cwd": row.get("cwd")}
        else:
            kind = row.get("type")
            if not isinstance(kind, str) or "content" not in row:
                yield _result(position, "unsupported", "unrecognized_record")
                continue
            conversation = row.get("conversation_id") or row.get("session_id")
            role, content, native_id = row.get("role", "event"), row.get("content"), row.get("id")
            parents, timestamp = [], row.get("created_at")
            extra = {"source_type": kind, "tool_calls": row.get("tool_calls"), "source": row.get("source")}
        yield _result(position, "accepted", "accepted", {
            "provider": provider, "conversation": str(conversation) if conversation else None,
            "native_id": str(native_id) if native_id else None, "identity_basis": "native" if native_id and conversation else "artifact_position",
            "kind": kind, "actor": {"role": str(role)}, "timestamp": timestamp,
            "parent_ids": parents, "content": _content(content), "extra": extra,
        })
