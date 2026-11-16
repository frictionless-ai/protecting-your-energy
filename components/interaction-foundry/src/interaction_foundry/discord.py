"""Streaming DiscordChatExporter adapter with optional explicit date bounds."""
from datetime import datetime
import json
import tempfile
from .focus import discord_in_period

MAX_RECORD_BYTES = 1_048_576


def _result(position, status, reason, event=None):
    result = {"position": position, "status": status, "reason": reason}
    if event is not None:
        result["event"] = event
    return result


def _root_channel(buffer):
    marker = buffer.find('"channel"')
    if marker < 0:
        return None
    colon = buffer.find(":", marker)
    if colon < 0:
        return None
    try:
        value, _ = json.JSONDecoder().raw_decode(buffer[colon + 1:].lstrip())
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) and value.get("id") else None


def _messages(stream):
    """Spool messages while bounded-reading an envelope; yield after channel discovery."""
    decoder, buffer, found, done, channel = json.JSONDecoder(), "", False, False, None
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as spool:
        count = 0
        while True:
            chunk = stream.read(8192)
            if not chunk:
                break
            buffer += chunk
            if done:
                buffer = buffer[-4096:]
                continue
            if not found:
                # The exporter contract places root channel metadata before the
                # messages array. Do not scan message objects for a key with
                # the same name after crossing that boundary.
                channel = channel or _root_channel(buffer)
                marker = buffer.find('"messages"')
                if marker < 0:
                    buffer = buffer[-4096:]
                    continue
                bracket = buffer.find("[", marker)
                if bracket < 0:
                    continue
                if channel is None:
                    raise ValueError("missing_root_channel")
                buffer, found = buffer[bracket + 1:], True
            while True:
                stripped = buffer.lstrip()
                if not stripped:
                    buffer = stripped
                    break
                if stripped[0] == "]":
                    buffer, done = stripped[1:], True
                    break
                try:
                    value, end = decoder.raw_decode(stripped)
                except json.JSONDecodeError:
                    if len(stripped.encode("utf-8")) > MAX_RECORD_BYTES:
                        raise ValueError("record_too_large")
                    buffer = stripped
                    break
                if not isinstance(value, dict):
                    raise ValueError("invalid_message")
                spool.write(json.dumps(value, ensure_ascii=False) + "\n")
                count += 1
                rest = stripped[end:].lstrip()
                if rest.startswith(","):
                    buffer = rest[1:]
                elif rest.startswith("]"):
                    buffer, done = rest[1:], True
                    break
                else:
                    buffer = rest
                    break
        if not found or not done or channel is None:
            raise ValueError("invalid_discord_envelope")
        spool.seek(0)
        for line in spool:
            yield json.loads(line), str(channel["id"])


def _in_window(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return discord_in_period(value)


def iter_discord(stream):
    """Yield events eligible for mining, not positive-social classifications."""
    # Envelope verification is intentionally conservative: a missing messages array
    # raises, causing the core to roll back rather than accept unrelated JSON.
    for position, (message, channel_id) in enumerate(_messages(stream), 1):
        in_window = _in_window(message.get("timestamp"))
        if in_window is None:
            yield _result(position, "quarantined", "ambiguous_timestamp")
            continue
        if not in_window:
            yield _result(position, "excluded", "outside_window")
            continue
        author, reference = message.get("author"), message.get("reference")
        if not isinstance(author, dict):
            yield _result(position, "quarantined", "missing_author")
            continue
        parents = [str(reference["messageId"])] if isinstance(reference, dict) and reference.get("messageId") else []
        yield _result(position, "accepted", "accepted", {
            "provider": "discord", "conversation": channel_id,
            "native_id": str(message["id"]) if message.get("id") else None,
            "identity_basis": "native" if message.get("id") else "artifact_position",
            "kind": str(message.get("type", "message")), "actor": {"role": "community", "id": author.get("id")},
            "timestamp": message.get("timestamp"), "parent_ids": parents, "content": message.get("content"),
            "extra": {"author": author, "reactions": message.get("reactions"), "embeds": message.get("embeds"),
                      "attachments": message.get("attachments"), "timestampEdited": message.get("timestampEdited"),
                      "reaction_time_attribution": "unknown" if message.get("reactions") else "not_applicable"},
        })
