#!/usr/bin/python3 -I
"""Bounded lexical acquisition and human/LLM-authored source verification. Stdlib only."""
import argparse
import collections
import datetime
import functools
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote as urlquote

VERSION = '1.0.0'
TOKEN = re.compile(r'[^\W\d_]+(?:\+\+|#)?', re.UNICODE)
# General function words and observed role boilerplate, not project synonyms.
NON_SIGNALS = frozenset(('a an and are as at be been being but by can could did do does for from '
                        'had has have he her hers him his how i if in into is it its me my no nor not '
                        'of on or our ours she should so than that the their theirs them then there '
                        'these they this those to us user was we were what when where which who '
                        'will with would you your yours').split())
WRAPPER = re.compile(r'\b(sub[ -]?agent|worker packet|task packet|you are (?:a |an )?(?:research |coding )?(?:worker|agent)|delegated task|NEW_TASK)\b', re.I)
EXCLUDES = {'.git', '.hg', '.svn', 'node_modules', '__pycache__', '.venv', 'venv'}
SUFFIXES = {'.json', '.jsonl', '.md', '.markdown'}
_UNPARSED = object()

class Invalid(ValueError):
    pass

def digest(data):
    return hashlib.sha256(data).hexdigest()

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def lineout(handle, value):
    handle.write(json.dumps(value, ensure_ascii=False) + '\n')

def words(text):
    return {t.casefold() for t in TOKEN.findall(text)} - NON_SIGNALS

def reference_words(text):
    # A prose variable such as x is weaker evidence than C or an explicit `x`.
    singletons = {t.casefold() for t in TOKEN.findall(text) if len(t) == 1 and t.isupper()}
    for quoted in re.findall(r'`([^`\r\n]+)`', text):
        singletons.update(words(quoted))
    return {t for t in words(text) if len(t) > 1 or t in singletons}

