"""Schema-specific, bounded adapters for ChatGPT and Claude web exports.

These exports are structured JSON documents rather than line streams. They are
accepted only below a documented cap; larger documents are quarantined as one
artifact rather than read without a bound or silently skipped.
"""

import json


MAX_DOCUMENT_BYTES = 128 * 1024 * 1024


def _size(stream) -> int:
    position = stream.tell()
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(position)
    return size


def _bounded_document(stream):
    if _size(stream) > MAX_DOCUMENT_BYTES:
        return None
    return json.load(stream)


def _result(position, status, reason, event=None):
    record = {"position": position, "status": status, "reason": reason}
    if event is not None:
        record["event"] = event
    return record


def iter_chatgpt_graph(stream):
    """Yield ChatGPT mapping nodes while retaining their graph parents."""
    document = _bounded_document(stream)
    if document is None:
        yield _result(1, "quarantined", "document_too_large")
        return
    conversations = document if isinstance(document, list) else [document]
    position, recognized = 0, False
    for conversation in conversations:
        if not isinstance(conversation, dict) or not isinstance(conversation.get("mapping"), dict):
            position += 1
            yield _result(position, "unsupported", "unrecognized_chatgpt_conversation")
            continue
        recognized = True
        conversation_id = conversation.get("conversation_id") or conversation.get("id") or conversation.get("uuid")
        node_to_native = {
            str(node_id): str(node["message"].get("id") or node_id)
            for node_id, node in conversation["mapping"].items()
            if isinstance(node, dict) and isinstance(node.get("message"), dict)
        }
        for node_id, node in conversation["mapping"].items():
            position += 1
            if not isinstance(node, dict):
                yield _result(position, "quarantined", "invalid_chatgpt_mapping_node")
                continue
            if not isinstance(node.get("message"), dict):
                yield _result(position, "unsupported", "chatgpt_mapping_node_missing_message")
                continue
            message = node["message"]
            author = message.get("author") if isinstance(message.get("author"), dict) else {}
            native_id = message.get("id") or node_id
            parents = [node_to_native.get(str(node["parent"]), str(node["parent"]))] if node.get("parent") else []
            children = [node_to_native.get(str(child), str(child)) for child in node.get("children", [])
                        if isinstance(child, (str, int))]
            yield _result(position, "accepted", "accepted", {
                "provider": "chatgpt_web", "conversation": str(conversation_id) if conversation_id else None,
                "native_id": str(native_id),
                "identity_basis": "native" if conversation_id else "artifact_position",
                "kind": "chat_message", "actor": {"role": str(author.get("role", "unknown"))},
                "timestamp": message.get("create_time"), "parent_ids": parents,
                "content": message.get("content"),
                "extra": {"mapping_node_id": str(node_id), "node_children": children,
                          "message_metadata": message.get("metadata")},
            })
    if not recognized:
        yield _result(1, "unsupported", "unrecognized_chatgpt_graph")


def iter_claude_web(stream):
    """Yield Claude web conversation messages without duplicating text/content."""
    document = _bounded_document(stream)
    if document is None:
        yield _result(1, "quarantined", "document_too_large")
        return
    conversations = document if isinstance(document, list) else [document]
    position, recognized = 0, False
    for conversation in conversations:
        if not isinstance(conversation, dict) or not isinstance(conversation.get("chat_messages"), list):
            position += 1
            yield _result(position, "unsupported", "unrecognized_claude_web_conversation")
            continue
        recognized = True
        conversation_id = conversation.get("uuid") or conversation.get("id")
        for message in conversation["chat_messages"]:
            position += 1
            if not isinstance(message, dict):
                yield _result(position, "quarantined", "invalid_claude_web_message")
                continue
            sender = message.get("sender", "unknown")
            role = "user" if sender == "human" else str(sender)
            native_id = message.get("uuid") or message.get("id")
            content = message.get("content") if message.get("content") is not None else message.get("text")
            yield _result(position, "accepted", "accepted", {
                "provider": "claude_web", "conversation": str(conversation_id) if conversation_id else None,
                "native_id": str(native_id) if native_id else None,
                "identity_basis": "native" if native_id and conversation_id else "artifact_position",
                "kind": "chat_message", "actor": {"role": role},
                "timestamp": message.get("created_at") or message.get("timestamp"), "parent_ids": [],
                "content": content,
                "extra": {"attachments": message.get("attachments"), "files": message.get("files")},
            })
    if not recognized:
        yield _result(1, "unsupported", "unrecognized_claude_web_export")