def filehash(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def bounded_read(path, limit):
    with path.open('rb') as f:
        data = f.read(limit + 1)
    if len(data) > limit:
        raise Invalid('document exceeds byte limit; JSON arrays are loaded whole, not element-streamed')
    return data

def text_content(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for p in value:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict) and isinstance(p.get('text'), str):
                parts.append(p['text'])
            else:
                raise Invalid('unsupported non-text message content; not silently omitted')
        return '\n'.join(parts)
    if isinstance(value, dict) and isinstance(value.get('parts'), list):
        return text_content(value['parts'])
    raise Invalid('unsupported message content')

def message(raw, index, discord, owner_id, mapping_node_id=None):
    if not isinstance(raw, dict):
        raise Invalid('message must be an object')
    author = raw.get('author') or {}
    if isinstance(author, str):
        author = {'name': author}
    if not isinstance(author, dict):
        raise Invalid('author must be object or string')
    aid = author.get('id')
    role = author.get('role', raw.get('role', 'unknown'))
    source_role = role
    if role is None:
        role = 'unknown'
    elif not isinstance(role, str) or not role.strip():
        raise Invalid('message role must be a nonempty string or null')
    if discord:
        role = ('owner' if str(aid) == owner_id else 'peer') if owner_id else 'unattributed_discord'
        attribution = ('exact_discord_owner_id' if role == 'owner' else 'discord_nonowner') if owner_id else 'discord_owner_id_unconfigured'
    elif role in ('self', 'user'):
        role = 'nominal_owner'
        attribution = 'source_role_claim_only'
    else:
        attribution = 'source_role'
    content = raw.get('content', raw.get('text', raw.get('display')))
    if content is None:
        raise Invalid('message has no supported text field')
    content = text_content(content)
    indicators = []
    extra = raw.get('extra')
    native = extra.get('raw') if isinstance(extra, dict) else None
    compact_summary = isinstance(native, dict) and any(native.get(k) for k in ('isCompactSummary', 'is_compact_summary'))
    if not discord and compact_summary:
        role = 'summary'
        attribution = 'generated_compact_summary_metadata_not_owner'
        indicators.append('generated_compact_summary')
    elif not discord and source_role in ('self', 'user'):
        role, attribution = user_text_role(content, False, False)
    elif (not discord and source_role in ('meta', 'system', 'tool')
            and isinstance(native, dict) and native.get('block_types') == ['tool_result']
            and not any(native.get(k) for k in ('is_sidechain', 'isSidechain', 'is_meta', 'isMeta'))
            and content.startswith('Your questions have been answered: ')):
        role = 'host_answer_candidate'
        attribution = 'canonical_tool_answer_report_requires_native_verification'
        indicators.append('host_mediated_answer_report_not_direct_owner_text')
    if WRAPPER.search(content):
        indicators.append('possible_delegated_or_injected_wrapper')
    if re.search(r'(?m)^\s*>', content):
        indicators.append('contains_blockquote')
    if '```' in content or '~~~' in content:
        indicators.append('contains_fenced_content')
    result = {'index': index, 'id': raw.get('id'), 'mapping_node_id': mapping_node_id, 'role': role, 'source_role': source_role, 'author_id': aid,
            'author_name': author.get('name'), 'attribution': attribution,
            'time_fields': {k: raw[k] for k in ('sent_at', 'timestamp', 'timestampEdited', 'create_time', 'update_time', 'created_at') if k in raw},
            'indicators': indicators, 'text': content, 'text_sha256': digest(content.encode())}
    if discord and raw.get('forwardedMessage') is not None:
        forwarded = raw['forwardedMessage']
        if not isinstance(forwarded, dict):
            raise Invalid('unsupported Discord forwardedMessage structure')
        forward_text = text_content(forwarded.get('content', ''))
        result['forwarded_message'] = {
            'text': forward_text, 'text_sha256': digest(forward_text.encode()),
            'attribution': 'forwarded_source_author_unknown_not_forwarder',
            'reference': raw.get('reference'),
            'metadata': {k: forwarded[k] for k in ('timestamp', 'timestampEdited', 'attachments', 'embeds', 'stickers') if k in forwarded},
            'media_status': 'metadata_only_payloads_not_inspected',
        }
        indicators.append('contains_forwarded_message_source_author_unverified')
    return result

def normalize(obj, owner_id, branch=None):
    if not isinstance(obj, dict):
        raise Invalid('conversation must be an object')
    wrapper_keys = {'derivative_format', 'identity_note', 'lineage', 'policy_changes', 'record'}
    if wrapper_keys.intersection(obj):
        if not wrapper_keys.issubset(obj) or obj.get('derivative_format') != 'historical_ai_conversation_v1':
            raise Invalid('malformed or unsupported historical AI conversation wrapper')
        lineage = obj.get('lineage')
        record = obj.get('record')
        if not isinstance(lineage, dict) or not isinstance(record, dict):
            raise Invalid('historical AI wrapper requires lineage and nested record objects')
        required_lineage = ('canonical_file', 'canonical_line', 'source_content_hash',
                            'source_line_sha256', 'source_record_id')
        if (any(not isinstance(lineage.get(k), str) or not lineage[k] for k in required_lineage if k != 'canonical_line')
                or type(lineage.get('canonical_line')) is not int or lineage['canonical_line'] < 1):
            raise Invalid('historical AI wrapper has incomplete lineage identifiers')
        if not isinstance(obj.get('identity_note'), str) or not isinstance(obj.get('policy_changes'), dict):
            raise Invalid('historical AI wrapper metadata has invalid types')
        normalized = normalize(record, owner_id, branch)
        normalized['record_schema'] = normalized['schema']
        normalized['schema'] = 'historical_ai_conversation_v1'
        normalized['notes'].append('wrapper lineage and policy metadata are source claims; canonical references are not independently verified')
        normalized['lineage'] = lineage
        normalized['provenance'] = record.get('provenance')
        normalized['wrapper_metadata'] = {k: obj[k] for k in ('derivative_format', 'identity_note', 'policy_changes')}
        normalized['record_metadata'] = {k: record[k] for k in ('schema_version', 'kind', 'type', 'language', 'participants', 'time', 'extra') if k in record}
        return normalized
    notes = []
    if obj.get('source') is not None and not isinstance(obj['source'], dict):
        raise Invalid('source metadata must be an object')
    if isinstance(obj.get('mapping'), dict):
        mapping = obj['mapping']
        end = branch or obj.get('current_node')
        if not end or end not in mapping:
            raise Invalid('ChatGPT mapping requires current_node or explicit --branch node ID')
        chain, seen = [], set()
        node = end
        while node is not None:
            if node in seen or node not in mapping:
                raise Invalid('ChatGPT mapping cycle or missing parent')
            seen.add(node)
            item = mapping[node]
            if not isinstance(item, dict):
                raise Invalid('invalid mapping node')
            if item.get('message') is not None:
                m = dict(item['message'])
                chain.append((node, m))
            node = item.get('parent')
        selected_chain = list(reversed(chain))
        raw_messages = [m for _, m in selected_chain]
        mapping_node_ids = [node_id for node_id, _ in selected_chain]
        notes.append({'branch_end': end, 'branch_policy': 'ancestor chain only; siblings never flattened',
                      'mapping_nodes': len(mapping), 'selected_nodes': len(seen),
                      'branch_incomplete': len(seen) != len(mapping)})
        schema = 'chatgpt_mapping'
    elif isinstance(obj.get('messages'), list):
        raw_messages = obj['messages']
        mapping_node_ids = [None] * len(raw_messages)
        discord = isinstance(obj.get('guild'), dict) or isinstance(obj.get('channel'), dict) or obj.get('platform') == 'discord' or (obj.get('source') or {}).get('platform') == 'discord'
        schema = 'discord' if discord else 'upar' if obj.get('kind') == 'conversation' else 'messages_array'
    else:
        raise Invalid('unsupported schema; expected mapping or messages array')
    messages = [message(m, i, schema == 'discord', owner_id, mapping_node_ids[i]) for i, m in enumerate(raw_messages)]
    forwarded_count = sum('forwarded_message' in m for m in messages)
    if forwarded_count:
        notes.append({'forwarded_messages': forwarded_count,
                      'limitation': 'forwarded text is a source-author-unverified lead; media metadata retained, payloads not inspected'})
    return {'id': obj.get('id', obj.get('conversation_id')), 'title': obj.get('title', obj.get('name')),
            'schema': schema, 'notes': notes, 'messages': messages,
            'source_metadata': obj.get('source'),
            'time_fields': {k: obj[k] for k in ('created_at', 'updated_at', 'create_time', 'update_time', 'exportedAt') if k in obj}}

# Per-event JSONL sessions (Claude Code transcripts, Codex rollouts): one file is one
# session and each line is one record, so locators keep per-line offset/length/hash.
EVENT_FORMATS = ('claude_code', 'codex_rollout')
EVENT_RECORD_FORMATS = EVENT_FORMATS + ('cursor_agent',)
GOOGLE_TAKEOUT_ACTIVITY_FORMAT = 'google_takeout_activity_event'
HARNESS_LEAD = re.compile(r'\s*(?:<(?:system-reminder|command-name|command-message|command-args|local-command-[a-z-]+|user-prompt-submit-hook|environment_context|user_instructions|codex_internal_context|external_codex_[a-z_]+|agent-message|task-notification|subagent_notification|turn_aborted|mcp_meta_tools|dynamic_tools|permissions\b[^>]*|INSTRUCTIONS)\b|# AGENTS\.md instructions|Another Claude session sent a message|Coordination message from )')
HARNESS_ANY = re.compile(r'<(?:system-reminder|user-prompt-submit-hook|environment_context|codex_internal_context|agent-message|task-notification|command-name|local-command-[a-z-]+)\b')
DETECT_LINES = 50

def detect_format(path, max_bytes, deadline=None):
    """Classify a .jsonl file from its first records; returns (format or None, session id)."""
    if Path(path).name == 'readable-activities.jsonl':
        return GOOGLE_TAKEOUT_ACTIVITY_FORMAT, None
    fmt, session = None, None
    with Path(path).open('rb') as f:
        for _ in range(DETECT_LINES):
            raw, oversized = read_projection_line(f, max_bytes, deadline)
            if not raw:
                break
            if oversized or not raw.strip():
                continue
            try:
                o = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(o, dict) or isinstance(o.get('messages'), list) or isinstance(o.get('mapping'), dict):
                continue
            if ('agent-transcripts' in Path(path).parts and o.get('role') in ('user', 'assistant', 'tool', 'system')
                    and isinstance(o.get('message'), dict) and 'content' in o['message']):
                # Path and schema establish an event format, not a session identity.
                return 'cursor_agent', None
            if fmt is None and isinstance(o.get('type'), str) and isinstance(o.get('sessionId'), str) and ('uuid' in o or 'message' in o):
                return 'claude_code', None
            if isinstance(o.get('type'), str) and isinstance(o.get('payload'), dict) and 'timestamp' in o:
                fmt = 'codex_rollout'
                if o['type'] == 'session_meta':
                    session = o['payload'].get('id') or o['payload'].get('session_id')
                    break
    if fmt == 'codex_rollout' and session is None:
        m = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$', str(path))
        session = m[1] if m else None
    return fmt, session

def google_takeout_activity_event(obj):
    """Keep one Takeout activity row as an unattributed event, never a conversation."""
    if not isinstance(obj, dict) or isinstance(obj.get('messages'), list) or isinstance(obj.get('mapping'), dict):
        raise Invalid('Google Takeout activity row must be a flat object, not a conversation')

    def text_values(value):
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            return [text for child in value.values() for text in text_values(child)]
        if isinstance(value, list):
            return [text for child in value for text in text_values(child)]
        return []

    authorship = {}
    def collect_authorship(value, path=()):
        if isinstance(value, dict):
            for key, child in value.items():
                field_path = path + (str(key),)
                if re.search(r'author|authorship|actor|creator', str(key), re.I):
                    authorship['.'.join(field_path)] = child
                else:
                    collect_authorship(child, field_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                collect_authorship(child, path + (str(index),))
    collect_authorship(obj)
    text = '\n'.join(value for value in text_values(obj) if value.strip())
    time_fields = {key: obj[key] for key in ('time', 'timestamp', 'date', 'dateTime', 'startTime', 'endTime')
                   if key in obj}
    activity_message = {'index': 0, 'id': None, 'mapping_node_id': None,
                        'role': 'activity_event', 'source_role': 'google_takeout_activity',
                        'author_id': None, 'author_name': None,
                        'attribution': 'source_authorship_statement_unverified',
                        'time_fields': time_fields, 'part_kind': 'activity_event',
                        'indicators': ['activity_event_not_conversation', 'authorship_not_verified'],
                        'text': text, 'text_sha256': digest(text.encode())}
    return {'id': None, 'title': None, 'schema': GOOGLE_TAKEOUT_ACTIVITY_FORMAT,
            'notes': [{'granularity': 'activity event; not a reconstructed conversation'},
                      {'authorship_statement_unverified': authorship}],
            'messages': [activity_message],
            'source_metadata': {'platform': 'google_takeout',
                                'authorship_statement_unverified': authorship,
                                'raw_record': obj},
            'time_fields': time_fields}

def is_cursor_prompt_history_path(path):
    """Recognize only cursor_prompt_history/<entry>/prompt_history.json inputs."""
    if path is None:
        return False
    parts = Path(path).parts
    return (Path(path).name == 'prompt_history.json'
            and any(part == 'cursor_prompt_history' for part in parts[:-2]))

def cursor_prompt_history_event(obj, element):
    """Keep one Cursor history string as an unattributed event, never a conversation."""
    if isinstance(obj, list):
        if type(element) is not int or not 0 <= element < len(obj):
            raise Invalid('Cursor prompt history requires a valid array element index')
        text = obj[element]
    elif isinstance(obj, str) and type(element) is int and element >= 0:
        # Acquisition streams one parsed element at a time; retain its source index.
        text = obj
    else:
        raise Invalid('Cursor prompt history must be an array or indexed string element')
    if not isinstance(text, str):
        raise Invalid('Cursor prompt history array element must be a string')
    element_hash = digest(text.encode('utf-8'))
    event = {'index': element, 'id': None, 'mapping_node_id': None,
             'role': 'prompt_event', 'source_role': 'cursor_prompt_history',
             'author_id': None, 'author_name': None,
             'attribution': 'unknown', 'time_fields': {}, 'part_kind': 'prompt_event',
             'indicators': ['prompt_event_not_conversation', 'authorship_unknown'],
             'text': text, 'text_sha256': element_hash, 'element_text_sha256': element_hash}
    return {'id': None, 'title': None, 'schema': 'cursor_prompt_history_event',
            'notes': [{'granularity': 'prompt event; not a reconstructed conversation'},
                      {'authorship': 'unknown'}],
            'messages': [event],
            'source_metadata': {'platform': 'cursor', 'format': 'cursor_prompt_history',
                                'element_index': element, 'element_text_sha256': element_hash,
                                'authorship': 'unknown'},
            'time_fields': {}}

def text_indicators(text):
    found = []
    if WRAPPER.search(text):
        found.append('possible_delegated_or_injected_wrapper')
    if HARNESS_ANY.search(text):
        found.append('contains_harness_wrapper')
    if '<pasted_content' in text:
        found.append('contains_pasted_content')
    if re.search(r'(?m)^\s*>', text):
        found.append('contains_blockquote')
    if '```' in text or '~~~' in text:
        found.append('contains_fenced_content')
    return found

def event_message(index, mid, role, source_role, text, attribution, time_fields, kind, extra=()):
    return {'index': index, 'id': mid, 'mapping_node_id': None, 'role': role, 'source_role': source_role, 'author_id': None,
            'author_name': None, 'attribution': attribution, 'time_fields': time_fields, 'part_kind': kind,
            'indicators': list(extra) + text_indicators(text), 'text': text, 'text_sha256': digest(text.encode())}

def candidate_words(msg):
    tokens = words(msg.get('cursor_query_text', msg['text']))
    forward = msg.get('forwarded_message')
    if isinstance(forward, dict):
        tokens |= words(forward.get('text', ''))
    report = msg.get('host_answer_report')
    if msg['role'] == 'host_answer_candidate' and isinstance(report, dict):
        for text in ([q['question'] for q in report['questions']
                      if isinstance(q, dict) and isinstance(q.get('question'), str)]
                     + list(report['answers'].values())):
            tokens |= words(text)
    return tokens

def candidate_signal_parts(msg, terms):
    forward = msg.get('forwarded_message')
    if not isinstance(forward, dict):
        return {}
    outer = dict(msg)
    del outer['forwarded_message']
    return {'signal_parts': {'outer_and_normalized': sorted(candidate_words(outer) & terms),
                             'forwarded_message': sorted(words(forward.get('text', '')) & terms)}}

def user_text_role(text, meta, sidechain):
    if meta:
        return 'harness_injected', 'harness_meta_event'
    if sidechain:
        return 'delegating_agent', 'subagent_transcript_prompt_not_owner'
    if HARNESS_LEAD.match(text):
        return 'harness_injected', 'harness_wrapper_text_not_owner'
    return 'nominal_owner', 'source_role_claim_only'

def cursor_event(obj, path):
    """Normalize one Cursor transcript event without inventing a session ID."""
    if not isinstance(obj, dict) or isinstance(obj.get('messages'), list) or isinstance(obj.get('mapping'), dict):
        raise Invalid('ambiguous Cursor transcript event')
    role = obj.get('role')
    msg = obj.get('message')
    notes = [{'cursor_path_session_identity_unverified': True,
              'event_type': obj.get('type'), 'status': obj.get('status')}]
    if role is None and msg is None and isinstance(obj.get('type'), str):
        notes.append({'uninterpreted_cursor_event': True, 'fields': sorted(obj.keys())})
        return {'id': None, 'title': None, 'schema': 'cursor_agent_event', 'notes': notes,
                'messages': [], 'source_metadata': {'platform': 'cursor'}, 'time_fields': {}}
    if role not in ('user', 'assistant', 'tool', 'system') or not isinstance(msg, dict) or 'content' not in msg:
        raise Invalid('unsupported Cursor transcript event shape')
    content = msg['content']
    parts = [{'type': 'text', 'text': content}] if isinstance(content, str) else content
    if not isinstance(parts, list):
        raise Invalid('Cursor message content must be a string or part list')
    result = []
    for part in parts:
        kind = part.get('type') if isinstance(part, dict) else None
        if kind == 'text' and isinstance(part.get('text'), str):
            text = part['text']
            if role == 'user':
                # A wrapped query may still be generated or delegated. Keep the
                # whole original text, and classify only by observed structure.
                query = (re.search(r'<user_query>(.*?)</user_query>', text, re.S)
                         if text.count('<user_query>') == 1 and text.count('</user_query>') == 1 else None)
                body = query.group(1).strip() if query else re.sub(r'^\s*<timestamp>.*?</timestamp>\s*', '', text, count=1, flags=re.S)
                worker = 'subagents' in Path(path).parts
                generated = (not body or body.startswith('<dynamic_tools>') or
                             body.startswith('Briefly inform the user about the task result') or
                             body.startswith('The above subagent result is already visible') or
                             body.startswith('The beginning of the above subagent result is already visible'))
                if generated:
                    normalized, attribution = 'harness_injected', 'cursor_wrapper_or_generated_notice_not_owner'
                else:
                    normalized, attribution = user_text_role(body, False, worker)
                extra = ['cursor_user_role_unverified']
                if query:
                    extra.append('cursor_user_query_wrapper')
            else:
                normalized, attribution, extra = role, 'source_role_not_owner', []
            result.append(event_message(len(result), None, normalized, role, text, attribution, {}, 'text', extra))
            if role == 'user' and query:
                result[-1]['cursor_query_text'] = query.group(1)
                result[-1]['lexical_basis'] = ['cursor_user_query']
        elif kind == 'tool_use':
            text = '[tool_use ' + str(part.get('name')) + '] ' + json.dumps(part.get('input'), ensure_ascii=False)
            result.append(event_message(len(result), None, 'tool_call', role, text, 'tool_context_not_owner', {}, 'tool_use'))
        elif kind == 'tool_result':
            result.append(event_message(len(result), None, 'tool_result', role, lenient_text(part.get('content')), 'tool_context_not_owner', {}, 'tool_result'))
        else:
            result.append(event_message(len(result), None, 'event_part', role, '[' + str(kind) + ' part not interpreted]',
                                        'context_not_owner', {}, str(kind), ['uninterpreted_part']))
    return {'id': None, 'title': None, 'schema': 'cursor_agent_event', 'notes': notes, 'messages': result,
            'source_metadata': {'platform': 'cursor'}, 'time_fields': {}}

def lenient_text(value):
    """Text from a tool result or part list; non-text parts become explicit placeholders."""
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        out = []
        for p in value:
            if isinstance(p, str):
                out.append(p)
            elif isinstance(p, dict) and isinstance(p.get('text'), str):
                out.append(p['text'])
            else:
                out.append('[non-text part not interpreted: ' + str(p.get('type') if isinstance(p, dict) else type(p).__name__) + ']')
        return '\n'.join(out)
    return json.dumps(value, ensure_ascii=False)

def codex_pair_text(obj):
    """Return only text that can be compared without lossy or model-based normalization."""
    if not isinstance(obj, dict) or not isinstance(obj.get('payload'), dict):
        return None
    payload = obj['payload']
    if obj.get('type') == 'event_msg' and payload.get('type') == 'user_message':
        value = payload.get('message')
        return value if isinstance(value, str) else None
    if (obj.get('type') == 'response_item' and payload.get('type') == 'message'
            and payload.get('role') == 'user'):
        value = payload.get('content')
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts = []
            for part in value:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and isinstance(part.get('text'), str):
                    parts.append(part['text'])
                else:
                    return None
            return parts[0] if len(parts) == 1 else None
    return None

@functools.lru_cache(maxsize=2)
def codex_echo_pairs(path, max_bytes, max_records=100000):
    """Link exact user-text matches without retaining source text."""
    events, responses = collections.defaultdict(list), collections.defaultdict(list)
    with Path(path).open('rb') as f:
        line_number = 0
        while True:
            offset = f.tell()
            raw = f.readline(max_bytes + 1)
            if not raw:
                break
            line_number += 1
            if line_number > max_records:
                raise Invalid('Codex pairing index exceeds record limit')
            if len(raw) > max_bytes:
                while raw and not raw.endswith(b'\n'):
                    raw = f.readline(max_bytes + 1)
                continue
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
            except (ValueError, UnicodeError, RecursionError):
                continue
            content = codex_pair_text(obj)
            if content is None:
                continue
            key = digest(content.encode())
            if obj.get('type') == 'event_msg':
                events[key].append((offset, line_number))
            else:
                responses[key].append((offset, line_number))
    pairs = {}
    for key, event_rows in events.items():
        response_rows = responses.get(key, ())
        if response_rows:
            occurrence_ambiguous = len(event_rows) != 1 or len(response_rows) != 1
            response_refs = [{'offset': offset, 'line': line} for offset, line in response_rows[:16]]
            event_refs = [{'offset': offset, 'line': line} for offset, line in event_rows[:16]]
            for event_offset, event_line in event_rows:
                pairs[event_offset] = {'status': 'exact_text_match_response_group', 'text_sha256': key,
                                       'counterpart_count': len(response_rows), 'counterparts': response_refs,
                                       'counterparts_truncated': len(response_rows) > len(response_refs),
                                       'occurrence_ambiguous': occurrence_ambiguous,
                                       'event_line': event_line, 'event_offset': event_offset}
            for response_offset, response_line in response_rows:
                pairs[response_offset] = {'status': 'exact_text_match_event_group', 'text_sha256': key,
                                          'counterpart_count': len(event_rows), 'counterparts': event_refs,
                                          'counterparts_truncated': len(event_rows) > len(event_refs),
                                          'occurrence_ambiguous': occurrence_ambiguous,
                                          'response_line': response_line, 'response_offset': response_offset}
        else:
            for event_offset, event_line in event_rows:
                pairs[event_offset] = {'status': 'no_exact_response_item_match', 'text_sha256': key,
                                       'event_line': event_line, 'event_offset': event_offset}
    for key, response_rows in responses.items():
        if key not in events:
            for response_offset, response_line in response_rows:
                pairs[response_offset] = {'status': 'no_exact_event_message_match', 'text_sha256': key,
                                          'response_line': response_line, 'response_offset': response_offset}
    return pairs

def claude_event(obj, path):
    etype = obj.get('type')
    times = {'timestamp': obj['timestamp']} if 'timestamp' in obj else {}
    meta = bool(obj.get('isMeta'))
    compact_summary = bool(obj.get('isCompactSummary'))
    sidechain = bool(obj.get('isSidechain')) or '/subagents/' in str(path)
    mid = obj.get('uuid')
    msgs = []
    def add(role, source_role, text, attribution, kind, extra=()):
        msgs.append(event_message(len(msgs), mid, role, source_role, text, attribution, times, kind, extra))
    msg = obj.get('message')
    if isinstance(msg, dict) and 'content' in msg:
        speaker = msg.get('role') or etype
        content = msg['content']
        parts = [{'type': 'text', 'text': content}] if isinstance(content, str) else content
        if not isinstance(parts, list):
            raise Invalid('Claude Code message content must be a string or part list')
        tool_results = [p for p in parts if isinstance(p, dict) and p.get('type') == 'tool_result']
        for p in parts:
            ptype = p.get('type') if isinstance(p, dict) else None
            if ptype == 'text' and isinstance(p.get('text'), str):
                if speaker == 'user':
                    if compact_summary:
                        add('summary', speaker, p['text'], 'generated_compact_summary_metadata_not_owner', 'text',
                            ['generated_compact_summary'])
                    else:
                        role, attribution = user_text_role(p['text'], meta, sidechain)
                        add(role, speaker, p['text'], attribution, 'text')
                else:
                    add(speaker, speaker, p['text'], 'source_role', 'text')
            elif ptype == 'thinking':
                add('assistant_thinking', speaker, str(p.get('thinking', '')), 'source_role', 'thinking')
            elif ptype == 'tool_use':
                add('tool_call', speaker, '[tool_use ' + str(p.get('name')) + '] ' + json.dumps(p.get('input'), ensure_ascii=False), 'tool_context_not_owner', 'tool_use')
            elif ptype == 'tool_result':
                text = lenient_text(p.get('content'))
                result = obj.get('toolUseResult')
                questions = result.get('questions') if isinstance(result, dict) else None
                answers = result.get('answers') if isinstance(result, dict) else None
                question_texts = {q.get('question') for q in questions
                                  if isinstance(q, dict) and isinstance(q.get('question'), str)} if isinstance(questions, list) else set()
                structured_answer = (speaker == 'user' and not meta and not compact_summary and not sidechain and not p.get('is_error')
                                     and len(tool_results) == 1
                                     and isinstance(p.get('tool_use_id'), str)
                                     and isinstance(answers, dict) and bool(answers)
                                     and set(answers) <= question_texts
                                     and all(isinstance(v, str) and v for v in answers.values()))
                if structured_answer:
                    add('host_answer_candidate', speaker, text, 'native_structured_question_answer_report_unverified', 'tool_result',
                        ['host_mediated_answer_report_not_direct_owner_text'])
                    msgs[-1]['host_answer_report'] = {'questions': questions, 'answers': answers,
                                                     'tool_use_id': p['tool_use_id'],
                                                     'question_message_id': obj.get('sourceToolAssistantUUID', obj.get('parentUuid'))}
                    msgs[-1]['lexical_basis'] = ['message_text', 'structured_questions_and_answers']
                    if not text.startswith('Your questions have been answered: '):
                        msgs[-1]['indicators'].append('structured_answer_with_unrecognized_prose')
                else:
                    add('tool_result', speaker, text, 'tool_context_not_owner', 'tool_result', ['tool_result_error'] if p.get('is_error') else [])
            else:
                add('event_part', speaker, '[' + str(ptype) + ' part not interpreted]', 'context_not_owner', str(ptype), ['uninterpreted_part'])
    elif etype == 'summary' and isinstance(obj.get('summary'), str):
        add('summary', etype, obj['summary'], 'generated_summary_not_owner', 'summary')
    elif etype == 'system' and isinstance(obj.get('content'), str):
        add('system', etype, obj['content'], 'source_role', 'system')
    notes = [{'event_type': etype, 'subtype': obj.get('subtype'), 'is_meta': meta, 'sidechain': sidechain,
              'is_compact_summary': compact_summary,
              'is_visible_in_transcript_only': bool(obj.get('isVisibleInTranscriptOnly'))}]
    result = obj.get('toolUseResult')
    if isinstance(msg, dict) and 'content' in msg and len(tool_results) > 1 and isinstance(result, dict) and 'questions' in result and 'answers' in result:
        notes.append({'unbound_host_answer_report': result,
                      'reason': 'multiple tool-result parts; event-level questionnaire metadata cannot identify its result part',
                      'tool_result_ids': [p.get('tool_use_id') for p in tool_results]})
    return {'id': obj.get('sessionId'), 'title': None, 'schema': 'claude_code_event', 'notes': notes, 'messages': msgs,
            'source_metadata': {'platform': 'claude_code', 'cwd': obj.get('cwd'), 'git_branch': obj.get('gitBranch')}, 'time_fields': times}

def codex_event(obj, session, pairing=None):
    etype = obj.get('type')
    p = obj.get('payload') if isinstance(obj.get('payload'), dict) else {}
    ptype = p.get('type')
    times = {'timestamp': obj['timestamp']} if 'timestamp' in obj else {}
    mid = p.get('id') if isinstance(p.get('id'), str) and etype == 'response_item' else None
    msgs, notes = [], [{'event_type': etype, 'payload_type': ptype}]
    if pairing is not None:
        notes.append({'user_message_pairing': pairing})
    def add(role, source_role, text, attribution, kind, extra=()):
        msgs.append(event_message(len(msgs), mid, role, source_role, text, attribution, times, kind, extra))
    if etype == 'session_meta':
        notes.append({'session_id': p.get('id'), 'cwd': p.get('cwd'), 'originator': p.get('originator'), 'source': p.get('source')})
    elif etype == 'response_item' and ptype == 'message':
        speaker = p.get('role')
        parts = p.get('content') if isinstance(p.get('content'), list) else [p.get('content')]
        for part in parts:
            text = part.get('text') if isinstance(part, dict) else part if isinstance(part, str) else None
            if not isinstance(text, str):
                add('event_part', speaker, '[' + str(part.get('type') if isinstance(part, dict) else None) + ' part not interpreted]', 'context_not_owner', 'uninterpreted', ['uninterpreted_part'])
            elif speaker == 'user':
                role, attribution = user_text_role(text, False, False)
                add(role, speaker, text, attribution, 'text')
                if pairing is not None:
                    msgs[-1]['codex_event_pairing'] = pairing
            else:
                add(speaker or 'unknown', speaker, text, 'source_role', 'text')
    elif etype == 'response_item' and ptype in ('function_call', 'custom_tool_call', 'local_shell_call', 'web_search_call'):
        add('tool_call', ptype, '[' + ptype + ' ' + str(p.get('name')) + '] ' + lenient_text(p.get('arguments', p.get('input', p.get('action')))), 'tool_context_not_owner', ptype)
    elif etype == 'response_item' and ptype in ('function_call_output', 'custom_tool_call_output'):
        out = p.get('output')
        if isinstance(out, dict) and 'content' in out:
            out = out['content']
        add('tool_result', ptype, lenient_text(out), 'tool_context_not_owner', ptype)
    elif etype == 'response_item' and ptype == 'reasoning':
        summary = [s.get('text', '') for s in p.get('summary') or [] if isinstance(s, dict)]
        add('assistant_thinking', ptype, '\n'.join(summary), 'source_role', 'reasoning_summary', ['encrypted_reasoning_not_read'] if p.get('encrypted_content') else [])
    elif etype == 'response_item' and ptype == 'agent_message':
        body = {k: v for k, v in p.items() if k not in ('type', 'encrypted_content')}
        add('inter_agent', ptype, lenient_text(body.get('content', body.get('text', body))), 'agent_context_not_owner', ptype)
    elif etype == 'event_msg' and ptype == 'user_message':
        text = lenient_text(p.get('message'))
        exact_match = (isinstance(pairing, dict)
                       and pairing.get('status') == 'exact_text_match_response_group')
        unique_pair = exact_match and not pairing.get('occurrence_ambiguous', True)
        if unique_pair:
            add('user_message_event_exact_match_context', 'user', text,
                'unique_exact_text_match_to_response_item', ptype,
                ['exact_text_present_in_response_item'])
        else:
            role, attribution = user_text_role(text, False, False)
            indicators = (['exact_text_match_occurrence_ambiguous_candidate_retained']
                          if exact_match else ['no_exact_response_item_match'])
            add(role, 'user', text, attribution, ptype, indicators)
        if pairing is not None:
            msgs[-1]['codex_event_pairing'] = pairing
    elif etype == 'event_msg' and ptype == 'agent_message':
        add('assistant_event_echo', 'assistant', lenient_text(p.get('message')), 'source_role', ptype)
    return {'id': session, 'title': None, 'schema': 'codex_rollout_event', 'notes': notes, 'messages': msgs,
            'source_metadata': {'platform': 'codex'}, 'time_fields': times}

def markdown(data, owner_id):
    text = data.decode('utf-8-sig')
    result, role, body = [], None, []
    fence, fence_len = None, 0
    for line in text.splitlines(keepends=True):
        mark = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line.rstrip('\r\n'))
        if mark:
            run, tail = mark.groups()
            if fence is None:
                fence, fence_len = run[0], len(run)
            elif run[0] == fence and len(run) >= fence_len and not tail.strip():
                fence = None
            body.append(line)
            continue
        heading = re.fullmatch(r'## (User|Assistant)\s*', line.rstrip('\r\n')) if fence is None else None
        if heading:
            if role is not None:
                result.append({'role': role, 'content': ''.join(body)})
            elif ''.join(body).strip():
                raise Invalid('ambiguous Markdown preamble outside role headings')
            role, body = heading[1].lower(), []
        else:
            body.append(line)
    if fence is not None:
        raise Invalid('unclosed Markdown fence')
    if role is None:
        raise Invalid('standalone Markdown lacks exact ## User / ## Assistant role headings')
    result.append({'role': role, 'content': ''.join(body)})
    return {'id': None, 'title': None, 'schema': 'markdown_roles', 'notes': ['role heading text is a source claim, not verified authorship'],
            'messages': [message(m, i, False, owner_id) for i, m in enumerate(result)]}

def profile(args):
    frequencies = collections.Counter()
    refs = []
    ignored, suppressed_singletons = set(), set()
    for value in args.reference:
        p = Path(value).expanduser().resolve(strict=True)
        if not p.is_file():
            raise Invalid('reference is not a regular file: ' + str(p))
        data = bounded_read(p, args.max_reference_bytes)
        text = data.decode('utf-8-sig')
        reference_terms = reference_words(text)
        frequencies.update(reference_terms)
        ignored.update(t.casefold() for t in TOKEN.findall(text) if t.casefold() in NON_SIGNALS)
        suppressed_singletons.update(words(text) - reference_terms)
        refs.append({'path': str(p), 'sha256': digest(data), 'bytes': len(data)})
    query_terms = words(args.query or '')
    ignored.update(t.casefold() for t in TOKEN.findall(args.query or '') if t.casefold() in NON_SIGNALS)
    chosen = sorted(query_terms) + [t for t in sorted(frequencies, key=lambda t: (-frequencies[t], t)) if t not in query_terms]
    terms = chosen[:args.max_profile_terms]
    if not terms:
        raise Invalid('profile contains no usable lexical signals after function-word/role filtering')
    return {'version': VERSION, 'references': refs, 'query': args.query, 'terms': terms,
            'method': 'distinct casefolded Unicode alphabetic runs with optional ++/# suffix; function words/role boilerplate omitted; reference single letters require uppercase or backticks; query first then reference document frequency and lexical tie break',
            'ignored_terms': sorted(ignored), 'suppressed_reference_singletons': sorted(suppressed_singletons),
            'truncated': len(chosen) > len(terms), 'auto_expansion': False,
            'limitations': 'lexical matching only; no semantic recall guarantee; frequent reference boilerplate may match'}

def enumerate_inputs(roots, max_files):
    seen = set()
    count = 0
    for root in roots:
        p = Path(root).expanduser().absolute()
        if p.is_symlink():
            try:
                p = p.resolve(strict=True)
            except (OSError, RuntimeError):
                yield p, 'missing', 'explicit root symlink could not be resolved'
                continue
        else:
            p = p.resolve(strict=False)
        if not p.exists():
            yield p, 'missing', None
            continue
        if p.is_dir():
            walk_errors = []
            def walkerror(error):
                walk_errors.append(error)
            def error_entry(error):
                filename = getattr(error, 'filename', None)
                affected = Path(os.fsdecode(filename)) if filename is not None else p
                return affected, 'enumeration_error', 'directory enumeration failed: ' + str(error)
            def descendants():
                for base, dirs, files in os.walk(p, followlinks=False, onerror=walkerror):
                    while walk_errors:
                        yield error_entry(walk_errors.pop(0))
                    for name in sorted(dirs):
                        q = Path(base) / name
                        if q.is_symlink() or name in EXCLUDES:
                            yield q, 'symlink_skipped' if q.is_symlink() else 'excluded_directory', None
                    dirs[:] = sorted(d for d in dirs if d not in EXCLUDES and not (Path(base) / d).is_symlink())
                    for name in sorted(files):
                        q = Path(base) / name
                        yield q, 'symlink_skipped' if q.is_symlink() else None, None
                while walk_errors:
                    yield error_entry(walk_errors.pop(0))
            entries = descendants()
        else:
            entries = [(p, None, None)]
        for q, status, reason in entries:
            key = str(q.absolute())
            if status != 'enumeration_error' and key in seen:
                continue
            seen.add(key)
            count += 1
            if count > max_files:
                raise Invalid('max-files limit reached; enumeration incomplete')
            yield q, status, reason

def locator(path, file_sha, offset, data, element, owner_id, branch, record_sha=None):
    return {'version': VERSION, 'path': str(path), 'file_sha256': file_sha,
            'offset': offset, 'length': len(data), 'record_sha256': record_sha if record_sha is not None else digest(data),
            'element_index': element, 'owner_id': owner_id, 'branch': branch}

def process_record(data, suffix, element, owner_id, branch, fmt=None, session=None, path=None, pairing=None):
    if fmt == GOOGLE_TAKEOUT_ACTIVITY_FORMAT and suffix == '.jsonl':
        return google_takeout_activity_event(json.loads(data))
    if fmt in EVENT_RECORD_FORMATS and suffix == '.jsonl':
        obj = json.loads(data)
        if not isinstance(obj, dict):
            raise Invalid('event record must be an object')
        if fmt == 'cursor_agent':
            return cursor_event(obj, path)
        return claude_event(obj, path) if fmt == 'claude_code' else codex_event(obj, session, pairing)
    if suffix in ('.md', '.markdown'):
        if element is not None:
            raise Invalid('unexpected Markdown element index')
        return markdown(data, owner_id)
    obj = json.loads(data)
    if suffix == '.json' and is_cursor_prompt_history_path(path):
        return cursor_prompt_history_event(obj, element)
    if element is not None:
        if not isinstance(obj, list) or not 0 <= element < len(obj):
            raise Invalid('array element index invalid')
        obj = obj[element]
    return normalize(obj, owner_id, branch)

def read_projection_line(source, max_bytes, deadline=None):
    """Consume one physical line with bounded memory, rolling back on timeout."""
    offset = source.tell()
    try:
        if deadline is not None and time.monotonic() >= deadline:
            raise TimeoutError('projection physical-line read timed out')
        raw = source.readline(max_bytes + 1)
        oversized = len(raw) > max_bytes
        if oversized:
            tail = raw
            while tail and not tail.endswith(b'\n'):
                if deadline is not None and time.monotonic() >= deadline:
                    raise TimeoutError('projection physical-line read timed out')
                tail = source.readline(max_bytes + 1)
        return raw, oversized
    except TimeoutError:
        source.seek(offset)
        raise


def validate_projection_prefix(source, cursor, max_bytes, deadline):
    for _ in range(cursor['next_line'] - 1):
        raw, _ = read_projection_line(source, max_bytes, deadline)
        if not raw:
            raise Invalid('projection continuation prefix ended before its recorded line')
    if source.tell() != cursor['next_offset']:
        raise Invalid('projection continuation offset is not the recorded line boundary')


def roust_jsonl_projection(args, binary, query, deadline, scratch_parent):
    """Nominate original JSONL records via private, bounded temporary search chunks.

    A projection is never a citation.  Its offsets and hashes only nominate
    records which the main scanner must reopen and validate against originals.
    """
    receipt = {'files_examined': 0, 'files_projected': 0, 'records_examined': 0,
               'records_projected': 0, 'chunks': 0, 'omissions': [], 'ranked_chunks': 0,
               'continuations': [], 'projection_complete': False, 'ranked_chunk_records': [],
               'bounds': {'files': 16, 'records_per_file': 256, 'records_per_chunk': 16,
                          'text_characters_per_record': args.projection_max_text_chars, 'projected_bytes': 4 * 1024 * 1024,
                          'source_bytes': min(args.max_total_bytes, args.projection_max_source_bytes)}}
    accepted, maps, pending_continuations, ranked_names = {}, {}, [], set()
    projected_bytes = 0
    source_bytes = 0
    try:
        with tempfile.TemporaryDirectory(prefix='roust-projection-', dir=scratch_parent) as tmp:
            directory = Path(tmp)
            for path, status, reason in enumerate_inputs(args.root, args.max_files):
                if time.monotonic() >= deadline or receipt['files_examined'] >= 16:
                    receipt['omissions'].append('projection file/time bound reached; remaining inputs unprojected')
                    cursor = getattr(args, 'projection_cursor', None)
                    if cursor:
                        pending_continuations.append(dict(cursor))
                        receipt['continuation_validation_pending'] = True
                    break
                if status or path.suffix.lower() != '.jsonl' or not path.is_file():
                    continue
                receipt['files_examined'] += 1
                try:
                    before = path.stat()
                    if before.st_size > args.max_file_bytes:
                        receipt['omissions'].append({'path': str(path), 'reason': 'file exceeds scanner file-size bound'})
                        if getattr(args, 'projection_cursor', None):
                            pending_continuations.append(dict(args.projection_cursor))
                            receipt['continuation_validation_pending'] = True
                        continue
                    if source_bytes + before.st_size > receipt['bounds']['source_bytes']:
                        receipt['omissions'].append({'path': str(path), 'reason': 'projection cumulative source-byte bound'})
                        if getattr(args, 'projection_cursor', None):
                            pending_continuations.append(dict(args.projection_cursor))
                            receipt['continuation_validation_pending'] = True
                        continue
                    source_bytes += before.st_size
                    source_sha = filehash(path)
                    cursor = getattr(args, 'projection_cursor', None)
                    if cursor and (str(path.absolute()) != cursor['path'] or source_sha != cursor['source_sha256']):
                        raise Invalid('projection continuation source path or hash changed')
                    try:
                        fmt, session = detect_format(path, args.max_bytes, deadline)
                    except TimeoutError:
                        pending_continuations.append(dict(cursor) if cursor else {
                            'version': 1, 'path': str(path.absolute()), 'source_sha256': source_sha,
                            'next_offset': 0, 'next_line': 1})
                        receipt['continuation_validation_pending'] = bool(cursor)
                        raise Invalid('projection format detection timed out; continuation retained')
                    chunks, entries, texts, offset_lines = [], [], [], {}
                    with path.open('rb') as source:
                        first_line = 1
                        if cursor:
                            # Verify both line count and byte boundary from the original,
                            # never trust offsets merely because the source hash matches.
                            try:
                                validate_projection_prefix(source, cursor, args.max_bytes, deadline)
                            except TimeoutError:
                                pending_continuations.append(dict(cursor))
                                receipt['continuation_validation_pending'] = True
                                raise Invalid('projection continuation prefix validation timed out')
                            first_line = cursor['next_line']
                        next_line = first_line
                        for number in range(first_line, first_line + 256):
                            offset = source.tell()
                            try:
                                raw, oversized = read_projection_line(source, args.max_bytes, deadline)
                            except TimeoutError:
                                receipt['omissions'].append({'path': str(path), 'line': number,
                                                            'reason': 'projection time bound; current physical line will be retried'})
                                break
                            if not raw:
                                break
                            next_line = number + 1
                            receipt['records_examined'] += 1
                            if oversized:
                                receipt['omissions'].append({'path': str(path), 'line': number,
                                                            'reason': 'oversize record skipped; later records remain eligible'})
                                continue
                            if not raw.strip():
                                continue
                            try:
                                conv = process_record(raw, '.jsonl', None, args.owner_id, args.branch, fmt, session, path)
                                projected_parts = []
                                for m in conv['messages']:
                                    outer = m.get('cursor_query_text', m['text'])
                                    if outer:
                                        projected_parts.append(str(m['role']) + ': ' + outer)
                                    forward = m.get('forwarded_message')
                                    if isinstance(forward, dict) and forward.get('text'):
                                        projected_parts.append('forwarded source author unverified: ' + forward['text'])
                                body = '\n'.join(projected_parts)
                            except (Invalid, ValueError, TypeError, KeyError, UnicodeError, RecursionError, AttributeError) as ex:
                                receipt['omissions'].append({'path': str(path), 'line': number, 'reason': str(ex)[:256]})
                                continue
                            if not body:
                                continue
                            if len(body) > args.projection_max_text_chars:
                                receipt['omissions'].append({'path': str(path), 'line': number, 'reason': 'projection text truncated to ' + str(args.projection_max_text_chars) + ' characters'})
                                body = body[:args.projection_max_text_chars]
                            texts.append(body)
                            entries.append((offset, digest(raw)))
                            offset_lines[offset] = number
                            receipt['records_projected'] += 1
                            if len(entries) == 16:
                                chunks.append((entries, texts))
                                entries, texts = [], []
                        if source.tell() < before.st_size:
                            receipt['omissions'].append({'path': str(path), 'line': next_line, 'reason': 'bounded projection; remainder unprojected'})
                            pending_continuations.append({'version': 1, 'path': str(path.absolute()),
                                                          'source_sha256': source_sha, 'next_offset': source.tell(),
                                                          'next_line': next_line})
                    if entries:
                        chunks.append((entries, texts))
                    after = path.stat()
                    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino) or filehash(path) != source_sha:
                        receipt['omissions'].append({'path': str(path), 'reason': 'source changed during projection'})
                        pending_continuations = [c for c in pending_continuations if c['path'] != str(path.absolute())]
                        continue
                    receipt['files_projected'] += 1
                    for offsets, contents in chunks:
                        # Roust rejects any file containing a line longer than
                        # 3000 characters.  JSON-escape worst-case input in
                        # short pieces so long chat messages remain indexable.
                        pieces = [text[i:i + 200] for text in contents for i in range(0, len(text), 200)]
                        data = json.dumps({'events': pieces}, ensure_ascii=False, indent=2).encode('utf-8')
                        if projected_bytes + len(data) > receipt['bounds']['projected_bytes']:
                            receipt['omissions'].append('projection byte bound reached; remaining chunks unprojected')
                            pending_continuations = [c for c in pending_continuations if c['path'] != str(path.absolute())]
                            pending_continuations.append({'version': 1, 'path': str(path.absolute()),
                                                          'source_sha256': source_sha, 'next_offset': offsets[0][0],
                                                          'next_line': offset_lines[offsets[0][0]]})
                            break
                        name = 'chunk-' + str(len(maps)) + '.json'
                        (directory / name).write_bytes(data)
                        maps[name] = {'path': str(path.absolute()), 'source_sha256': source_sha, 'offsets': offsets,
                                      'first_line': offset_lines[offsets[0][0]]}
                        projected_bytes += len(data)
                    if projected_bytes >= receipt['bounds']['projected_bytes']:
                        break
                except (OSError, Invalid, ValueError, TypeError, UnicodeError, RecursionError) as ex:
                    receipt['omissions'].append({'path': str(path), 'reason': str(ex)[:256]})
            receipt['chunks'] = len(maps)
            receipt['projected_bytes'] = projected_bytes
            receipt['source_bytes'] = source_bytes
            if maps and time.monotonic() < deadline:
                process = subprocess.Popen([binary, query, str(directory), '--no-cache', '--no-history', '--docs-data-files', '--files-only'],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
                try:
                    stdout, stderr = process.communicate(timeout=max(0.1, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.communicate()
                    raise
                receipt['exit_code'] = process.returncode
                receipt['stderr'] = stderr[-4096:]
                if process.returncode in (0, 1):
                    receipt['continuations'] = pending_continuations
                if process.returncode == 0:
                    for rank, name in enumerate(stdout.splitlines()):
                        item = maps.get(name)
                        if item is None or name in ranked_names:
                            continue
                        ranked_names.add(name)
                        receipt['ranked_chunks'] += 1
                        ranking = {'chunk_name': name, 'rank': rank, 'rank_basis': 'files_only_output_order'}
                        receipt['ranked_chunk_records'].append(dict(
                            ranking, path=item['path'], source_sha256=item['source_sha256'],
                            first_line=item['first_line'],
                            records=[{'offset': offset, 'record_sha256': record_sha}
                                     for offset, record_sha in item['offsets']]))
                        dest = accepted.setdefault(item['path'], {'source_sha256': item['source_sha256'],
                                                                  'records': {}, 'rankings': {}})
                        dest['records'].update(dict(item['offsets']))
                        dest['rankings'].update({offset: ranking for offset, _ in item['offsets']})
                receipt['unranked_chunks'] = len(maps) - receipt['ranked_chunks']
            elif maps:
                receipt['omissions'].append('no time remained to rank projected chunks')
            else:
                # No text chunks exist to rank; the recorded span can still be
                # continued, while all omissions remain visible in this receipt.
                receipt['continuations'] = pending_continuations
    except (OSError, Invalid, subprocess.TimeoutExpired, UnicodeError) as ex:
        receipt['error'] = str(ex)[:512]
    if maps and receipt.get('exit_code') not in (0, 1):
        # Ranking never completed: retry the first prepared chunk for each source.
        retries = {}
        for item in maps.values():
            retries.setdefault(item['path'], {'version': 1, 'path': item['path'],
                                               'source_sha256': item['source_sha256'],
                                               'next_offset': item['offsets'][0][0],
                                               'next_line': item['first_line']})
        receipt['continuations'] = list(retries.values())
        receipt['unranked_chunks'] = len(maps)
    elif maps and 'exit_code' not in receipt:
        receipt['unranked_chunks'] = len(maps)
    receipt['unranked_chunk_records'] = [
        {'path': item['path'], 'source_sha256': item['source_sha256'],
         'first_line': item['first_line'], 'record_offsets': [offset for offset, _ in item['offsets']]}
        for name, item in maps.items() if name not in ranked_names
    ]
    for continuation in receipt['continuations']:
        continuation['query_sha256'] = digest(query.encode('utf-8'))
        continuation['projection_format'] = 'jsonl-events-v1'
    receipt['limitation'] = 'bounded lexical nominations only; original scan and source verification required'
    # This concerns preparation of a single explicit input file, not whether
    # Roust returned every relevant record or whether any claim is true.
    receipt['projection_complete'] = (len(args.root) == 1 and Path(args.root[0]).expanduser().is_file()
                                      and getattr(args, 'projection_cursor', None) is None
                                      and receipt['files_projected'] == 1 and not receipt['omissions']
                                      and not receipt.get('error') and not receipt['continuations']
                                      and not receipt.get('unranked_chunks', 0)
                                      and (not receipt['chunks'] or receipt.get('exit_code') in (0, 1)))
    return accepted, receipt

def acquire(args):
    start = time.monotonic()
    prof = profile(args)
    args.projection_cursor = None
    if args.projection_resume:
        if args.no_roust or len(args.root) != 1:
            raise Invalid('projection resume requires Roust and exactly one explicit JSONL file root')
        root = Path(args.root[0]).expanduser().resolve(strict=True)
        if not root.is_file() or root.suffix.lower() != '.jsonl':
            raise Invalid('projection resume requires an explicit JSONL file root')
        previous = json.loads(bounded_read(Path(args.projection_resume).expanduser(), args.max_projection_receipt_bytes))
        candidates = previous.get('jsonl_projection', {}).get('continuations', [])
        if not isinstance(candidates, list):
            raise Invalid('projection continuation list invalid')
        matching = [c for c in candidates if isinstance(c, dict) and isinstance(c.get('path'), str)
                    and Path(c['path']).expanduser().resolve(strict=False) == root]
        if len(matching) != 1:
            raise Invalid('projection receipt must contain exactly one continuation for the root')
        cursor = dict(matching[0], path=str(root))
        if (cursor.get('version') != 1 or not isinstance(cursor.get('source_sha256'), str)
                or type(cursor.get('next_offset')) is not int or cursor['next_offset'] < 0
                or type(cursor.get('next_line')) is not int or cursor['next_line'] < 1):
            raise Invalid('projection continuation has invalid fields')
        if cursor.get('projection_format') != 'jsonl-events-v1':
            raise Invalid('projection continuation format does not match')
        if cursor.get('query_sha256') != digest((args.query or ' '.join(prof['terms'])).encode('utf-8')):
            raise Invalid('projection continuation query does not match')
        if filehash(root) != cursor['source_sha256']:
            raise Invalid('projection continuation source hash changed')
        with root.open('rb') as f:
            validate_projection_prefix(f, cursor, args.max_bytes, start + args.max_seconds)
        args.projection_cursor = cursor
    out = Path(args.out).expanduser().resolve(strict=False)
    for root in args.root:
        root_path = Path(root).expanduser().resolve(strict=False)
        if root_path.is_dir() and (out == root_path or root_path in out.parents):
            raise Invalid('output must be outside input roots to avoid acquiring generated output')
    out.mkdir(parents=True, exist_ok=False)
    dump(out / 'profile.json', prof)
    # Roust nominates files only; it is never a gate on the existing scan.
    direct_roust = Path.home() / '.local/share/thought-reconstruction-roust/node_modules/roust-linux-x64/bin/roust'
    roust_path = str(direct_roust) if direct_roust.is_file() else (shutil.which('roust') or '')
    if args.projection_resume and not Path(roust_path).is_file():
        raise Invalid('projection resume requires an available Roust binary')
    nominations, roust_runs, roust_version = [], [], None
    projection, projection_receipt = {}, {'status': 'disabled_or_unavailable'}
    query = args.query or ' '.join(prof['terms'])
    if not args.no_roust and Path(roust_path).is_file():
        # Version probing is restricted to the known direct binary; an arbitrary
        # PATH launcher may leave a child holding pipes after a timeout.
        if direct_roust.is_file():
            try:
                roust_version = subprocess.run([roust_path, '--version'], capture_output=True, text=True,
                                               timeout=min(2, args.max_seconds / 10), check=False).stdout.strip()[:256]
            except (OSError, subprocess.TimeoutExpired, UnicodeError):
                pass
        projection, projection_receipt = roust_jsonl_projection(args, roust_path, query, start + args.max_seconds / 6, out)
        for root in args.root:
            if time.monotonic() - start >= args.max_seconds / 3:
                roust_runs.append({'root': root, 'error': 'nomination time budget exhausted; scanner continues'})
                break
            directory = Path(root).expanduser().resolve(strict=False)
            if not directory.is_dir():
                continue
            started = time.monotonic()
            before_count = len(nominations)
            record = {'root': str(directory), 'supplied_root': str(root), 'binary': roust_path, 'no_cache': True}
            try:
                process = subprocess.Popen([roust_path, query, str(directory), '--no-cache', '--no-history', '--docs-data-files', '--files-only'],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
                try:
                    stdout, stderr = process.communicate(timeout=max(0.1, min(20, args.max_seconds / 3 - (time.monotonic() - start))))
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()
                    raise
                result = subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)
                record.update(exit_code=result.returncode, stderr=result.stderr[-4096:])
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        candidate = directory / line
                        relative = candidate.relative_to(directory) if candidate.is_relative_to(directory) else None
                        if relative is None or any(part in EXCLUDES for part in relative.parts):
                            continue
                        if any((directory.joinpath(*relative.parts[:i])).is_symlink() for i in range(1, len(relative.parts) + 1)):
                            continue
                        if candidate.is_file() and candidate.suffix.lower() in SUFFIXES:
                            resolved = candidate.resolve()
                            if directory.resolve() in resolved.parents:
                                nominations.append(str(candidate.absolute()))
                record['nominations'] = len(nominations) - before_count
            except (OSError, subprocess.TimeoutExpired, UnicodeError) as ex:
                record['error'] = str(ex)
            record['elapsed_seconds'] = time.monotonic() - started
            roust_runs.append(record)
    dump(out / 'roust.json', {'mode': 'disabled' if args.no_roust else 'additive',
                              'available': Path(roust_path).is_file(), 'version': roust_version, 'runs': roust_runs,
                              'jsonl_projection': projection_receipt,
                              'jsonl_nominations': [{'path': path, 'source_sha256': item['source_sha256'],
                                                     'record_offsets': sorted(item['records'])} for path, item in projection.items()],
                              'nominated_paths': list(dict.fromkeys(nominations)),
                              'limitation': 'ranked lexical file leads only; no semantic or coverage guarantee; full scanner remains authoritative'})
    nominated_set = set(nominations)
    stats = collections.Counter(matching_passages=0, truncated_records=0, omitted_matching_passages=0)
    candidate_roles, candidate_bases = collections.Counter(), collections.Counter()
    total_bytes = 0
    negative = []
    terms = set(prof['terms'])
    with (out/'manifest.jsonl').open('w') as manifest, (out/'inputs.jsonl').open('w') as inputs, (out/'candidates.jsonl').open('w') as candidates, (out/'errors.jsonl').open('w') as errors:
        def write_candidate(item):
            lineout(candidates, item)
            candidate_roles[item['message']['role']] += 1
            candidate_bases[item['candidate_basis']] += 1
            stats['candidate_passages'] += 1
        def error(path, reason, loc=None):
            stats['errors'] += 1
            lineout(errors, {'path': str(path), 'reason': reason, 'locator': loc})
        try:
            for p, status, enumeration_reason in enumerate_inputs(list(projection) + nominations + args.root, args.max_files):
                if time.monotonic() - start > args.max_seconds:
                    raise Invalid('max-seconds limit reached; input enumeration incomplete')
                info = {'path': str(p), 'status': status}
                if status:
                    stats[status] += 1
                    if status == 'missing':
                        error(p, 'explicit root missing')
                    elif status == 'enumeration_error':
                        stats['enumeration_incomplete'] += 1
                        error(p, enumeration_reason)
                        info['reason'] = enumeration_reason
                    lineout(inputs, info)
                    continue
                if not p.is_file():
                    stats['nonregular_skipped'] += 1
                    lineout(inputs, dict(info, status='nonregular_skipped'))
                    continue
                if p.suffix.lower() not in SUFFIXES:
                    stats['unsupported'] += 1
                    lineout(inputs, dict(info, status='unsupported'))
                    continue
                before = p.stat()
                info.update(bytes=before.st_size, mtime_ns=before.st_mtime_ns)
                if before.st_size > args.max_file_bytes:
                    stats['oversize_files'] += 1
                    lineout(inputs, dict(info, status='oversize'))
                    error(p, 'max-file-bytes exceeded')
                    continue
                total_bytes += before.st_size
                if total_bytes > args.max_total_bytes:
                    lineout(inputs, dict(info, status='total_byte_limit'))
                    raise Invalid('max-total-bytes reached; input enumeration incomplete')
                try:
                    full_hash = filehash(p)
                    info['sha256'] = full_hash
                    projected = projection.get(str(p.absolute()))
                    if projected and projected['source_sha256'] != full_hash:
                        error(p, 'source changed since Roust JSONL projection; projected nominations discarded')
                        projected = None
                    suffix = p.suffix.lower()
                    fmt, session = detect_format(p, args.max_bytes) if suffix == '.jsonl' else (None, None)
                    pairing_index = codex_echo_pairs(str(p), args.max_bytes, args.max_records) if fmt == 'codex_rollout' else {}
                    if fmt == 'codex_rollout':
                        info['codex_exact_text_matched_events'] = sum(v.get('status') == 'exact_text_match_response_group' for v in pairing_index.values())
                        info['codex_unpaired_user_events'] = sum(v.get('status') == 'no_exact_response_item_match' for v in pairing_index.values())
                    info['format'] = fmt
                    recent = collections.deque(maxlen=args.neighbors)
                    pending = []
                    def emit(c):
                        c.pop('_need', None)
                        write_candidate(c)
                    def chunks():
                        with p.open('rb') as f:
                            if suffix == '.jsonl':
                                number = 0
                                while True:
                                    offset = f.tell()
                                    raw = f.readline(args.max_bytes + 1)
                                    if not raw:
                                        break
                                    number += 1
                                    if len(raw) > args.max_bytes:
                                        while raw and not raw.endswith(b'\n'):
                                            raw = f.readline(args.max_bytes + 1)
                                        stats['oversize_records'] += 1
                                        error(p, 'JSONL record exceeds max-bytes at line ' + str(number))
                                        continue
                                    if raw.strip():
                                        yield offset, raw, None, number, _UNPARSED, None
                            else:
                                raw = f.read(args.max_bytes + 1)
                                if len(raw) > args.max_bytes:
                                    stats['oversize_documents'] += 1
                                    raise Invalid('document exceeds max-bytes; JSON arrays are not element-streamed')
                                if suffix == '.json':
                                    obj = json.loads(raw)
                                    document_hash = digest(raw)
                                    if isinstance(obj, list):
                                        if len(obj) > args.max_records:
                                            raise Invalid('JSON array exceeds max-records')
                                        for i in range(len(obj)):
                                            yield 0, raw, i, None, obj[i], document_hash
                                        return
                                    yield 0, raw, None, None, obj, document_hash
                                    return
                                yield 0, raw, None, None, _UNPARSED, None
                    try:
                     for offset, data, element, lineno, parsed, record_sha in chunks():
                         if stats['attempted_records'] >= args.max_records or time.monotonic() - start > args.max_seconds:
                             raise Invalid('record/time limit reached; file processing incomplete')
                         stats['attempted_records'] += 1
                         loc = locator(p, full_hash, offset, data, element, args.owner_id, args.branch, record_sha)
                         projected_record = bool(projected and projected['records'].get(offset) == digest(data))
                         projection_metadata = {'roust_projection': projected['rankings'][offset]} if projected_record else {}
                         try:
                             if parsed is _UNPARSED:
                                 conv = process_record(data, suffix, element, args.owner_id, args.branch, fmt, session, p,
                                                       pairing_index.get(offset))
                             elif suffix == '.json' and is_cursor_prompt_history_path(p):
                                 conv = cursor_prompt_history_event(parsed, element)
                             else:
                                 conv = normalize(parsed, args.owner_id, args.branch)
                             hits = []
                             for m in conv['messages']:
                                 # Unattributed Cursor events are searchable leads, never owner evidence.
                                 if m['role'] not in ('owner', 'nominal_owner', 'host_answer_candidate', 'prompt_event', 'unattributed_discord') and not (projected_record and m['role'] in ('assistant', 'peer')) and 'forwarded_message' not in m:
                                     continue
                                 matched = sorted(candidate_words(m) & terms)
                                 if len(matched) >= args.min_signals or str(p.absolute()) in nominated_set or projected_record:
                                     hits.append((m, matched))
                             capped = hits[:args.max_passages]
                             omitted = len(hits) - len(capped)
                             stats['matching_passages'] += len(hits)
                             stats['truncated_records'] += bool(omitted)
                             stats['omitted_matching_passages'] += omitted
                             eid = digest(json.dumps(loc, sort_keys=True).encode())
                             row = {'evidence_id': eid, 'conversation_id': conv['id'], 'title': conv['title'], 'schema': conv['schema'],
                                    'locator': loc, 'line': lineno, 'include': bool(hits), 'message_count': len(conv['messages']),
                                    'matching_passages': len(hits), 'materialized_passages': len(capped), 'omitted_matching_passages': omitted, 'passages_truncated': len(hits) > len(capped), 'roust_file_nomination': str(p.absolute()) in nominated_set, 'roust_record_nomination': projected_record, 'notes': conv['notes'],
                                    **projection_metadata}
                             lineout(manifest, row)
                             stats['processed_records'] += 1
                             stats['included_records'] += bool(hits)
                             if not hits and conv['messages']:
                                 rank = digest((args.sample_seed + eid).encode())
                                 negative.append((rank, row))
                                 negative.sort(key=lambda a: a[0])
                                 del negative[args.negative_sample:]
                             if fmt in EVENT_RECORD_FORMATS:
                                 hit_signals = {m['index']: matched for m, matched in capped}
                                 for m in conv['messages']:
                                     entry = dict(m, locator=loc, line=lineno)
                                     for c in pending:
                                         c['window'].append(entry)
                                         c['_need'] -= 1
                                     for c in [c for c in pending if c['_need'] <= 0]:
                                         pending.remove(c)
                                         emit(c)
                                     if m['index'] in hit_signals:
                                         matched = hit_signals[m['index']]
                                         c = {'evidence_id': eid + ':' + str(m['index']), 'record_evidence_id': eid,
                                              'locator': loc, 'line': lineno, 'conversation_id': conv['id'], 'message': m,
                                              'distinct_signals': matched, 'score': len(matched), 'window': list(recent) + [entry], **candidate_signal_parts(m, terms),
                                              'candidate_basis': 'lexical_and_roust' if len(matched) >= args.min_signals and (str(p.absolute()) in nominated_set or projected_record) else ('lexical' if len(matched) >= args.min_signals else ('roust_record_nomination' if projected_record else 'roust_file_nomination')),
                                              'window_scope': 'adjacent messages across event lines; each window entry carries its own locator',
                                              'warning': 'lexical hit or Roust-nominated file; authorship/relevance require curation, including quoted or delegated content',
                                              '_need': args.neighbors, **projection_metadata}
                                         if args.neighbors:
                                             pending.append(c)
                                         else:
                                             emit(c)
                                     recent.append(entry)
                                 continue
                             for m, matched in capped:
                                 idx = m['index']
                                 window = conv['messages'][max(0,idx-args.neighbors):idx+args.neighbors+1]
                                 write_candidate({'evidence_id': eid + ':' + str(idx), 'record_evidence_id': eid,
                                                     'locator': loc, 'conversation_id': conv['id'], 'message': m,
                                                     'distinct_signals': matched, 'score': len(matched), 'window': window, **candidate_signal_parts(m, terms),
                                                     'candidate_basis': 'lexical_and_roust' if len(matched) >= args.min_signals and (str(p.absolute()) in nominated_set or projected_record) else ('lexical' if len(matched) >= args.min_signals else ('roust_record_nomination' if projected_record else 'roust_file_nomination')),
                                                     'warning': 'lexical hit or Roust-nominated file; authorship/relevance require curation, including quoted or delegated content',
                                                     **projection_metadata})
                         except (Invalid, ValueError, TypeError, KeyError, UnicodeError, RecursionError, AttributeError) as ex:
                             error(p, str(ex), loc)
                    finally:
                        for c in pending:
                            c['window_incomplete'] = True
                            emit(c)
                    after = p.stat()
                    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino) or filehash(p) != full_hash:
                        raise Invalid('source changed during acquisition; all file results must be treated as invalid')
                    info['status'] = 'processed'
                except (OSError, Invalid, ValueError, TypeError, UnicodeError, RecursionError, AttributeError) as ex:
                    info['status'] = 'error'
                    error(p, str(ex))
                lineout(inputs, info)
        except (OSError, Invalid) as ex:
            error('<invocation>', str(ex))
            stats['enumeration_incomplete'] += 1
    # Keep coverage_complete as source-scan coverage for existing receipt consumers.
    coverage_skips = {key: stats[key] for key in
                      ('symlink_skipped', 'unsupported', 'excluded_directory', 'nonregular_skipped')
                      if stats[key]}
    coverage_complete = not stats['errors'] and not stats['enumeration_incomplete'] and not coverage_skips
    materialization = {'materialization_complete': bool(coverage_complete and not stats['omitted_matching_passages']
                                                       and stats['candidate_passages'] == stats['matching_passages']),
                       'matching_passages': stats['matching_passages'],
                       'truncated_records': stats['truncated_records'],
                       'omitted_matching_passages': stats['omitted_matching_passages'],
                       'materialization_scope': 'eligible matching passages from the supplied source scan; no semantic recall guarantee',
                       'passage_cap_recovery': 'rerun the same acquisition with a higher --max-passages and a fresh --out directory; resolve scan skips/errors separately'}
    dump(out/'candidate-summary.json', {'candidate_events': stats['candidate_passages'], 'by_role': dict(candidate_roles),
                                        'by_basis': dict(candidate_bases), **materialization,
                                        'limitation': 'source-role and nomination counts, not verified authorship or relevance; consult scan coverage and errors'})
    dump(out/'negative-sample.json', {'seed': args.sample_seed, 'method': 'lowest sha256(seed + record evidence ID); bounded lexical negatives only', 'records': [dict(row, sample_rank=rank) for rank,row in negative]})
    dump(out/'run.json', {'version': VERSION, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'arguments': vars(args),
                         'counts': dict(stats), 'considered_supported_bytes': total_bytes, 'elapsed_seconds': time.monotonic()-start,
                         'peak_rss_kib_linux': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                         'complete_without_errors': not stats['errors'],
                         'coverage_skips': coverage_skips,
                         'coverage_complete': coverage_complete, **materialization,
                         'excluded_directory_names': sorted(EXCLUDES),
                         'limitations': ['hidden files/directories included; no symlink recursion', 'lexical candidates only; no semantic recall or near-rg speed promise', 'no automatic profile expansion, embeddings, persistent corpus index, or training', 'native arrays loaded whole under max-bytes; branch siblings omitted explicitly', 'inputs manifest complete only when enumeration_incomplete is zero; excluded directory contents not enumerated', 'record errors have no binary include row; consult errors.jsonl; source drift invalidates all rows from that file']})
    print(json.dumps({'out': str(out), 'counts': dict(stats)}))
    return 1 if stats['errors'] else 0

def materialize(loc, max_bytes, max_source_bytes=256*1024*1024):
    if not isinstance(loc, dict) or loc.get('version') != VERSION:
        raise Invalid('unsupported locator')
    p = Path(loc['path'])
    if not p.is_absolute() or not p.is_file() or p.is_symlink():
        raise Invalid('locator path must be an absolute regular nonsymlink file')
    if p.suffix.lower() not in SUFFIXES:
        raise Invalid('unsupported locator suffix')
    if p.stat().st_size > max_source_bytes:
        raise Invalid('source exceeds --max-source-bytes')
    if filehash(p) != loc['file_sha256']:
        raise Invalid('source digest drift: ' + str(p))
    offset, length = loc['offset'], loc['length']
    if type(offset) is not int or type(length) is not int or offset < 0 or length < 0:
        raise Invalid('invalid locator range')
    if length > max_bytes:
        raise Invalid(f'locator record length {length} exceeds --max-bytes {max_bytes}; increase --max-bytes to at least {length} after considering memory use')
    with p.open('rb') as f:
        f.seek(offset)
        raw = f.read(length)
    if len(raw) != length or digest(raw) != loc['record_sha256']:
        raise Invalid('record digest drift')
    fmt, session = detect_format(p, max_bytes) if p.suffix.lower() == '.jsonl' else (None, None)
    pairing_index = codex_echo_pairs(str(p), max_bytes) if fmt == 'codex_rollout' else {}
    conv = process_record(raw, p.suffix.lower(), loc['element_index'], str(loc['owner_id']), loc.get('branch'),
                          fmt, session, p, pairing_index.get(offset))
    if filehash(p) != loc['file_sha256']:
        raise Invalid('source changed during materialization')
    return conv

def session_context(args, loc, anchor, start):
    """Read one bounded page of a verified native session, without relevance filtering."""
    p = Path(loc['path'])
    if p.suffix.lower() != '.jsonl' or loc.get('element_index') is not None:
        raise Invalid('--session-context requires native per-event JSONL')
    fmt, _ = detect_format(p, args.max_bytes)
    if fmt not in EVENT_RECORD_FORMATS:
        raise Invalid('--session-context requires native per-event JSONL')
    # Require an explicit identity, never the filename fallback used by detection.
    session = None
    with p.open('rb') as f:
        # Cursor captures have no authenticated embedded session identity.
        # Their scope is the exact verified file, not an inferred session.
        if fmt == 'cursor_agent':
            pass
        else:
            session = _native_session_identity(f, fmt, args.max_bytes)
    if fmt != 'cursor_agent' and (session is None or (anchor['id'] is not None and anchor['id'] != session)):
        raise Invalid('missing or mismatching native session identity')
    binding = {'version': VERSION, 'path': str(p), 'file_sha256': loc['file_sha256'],
               'format': fmt, 'session_id': session, 'owner_id': loc['owner_id'], 'branch': loc.get('branch')}
    if fmt == 'cursor_agent':
        binding['identity_scope'] = 'verified_source_file_only; native session identity unverified'
    offset, line = 0, 1
    if args.resume:
        token = json.loads(bounded_read(Path(args.resume), args.max_bytes))
        if isinstance(token, dict) and 'continuation' in token:
            token = token['continuation']
        if not isinstance(token, dict) or any(token.get(k) != v for k, v in binding.items()):
            raise Invalid('continuation does not match verified source/session')
        offset, line = token.get('offset'), token.get('line')
        if type(offset) is not int or type(line) is not int or offset < 0 or line < 1:
            raise Invalid('invalid continuation offset/line')
    before = p.stat()
    if before.st_size > args.max_source_bytes:
        raise Invalid('source exceeds --max-source-bytes during session inspection')
    if offset > before.st_size:
        raise Invalid('continuation offset exceeds source')
    pairing_index = codex_echo_pairs(str(p), args.max_bytes) if fmt == 'codex_rollout' else {}
    def parse_event(raw, record_line, record_offset):
        obj = json.loads(raw)
        if fmt == 'cursor_agent':
            if not isinstance(obj, dict) or 'messages' in obj or 'mapping' in obj:
                raise Invalid('ambiguous Cursor event at line ' + str(record_line))
            return cursor_event(obj, p)
        if (not isinstance(obj, dict) or not isinstance(obj.get('type'), str)
                or 'messages' in obj or 'mapping' in obj):
            raise Invalid('ambiguous native event at line ' + str(record_line))
        if fmt == 'claude_code':
            sid = obj.get('sessionId')
            if sid is not None and sid != session:
                raise Invalid('mismatching native session identity at line ' + str(record_line))
            if 'payload' in obj or ('message' in obj and not isinstance(obj['message'], dict)):
                raise Invalid('ambiguous Claude event at line ' + str(record_line))
        else:
            if not isinstance(obj.get('payload'), dict) or 'timestamp' not in obj or 'sessionId' in obj:
                raise Invalid('ambiguous Codex event at line ' + str(record_line))
            if obj['type'] == 'session_meta' and obj['payload'].get('id') != session:
                raise Invalid('mismatching native session identity at line ' + str(record_line))
        return process_record(raw, '.jsonl', None, str(loc['owner_id']), loc.get('branch'), fmt, session, p,
                              pairing_index.get(record_offset))

    prefix_bytes, prefix_records = 0, 0
    with p.open('rb') as f:
        # Validate both the byte boundary and displayed line number, even for supplied tokens.
        if offset:
            f.seek(offset - 1)
            if f.read(1) != b'\n':
                raise Invalid('continuation offset is not a record boundary')
            f.seek(0)
            while prefix_bytes < offset:
                if time.monotonic() - start >= args.max_seconds:
                    raise Invalid('max-seconds reached while validating continuation prefix; increase --max-seconds')
                raw = f.readline(min(args.max_bytes + 1, offset-prefix_bytes))
                if not raw:
                    raise Invalid('source changed while validating continuation')
                prefix_records += 1
                if len(raw) > args.max_bytes:
                    raise Invalid('session prefix record exceeds --max-bytes at line ' + str(prefix_records))
                if raw.strip():
                    parse_event(raw, prefix_records, prefix_bytes)
                prefix_bytes += len(raw)
            if line != prefix_records + 1:
                raise Invalid('continuation line does not match offset')
        elif line != 1:
            raise Invalid('continuation line does not match offset')
        f.seek(offset)
        records, messages, parsed_bytes, output_bytes = [], 0, 0, 0
        examined, reason, next_offset, next_line = 0, None, offset, line
        # Reserve a bounded envelope; enforce the exact serialized limit before printing.
        envelope_bytes = len(json.dumps(binding, ensure_ascii=False).encode()) + 4096
        if args.max_output_bytes < envelope_bytes:
            raise Invalid('--max-output-bytes is too small for session receipt')
        while next_offset < before.st_size:
            if examined >= args.max_records:
                reason = 'max_records'
                break
            if time.monotonic() - start >= args.max_seconds:
                reason = 'max_seconds'
                break
            raw = f.readline(args.max_bytes + 1)
            if not raw:
                raise Invalid('source ended before recorded size')
            examined += 1
            parsed_bytes += len(raw)
            if len(raw) > args.max_bytes:
                raise Invalid('session record exceeds --max-bytes at line ' + str(next_line))
            if raw.strip():
                conv = parse_event(raw, next_line, next_offset)
                entry = dict(conv, locator=locator(p, loc['file_sha256'], next_offset, raw, None,
                                                  loc['owner_id'], loc.get('branch')), line=next_line)
                entry_bytes = len(json.dumps(entry, ensure_ascii=False).encode()) + 2
                if output_bytes + entry_bytes + envelope_bytes > args.max_output_bytes:
                    reason = 'max_output_bytes'
                    break
                records.append(entry)
                output_bytes += entry_bytes
                messages += len(conv['messages'])
            next_offset += len(raw)
            next_line += 1
    after = p.stat()
    if ((before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino)
            or filehash(p) != loc['file_sha256']):
        raise Invalid('source changed during session inspection; discard page')
    complete = next_offset == before.st_size
    result = {'session': binding, 'records': records,
              'review': {'scope': ('Cursor source-file events; all normalized roles; native session identity unverified; no lexical filtering'
                                   if fmt == 'cursor_agent' else 'native session events; all normalized roles; no lexical filtering'),
                         'complete': complete, 'stop_reason': reason,
                         'start_offset': offset, 'next_offset': next_offset,
                         'start_line': line, 'next_line': next_line,
                         'records_examined': examined, 'records_emitted': len(records),
                         'messages_emitted': messages, 'bytes_parsed': parsed_bytes,
                         'resume_prefix_bytes_read': prefix_bytes,
                         'resume_prefix_records_validated': prefix_records,
                         'source_bytes_hashed': before.st_size * 3,
                         'elapsed_seconds': time.monotonic()-start,
                         'peak_rss_kib_linux': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},
              'continuation': None if complete else dict(binding, offset=next_offset, line=next_line)}
    encoded = json.dumps(result, ensure_ascii=False)
    if len(encoded.encode()) + 1 > args.max_output_bytes:
        raise Invalid('session receipt exceeds --max-output-bytes; increase limit')
    print(encoded)
    return 0 if complete else 1

def _native_session_identity(f, fmt, max_bytes):
    session = None
    for _ in range(DETECT_LINES):
        raw = f.readline(max_bytes + 1)
        if not raw:
            break
        if len(raw) > max_bytes:
            raise Invalid('session detection record exceeds --max-bytes')
        if not raw.strip():
            continue
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise Invalid('session event must be an object')
        sid = (obj.get('sessionId') if fmt == 'claude_code' else
               (obj.get('payload') or {}).get('id') if obj.get('type') == 'session_meta' else None)
        if sid is not None:
            if not isinstance(sid, str) or not sid:
                raise Invalid('invalid native session identity')
            if session is not None and sid != session:
                raise Invalid('ambiguous native session identity')
            session = sid
    return session

def inspect(args):
    start = time.monotonic()
    if args.session_context and (args.review_turns or args.message is not None or args.message_id is not None or args.text_sha256):
        raise Invalid('--session-context cannot be combined with --review-turns, --message, --message-id or --text-sha256')
    if args.resume and not args.session_context:
        raise Invalid('--resume requires --session-context')
    if args.review_turns and (args.message is not None or args.message_id is not None or args.text_sha256):
        raise Invalid('--review-turns cannot be combined with --message, --message-id or --text-sha256')
    if args.message is not None and args.message_id is not None:
        raise Invalid('--message and --message-id cannot be combined')
    spec = json.loads(bounded_read(Path(args.citation), args.max_bytes))
    if not isinstance(spec, dict):
        raise Invalid('citation must be an object')
    loc = spec.get('locator', spec)
    conv = materialize(loc, args.max_bytes, args.max_source_bytes)
    if args.message_id is not None:
        matches = [i for i, m in enumerate(conv['messages'])
                   if m.get('id') is not None and str(m['id']) == args.message_id]
        if not matches:
            raise Invalid('message ID not found in this conversation')
        if len(matches) != 1:
            raise Invalid('message ID is ambiguous in this conversation; use --message with an ordinal')
        args.message = matches[0]
    if 'message' in spec:
        expected = spec['message']
        idx = expected['index']
        if type(idx) is not int or not 0 <= idx < len(conv['messages']):
            raise Invalid('citation message index invalid')
        actual = conv['messages'][idx]
        if any(expected.get(k) != actual[k] for k in ['id','text','text_sha256']):
            raise Invalid('citation message ID/text/digest mismatch')
        if 'mapping_node_id' in expected and expected['mapping_node_id'] != actual['mapping_node_id']:
            raise Invalid('citation mapping node ID mismatch')
        if args.message is None and not args.review_turns and not args.session_context:
            args.message = idx
    if args.session_context:
        return session_context(args, loc, conv, start)
    result = dict(conv)
    if args.review_turns:
        selected = set()
        roles = {'owner', 'nominal_owner', 'host_answer_candidate', 'unattributed_discord'}
        for idx, m in enumerate(conv['messages']):
            if m['role'] in roles or 'forwarded_message' in m:
                selected.update(range(max(0, idx-args.neighbors), min(len(conv['messages']), idx+args.neighbors+1)))
        result['messages'] = [conv['messages'][idx] for idx in sorted(selected)]
        result['review'] = {'total_messages': len(conv['messages']),
                            'selected_turns': sum(m['role'] in roles or 'forwarded_message' in m for m in conv['messages']),
                            'materialized_messages': len(selected),
                            'scope': 'owner-role, unattributed Discord, host-answer and forwarded-message candidates plus neighbors in this record; no lexical gate; attribution and full context require review'}
    elif args.message is not None:
        if not 0 <= args.message < len(conv['messages']):
            raise Invalid('message index out of range')
        m = conv['messages'][args.message]
        if args.text_sha256 and m['text_sha256'] != args.text_sha256:
            raise Invalid('message text digest mismatch')
        result['messages'] = conv['messages'][max(0,args.message-args.neighbors):args.message+args.neighbors+1]
    elif args.text_sha256:
        raise Invalid('--text-sha256 requires --message')
    result['locator'] = loc
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

def discover_metadata_hints(value, pointer='', depth=0):
    if depth > 3 or not isinstance(value, dict):
        return []
    hints = []
    for key in ('cwd', 'working_directory', 'project_path', 'repository', 'repo_url',
                'project_name', 'project', 'title', 'name'):
        text = value.get(key)
        if isinstance(text, str) and text.strip():
            hints.append((key, text.strip(), pointer + '/' + key))
    for key in ('payload', 'metadata', 'session_meta', 'project', 'repository'):
        if isinstance(value.get(key), dict):
            hints.extend(discover_metadata_hints(value[key], pointer + '/' + key, depth + 1))
    return hints

def discovery_defaults():
    home = Path.home()
    context = [Path.cwd() / name for name in ('README.md', 'AGENTS.md', 'CLAUDE.md', 'package.json')]
    memory = [home / '.codex/memories/MEMORY.md', home / '.codex/memories/memory_summary.md']
    sessions = [home / name for name in ('.codex/sessions', '.claude/projects', '.cursor/projects')]
    configured_archive = os.environ.get('THOUGHT_RECONSTRUCTION_ARCHIVE')
    archive = [Path(configured_archive).expanduser() / 'archive/originals'] if configured_archive else []
    return [str(path) for path in context + memory + sessions + archive if path.exists()]

def validate_discovery_position(resumed, path, raw, source_hash):
    if not resumed or str(path) != resumed['path']:
        return
    recorded_hash = resumed.get('file_sha256')
    record_index = resumed['record_index']
    hint_index = resumed['hint_index']
    if recorded_hash is None:
        if record_index or hint_index:
            raise Invalid('unhashed discovery continuation must be unstarted; start a fresh discovery')
        return
    if not isinstance(recorded_hash, str) or not re.fullmatch(r'[0-9a-f]{64}', recorded_hash):
        raise Invalid('invalid discovery source hash; start a fresh discovery')
    if recorded_hash != source_hash:
        raise Invalid('resumed source changed; start a fresh discovery')
    suffix = path.suffix.lower()
    if suffix in ('.md', '.markdown'):
        records = raw.decode('utf-8').splitlines()
    elif suffix == '.jsonl':
        records = raw.splitlines(keepends=True)
    else:
        value = json.loads(raw)
        records = value if isinstance(value, list) else [value]
    if record_index >= len(records):
        raise Invalid('discovery record position is outside the source; start a fresh discovery')
    if not hint_index:
        return
    record = records[record_index]
    if suffix in ('.md', '.markdown'):
        heading = re.match(r'^#{1,3}\s+(?:Task Group:\s*)?(.+?)\s*#*$', record)
        hint_count = int(bool(heading)) + len(re.findall(r'\bcwd=([^\s,;]+)', record))
    else:
        try:
            value = json.loads(record) if suffix == '.jsonl' else record
            hint_count = len(discover_metadata_hints(value))
        except (ValueError, UnicodeError, RecursionError) as ex:
            raise Invalid('discovery hint position cannot be verified; start a fresh discovery') from ex
    if hint_index > hint_count:
        raise Invalid('discovery hint position is outside the record; start a fresh discovery')

def discover(args):
    resumed = None
    if args.resume:
        receipt = json.loads(bounded_read(Path(args.resume).expanduser(), 8 * 1024 * 1024))
        resumed = receipt.get('continuation')
        if not isinstance(resumed, dict) or resumed.get('version') != 1:
            raise Invalid('discovery resume receipt has no supported continuation')
        if args.root and args.root != resumed.get('roots'):
            raise Invalid('discovery resume roots differ from the recorded roots')
        if not isinstance(resumed.get('path'), str) or any(type(resumed.get(key)) is not int or resumed[key] < 0 for key in ('record_index', 'hint_index')):
            raise Invalid('invalid discovery continuation position')
    roots = resumed['roots'] if resumed else (args.root or discovery_defaults())
    if not roots:
        raise Invalid('no default context or memory sources found; use --root for another local source')
    destination = args.out or str(Path.home() / '.cache/thought-reconstruction/discovery' / (str(time.time_ns()) + '-' + str(os.getpid())))
    out = Path(destination).expanduser().resolve(strict=False)
    configured_archive = os.environ.get('THOUGHT_RECONSTRUCTION_ARCHIVE')
    archive = Path(configured_archive).expanduser().resolve(strict=False) if configured_archive else None
    if archive and (out == archive or archive in out.parents):
        raise Invalid('discovery output must be outside the original archive')
    for root in roots:
        source = Path(root).expanduser().resolve(strict=False)
        if out == source or source.is_dir() and source in out.parents:
            raise Invalid('discovery output must be outside input roots')
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    started = time.monotonic()
    counts = collections.Counter()
    omissions = collections.Counter()
    candidate_ids = set()
    position = dict(resumed) if resumed else {'version': 1, 'roots': roots, 'path': None, 'file_sha256': None, 'record_index': 0, 'hint_index': 0}
    resume_found = not resumed
    resume_validated = not resumed
    continuation = None
    def check_deadline():
        if time.monotonic() - started >= args.max_seconds:
            raise Invalid('discovery time bound reached')
    with (out / 'candidates.jsonl').open('w', encoding='utf-8') as candidates, \
         (out / 'sources.jsonl').open('w', encoding='utf-8') as sources, \
         (out / 'errors.jsonl').open('w', encoding='utf-8') as errors:
        def record_error(path, reason, location=None):
            counts['errors'] += 1
            lineout(errors, {'path': str(path), 'reason': reason, 'location': location})
        def emit_hint(kind, value, source, location, source_role):
            hint_index = position['hint_index']
            if resumed and position['path'] == resumed['path'] and position['record_index'] == resumed['record_index'] and hint_index < resumed['hint_index']:
                position['hint_index'] += 1
                return
            check_deadline()
            if len(value) > 1000:
                omissions['oversize_identity_hint'] += 1
                record_error(source['path'], 'identity hint exceeds 1000 characters', location)
                position['hint_index'] += 1
                return
            if counts['candidate_occurrences'] >= args.max_candidates:
                raise Invalid('candidate bound reached; remaining metadata unexamined')
            identity = digest((kind + '\0' + value.casefold()).encode())
            candidate_ids.add(identity)
            lineout(candidates, {'candidate_id': identity, 'identity_hint': value, 'hint_kind': kind,
                    'source': source, 'location': location, 'source_role': source_role,
                    'status': 'requires_agent_interpretation',
                    'attribution': 'metadata_or_document_hint_owner_authorship_unverified',
                    'ambiguities': ['may name a task, document, repository, example or unrelated project',
                                    'copied context and memory lists do not establish conversation subject or owner adoption'],
                    'next_action': 'inspect original context, resolve aliases and scope, then author a cohesive source-linked design'})
            counts['candidate_occurrences'] += 1
            position['hint_index'] += 1
        try:
            for path, status, reason in enumerate_inputs(roots, sys.maxsize):
                if not resume_found:
                    check_deadline()
                    if str(path) != resumed['path']:
                        counts['prefix_entries_examined'] += 1
                        continue
                    resume_found = True
                if resume_validated:
                    position.update(path=str(path), file_sha256=None, record_index=0, hint_index=0)
                if counts['entries_examined'] >= args.max_files:
                    raise Invalid('file enumeration bound reached; remaining sources unexamined')
                counts['entries_examined'] += 1
                check_deadline()
                if status:
                    omissions[status] += 1
                    lineout(sources, {'path': str(path), 'status': status, 'reason': reason})
                    if not resume_validated:
                        raise Invalid('resumed source unavailable; metadata unexamined')
                    continue
                if path.suffix.lower() not in SUFFIXES:
                    omissions['unsupported_format'] += 1
                    lineout(sources, {'path': str(path), 'status': 'unsupported_format'})
                    if not resume_validated:
                        raise Invalid('resumed source format unsupported; metadata unexamined')
                    continue
                counts['files_attempted'] += 1
                try:
                    size = path.stat().st_size
                    if size > args.max_file_bytes:
                        raise Invalid('file exceeds max-file-bytes; metadata unexamined')
                    if counts['bytes_read'] + size > args.max_total_bytes:
                        raise Invalid('total byte bound reached; remaining sources unexamined')
                    raw = bounded_read(path, args.max_file_bytes)
                    counts['bytes_read'] += len(raw)
                    source = {'path': str(path), 'file_sha256': digest(raw)}
                    validate_discovery_position(resumed, path, raw, source['file_sha256'])
                    position['file_sha256'] = source['file_sha256']
                    resume_validated = True
                    suffix = path.suffix.lower()
                    if suffix in ('.md', '.markdown'):
                        text = raw.decode('utf-8')
                        for lineno, line in enumerate(text.splitlines(), 1):
                            if resumed and str(path) == resumed['path'] and lineno - 1 < resumed['record_index']:
                                continue
                            position.update(record_index=lineno - 1, hint_index=0)
                            check_deadline()
                            heading = re.match(r'^#{1,3}\s+(?:Task Group:\s*)?(.+?)\s*#*$', line)
                            if heading:
                                emit_hint('document_heading', heading.group(1), source, {'line': lineno}, 'document_authorship_unverified')
                            for match in re.finditer(r'\bcwd=([^\s,;]+)', line):
                                emit_hint('cwd', match.group(1), source, {'line': lineno}, 'document_authorship_unverified')
                    elif suffix == '.jsonl':
                        offset = 0
                        for lineno, record in enumerate(raw.splitlines(keepends=True), 1):
                            record_offset = offset
                            offset += len(record)
                            if resumed and str(path) == resumed['path'] and lineno - 1 < resumed['record_index']:
                                continue
                            position.update(record_index=lineno - 1, hint_index=0)
                            check_deadline()
                            if counts['records_examined'] >= args.max_records:
                                raise Invalid('record bound reached; remaining records unexamined')
                            counts['records_examined'] += 1
                            location = {'line': lineno, 'offset': record_offset, 'length': len(record), 'record_sha256': digest(record)}
                            if len(record) > args.max_record_bytes:
                                omissions['oversize_record'] += 1
                                record_error(path, 'record exceeds max-record-bytes', location)
                                continue
                            if not record.strip():
                                continue
                            try:
                                obj = json.loads(record)
                            except (ValueError, UnicodeError) as ex:
                                record_error(path, 'record parse failed: ' + str(ex), location)
                                continue
                            role = obj.get('role', obj.get('type', 'unknown')) if isinstance(obj, dict) else 'unknown'
                            for kind, value, pointer in discover_metadata_hints(obj):
                                emit_hint(kind, value, source, dict(location, json_pointer=pointer), role)
                    else:
                        value = json.loads(raw)
                        array = isinstance(value, list)
                        records = value if array else [value]
                        for index, obj in enumerate(records):
                            if resumed and str(path) == resumed['path'] and index < resumed['record_index']:
                                continue
                            position.update(record_index=index, hint_index=0)
                            check_deadline()
                            if counts['records_examined'] >= args.max_records:
                                raise Invalid('record bound reached; remaining records unexamined')
                            counts['records_examined'] += 1
                            for kind, value, pointer in discover_metadata_hints(obj):
                                emit_hint(kind, value, source, {'json_pointer': ('/' + str(index) if array else '') + pointer}, 'metadata_authorship_unverified')
                    counts['files_processed'] += 1
                    lineout(sources, dict(source, status='metadata_examined', semantic_review='not_performed'))
                except (OSError, ValueError, UnicodeError, RecursionError) as ex:
                    record_error(path, str(ex))
                    omissions['file_processing_incomplete'] += 1
                    if not resume_validated or 'bound reached' in str(ex) or 'fresh discovery' in str(ex):
                        raise
            if not resume_found:
                raise Invalid('resume path no longer enumerates; start a fresh discovery')
        except (OSError, ValueError, RecursionError) as ex:
            record_error('', str(ex))
            omissions['enumeration_or_processing_incomplete'] += 1
            if 'fresh discovery' not in str(ex):
                continuation = dict(resumed) if not resume_found and resumed else (dict(position) if position['path'] else None)
    run = {'version': VERSION, 'roots': roots, 'source_selection': 'resumed' if resumed else ('explicit' if args.root else 'automatic_local_context_memory_and_session_metadata'),
           'bounds': dict({key: value for key, value in vars(args).items() if key.startswith('max_')}, max_metadata_value_characters=1000, metadata_nested_depth=3),
           'counts': dict(counts), 'distinct_candidate_keys': len(candidate_ids), 'omissions': dict(omissions),
           'continuation': continuation,
           'complete_within_requested_metadata_scope': not counts['errors'] and not omissions,
           'limitations': ['metadata hints require original-context review and identity resolution',
                           'default roots cover selected local host surfaces and archive originals under explicit bounds',
                           'headings and metadata omit concepts expressed only in message prose',
                           'resume validates its active file hash; new or moved earlier paths require a fresh scan',
                           'no repository or design document is created automatically from uncurated candidates']}
    dump(out / 'run.json', run)
    print(json.dumps({'out': str(out), 'counts': dict(counts), 'distinct_candidate_keys': len(candidate_ids), 'omissions': dict(omissions)}))
    return 1 if counts['errors'] or omissions else 0

DESIGN_SECTIONS = {
    'problem': 'Problem and motivation',
    'outcomes': 'Desired outcomes',
    'requirements': 'Requirements and constraints',
    'behavior': 'User experience and workflow',
    'interfaces': 'Inputs, outputs and interfaces',
    'architecture': 'Provisional architecture',
    'evaluation': 'Acceptance and evaluation',
}

def validate_scope_contract(ledger, claims, evidence):
    contract = ledger.get('scope_contract')
    if contract is None:
        if 'scope_dispositions' in ledger:
            raise Invalid('scope decisions require scope_contract')
        return None
    if not isinstance(contract, dict) or type(contract.get('version', 1)) is not int or contract.get('version', 1) != 1:
        raise Invalid('scope_contract must be a supported version 1 object')
    for key in ('project_id', 'purpose'):
        if not isinstance(contract.get(key), str) or not contract[key].strip():
            raise Invalid('scope_contract requires nonempty ' + key)
    def entries(name, required):
        items = contract.get(name)
        if not isinstance(items, list) or required and not items:
            raise Invalid('scope_contract requires ' + name + ' array')
        result = set()
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'].strip() or item['id'] in result:
                raise Invalid('scope_contract ' + name + ' IDs must be unique nonempty strings')
            if not isinstance(item.get('text'), str) or not item['text'].strip():
                raise Invalid('scope_contract ' + name + ' text must be nonempty')
            result.add(item['id'])
        return result
    criteria = entries('criteria', True)
    exclusions = entries('exclusions', False)
    def decision(value, label):
        if not isinstance(value, dict) or value.get('disposition') not in ('include', 'adjacent', 'exclude', 'unresolved'):
            raise Invalid('scope decision requires supported disposition: ' + label)
        if not isinstance(value.get('relation'), str) or not value['relation'].strip():
            raise Invalid('scope decision requires authored project relation/reason: ' + label)
        for key, allowed in (('criterion_ids', criteria), ('exclusion_ids', exclusions)):
            refs = value.get(key, [])
            if not isinstance(refs, list) or any(not isinstance(ref, str) or ref not in allowed for ref in refs) or len(set(refs)) != len(refs):
                raise Invalid('scope decision has invalid ' + key + ': ' + label)
        if value['disposition'] == 'include' and not value.get('criterion_ids'):
            raise Invalid('included scope decision requires criterion_ids: ' + label)
    rows = ledger.get('scope_dispositions')
    if not isinstance(rows, list) or len(rows) != len(evidence):
        raise Invalid('scope_dispositions must map every evidence ID exactly once')
    evidence_scope = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('evidence_id'), str) or row['evidence_id'] not in evidence or row['evidence_id'] in evidence_scope:
            raise Invalid('scope_dispositions has unknown or repeated evidence ID')
        decision(row, row['evidence_id'])
        evidence_scope[row['evidence_id']] = row
    for claim in claims:
        decision(claim.get('scope'), claim['id'])
        if claim['scope']['disposition'] == 'include' and any(evidence_scope[eid]['disposition'] != 'include' for eid in claim['evidence_ids']):
            raise Invalid('included claim references evidence outside included scope: ' + claim['id'])
    return {'contract': contract, 'evidence': evidence_scope,
            'claim_counts': dict(collections.Counter(claim['scope']['disposition'] for claim in claims)),
            'evidence_counts': dict(collections.Counter(row['disposition'] for row in rows)),
            'validation': 'authored decision structure and reference consistency only; semantic relevance and entailment require agent review'}

def render_scope_review(scope, claims, evidence):
    lines = ['# Project scope review', '', scope['contract']['purpose'], '',
             'This ledger records authored scope judgments over the supplied claims and passages. '
             'The counts cover this ledger. Archive-wide coverage and semantic correctness remain subject to source review.', '',
             'Claim dispositions ' + json.dumps(scope['claim_counts'], sort_keys=True) + '.', '',
             'Evidence dispositions ' + json.dumps(scope['evidence_counts'], sort_keys=True) + '.', '']
    for disposition in ('include', 'adjacent', 'exclude', 'unresolved'):
        lines += ['## ' + disposition.capitalize(), '']
        for claim in claims:
            value = claim['scope']
            if value['disposition'] == disposition:
                lines += ['### Claim ' + claim['id'], '', claim['text'], '',
                          'Authored relation ' + value['relation'], '',
                          'Evidence IDs ' + ', '.join(claim['evidence_ids']) + '.', '',
                          'Criteria ' + ', '.join(value.get('criterion_ids', [])) + '. Exclusions '
                          + ', '.join(value.get('exclusion_ids', [])) + '.', '']
        for eid, value in scope['evidence'].items():
            if value['disposition'] == disposition:
                item = evidence[eid]
                path = urlquote(item['locator']['path'], safe='/')
                lines += ['- Passage [' + eid + '](' + path + '), message ' + str(item['message_index'])
                          + ', role ' + item['verified_role'] + '. ' + value['relation']
                          + ' Criteria ' + ', '.join(value.get('criterion_ids', [])) + '. Exclusions '
                          + ', '.join(value.get('exclusion_ids', [])) + '.', '']
    return '\n'.join(lines)

def render_user_account(ledger, evidence):
    lines = ['# ' + str(ledger.get('title', 'Recovered idea')), '']
    sections = ledger.get('account_sections')
    if sections is None:
        lines += ['Source excerpts awaiting contextual selection and combination.', '']
        for eid, item in evidence.items():
            path = urlquote(item['locator']['path'], safe='/')
            lines += ['## ' + eid, '', 'Recorded role ' + item['verified_role'] + '. '
                      + item['attribution'] + '. [' + eid + '](' + path + ')', '',
                      *['> ' + line for line in item['quote'].splitlines()], '']
        return '\n'.join(lines)
    if not isinstance(sections, list) or not sections:
        raise Invalid('account_sections must be a nonempty list')
    for section in sections:
        if not isinstance(section, dict) or not isinstance(section.get('passages'), list) or not section['passages']:
            raise Invalid('each account section requires selected passages')
        heading = section.get('heading')
        if heading is not None:
            if not isinstance(heading, str) or not heading.strip() or '\n' in heading:
                raise Invalid('account heading must be a nonempty single line')
            lines += ['## ' + heading, '']
        for passage in section['passages']:
            if not isinstance(passage, dict):
                raise Invalid('account passage must be an object')
            eid = passage.get('evidence_id')
            if not isinstance(eid, str) or eid not in evidence:
                raise Invalid('account passage requires included evidence')
            wording = passage.get('text')
            if not isinstance(wording, str) or not wording or wording not in evidence[eid]['quote']:
                raise Invalid('account passage wording must be an exact span of its verified quotation')
            kind = passage.get('kind', 'owner_words')
            if kind == 'owner_words':
                if evidence[eid]['verified_role'] not in ('owner', 'nominal_owner'):
                    raise Invalid('owner wording requires an owner-role source with contextual authorship review')
                review = passage.get('authorship_review')
                if not isinstance(review, str) or not review.strip():
                    raise Invalid('owner wording requires an authored contextual authorship_review')
            elif kind != 'supporting_context':
                raise Invalid('account passage kind must be owner_words or supporting_context')
            prefix = 'Supporting context\n\n' if kind == 'supporting_context' else ''
            path = urlquote(evidence[eid]['locator']['path'], safe='/')
            lines += [prefix + wording + ' [' + eid + '](' + path + ')', '']
    return '\n'.join(lines)


def render_project_design(ledger, claims, evidence, scope=None):
    representation = ledger.get('representation', 'user_account')
    if representation == 'user_account':
        return render_user_account(ledger, evidence)
    if representation != 'implementation_design':
        raise Invalid('representation must be user_account or implementation_design')
    groups = collections.defaultdict(list)
    for claim in claims:
        target = claim.get('design_section')
        if target is not None and target not in DESIGN_SECTIONS:
            raise Invalid('unsupported design_section: ' + str(target))
        if claim['section'] in ('uncertainties', 'contradictions', 'hypotheses'):
            target = claim['section']
        groups[target or claim['section']].append(claim)
    lines = ['# ' + str(ledger.get('title', 'Project')) + ' — project design specification', '',
             'Working document assembled from externally curated claims. Missing sections remain explicit. '
             'An agent must review cohesion, meaning, omissions and attribution before treating this as a finished design.', '']
    if scope:
        lines += ['## Authored project scope', '', scope['contract']['purpose'], '']
        lines += ['- ' + item['id'] + ' — ' + item['text'] for item in scope['contract']['criteria']]
        lines += ['', 'Scope exclusions', '']
        lines += ['- ' + item['id'] + ' — ' + item['text'] for item in scope['contract']['exclusions']]
        lines += ['', 'Disposition counts ' + json.dumps(scope['claim_counts'], sort_keys=True)
                  + '. [Scope review](scope-review.md) retains adjacent, excluded and unresolved claims and passage mappings.', '']
    headings = [('core', 'Recovered core'), *DESIGN_SECTIONS.items(),
                ('details', 'Additional recovered detail'), ('uncertainties', 'Open questions and gaps'),
                ('contradictions', 'Unresolved conflicts'), ('hypotheses', 'Implementation hypotheses')]
    for key, title in headings:
        lines += ['## ' + title, '']
        if not groups[key]:
            lines += ['The curated ledger supplies no claims for this section. Further synthesis or source review is required.', '']
        for claim in groups[key]:
            refs = ' '.join('[' + eid + '](' + urlquote(evidence[eid]['locator']['path'], safe='/') + ')' for eid in claim['evidence_ids'])
            lines += ['[' + claim['kind'] + '] ' + claim['text'] + ' ' + refs, '']
            if scope:
                lines += ['Project relation ' + claim['scope']['relation'] + ' Criteria '
                          + ', '.join(claim['scope']['criterion_ids']) + '.', '']
    lines += ['## Source access and verification', '',
              'The companion verified-ledger.json retains exact source locators and quotes. '
              'Source correspondence was checked during assembly. Claim support, owner adoption, '
              'current implementation and comprehensive coverage require separate review.', '']
    for eid, item in evidence.items():
        path = urlquote(item['locator']['path'], safe='/')
        lines += ['- [' + eid + '](' + path + ') — message ' + str(item['message_index'])
                  + ', role ' + item['verified_role'] + ', attribution ' + item['attribution'] + '.', '']
    return '\n'.join(lines)

def assemble(args):
    ledger = json.loads(bounded_read(Path(args.ledger), args.max_bytes))
    if not isinstance(ledger, dict) or not isinstance(ledger.get('evidence'), list) or not isinstance(ledger.get('claims'), list):
        raise Invalid('ledger requires evidence and claims arrays')
    if len(ledger['evidence']) > args.max_evidence or len(ledger['claims']) > args.max_evidence:
        raise Invalid('ledger evidence/claims exceed --max-evidence')
    evidence, cache = {}, {}
    started = time.monotonic()
    for e in ledger['evidence']:
        if time.monotonic() - started > args.max_seconds:
            raise Invalid('assembly max-seconds exceeded')
        if not isinstance(e, dict):
            raise Invalid('evidence must be an object')
        eid = e.get('id')
        if not isinstance(eid, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]+', eid) or eid in evidence:
            raise Invalid('evidence IDs must be unique simple nonempty strings')
        loc = e['locator']; key = json.dumps(loc, sort_keys=True)
        if key not in cache:
            if len(cache) >= args.max_sources:
                raise Invalid('assembly --max-sources exceeded')
            if Path(loc['path']).stat().st_size > args.max_source_bytes:
                raise Invalid('assembly --max-source-bytes exceeded')
            cache[key] = materialize(loc, args.max_bytes, args.max_source_bytes)
        conv = cache[key]; idx = e['message_index']
        if type(idx) is not int or not 0 <= idx < len(conv['messages']):
            raise Invalid('evidence message index invalid: ' + eid)
        m = conv['messages'][idx]
        if 'message_id' not in e or e['message_id'] != m['id']:
            raise Invalid('evidence message ID mismatch: ' + eid)
        if 'mapping_node_id' in e and e['mapping_node_id'] != m['mapping_node_id']:
            raise Invalid('evidence mapping node ID mismatch: ' + eid)
        part = e.get('text_part', 'message')
        if part == 'message':
            evidence_text, evidence_hash = m['text'], m['text_sha256']
            verified_role, attribution = m['role'], m['attribution']
        elif part == 'forwarded_message' and isinstance(m.get('forwarded_message'), dict):
            evidence_text = m['forwarded_message']['text']
            evidence_hash = m['forwarded_message']['text_sha256']
            verified_role, attribution = 'unknown', m['forwarded_message']['attribution']
        else:
            raise Invalid('unknown or unavailable evidence text part: ' + eid)
        if e.get('text_sha256') != evidence_hash:
            raise Invalid('evidence message text digest mismatch: ' + eid)
        quote = e.get('quote')
        if not isinstance(quote, str) or not quote or quote not in evidence_text:
            raise Invalid('exact quote missing or mismatched: ' + eid)
        evidence[eid] = dict(e, mapping_node_id=m['mapping_node_id'], verified_role=verified_role, source_role=m['source_role'] if part == 'message' else 'unknown', author_id=m['author_id'] if part == 'message' else None, author_name=m['author_name'] if part == 'message' else None, time_fields=m['time_fields'] if part == 'message' else {}, attribution=attribution, indicators=m['indicators'], conversation_id=conv['id'], source_metadata=conv.get('source_metadata'))
    kinds = {'stated', 'inferred', 'reported', 'hypothesis'}
    sections = {'core','details','uncertainties','contradictions','hypotheses'}
    seen, claims = set(), []
    for c in ledger['claims']:
        if not isinstance(c, dict):
            raise Invalid('claim must be an object')
        cid = c.get('id')
        if not isinstance(cid,str) or not cid or cid in seen:
            raise Invalid('claim IDs must be unique nonempty strings')
        seen.add(cid)
        if c.get('kind') not in kinds or c.get('section') not in sections:
            raise Invalid('invalid claim kind or section: ' + cid)
        if c['section'] == 'hypotheses' and c['kind'] != 'hypothesis' or c['kind'] == 'hypothesis' and c['section'] != 'hypotheses':
            raise Invalid('hypothesis claims must be in hypotheses section')
        if not isinstance(c.get('text'),str) or not c['text'].strip():
            raise Invalid('claim text required')
        refs = c.get('evidence_ids')
        if not isinstance(refs,list) or not refs or any(not isinstance(r,str) or r not in evidence for r in refs):
            raise Invalid('claim requires existing evidence IDs: ' + cid)
        if 'confidence' in c:
            raise Invalid('confidence field unsupported; use authored uncertainty claims')
        if 'design_section' in c and (not isinstance(c['design_section'], str) or c['design_section'] not in DESIGN_SECTIONS):
            raise Invalid('unsupported design_section: ' + str(c['design_section']))
        claims.append(c)
    if not any(c['section'] == 'core' for c in claims):
        raise Invalid('ledger needs at least one authored core claim')
    scope = validate_scope_contract(ledger, claims, evidence)
    included_claims = [claim for claim in claims if not scope or claim['scope']['disposition'] == 'include']
    included_ids = {eid for claim in included_claims for eid in claim['evidence_ids']}
    included_evidence = {eid: item for eid, item in evidence.items() if not scope or eid in included_ids}
    out = Path(args.out).expanduser().resolve(strict=False)
    lines = ['# ' + str(ledger.get('title','Thought reconstruction')), '',
             'Authored synthesis with verified source quotes. Quote verification does not establish semantic truth or owner authorship.', '']
    if scope:
        lines += ['Project scope ' + scope['contract']['purpose'], '',
                  'Authored claim dispositions ' + json.dumps(scope['claim_counts'], sort_keys=True)
                  + '. [Scope review](scope-review.md) retains all decisions.', '']
        if not included_claims:
            lines += ['No claims are currently included in the authored project scope. Review the unresolved decisions before developing this account.', '']
    for section in ['core','details','uncertainties','contradictions','hypotheses']:
        lines += ['## '+section.capitalize(), '']
        for c in included_claims:
            if c['section'] == section:
                lines += ['- ['+c['kind']+'] '+c['text']+' ('+', '.join(c['evidence_ids'])+')', '']
                if scope:
                    lines += ['Project relation ' + c['scope']['relation'] + ' Criteria '
                              + ', '.join(c['scope']['criterion_ids']) + '.', '']
    lines += ['## Provenance', '']
    for eid,e in included_evidence.items():
        lines += ['### '+eid, '', '`'+e['locator']['path']+'` — message index '+str(e['message_index'])+', ID '+str(e['message_id'])+', role '+e['verified_role']+'; '+e['attribution']+'.', '',
                  'Recorded role: '+str(e['source_role'])+'; author: '+str(e['author_name'])+' ('+str(e['author_id'])+').', '',
                  *(['Mapping node ID: `'+str(e['mapping_node_id'])+'`.', ''] if e['mapping_node_id'] is not None else []),
                  *(['Recorded source time fields: `'+json.dumps(e['time_fields'],ensure_ascii=False)+'`.', ''] if e['time_fields'] else []),
                  *['> '+s for s in e['quote'].splitlines()], '', 'Source SHA-256: `'+e['locator']['file_sha256']+'`; message text SHA-256: `'+e['text_sha256']+'`.', '']
    rendered = '\n'.join(lines)
    design = render_project_design(ledger, included_claims, included_evidence, scope)
    scope_review = render_scope_review(scope, claims, evidence) if scope else None
    verified = {'ledger': ledger, 'verified_evidence': evidence, 'validation': 'exact source/message/quote verification only; claim interpretation authored externally', 'version': VERSION}
    if scope:
        verified['scope_validation'] = scope
    verified_json = json.dumps(verified, ensure_ascii=False, indent=2) + '\n'
    rendered_bytes = rendered.encode('utf-8')
    verified_bytes = verified_json.encode('utf-8')
    out.mkdir(parents=True, exist_ok=False)
    (out/'reconstruction.md').write_bytes(rendered_bytes)
    (out/'verified-ledger.json').write_bytes(verified_bytes)
    (out/'PROJECT-DESIGN-SPEC.md').write_text(design, encoding='utf-8')
    if scope_review is not None:
        (out/'scope-review.md').write_text(scope_review, encoding='utf-8')
    print(json.dumps({'out':str(out),'claims':len(claims),'included_claims':len(included_claims),'verified_evidence':len(evidence),
                      **({'scope_claim_counts':scope['claim_counts']} if scope else {})}))
    return 0

def positive(value):
    n = int(value)
    if n <= 0:
        raise argparse.ArgumentTypeError('must be positive')
    return n

def nonnegative(value):
    n = int(value)
    if n < 0:
        raise argparse.ArgumentTypeError('must be nonnegative')
    return n

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', action='version', version=VERSION)
    sub = p.add_subparsers(dest='command', required=True)
    d = sub.add_parser('discover', help='discover review-required project hints from local context and metadata without a project name')
    d.add_argument('--root', action='append', help='optional local metadata sources; defaults to current-context documents, memory registry, host session stores and configured archive originals')
    d.add_argument('--resume', help='prior discovery run.json with a source-bound continuation')
    d.add_argument('--out', help='fresh private output directory; defaults to a unique directory under ~/.cache/thought-reconstruction/discovery')
    for name, default in [('max-files',256), ('max-file-bytes',8*1024*1024),
                          ('max-total-bytes',64*1024*1024), ('max-record-bytes',1024*1024),
                          ('max-records',10000), ('max-candidates',1000), ('max-seconds',30)]:
        d.add_argument('--' + name, type=positive, default=default)
    a = sub.add_parser('acquire', help='stream bounded records and collect lexical candidates')
    a.add_argument('--reference', action='append', required=True)
    a.add_argument('--query')
    a.add_argument('--no-roust', action='store_true', help='skip optional Roust file nomination and use the existing scanner')
    a.add_argument('--projection-resume', help='prior roust.json with a continuation for the single explicit JSONL file root')
    a.add_argument('--max-projection-receipt-bytes', type=positive, default=8*1024*1024,
                   help='maximum projection-resume receipt bytes, independent of source max-bytes (default 8 MiB)')
    a.add_argument('--projection-max-text-chars', type=positive, default=8192,
                   help='maximum text characters projected per record (default 8192; subject to total projection byte bound)')
    a.add_argument('--projection-max-source-bytes', type=positive, default=64*1024*1024,
                   help='cumulative JSONL source bytes eligible for temporary projection (default 64 MiB; each file is hashed twice)')
    a.add_argument('--root', action='append', required=True)
    a.add_argument('--out', required=True)
    a.add_argument('--owner-id', default=os.environ.get('THOUGHT_RECONSTRUCTION_OWNER_ID', ''),
                   help='Discord owner ID, defaulting to THOUGHT_RECONSTRUCTION_OWNER_ID; unset authors remain review-required candidates')
    a.add_argument('--branch', help='explicit native ChatGPT mapping end node; otherwise current_node')
    for name,default in [('max-bytes',8*1024*1024),('max-reference-bytes',2*1024*1024),('max-file-bytes',256*1024*1024),('max-total-bytes',1024*1024*1024),('max-files',10000),('max-records',100000),('max-seconds',300),('max-profile-terms',128),('min-signals',2),('max-passages',100)]:
        a.add_argument('--'+name,type=positive,default=default)
    a.add_argument('--neighbors',type=nonnegative,default=1)
    a.add_argument('--negative-sample',type=nonnegative,default=12)
    a.add_argument('--sample-seed',default='thought-reconstruction-v1')
    i = sub.add_parser('inspect', help='verify immutable locator then materialize conversation or message window')
    i.add_argument('--citation',required=True,help='JSON object containing locator, or bare locator')
    i.add_argument('--message',type=nonnegative,help='zero-based message ordinal within the conversation')
    i.add_argument('--message-id',help='exact message ID within the conversation; ambiguous IDs require --message')
    i.add_argument('--review-turns',action='store_true',help='materialize owner-role, unattributed Discord, host-answer and forwarded-message candidates plus neighbors in the verified record, without lexical filtering')
    i.add_argument('--session-context',action='store_true',help='read a bounded all-role native session page; partial pages exit 1 with continuation')
    i.add_argument('--resume',help='previous session page JSON or its continuation object; requires --session-context')
    i.add_argument('--max-records',type=positive,default=200)
    i.add_argument('--max-seconds',type=positive,default=30)
    i.add_argument('--max-output-bytes',type=positive,default=8*1024*1024)
    i.add_argument('--neighbors',type=nonnegative,default=1)
    i.add_argument('--text-sha256')
    i.add_argument('--max-bytes',type=positive,default=8*1024*1024)
    i.add_argument('--max-source-bytes',type=positive,default=256*1024*1024)
    s = sub.add_parser('assemble', help='validate externally curated ledger and render verified synthesis')
    s.add_argument('--ledger',required=True)
    s.add_argument('--out',required=True)
    s.add_argument('--max-bytes',type=positive,default=8*1024*1024)
    s.add_argument('--max-evidence',type=positive,default=1000)
    s.add_argument('--max-sources',type=positive,default=32)
    s.add_argument('--max-source-bytes',type=positive,default=256*1024*1024)
    s.add_argument('--max-seconds',type=positive,default=300)
    args = p.parse_args(argv)
    invocation_start = time.monotonic()
    try:
        return {'discover':discover,'acquire':acquire,'inspect':inspect,'assemble':assemble}[args.command](args)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, RecursionError, AttributeError) as ex:
        print('error: '+str(ex), file=sys.stderr)
        return 1
    finally:
        print(json.dumps({'command': args.command, 'elapsed_seconds': time.monotonic()-invocation_start, 'peak_rss_kib_linux': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}), file=sys.stderr)

if __name__ == '__main__':
    sys.exit(main())
