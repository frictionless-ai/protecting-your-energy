#!/usr/bin/env python3
"""Build and query owner-attributed archive evidence with local ONNX embeddings.

Sources stay read-only. Each build has its own SQLite generation; a shared
append-only content cache reuses vectors. Publication requires every planned
unit to have a vector and every input part to retain its collected hash.
"""
from __future__ import annotations

import argparse
import ast
import collections
import contextlib
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import time
from urllib.parse import quote
import uuid

sys.dont_write_bytecode = True
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'protecting-your-energy'
DATA_ROOT = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share') / 'protecting-your-energy'
_LEGACY = Path.home() / 'brain-data/upar-dip'
_legacy_index = _LEGACY / 'derived/semantic-archive'
_portable_index = DATA_ROOT / 'semantic-archive'
DEFAULT_INDEX = Path(os.environ.get('PYE_SEMANTIC_ARCHIVE_INDEX') or (_portable_index if _portable_index.exists() or not _legacy_index.exists() else _legacy_index)).expanduser()
ENCODER_SCRIPT = Path(os.environ.get('PYE_SEMANTIC_ENCODER') or PACKAGE_ROOT / 'scripts/semantic_retrieve_portable.py').expanduser()
COMMON_SCRIPT = Path(__file__).with_name('common.py')
_legacy_model = _LEGACY / 'derived/protect-your-energy/2026-10-11/deeper-pass/semantic/model-bge-small-en-v1.5'
_portable_model = DATA_ROOT / 'semantic/model-bge-small-en-v1.5'
MODEL = Path(os.environ.get('PYE_SEMANTIC_MODEL') or (_portable_model if _portable_model.exists() or not _legacy_model.exists() else _legacy_model)).expanduser()
_legacy_config = _LEGACY / 'derived/protect-your-energy/config.json'
_portable_config = CONFIG_ROOT / 'config.json'
CONFIG = Path(os.environ.get('PYE_ARCHIVE_ACCESS_CONFIG') or (_portable_config if _portable_config.exists() or not _legacy_config.exists() else _legacy_config)).expanduser()
BLOCKED = ('.sealed', '.sanitized', '.seal-', '.request-only', 'request-only', 'request_only', 'quarantine', 'credentials', '.staging')
MARKERS = ('.sealing-in-progress', '.request-only', 'REQUEST_ONLY', '.sealed')
SCAFFOLD = re.compile(r'MEMORY_SUMMARY BEGINS|<oai-mem-citation>|## Learned User Preferences|<multi_agent_role>|<codex_delegation(?:\s|>)|<environment_context>|<permissions instructions>|<INSTRUCTIONS>|^# AGENTS\.md instructions', re.M)
MACHINE = {'system', 'developer', 'assistant', 'tool', 'function', 'ai', 'machine', 'meta'}
UNCONFIRMED_INPUT_LANES = {'unconfirmed_input', 'unconfirmed_imported_input'}
CONTEXT_DOCUMENT_FAMILIES = {'server_data', 'system_log', 'archive_meta'}
SURROGATE = re.compile(r'[\ud800-\udfff]')
ARCHIVE_SCOPE = 'Accessible canonical owner writing, with separate opt-in lanes for caller-unconfirmed input and source documents whose ownership does not establish personal authorship. Other speakers are hydration context. Restricted data, credentials and instruction scaffolding remain excluded. Unpaired-surrogate documents are non-embeddable; exact canonical JSON and original bytes remain unchanged, with explicit coverage counts. Exact normalized records are authoritative hydration evidence; raw-source availability is not byte confirmation.'
AI = {'agent', 'chatgpt', 'claude', 'claude_code', 'codex', 'cursor', 'copilot', 'gemini', 'grok', 'perplexity', 'deepseek', 'lmstudio', 'openclaw', 'commandcode', 'continue'}
# Only an independently pinned proof can populate this in-memory key. JSON
# source records cannot supply object keys or impersonate verified metadata.
NATIVE_ATTRIBUTION = object()


def native_attribution(record):
    if NATIVE_ATTRIBUTION in record:
        return record[NATIVE_ATTRIBUTION]
    record[NATIVE_ATTRIBUTION] = None
    source = record.get('source') or {}
    extra = record.get('extra') or {}
    ir = extra.get('ir_v2_meta') or extra.get('ir_v1_meta') or {}
    messages = record.get('messages') or []
    if source.get('platform') != 'codex' or ir.get('all_event_types_retained') is not True or not messages:
        return None
    first = ((messages[0].get('extra') or {}).get('raw') or {}).get('codex_event')
    if not isinstance(first, dict) or first.get('type') != 'session_meta':
        return None
    payload = first.get('payload') or {}
    if not isinstance(payload, dict):
        return None
    sid = payload.get('id')
    if not isinstance(sid, str) or not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', sid) or ir.get('session_id') != sid:
        return None
    paths = [source.get('origin_path'), source.get('archive_path')]
    cluster = ir.get('cluster_source') or {}
    if not isinstance(cluster, dict):
        return None
    if cluster:
        paths.append(cluster.get('archive_member'))
    if not all(isinstance(path, str) and path.replace('\\', '/').rsplit('/', 1)[-1].endswith('-' + sid + '.jsonl') for path in paths):
        return None
    headers = [((message.get('extra') or {}).get('raw') or {}).get('codex_event') for message in messages]
    if sum(isinstance(event, dict) and event.get('type') == 'session_meta' for event in headers) != 1:
        return None
    entrypoint = payload.get('source')
    if entrypoint not in ('cli', 'vscode'):
        return None
    # This establishes the retained frame's caller provenance, not availability
    # or byte confirmation of its original raw export.
    proof = {'native_session_id': sid, 'native_source_kind': 'human_cli',
        'native_source_entrypoint': entrypoint, 'native_capture_sha256': None,
        'attribution_basis': 'canonical-retained-own-first-header-and-structural-source-identity'}
    record[NATIVE_ATTRIBUTION] = proof
    return proof


def document_context_reason(record):
    """Export ownership and operational files do not establish personal prose."""
    if record.get('kind') != 'document':
        return None
    source = record.get('source') or {}
    extra = record.get('extra') or {}
    wrapped = extra.get('wrapped_message') or {}
    raw = (wrapped.get('extra') or {}).get('raw') or {}
    ir = extra.get('ir_v2_meta') or extra.get('ir_v1_meta') or {}
    if ir.get('self_labels_verified') is False or any(meta.get('authorship_verified') is False for meta in (raw, ir)):
        return 'explicitly_unverified_document_authorship'
    if source.get('family') in CONTEXT_DOCUMENT_FAMILIES:
        return 'administrative_source_family'
    # An independently reviewed authorship assertion must name its basis;
    # account ownership or an inferred self role alone is insufficient.
    authored = (ir.get('self_labels_verified') is True and isinstance(ir.get('self_label_rule'), str) and bool(ir['self_label_rule'].strip())) or any(meta.get('authorship_verified') is True and isinstance(meta.get('authorship_basis'), str) and meta['authorship_basis'].strip() for meta in (raw, ir))
    if raw.get('whole_file') is True and not authored:
        return 'whole_file_ownership_without_authorship'
    if source.get('platform') == 'filesystem' and wrapped and not authored:
        return 'generic_file_ownership_without_authorship'
    return None


def digest(data):
    return hashlib.sha256(data).hexdigest()


def packed(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def guarded(path):
    p = Path(path).expanduser()
    for value in (p.absolute(), p.resolve()):
        if any(part.lower().startswith(BLOCKED) for part in value.parts):
            return True
        if any((parent / marker).exists() for parent in (value, *value.parents) for marker in MARKERS):
            return True
    return False


def allowed(path):
    p = Path(path).expanduser().resolve()
    if guarded(path):
        raise ValueError('guarded path')
    return p


def private(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def atomic(path, obj):
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with temporary.open('x') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    temporary.chmod(0o600)
    os.replace(temporary, path)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, allowed(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def file_hash(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


class Policy:
    def __init__(self, args):
        self.encoder_module = load_module('archive_local_encoder', ENCODER_SCRIPT)
        self.common = load_module('archive_common_policy', COMMON_SCRIPT)
        cfg = json.loads(allowed(CONFIG).read_text()) if CONFIG.exists() else {}
        access = cfg.get('archive_access', {})
        self.author_ids = set(self.common.EXCLUDED_IDS) | set(access.get('excluded_author_ids', []))
        self.message_ids = set(access.get('excluded_message_ids', []))
        self.record_ids = set(access.get('excluded_record_ids', []))
        self.prefixes = sorted(set(access.get('excluded_source_prefixes', [])) | set(args.exclude_source_prefix))
        self.original_root = allowed(args.original_root) if getattr(args, 'original_root', None) else None
        self.source_states = {}
        self.session_sources = {}
        self.dependency_hashes = {'common': file_hash(COMMON_SCRIPT), 'encoder': file_hash(ENCODER_SCRIPT)}
        self.native_proofs = {}
        self.native_parts = {}
        self.native_seen = set()
        self.native_verified_parts = {}
        configured = access.get('native_attribution') or {}
        if not isinstance(configured, dict):
            raise ValueError('native attribution configuration must be a mapping')
        proof_path = getattr(args, 'native_attribution_proof', None) or configured.get('path')
        proof_sha = getattr(args, 'native_attribution_proof_sha256', None) or configured.get('sha256')
        self.native_proof_sha256 = None
        if bool(proof_path) != bool(proof_sha):
            raise ValueError('native attribution proof requires its pinned SHA256')
        if proof_path:
            if not isinstance(proof_sha, str) or not re.fullmatch(r'[0-9a-f]{64}', proof_sha):
                raise ValueError('invalid native attribution proof SHA256')
            raw_proof = allowed(proof_path).read_bytes()
            if digest(raw_proof) != proof_sha:
                raise ValueError('native attribution proof changed')
            for raw_line in raw_proof.splitlines():
                if not raw_line.strip():
                    continue
                proof = json.loads(raw_line)
                if not isinstance(proof, dict) or proof.get('schema_version') != 1 or proof.get('source_family') != 'codex_cli':
                    raise ValueError('unsupported native attribution proof')
                rel = proof.get('normalized_part')
                if not isinstance(rel, str) or Path(rel).is_absolute() or '..' in Path(rel).parts or not rel.startswith('archive/corpus/records/kind=conversation/'):
                    raise ValueError('invalid native attribution part locator')
                for field in ('record_line_sha256', 'normalized_part_sha256', 'native_capture_sha256', 'native_session_meta_line_sha256'):
                    if not isinstance(proof.get(field), str) or not re.fullmatch(r'[0-9a-f]{64}', proof[field]):
                        raise ValueError('invalid native attribution hash')
                if not isinstance(proof.get('record_id'), str) or not isinstance(proof.get('native_session_id'), str) or not proof['native_session_id']:
                    raise ValueError('native attribution identity missing')
                if proof.get('native_source_kind') not in {'human_cli', 'subagent', 'unknown', 'conflicting'}:
                    raise ValueError('invalid native attribution source kind')
                for field in ('canonical_source_origin_path', 'canonical_source_archive_path', 'canonical_source_sha256', 'native_capture_archive_path', 'native_origin_path'):
                    if field not in proof or proof[field] is not None and not isinstance(proof[field], str):
                        raise ValueError('native attribution source binding missing')
                if proof.get('native_source_entrypoint') is not None and not isinstance(proof['native_source_entrypoint'], str):
                    raise ValueError('invalid native attribution entrypoint')
                for field in ('normalized_line', 'native_session_meta_line', 'native_session_meta_byte_offset', 'native_session_meta_length'):
                    value = proof.get(field)
                    if type(value) is not int or value < (0 if field == 'native_session_meta_byte_offset' else 1):
                        raise ValueError('invalid native attribution frame locator')
                key = (rel, proof['record_id'])
                if key in self.native_proofs:
                    raise ValueError('duplicate native attribution binding')
                if rel in self.native_parts and self.native_parts[rel] != proof['normalized_part_sha256']:
                    raise ValueError('conflicting native attribution part hashes')
                self.native_proofs[key] = proof
                self.native_parts[rel] = proof['normalized_part_sha256']
            if not self.native_proofs:
                raise ValueError('native attribution proof is empty')
            self.native_proof_sha256 = proof_sha
        self.policy_hash = digest(packed({'author_ids': sorted(self.author_ids), 'message_ids': sorted(self.message_ids), 'record_ids': sorted(self.record_ids), 'excluded_names': sorted(self.common.EXCLUDED_NAMES), 'verified_discord_id': self.common.OWNER_DISCORD_ID, 'verified_xfire_ids': sorted(self.common.OWNER_ALIASES), 'source_prefixes': sorted(self.prefixes), 'blocked_paths': BLOCKED, 'guard_markers': MARKERS, 'credential_pattern': self.encoder_module.SENSITIVE.pattern, 'scaffold_patterns': [SCAFFOLD.pattern, self.encoder_module.SCAFFOLD.pattern], 'native_attribution_proof_sha256': self.native_proof_sha256, 'dependency_hashes': self.dependency_hashes, 'self_policy': file_hash(Path(__file__))}).encode())

    def bind_native(self, row, raw, part, root):
        rel = str(part.relative_to(root))
        key = (rel, row.get('id'))
        proof = self.native_proofs.get(key)
        if proof is None:
            return
        stat = part.stat()
        version = (stat.st_size, stat.st_mtime_ns)
        if self.native_verified_parts.get(rel) != version:
            if file_hash(part) != proof['normalized_part_sha256']:
                raise ValueError('native attribution normalized part changed')
            self.native_verified_parts[rel] = version
        source = row.get('source') or {}
        if digest(raw) != proof['record_line_sha256'] or source.get('origin_path') != proof['canonical_source_origin_path'] or source.get('archive_path') != proof['canonical_source_archive_path'] or source.get('source_sha256') != proof['canonical_source_sha256']:
            raise ValueError('native attribution canonical record binding changed')
        if source.get('platform') != 'codex':
            raise ValueError('native attribution provider binding changed')
        identities = set(source_path_identities(row))
        if proof['native_origin_path'] not in identities and proof['native_capture_archive_path'] not in identities:
            raise ValueError('native attribution capture source identity differs')
        if source.get('archive_path') == proof['native_capture_archive_path'] and source.get('source_sha256') is not None and source['source_sha256'] != proof['native_capture_sha256']:
            raise ValueError('native attribution capture hash differs')
        row[NATIVE_ATTRIBUTION] = proof
        self.native_seen.add(key)

    def require_native_bindings(self):
        if self.native_seen != set(self.native_proofs):
            raise ValueError('native attribution proof references missing normalized records')

    def restriction(self, value):
        return isinstance(value, dict) and self.encoder_module.restricted(value)

    def record_reason(self, row, root):
        if row.get('id') in self.record_ids or self.restriction(row) or self.restriction(row.get('extra', {})):
            return 'restricted-record'
        if cursor_delegated_source(row):
            return 'cursor-delegated-session'
        classification = self.session_classification(row)
        native = native_attribution(row)
        captured_classification = native['native_source_kind'] if native else ((row.get('extra') or {}).get('agent_snapshot') or {}).get('source_kind')
        source = row.get('source') or {}
        family = ((row.get('extra') or {}).get('agent_snapshot') or {}).get('source_family') or source.get('family')
        if source.get('platform') == 'codex' and family != 'codex_prompt_history' and native is None:
            captured_classification = None
        if classification in {'subagent', 'conflicting'} or captured_classification in {'subagent', 'conflicting'}:
            return 'machine-session' if classification != 'conflicting' and captured_classification != 'conflicting' else 'conflicting-session-attribution'
        source = row.get('source') or {}
        raw = source.get('archive_path') or ''
        extra = row.get('extra') or {}
        snapshot = extra.get('agent_snapshot') or {}
        ir = extra.get('ir_v2_meta') or extra.get('ir_v1_meta') or {}
        identities = [raw, source.get('origin_path') or '', snapshot.get('source_path') or '', snapshot.get('logical_session_id') or '', ir.get('session_id') or '', ir.get('agent_id') or '', ir.get('conversation_id_source') or '']
        if self.restriction(source) or any(str(value).startswith(p) or p in str(value) for p in self.prefixes for value in identities):
            return 'restricted-source'
        if raw:
            path = Path(raw) if Path(raw).is_absolute() else root / raw
            if guarded(path):
                return 'guarded-source'
            if self.original_root and not Path(raw).is_absolute() and guarded(self.original_root / raw):
                return 'guarded-source'
        return None

    def session_classification(self, record):
        source = record.get('source') or {}
        snapshot = ((record.get('extra') or {}).get('agent_snapshot') or {})
        family = snapshot.get('source_family') or source.get('family')
        if source.get('platform') == 'codex' and family != 'codex_prompt_history' and native_attribution(record) is None:
            return None
        return self.session_sources.get(classification_key(record))

    def source_state(self, row, root):
        raw = (row.get('source') or {}).get('archive_path') or ''
        if not raw:
            return 'raw-provenance-unspecified'
        key = (str(root), raw)
        if key not in self.source_states:
            path = Path(raw) if Path(raw).is_absolute() else root / raw
            alternate = self.original_root / raw if self.original_root and not Path(raw).is_absolute() else None
            self.source_states[key] = 'raw-present-unconfirmed' if path.is_file() or alternate and alternate.is_file() else 'raw-unavailable-normalized-evidence-only'
        return self.source_states[key]

    def message_reason(self, message, text):
        author = message.get('author') or {}
        raw = (message.get('extra') or {}).get('raw') or {}
        if str(message.get('id')) in self.message_ids or str(author.get('id')) in self.author_ids or author.get('name') in self.common.EXCLUDED_NAMES:
            return 'installed-access-exclusion'
        if self.restriction(message) or self.restriction(author) or self.restriction(message.get('extra', {})) or self.restriction(raw):
            return 'restricted-message'
        if self.encoder_module.SENSITIVE.search(text):
            return 'credential-bearing-message'
        if SCAFFOLD.search(text) or self.encoder_module.SCAFFOLD.search(text):
            return 'instruction-or-profile-scaffolding'
        return None

    def owner(self, message, platform, record=None):
        native = native_attribution(record) if record is not None else None
        if native and native['native_source_kind'] in {'subagent', 'conflicting'}:
            return False
        if record is not None and cursor_delegated_source(record):
            return False
        if record is not None and self.session_sources.get(message_classification_key(record, message)) in {'machine_message', 'conflicting_message'}:
            return False
        author = message.get('author') or {}
        aid = str(author.get('id') or '')
        role = str(author.get('role') or message.get('role') or '').lower()
        raw = (message.get('extra') or {}).get('raw') or {}
        if raw.get('not_boden_reason') or raw.get('isSidechain') or raw.get('is_sidechain'):
            return False
        if raw.get('origin_kind') is not None and raw.get('origin_kind') != 'human':
            return False
        # A conflicting Discord identity takes precedence over an inferred role.
        if platform == 'discord':
            return bool(self.common.OWNER_DISCORD_ID) and aid == self.common.OWNER_DISCORD_ID
        if role in MACHINE or str(message.get('role') or '').lower() in MACHINE:
            return False
        if record is not None and document_context_reason(record):
            # Eligible for the separate source-context lane, never owner prose.
            return True
        if str(message.get('role') or '').lower() in {'user', 'human'} and (raw.get('unconfirmed_native_input') is True or raw.get('self_label_rule') == 'no_origin_field_sdk_fallback'):
            # An explicit unresolved-input marker permits context retrieval,
            # never primary owner evidence. Canonical authorship stays unknown.
            return role in {'unknown', 'user', 'human', 'self', 'me', 'owner', ''}
        if role in {'self', 'me', 'owner'}:
            return True
        if platform in AI and role in {'user', 'human'}:
            return True
        # A generic display name alone cannot establish personal authorship.
        return bool(self.common.OWNER_DISCORD_ID) and aid == self.common.OWNER_DISCORD_ID or aid.lower() in sorted(self.common.OWNER_ALIASES)

    def input_lane(self, record, message):
        """Unresolved caller origin is queryable context, not primary authorship."""
        if document_context_reason(record):
            return 'context_document'
        key = message_classification_key(record, message)
        proven = self.session_sources.get(key)
        direct = explicit_message_classification(record, message)
        if proven in {'machine_message', 'conflicting_message'} or direct == 'machine_message':
            return 'machine'
        if proven == 'command_control' or command_control(message):
            return 'command_control'
        if proven == 'human_message' or direct == 'human_message':
            return 'self'
        snapshot = ((record.get('extra') or {}).get('agent_snapshot') or {})
        if proven in {'unconfirmed_sdk', 'unconfirmed_native'} or direct in {'unconfirmed_sdk', 'unconfirmed_native'}:
            return 'unconfirmed_input'
        native = native_attribution(record)
        if native:
            return 'unconfirmed_input' if native['native_source_kind'] == 'unknown' else 'self'
        source = record.get('source') or {}
        if source.get('platform') == 'codex':
            raw = (message.get('extra') or {}).get('raw') or {}
            if raw.get('origin_kind') == 'human':
                return 'self'
            # A history row uses its own session ID. Native CLI imports can
            # instead retain an inherited parent ID; registry membership alone
            # cannot prove their caller. Missing evidence stays queryable.
            family = snapshot.get('source_family') or source.get('family')
            captured_hash = snapshot.get('source_sha256')
            if (family == 'codex_prompt_history' and snapshot.get('source_kind') == 'human_cli'
                and self.session_sources.get(classification_key(record)) == 'human_cli'
                and isinstance(captured_hash, str) and re.fullmatch(r'[0-9a-f]{64}', captured_hash)
                and source.get('source_sha256') == captured_hash):
                return 'self'
            return 'unconfirmed_imported_input'
        return 'self'


def open_db(path, readonly=False, wal=False):
    if readonly:
        # Published generation files never change. Immutable mode also prevents
        # SQLite from creating journals, WAL shared-memory files or read locks.
        return sqlite3.connect('file:' + quote(str(path), safe='/') + '?mode=ro&immutable=1', uri=True)
    db = sqlite3.connect(path, uri=True)
    path.chmod(0o600)
    db.execute('PRAGMA journal_mode=' + ('WAL' if wal else 'DELETE'))
    db.execute('PRAGMA synchronous=FULL')
    return db


def schema(db):
    db.executescript('''
      CREATE TABLE IF NOT EXISTS units(id TEXT PRIMARY KEY, vector_key TEXT NOT NULL, text TEXT NOT NULL, metadata TEXT NOT NULL);
      CREATE INDEX IF NOT EXISTS units_vector_key ON units(vector_key);
      CREATE TABLE IF NOT EXISTS parts(path TEXT PRIMARY KEY, sha256 TEXT, bytes INTEGER, mtime_ns INTEGER, stats TEXT);
      CREATE TABLE IF NOT EXISTS parent_versions(key TEXT PRIMARY KEY);
    ''')
    db.commit()


def encoder(args, policy):
    return policy.encoder_module.Encoder(str(allowed(args.model)), args.threads)


def temporal_gap(a, b):
    if not a or not b:
        return False
    try:
        difference = (dt.datetime.fromisoformat(b.replace('Z', '+00:00')) - dt.datetime.fromisoformat(a.replace('Z', '+00:00'))).total_seconds()
        return difference < 0 or difference > 1800
    except ValueError:
        return True


def record_messages(record, owner_id):
    """Return a read-only message view and its exact normalized source pointer."""
    kind = record.get('kind')
    if kind == 'event':
        if record.get('type') != 'log.discord_channel_snapshot':
            return [], None
        body = record.get('body') or {}
        payload = json.loads(body['text'])
        exported = payload['export']
        if not isinstance(exported.get('messages'), list):
            raise ValueError('snapshot event lacks exported message array')
        messages = []
        for raw in exported['messages']:
            author = dict(raw.get('author') or {})
            author['role'] = 'self' if str(author.get('id')) == owner_id else 'other'
            messages.append({'id': raw.get('id'), 'content': raw.get('content') or '',
                'sent_at': raw.get('timestamp'), 'role': author['role'], 'author': author,
                'reply_to': (raw.get('reference') or {}).get('messageId'),
                'extra': {'raw': raw}})
        return messages, '/body/text (decoded JSON)/export/messages'
    if kind == 'document':
        extra = record.get('extra') or {}
        if isinstance(extra.get('wrapped_message'), dict):
            body = record.get('body') or ''
            body_text = body.get('text', '') if isinstance(body, dict) else body
            if isinstance(extra['wrapped_message'].get('content'), str) and extra['wrapped_message']['content'] != body_text:
                raise ValueError('wrapped document content differs from normalized body')
            return [extra['wrapped_message']], '/extra/wrapped_message'
        body = record.get('body') or ''
        text = body.get('text', '') if isinstance(body, dict) else body
        message = {'id': record.get('id'), 'author': record.get('author') or extra.get('author') or {},
            'content': text, 'sent_at': (record.get('time') or {}).get('created_at')}
        return [message], '/body/text' if isinstance(body, dict) else '/body'
    return record.get('messages') or [], '/messages'


def session_identity(record):
    source = record.get('source') or {}
    platform = source.get('platform') or 'unknown'
    family = source.get('family') or platform
    extra = record.get('extra') or {}
    snapshot = extra.get('agent_snapshot') or {}
    ir = extra.get('ir_v2_meta') or extra.get('ir_v1_meta') or {}
    native = native_attribution(record)
    logical = ((native or {}).get('native_session_id') or snapshot.get('logical_session_id') or ir.get('session_id') or ir.get('sessionId')
        or ir.get('agent_id') or ir.get('conversation_id_source') or ir.get('conversation_id'))
    if platform == 'discord':
        channel = ir.get('channel') or {}
        logical = extra.get('channel_id') or ir.get('channel_id') or (channel.get('id') if isinstance(channel, dict) else None)
        if not logical:
            match = re.search(r'\[(\d{15,22})\]', source.get('archive_path') or '')
            logical = match.group(1) if match else None
        family = 'discord-channel'
    if not logical:
        logical = (record.get('provenance') or {}).get('prior_ids', {}).get('ir_v2')
    if not logical:
        origin = snapshot.get('source_path') or source.get('origin_path') or source.get('archive_path') or str(record.get('id'))
        # Export-root changes do not create another logical source. Native
        # databases need per-conversation metadata/prior IDs before this fallback.
        for marker in ('/archive/originals/', '/raw/', '/inbox/home-conversations/', '/.codex/', '/.claude/', '/.cursor/'):
            if marker in origin:
                origin = origin.split(marker, 1)[1]
                break
        logical = 'path:' + origin.replace('\\', '/')
    return digest(packed([platform, family, str(logical)]).encode())


def classification_key(record):
    """Classification crosses provider-specific capture formats for one session."""
    source = record.get('source') or {}
    extra = record.get('extra') or {}
    snapshot = extra.get('agent_snapshot') or {}
    ir = extra.get('ir_v2_meta') or extra.get('ir_v1_meta') or {}
    native = native_attribution(record)
    logical = (native or {}).get('native_session_id') or snapshot.get('logical_session_id') or ir.get('session_id') or ir.get('sessionId') or ir.get('agent_id') or ir.get('conversation_id_source')
    if not logical:
        return None
    provider = source.get('platform')
    if provider in {'cursor_agent', 'cursor_chat_store', 'cursor_prompt_history'} or provider in {'agent', 'unknown', None} and source.get('family') in {'cursor_agent', 'cursor_chat_store'}:
        provider = 'cursor'
    return digest(packed([provider, str(logical)]).encode())


def message_classification_key(record, message):
    session = classification_key(record)
    mid = message.get('id')
    return 'message:' + digest(packed([session, str(mid)]).encode()) if session and mid is not None else None


def explicit_message_classification(record, message):
    source = record.get('source') or {}
    raw = (message.get('extra') or {}).get('raw') or {}
    if command_control(message):
        return 'command_control'
    if source.get('platform') != 'claude_code' and source.get('family') != 'claude_code':
        return 'unconfirmed_native' if raw.get('unconfirmed_native_input') is True else None
    if raw.get('not_boden_reason') or raw.get('isSidechain') or raw.get('is_sidechain') or raw.get('origin_kind') is not None and raw.get('origin_kind') != 'human':
        return 'machine_message'
    if raw.get('origin_kind') == 'human':
        return 'human_message'
    if raw.get('unconfirmed_native_input') is True:
        return 'unconfirmed_native'
    if raw.get('self_label_rule') == 'no_origin_field_sdk_fallback':
        return 'unconfirmed_sdk'
    return None


def merge_message_classification(previous, current):
    if previous == 'conflicting_message' or {previous, current} == {'human_message', 'machine_message'}:
        return 'conflicting_message'
    if previous == 'command_control' or current == 'command_control':
        return 'command_control'
    if current in {'unconfirmed_sdk', 'unconfirmed_native'}:
        return previous or current
    return current


def command_control(message):
    """Explicit native action metadata, never a guess from prose or syntax."""
    extra = message.get('extra') or {}
    raw = extra.get('raw') or {}
    native = raw.get('native_frame_metadata') or {}
    return (any(container.get('content_kind') == 'command_control' for container in (message, extra, raw))
        or raw.get('native_type') in {'command', 'control'}
        or raw.get('native_role') in {'command', 'control'}
        or native.get('type') in {'command', 'control'})


def source_path_identities(record):
    """Read path metadata only; prompts, titles and free-form notes are excluded."""
    extra = record.get('extra') or {}
    provenance = record.get('provenance') or {}
    containers = [record.get('source') or {}, extra, extra.get('agent_snapshot') or {},
        extra.get('ir_v1_meta') or {}, extra.get('ir_v2_meta') or {},
        extra.get('ir_v1_provenance_extra') or {}, extra.get('ir_v2_provenance_extra') or {}]
    containers.extend(item for item in provenance.get('wasDerivedFrom') or [] if isinstance(item, dict))
    fields = ('origin_path', 'archive_path', 'source_path', 'original_path',
        'source_resolved_path', 'source_relative_path', 'source_file', 'path')
    for container in containers:
        if not isinstance(container, dict):
            continue
        for field in fields:
            value = container.get(field)
            if isinstance(value, str):
                yield value


def cursor_delegated_source(record):
    source = record.get('source') or {}
    snapshot = ((record.get('extra') or {}).get('agent_snapshot') or {})
    families = {source.get('family'), snapshot.get('source_family')}
    if source.get('platform') not in {'cursor', 'cursor_agent', 'cursor_chat_store', 'cursor_prompt_history'} and not families.intersection({'cursor', 'cursor_agent', 'cursor_chat_store'}):
        return False
    for spelling in source_path_identities(record):
        if '://' in spelling:
            continue
        parts = spelling.replace('\\', '/').split('/')
        for i, part in enumerate(parts):
            if part != 'agent-transcripts':
                continue
            tail = parts[i+1:]
            # Native delegated transcripts have exactly one root session,
            # the subagents directory and one transcript leaf. A human project
            # directory or a prose mention of subagents is not this structure.
            if (len(tail) == 3 and tail[1] == 'subagents'
                and re.fullmatch(r'[A-Za-z0-9_-]+', tail[0])
                and re.fullmatch(r'[A-Za-z0-9_-]+\.(?:jsonl|txt)', tail[2])):
                return True
    return False


def source_classifications(files, policy=None, root=None):
    """Read explicit capture classifications before accepting historical labels.

    Most historical parts have no such field; byte screening avoids parsing
    their contents twice. No original or request-only store is opened here.
    """
    registry = {}
    proofs = []
    if policy is not None:
        policy.native_seen.clear()
    for part in files:
        if 'kind=conversation' not in part.parts:
            continue
        proof_records = []
        pinned_part = policy is not None and str(part.relative_to(root)) in policy.native_parts
        with part.open('rb') as stream:
            for raw in stream:
                if not pinned_part and not any(field in raw for field in (b'"source_kind"', b'"origin_kind"', b'"self_label_rule"', b'"not_boden_reason"', b'"is_sidechain"', b'"isSidechain"', b'"unconfirmed_native_input"', b'"content_kind"', b'"native_type"', b'"codex_event"')) and not (b'agent-transcripts' in raw and b'subagents' in raw):
                    continue
                record = json.loads(raw)
                if not isinstance(record, dict):
                    continue
                if policy is not None:
                    policy.bind_native(record, raw, part, root)
                record_line_hash = digest(raw)
                for message in record.get('messages') or []:
                    if str(message.get('role') or '').lower() in {'assistant', 'tool', 'function', 'system', 'developer'}:
                        continue
                    classification = explicit_message_classification(record, message)
                    message_key = message_classification_key(record, message)
                    if classification and message_key:
                        registry[message_key] = merge_message_classification(registry.get(message_key), classification)
                        proof_records.append({'record_id': record.get('id'), 'record_line_sha256': record_line_hash, 'message_id': message.get('id'), 'classification_key': message_key, 'effective_classification': classification, 'classification_basis': 'explicit retained per-message origin, caller uncertainty or command metadata'})
                snapshot = ((record.get('extra') or {}).get('agent_snapshot') or {})
                native = native_attribution(record)
                kind = native['native_source_kind'] if native else snapshot.get('source_kind')
                entrypoint = native['native_source_entrypoint'] if native else snapshot.get('source_entrypoint')
                source = record.get('source') or {}
                if source.get('platform') == 'codex' and (snapshot.get('source_family') or source.get('family')) != 'codex_prompt_history' and native is None:
                    kind = None
                # A recovery route describes parsing, not who supplied input.
                # Its preserved per-message proofs establish each input lane.
                if kind == 'native_cli_recovery':
                    kind = None
                key = classification_key(record)
                delegated_cursor = cursor_delegated_source(record)
                if delegated_cursor:
                    kind = 'subagent'
                if kind == 'unknown' and native:
                    kind = 'unconfirmed_exec' if entrypoint == 'exec' else 'unconfirmed_native_session'
                elif kind == 'unknown' and entrypoint == 'exec':
                    kind = 'unconfirmed_exec'
                if not key or kind in (None, 'unknown'):
                    continue
                if kind not in {'human_cli', 'subagent', 'conflicting', 'unconfirmed_exec', 'unconfirmed_native_session'}:
                    raise ValueError('unrecognized captured session classification')
                old = registry.get(key)
                registry[key] = 'conflicting' if kind == 'conflicting' or old == 'conflicting' or old is not None and old != kind else kind
                proof_records.append({'record_id': record.get('id'), 'record_line_sha256': record_line_hash, 'classification_key': key, 'source_kind': kind if native else snapshot.get('source_kind'), 'source_entrypoint': entrypoint, 'effective_classification': kind, 'classification_basis': 'pinned first native session header bound to this exact canonical record' if native else 'explicit native Cursor delegated transcript path' if delegated_cursor else 'captured session classification'})
        if proof_records:
            proofs.append({'part': str(part), 'records': proof_records})
    if policy is not None:
        policy.require_native_bindings()
    return registry, proofs


def record_units(record, locator, policy, enc, stats):
    platform = (record.get('source') or {}).get('platform') or 'unknown'
    if cursor_delegated_source(record) or policy.session_classification(record) in {'subagent', 'conflicting'}:
        stats['excluded_record:machine-session'] += 1
        return
    session_key = session_identity(record)
    messages, message_pointer = record_messages(record, policy.common.OWNER_DISCORD_ID)
    observed_at = ((record.get('extra') or {}).get('agent_snapshot') or {}).get('captured_at') or (record.get('provenance') or {}).get('generatedAtTime')
    snapshot = ((record.get('extra') or {}).get('agent_snapshot') or {})
    native = native_attribution(record)
    if message_pointer is None:
        stats['unsupported_event_records'] += 1
        return
    if record.get('kind') == 'event':
        stats['discord_snapshot_events'] += 1
    if record.get('kind') == 'document':
        context_reason = document_context_reason(record)
        if context_reason or not any(policy.owner(message, platform, record) for message in messages):
            stats['authorship_unverified_documents'] += 1
        if context_reason:
            stats['context_document_records'] += 1
            stats['context_document_reason:' + context_reason] += 1
        invalid_codepoints = sum(len(SURROGATE.findall(policy.common.message_text(message))) for message in messages)
        if invalid_codepoints:
            stats['non_embeddable_document_records'] += 1
            stats['non_embeddable_document_unicode_codepoints'] += invalid_codepoints
            # The canonical JSON and original bytes remain untouched. No guessed
            # character encoding or replacement text enters the model.
            return
    group = []
    token_count = 0

    def emit(group):
        if not group:
            return
        input_lane = policy.input_lane(record, group[0][1])
        unconfirmed_input = input_lane in UNCONFIRMED_INPUT_LANES
        context_document = input_lane == 'context_document'
        text = ''
        spans = []
        for i, message, content in group:
            if text:
                text += '\n'
            start = len(text)
            text += content
            message_id = str(message.get('id') or f'{session_key}:{i}')
            text_hash = digest(content.encode())
            parent_key = digest(packed([session_key, message_id, text_hash]).encode())
            spans.append((start, len(text), i, message, message_id, text_hash, parent_key))
        for split in enc.split(text):
            parents = []
            for start, end, i, message, message_id, text_hash, parent_key in spans:
                left, right = max(start, split['char_start']), min(end, split['char_end'])
                if left >= right:
                    continue
                raw_meta = (message.get('extra') or {}).get('raw') or {}
                reply = message.get('reply_to') or (raw_meta.get('reference') or {}).get('messageId')
                edited = raw_meta.get('timestampEdited') or raw_meta.get('timestamp_edited')
                parents.append({'message_index': i, 'message_id': message_id, 'text_sha256': text_hash, 'parent_version_key': parent_key, 'char_start': left - start, 'char_end': right - start, 'timestamp': message.get('sent_at'), 'timestamp_edited': edited, 'reply_to': reply, 'author': message.get('author') or {}, 'role': message.get('role'), 'attribution_class': policy.input_lane(record, message)})
                if record.get('kind') == 'event':
                    parents[-1]['raw_observation_version_sha256'] = ((record.get('extra') or {}).get('message_versions') or {}).get(message_id)
            identity = {'session_key': session_key, 'authorship_class': 'context_document' if context_document else 'unconfirmed_input' if unconfirmed_input else 'self', 'parents': [(p['message_id'], p['text_sha256'], p['char_start'], p['char_end']) for p in parents]}
            uid = digest(packed(identity).encode())
            metadata = {**locator, 'record_id': record.get('id'), 'record_hash': record.get('content_hash'), 'kind': record.get('kind'), 'platform': platform, 'source': record.get('source') or {}, 'message_pointer': message_pointer, 'session_key': session_key, 'observed_at': observed_at, 'parents': parents, 'timestamp': parents[0].get('timestamp'), 'year': str(parents[0].get('timestamp') or '')[:4], 'role': 'unconfirmed_input' if unconfirmed_input else 'self', 'source_kind': snapshot.get('source_kind'), 'source_entrypoint': snapshot.get('source_entrypoint'), 'encoded_tokens': split['encoded_tokens'], 'evidence_class': 'Unconfirmed task input: formal user role does not establish human authorship or adopted beliefs.' if unconfirmed_input else 'owner-attributed-source; quotation-or-belief-adoption-unverified'}
            metadata['input_attribution_class'] = input_lane
            if context_document:
                metadata.update(role='context_document', primary_owner_evidence=False, effective_attribution_reason=document_context_reason(record), evidence_class='Source document context; ownership and export wrappers do not establish personal authorship or adopted beliefs.')
            if input_lane == 'unconfirmed_imported_input':
                metadata.update(effective_attribution_reason='unconfirmed_imported_input', evidence_class='Imported formal-user input without verified native caller attribution; available as context, not primary owner evidence.')
            if native:
                metadata.update(source_kind=native['native_source_kind'], source_entrypoint=native['native_source_entrypoint'], native_session_id=native['native_session_id'], native_attribution_proof_sha256=policy.native_proof_sha256 if not native.get('attribution_basis') else None, native_capture_sha256=native['native_capture_sha256'], native_attribution_basis=native.get('attribution_basis') or 'pinned-first-native-session-header')
            if record.get('kind') == 'event':
                observation = record.get('extra') or {}
                event_snapshot = {k: observation.get(k) for k in ('run_id', 'channel_id', 'after', 'before', 'complete', 'version_hash_scope')}
                event_snapshot.update(changed_observations=len(observation.get('changed_observations') or []), missing_observations=len(observation.get('missing_observations') or []))
                metadata.update(message_container_pointer='/body/text', decoded_message_pointer='/export/messages', payload_decoding='JSON string', snapshot_observation=event_snapshot)
            if unconfirmed_input:
                direct = explicit_message_classification(record, group[0][1])
                proven = policy.session_sources.get(message_classification_key(record, group[0][1]))
                metadata['attribution_basis'] = 'Imported caller provenance does not independently identify a human actor.' if input_lane == 'unconfirmed_imported_input' else 'Pinned first native session header leaves caller identity unresolved.' if native else 'Explicit native input marker leaves caller identity unresolved.' if direct == 'unconfirmed_native' or proven == 'unconfirmed_native' else 'Explicit Claude SDK fallback leaves caller origin unresolved.' if direct == 'unconfirmed_sdk' or proven == 'unconfirmed_sdk' else 'Captured session header leaves formal-user input unconfirmed.'
            stats['context_document_units' if context_document else 'unconfirmed_input_units' if unconfirmed_input else 'owner_units'] += 1
            yield uid, digest(split['text'].encode()), split['text'], packed(metadata)

    for i, message in enumerate(messages):
        stats['messages_observed'] += 1
        content = policy.common.message_text(message)
        lane = policy.input_lane(record, message)
        if lane == 'command_control':
            stats['context_only_command_control_messages'] += 1
            stats['human_command_actions' if policy.owner(message, platform, record) else 'other_or_unknown_command_actions'] += 1
            yield from emit(group)
            group, token_count = [], 0
            continue
        reason = policy.message_reason(message, content)
        if reason:
            stats['excluded:' + reason] += 1
            yield from emit(group)
            group, token_count = [], 0
            continue
        if not policy.owner(message, platform, record):
            stats['nonowner_or_unknown_messages'] += 1
            continue
        if lane == 'machine':
            stats['nonowner_or_unknown_messages'] += 1
            continue
        if not content.strip():
            stats['empty_owner_messages'] += 1
            continue
        tokens = len(enc.tokenizer.encode(content, add_special_tokens=False).ids)
        previous = group[-1][1].get('sent_at') if group else None
        if group and (token_count + tokens > 400 or temporal_gap(previous, message.get('sent_at')) or policy.input_lane(record, group[-1][1]) != lane):
            yield from emit(group)
            group, token_count = [], 0
        group.append((i, message, content))
        token_count += tokens
        stats['context_document_messages' if lane == 'context_document' else 'unconfirmed_input_messages' if lane in UNCONFIRMED_INPUT_LANES else 'owner_messages'] += 1
        if lane == 'unconfirmed_imported_input':
            stats['unconfirmed_imported_input_messages'] += 1
        if tokens > 400:
            yield from emit(group)
            group, token_count = [], 0
    yield from emit(group)


def inputs(root):
    base = allowed(root / 'archive/corpus/records')
    files = []
    for kind in ('conversation', 'document', 'event'):
        folder = base / ('kind=' + kind)
        if not folder.is_dir():
            continue
        for platform in sorted(folder.iterdir()):
            if guarded(platform) or not platform.is_dir():
                continue
            files.extend(p for p in sorted(platform.glob('*.jsonl')) if not guarded(p))
    return files


def compact_status(manifest, generation_path):
    """Bounded status metadata for read-only consumers; full manifests stay on disk."""
    fields = ('state', 'generation', 'created_at', 'updated_at', 'root', 'native_attribution_proof_sha256', 'dependency_hashes',
              'original_root', 'policy_hash', 'model_key', 'model', 'scope',
              'network', 'coverage', 'classification_hash', 'classification_counts',
              'planned_parts', 'planned_source_bytes', 'processed_parts', 'units',
              'elapsed_seconds', 'collecting_source_bytes',
              'collecting_source_total_bytes', 'collection_counts_provisional',
              'compatible_policy_migration', 'audited_non_embeddable_documents')
    result = {key: manifest[key] for key in fields if key in manifest}
    result['manifest_path'] = str(generation_path / 'manifest.json')
    return result


def report(gen, db, state, started, counters=None, extra=None):
    data = json.loads((gen / 'manifest.json').read_text())
    for field in ('collecting_source_bytes', 'collecting_source_total_bytes', 'collection_counts_provisional'):
        data.pop(field, None)
    data.update(state=state, updated_at=now(), units=db.execute('SELECT count(*) FROM units').fetchone()[0], processed_parts=db.execute('SELECT count(*) FROM parts').fetchone()[0], elapsed_seconds=round(time.monotonic() - started, 3))
    if counters is not None:
        data['coverage'] = dict(counters)
    if extra:
        data.update(extra)
    atomic(gen / 'manifest.json', data)
    return data


def require_build_space(index, reserve_bytes, additional_bytes=0):
    free = shutil.disk_usage(index).free
    required = reserve_bytes + additional_bytes
    if free < required:
        raise ValueError(f'insufficient index space: {free} bytes free, {required} required; committed source parts and shared vectors retained, generation not activated')


def migrate_document_policy(args, root, index, policy):
    """Fork an audited incomplete generation; invalidate only document parts."""
    prior_code = allowed(args.prior_code)
    supported = '36cc84aaca1ed91a99b2a3bdecb92d6f40ee99aaca2e1accef066dbc139f4f8c'
    if args.prior_code_sha256 != supported or file_hash(prior_code) != supported:
        raise ValueError('unsupported or changed document migration predecessor')
    pins = dict(value.split('=', 1) for value in args.dependency_pin)
    if pins != policy.dependency_hashes or len(args.dependency_pin) != len(pins):
        raise ValueError('migration requires exact current common and encoder dependency pins')
    old_code = load_module('archive_document_migration_predecessor', prior_code)
    old_policy = old_code.Policy(args)
    prior = allowed(index / 'generations' / args.from_generation)
    if prior.parent != (index / 'generations').resolve():
        raise ValueError('migration predecessor outside generations')
    prior_manifest = prior / 'manifest.json'
    old_meta = json.loads(prior_manifest.read_text())
    if old_meta.get('state') not in {'collecting', 'embedding'} or old_meta.get('root') != str(root) or old_meta.get('original_root') != (str(policy.original_root) if policy.original_root else None) or old_meta.get('policy_hash') != old_policy.policy_hash:
        raise ValueError('migration predecessor state, root or access policy differs')
    created_ns = int(dt.datetime.fromisoformat(old_meta['created_at']).timestamp() * 1e9)
    for dependency in (COMMON_SCRIPT, ENCODER_SCRIPT):
        if dependency.stat().st_mtime_ns > created_ns:
            raise ValueError('dependency changed after predecessor creation; cannot infer compatibility')
    if old_meta.get('dependency_hashes') is not None and old_meta['dependency_hashes'] != pins:
        raise ValueError('predecessor dependency fingerprints differ')
    # These classifiers are unchanged by the document-only policy transition.
    # Pinning dependencies avoids silently importing a changed text adapter.
    stable = {'native_attribution', 'source_classifications', 'classification_key', 'message_classification_key', 'explicit_message_classification', 'merge_message_classification', 'command_control', 'cursor_delegated_source', 'source_path_identities', 'session_identity'}
    def stable_ast(path):
        tree = ast.parse(path.read_text())
        return {node.name: ast.dump(node, include_attributes=False) for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in stable}
    if stable_ast(prior_code) != stable_ast(Path(__file__)):
        raise ValueError('non-document classification changes are not compatible')
    enc = encoder(args, policy)
    model_key = digest(packed({k: v for k, v in enc.meta.items() if k != 'threads'}).encode())
    transition = None
    if args.model_transition_receipt or args.prior_model or args.model_transition_receipt_sha256:
        if not all((args.model_transition_receipt, args.model_transition_receipt_sha256, args.prior_model)):
            raise ValueError('model transition requires prior model and pinned receipt')
        transition_path = allowed(args.model_transition_receipt)
        if file_hash(transition_path) != args.model_transition_receipt_sha256:
            raise ValueError('model transition receipt changed')
        transition = json.loads(transition_path.read_text())
        if transition.get('schema_version') != 1 or allowed(args.prior_model) != allowed(transition['original_directory']) or allowed(args.model) != allowed(transition['candidate_directory']):
            raise ValueError('model transition identifies different model directories')
        prior_args = argparse.Namespace(**vars(args))
        prior_args.model = args.prior_model
        prior_enc = encoder(prior_args, old_policy)
        prior_key = digest(packed({k: v for k, v in prior_enc.meta.items() if k != 'threads'}).encode())
        if prior_key != old_meta['model_key'] or prior_enc.model_hash != transition['original_model_sha256'] or enc.model_hash != transition['candidate_model_sha256']:
            raise ValueError('model transition byte identities differ')
        if {k: v for k, v in prior_enc.meta.items() if k not in {'threads', 'sha256'}} != {k: v for k, v in enc.meta.items() if k not in {'threads', 'sha256'}}:
            raise ValueError('model transition changes tokenizer or encoder contract')
        artifacts = {artifact['name']: artifact for artifact in transition['files']}
        if set(artifacts) != {'model_optimized.onnx', 'tokenizer.json', 'config.json'} or len(artifacts) != len(transition['files']):
            raise ValueError('model transition artifact manifest differs')
        for name, artifact in artifacts.items():
            candidate = allowed(Path(args.model) / name)
            if candidate.stat().st_size != artifact['bytes'] or file_hash(candidate) != artifact['sha256']:
                raise ValueError('model transition artifact bytes changed')
        if any(transition.get(field) is not True for field in ('all_graph_node_bytes_unchanged', 'opsets_unchanged', 'ort_persisted_model_load_passed')) or any(transition.get(field) is not False for field in ('activated', 'cache_modified', 'original_modified')):
            raise ValueError('model transition lacks audited graph and preservation assertions')
        if file_hash(allowed(Path(args.prior_model) / 'config.json')) != artifacts['config.json']['sha256'] or file_hash(allowed(Path(args.prior_model) / 'tokenizer.json')) != artifacts['tokenizer.json']['sha256']:
            raise ValueError('model transition changes configuration or splitting tokenizer')
    elif model_key != old_meta.get('model_key'):
        raise ValueError('migration model differs without an explicit transition receipt')
    if policy.native_proof_sha256 != old_meta.get('native_attribution_proof_sha256'):
        raise ValueError('migration model or native attribution proof differs')
    receipt_path = allowed(args.compatibility_receipt)
    if file_hash(receipt_path) != args.compatibility_receipt_sha256:
        raise ValueError('document compatibility receipt changed')
    audit = json.loads(receipt_path.read_text())
    if audit.get('schema_version') != 1 or Path(audit.get('generation', '')).resolve() != prior or audit.get('conversation_units_affected') != 0:
        raise ValueError('document compatibility receipt identifies another generation')
    expected = {(row['part'], row['record_id']): row for row in audit['rows']}
    if len(expected) != len(audit['rows']):
        raise ValueError('duplicate document audit bindings')
    actual, context_parts = set(), set()
    for part in inputs(root):
        if 'kind=document' not in part.parts:
            continue
        rel = str(part.relative_to(root))
        part_sha = file_hash(part)
        with part.open('rb') as stream:
            for line, raw in enumerate(stream, 1):
                record = json.loads(raw)
                if not document_context_reason(record):
                    continue
                key = (rel, record.get('id'))
                proof = expected.get(key)
                if not proof or proof['part_sha256'] != part_sha or proof['record_line_sha256'] != digest(raw) or proof['line'] != line:
                    raise ValueError('document policy differs from its exact audited source bindings')
                actual.add(key)
                context_parts.add(rel)
    if actual != set(expected):
        raise ValueError('document compatibility audit has missing source records')
    lock = (index / 'BUILD.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    old_db_path = prior / 'units.sqlite'
    if any(Path(str(old_db_path) + suffix).exists() and Path(str(old_db_path) + suffix).stat().st_size for suffix in ('-wal', '-journal')):
        raise ValueError('predecessor has a pending journal; require a clean committed snapshot')
    before_db_sha, before_manifest_sha = file_hash(old_db_path), file_hash(prior_manifest)
    with contextlib.ExitStack() as cleanup:
        source = cleanup.enter_context(contextlib.closing(open_db(old_db_path, True)))
        if transition:
            names = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'vectors' in names and source.execute('SELECT count(*) FROM vectors').fetchone()[0]:
                raise ValueError('model transition requires a predecessor without vectors')
            shared = index / 'vectors.sqlite'
            if shared.exists():
                if any(Path(str(shared) + suffix).exists() and Path(str(shared) + suffix).stat().st_size for suffix in ('-wal', '-journal')):
                    raise ValueError('shared cache has a pending journal; cannot confirm an empty model cache')
                cache = open_db(shared, True)
                try:
                    if cache.execute('SELECT count(*) FROM vectors').fetchone()[0]:
                        raise ValueError('model transition requires an empty shared vector cache')
                finally:
                    cache.close()
        parts = source.execute('SELECT path,sha256,bytes,mtime_ns FROM parts').fetchall()
        affected = context_parts & {row[0] for row in parts}
        if len(affected) != audit['affected_committed_document_part_count']:
            raise ValueError('audited affected part count differs')
        for rel, sha, size, _mtime in parts:
            part = allowed(root / rel)
            if part.stat().st_size != size or file_hash(part) != sha:
                raise ValueError('committed source bytes changed before migration')
        affected_units = 0
        for (metadata,) in source.execute("SELECT metadata FROM units WHERE json_extract(metadata,'$.kind')='document'"):
            md = json.loads(metadata)
            if md['part'] in affected:
                affected_units += 1
            elif any(observation.get('part') in affected for observation in md.get('observations', [])):
                raise ValueError('mixed document observations require a fuller migration')
        old_units = source.execute('SELECT count(*) FROM units').fetchone()[0]
        if affected_units != audit['affected_committed_document_units'] or old_units - affected_units != audit['unaffected_old_units_to_preserve_exactly']:
            raise ValueError('audited unit preservation counts differ')
        require_build_space(index, args.reserve_bytes, old_db_path.stat().st_size + 64 * 1024 ** 2)
        gen = private(index / 'generations' / ('gen-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]))
        db = cleanup.enter_context(contextlib.closing(open_db(gen / 'units.sqlite')))
        source.backup(db)
        source.close()
        db.execute('ATTACH DATABASE ? AS prior', ('file:' + quote(str(old_db_path), safe='/') + '?mode=ro&immutable=1',))
        for rel in sorted(affected):
            db.execute("DELETE FROM units WHERE json_extract(metadata,'$.kind')='document' AND json_extract(metadata,'$.part')=?", (rel,))
            db.execute('DELETE FROM parts WHERE path=?', (rel,))
        # Check full row equality, including text and provenance; no conversation
        # projection or metadata reserialization occurs during this migration.
        unequal = db.execute("SELECT count(*) FROM prior.units p LEFT JOIN main.units n ON n.id=p.id WHERE (json_extract(p.metadata,'$.kind')!='document' OR json_extract(p.metadata,'$.part') NOT IN (SELECT value FROM json_each(?))) AND (n.id IS NULL OR n.vector_key!=p.vector_key OR n.text!=p.text OR n.metadata!=p.metadata)", (packed(sorted(affected)),)).fetchone()[0]
        conversations = db.execute("SELECT count(*) FROM units WHERE json_extract(metadata,'$.kind')='conversation'").fetchone()[0]
        if unequal or conversations != audit['committed_conversation_units_preserved'] or db.execute('SELECT count(*) FROM units').fetchone()[0] != old_units - affected_units:
            db.rollback()
            db.close()
            raise ValueError('migration failed exact committed-unit preservation')
        db.execute('DELETE FROM parent_versions')
        db.execute("INSERT OR IGNORE INTO parent_versions SELECT json_extract(parent.value,'$.parent_version_key') FROM units u,json_each(u.metadata,'$.parents') parent WHERE json_extract(u.metadata,'$.role')='self'")
        db.commit()
        stats = collections.Counter()
        for (raw_stats,) in db.execute('SELECT stats FROM parts'):
            stats.update(json.loads(raw_stats))
        db.close()
    if file_hash(old_db_path) != before_db_sha or file_hash(prior_manifest) != before_manifest_sha:
        raise ValueError('predecessor changed during migration; new generation not activated')
    meta = dict(old_meta)
    meta.update(generation=gen.name, state='collecting', created_at=now(), updated_at=now(), policy_hash=policy.policy_hash, dependency_hashes=pins, scope=ARCHIVE_SCOPE, model_key=model_key, model=enc.meta, units=old_units - affected_units, processed_parts=len(parts) - len(affected), coverage=dict(stats), elapsed_seconds=0)
    if transition:
        meta['model_transition'] = {'receipt_sha256': args.model_transition_receipt_sha256, 'prior_model_sha256': transition['original_model_sha256'], 'current_model_sha256': transition['candidate_model_sha256'], 'prior_model_key': old_meta['model_key'], 'current_model_key': model_key, 'tokenizer_unchanged': True, 'configuration_unchanged': True, 'existing_vector_count': 0, 'weight_conversion': 'Audited lossless FP16 weight values represented in FP32; FP32 execution is not bit-identical to prior arithmetic.'}
    meta['audited_non_embeddable_documents'] = {'records': len(audit['remaining_unicode_records']), 'unpaired_surrogate_codepoints': audit['remaining_unicode_codepoints'], 'audit_sha256': args.compatibility_receipt_sha256, 'status': 'Audited source limitations; completed collection counters are reported separately in coverage.', 'preservation': 'Exact canonical JSON and original bytes retained; no replacement or guessed decoding.'}
    for field in ('collecting_source_bytes', 'collecting_source_total_bytes', 'collection_counts_provisional', 'embedded_unique_texts'):
        meta.pop(field, None)
    meta['compatible_policy_migration'] = {'source_generation': prior.name, 'source_manifest_sha256': before_manifest_sha, 'source_database_sha256': before_db_sha, 'prior_code_sha256': supported, 'current_code_sha256': file_hash(Path(__file__)), 'prior_policy_hash': old_policy.policy_hash, 'current_policy_hash': policy.policy_hash, 'compatibility_receipt_sha256': args.compatibility_receipt_sha256, 'dependency_hashes': pins, 'dependency_evidence': 'Current hashes explicitly pinned; file modification times predate source-generation creation. Earlier generation did not record dependency hashes.' if old_meta.get('dependency_hashes') is None else 'Exact predecessor dependency hashes retained.', 'recollect_document_parts': sorted(affected), 'removed_document_units': affected_units, 'preserved_units': old_units - affected_units, 'preserved_conversation_units': conversations, 'exact_unit_row_comparison': 'passed', 'predecessor_unchanged': True, 'activated': False}
    atomic(gen / 'manifest.json', meta)
    return compact_status(meta, gen)


def activate_completed_generation(args, root, index, gen, meta, files):
    """Retry only the final pointer write after revalidating a completed build."""
    db = open_db(gen / 'units.sqlite', True)
    try:
        parts = db.execute('SELECT path,sha256,bytes FROM parts').fetchall()
        if {str(p.relative_to(root)) for p in files} != {row[0] for row in parts}:
            raise ValueError('completed generation source set changed')
        for rel, sha, size in parts:
            path = allowed(root / rel)
            if path.stat().st_size != size or file_hash(path) != sha:
                raise ValueError('completed generation source bytes changed')
        if db.execute('SELECT count(*) FROM units').fetchone()[0] != meta['units'] or len(parts) != meta['planned_parts']:
            raise ValueError('completed generation coverage differs')
        missing = db.execute('SELECT count(*) FROM units u LEFT JOIN vectors v ON u.vector_key=v.key WHERE v.key IS NULL').fetchone()[0]
        if missing:
            raise ValueError('completed generation vectors missing')
        for blob, sha, model_key in db.execute('SELECT vector,vector_sha256,model_hash FROM vectors'):
            if model_key != meta['model_key'] or len(blob) != 4 * meta['model']['dim'] or digest(blob) != sha:
                raise ValueError('completed generation vector bytes differ')
    finally:
        db.close()
    require_build_space(index, args.reserve_bytes, 8192)
    atomic(index / 'CURRENT.json', {'generation': gen.name})
    return meta


def build(args, root, index, policy):
    started = time.monotonic()
    require_build_space(index, args.reserve_bytes)
    lock = (index / 'BUILD.lock').open('a+')
    (index / 'BUILD.lock').chmod(0o600)
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    enc = encoder(args, policy)
    files = inputs(root)
    registry, proofs = source_classifications(files, policy, root)
    policy.session_sources = registry
    registry_hash = digest(packed(registry).encode())
    cache = open_db(index / 'vectors.sqlite', wal=True)
    cache.execute('CREATE TABLE IF NOT EXISTS vectors(key TEXT NOT NULL, vector BLOB NOT NULL, vector_sha256 TEXT NOT NULL, model_hash TEXT NOT NULL, PRIMARY KEY(key,model_hash))')
    cache.commit()
    model_key = digest(packed({k:v for k,v in enc.meta.items() if k != 'threads'}).encode())
    if args.resume:
        gen = allowed(index / 'generations' / args.resume)
        if gen.parent != (index / 'generations').resolve():
            raise ValueError('resume outside generations')
        meta = json.loads((gen / 'manifest.json').read_text())
        if meta['root'] != str(root) or meta.get('original_root') != (str(policy.original_root) if policy.original_root else None) or meta['policy_hash'] != policy.policy_hash or meta['model_key'] != model_key or meta.get('classification_hash') != registry_hash:
            raise ValueError('resume differs from root, policy, model or completed state')
        if meta['state'] == 'complete':
            cache.close()
            return activate_completed_generation(args, root, index, gen, meta, files)
    else:
        gen = private(index / 'generations' / ('gen-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]))
        meta = {'state': 'collecting', 'generation': gen.name, 'created_at': now(), 'root': str(root), 'original_root': str(policy.original_root) if policy.original_root else None, 'policy_hash': policy.policy_hash, 'model_key': model_key, 'model': enc.meta, 'scope': 'All accessible canonical conversations, documents and Discord snapshot events. Primary retrieval covers attributed owner writing; explicitly unresolved caller input is retained in a separate opt-in lane and is not primary profile evidence. Other speakers, unattributed documents, tools, unsupported events, restricted rows, credentials and instruction scaffolding excluded. No text truncation. Exact normalized records are authoritative hydration evidence; raw-source presence is reported separately and is not byte confirmation.', 'network': 'No inference network calls; local ONNX encoder', 'coverage': {}}
        atomic(gen / 'manifest.json', meta)
    meta.update(classification_hash=registry_hash, session_classifications=registry, classification_proofs=proofs, classification_counts=dict(collections.Counter(registry.values())), native_attribution_proof_sha256=policy.native_proof_sha256, dependency_hashes=policy.dependency_hashes)
    meta['scope'] = ARCHIVE_SCOPE
    atomic(gen / 'manifest.json', meta)
    db = open_db(gen / 'units.sqlite')
    schema(db)
    stats = collections.Counter()
    for row in db.execute('SELECT stats FROM parts'):
        stats.update(json.loads(row[0]))
    meta['planned_parts'] = len(files)
    meta['planned_source_bytes'] = sum(p.stat().st_size for p in files)
    atomic(gen / 'manifest.json', meta)
    last_progress = time.monotonic()
    for part in files:
        require_build_space(index, args.reserve_bytes)
        rel = str(part.relative_to(root))
        existing = db.execute('SELECT sha256,bytes,mtime_ns FROM parts WHERE path=?', (rel,)).fetchone()
        stat = part.stat()
        if existing:
            if (stat.st_size, stat.st_mtime_ns) != (existing[1], existing[2]) and file_hash(part) != existing[0]:
                raise ValueError('collected source part changed; start a new generation')
            continue
        local = collections.Counter()
        sha = file_hash(part)
        with part.open('rb') as stream:
            while True:
                require_build_space(index, args.reserve_bytes)
                offset = stream.tell()
                raw = stream.readline()
                if not raw:
                    break
                if not raw.strip():
                    continue
                local['records_observed'] += 1
                try:
                    record = json.loads(raw)
                except (ValueError, UnicodeError):
                    local['invalid_records'] += 1
                    continue
                if not isinstance(record, dict):
                    local['invalid_records'] += 1
                    continue
                policy.bind_native(record, raw, part, root)
                reason = policy.record_reason(record, root)
                if reason:
                    local['excluded_record:' + reason] += 1
                    continue
                source_state = policy.source_state(record, root)
                local[source_state] += 1
                locator = {'part': rel, 'part_sha256': sha, 'part_bytes': stat.st_size, 'part_mtime_ns': stat.st_mtime_ns, 'record_offset': offset, 'record_bytes': len(raw), 'record_line_sha256': digest(raw), 'raw_source_confirmation': source_state}
                for unit_number, unit in enumerate(record_units(record, locator, policy, enc, local)):
                    if unit_number % 256 == 0:
                        require_build_space(index, args.reserve_bytes)
                    old = db.execute('SELECT metadata FROM units WHERE id=?', (unit[0],)).fetchone()
                    if old:
                        previous, current = json.loads(old[0]), json.loads(unit[3])
                        historical = previous.pop('observations', [])
                        def observation_time(value):
                            try:
                                return dt.datetime.fromisoformat(value.get('observed_at', '').replace('Z', '+00:00')).timestamp()
                            except (ValueError, AttributeError):
                                return value.get('part_mtime_ns', 0) / 1e9
                        if observation_time(current) >= observation_time(previous):
                            current['observations'] = historical + [previous]
                            chosen = current
                        else:
                            previous['observations'] = historical + [current]
                            chosen = previous
                        db.execute('UPDATE units SET metadata=? WHERE id=?', (packed(chosen), unit[0]))
                        local['duplicate_unit_observations'] += 1
                    else:
                        db.execute('INSERT INTO units VALUES(?,?,?,?)', unit)
                    unit_metadata = json.loads(unit[3])
                    if unit_metadata['role'] == 'self':
                        for parent in unit_metadata['parents']:
                            db.execute('INSERT OR IGNORE INTO parent_versions VALUES(?)', (parent['parent_version_key'],))
                if time.monotonic() - last_progress >= 15:
                    current = report(gen, db, 'collecting', started, stats + local)
                    current['collecting_source_bytes'] = stream.tell()
                    current['collecting_source_total_bytes'] = stat.st_size
                    current['collection_counts_provisional'] = True
                    atomic(gen / 'manifest.json', current)
                    if args.progress:
                        print(packed({'state': 'collecting', 'generation': gen.name, 'processed_parts': current['processed_parts'], 'planned_parts': len(files), 'units': current['units'], 'pending_source_bytes': stream.tell(), 'pending_source_total_bytes': stat.st_size}), file=sys.stderr, flush=True)
                    last_progress = time.monotonic()
        after = part.stat()
        if (stat.st_size, stat.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            db.rollback()
            raise ValueError('source changed while collecting')
        db.execute('INSERT INTO parts VALUES(?,?,?,?,?)', (rel, sha, stat.st_size, stat.st_mtime_ns, packed(local)))
        db.commit()
        stats.update(local)
        current = report(gen, db, 'collecting', started, stats)
        if args.progress:
            print(packed({'state': 'collecting', 'generation': gen.name, 'processed_parts': current['processed_parts'], 'total_parts': len(files), 'units': current['units']}), file=sys.stderr, flush=True)
        if time.monotonic() - started >= args.budget_seconds:
            return current
    # Attach the append-only cache for bounded pending queries.
    require_build_space(index, args.reserve_bytes)
    db.execute('ATTACH DATABASE ? AS cache', (str(index / 'vectors.sqlite'),))
    meta = report(gen, db, 'embedding', started, stats)
    db.execute('CREATE TEMP TABLE pending AS SELECT u.vector_key,min(u.text) AS text FROM units u LEFT JOIN cache.vectors v ON v.key=u.vector_key AND v.model_hash=? WHERE v.key IS NULL GROUP BY u.vector_key', (model_key,))
    db.commit()
    embedded = db.execute('SELECT count(DISTINCT u.vector_key) FROM units u JOIN cache.vectors v ON v.key=u.vector_key AND v.model_hash=?', (model_key,)).fetchone()[0]
    pending_offset = 0
    last_progress = time.monotonic()
    while True:
        require_build_space(index, args.reserve_bytes)
        # Exhaust each SELECT before the independent cache connection commits.
        # A live cursor on an attached database can otherwise hold a read lock
        # across batches, even when selecting only the temporary pending table.
        page = db.execute('SELECT rowid,vector_key,text FROM pending WHERE rowid>? ORDER BY rowid LIMIT ?', (pending_offset, args.batch_size)).fetchall()
        if not page:
            break
        pending = [(row[1], row[2]) for row in page]
        encoded = enc.encode([row[1] for row in pending])
        for (key, _), vector in zip(pending, encoded):
            blob = vector.astype('<f4').tobytes()
            cache.execute('INSERT OR REPLACE INTO vectors VALUES(?,?,?,?)', (key, blob, digest(blob), model_key))
        cache.commit()
        pending_offset = page[-1][0]
        embedded += len(pending)
        current_time = time.monotonic()
        budget_reached = current_time - started >= args.budget_seconds
        if budget_reached or current_time - last_progress >= 15:
            meta = report(gen, db, 'embedding', started, stats, {'embedded_unique_texts': embedded})
            if args.progress:
                print(packed({'state': 'embedding', 'generation': gen.name, 'units': meta['units'], 'embedded_unique_texts': embedded, 'elapsed_seconds': meta['elapsed_seconds']}), file=sys.stderr, flush=True)
            last_progress = current_time
        if budget_reached:
            return meta
    if set(str(p.relative_to(root)) for p in inputs(root)) != set(row[0] for row in db.execute('SELECT path FROM parts')):
        raise ValueError('archive part set changed; resume to collect additions')
    final_registry, _ = source_classifications(inputs(root), policy, root)
    if digest(packed(final_registry).encode()) != registry_hash:
        raise ValueError('captured session classification changed; start a new generation using cached vectors')
    for rel, sha, size, mtime in db.execute('SELECT path,sha256,bytes,mtime_ns FROM parts'):
        part = allowed(root / rel)
        stat = part.stat()
        if (stat.st_size, stat.st_mtime_ns) != (size, mtime) and file_hash(part) != sha:
            raise ValueError('source changed before publication')
    if stats['invalid_records']:
        meta = report(gen, db, 'coverage-gaps', started, stats)
        return meta
    # Freeze this generation's vectors in its own database. Queries must never
    # read the shared cache while another build appends or checkpoints its WAL.
    vector_count, vector_bytes = db.execute('SELECT count(*),coalesce(sum(length(v.vector)+length(v.key)+length(v.vector_sha256)+length(v.model_hash)),0) FROM cache.vectors v JOIN (SELECT DISTINCT vector_key FROM units) u ON u.vector_key=v.key WHERE v.model_hash=?', (model_key,)).fetchone()
    # Payload plus conservative SQLite row/page overhead, doubled for the
    # generation copy and transaction journal. This uses stored byte lengths.
    require_build_space(index, args.reserve_bytes, 2 * (vector_bytes + vector_count * 256))
    db.execute('CREATE TABLE IF NOT EXISTS vectors(key TEXT PRIMARY KEY, vector BLOB NOT NULL, vector_sha256 TEXT NOT NULL, model_hash TEXT NOT NULL)')
    db.execute('DELETE FROM vectors')
    db.execute('INSERT INTO vectors SELECT DISTINCT v.key,v.vector,v.vector_sha256,v.model_hash FROM units u JOIN cache.vectors v ON u.vector_key=v.key AND v.model_hash=?', (model_key,))
    missing = db.execute('SELECT count(*) FROM units u LEFT JOIN vectors v ON u.vector_key=v.key WHERE v.key IS NULL').fetchone()[0]
    if missing:
        db.rollback()
        raise ValueError('generation vector snapshot is incomplete')
    db.commit()
    require_build_space(index, args.reserve_bytes)
    meta = report(gen, db, 'complete', started, stats)
    meta['unique_owner_message_versions'] = db.execute('SELECT count(*) FROM parent_versions').fetchone()[0]
    meta['embedded_unique_texts'] = embedded
    meta['vector_storage'] = 'Immutable vectors table in generation units.sqlite; shared cache is build-only'
    meta['completed_at'] = now()
    atomic(gen / 'manifest.json', meta)
    db.commit()
    db.close()
    cache.close()
    require_build_space(index, args.reserve_bytes, 8192)
    atomic(index / 'CURRENT.json', {'generation': gen.name})
    return meta


def active(args, root, index, policy):
    name = args.generation or json.loads((index / 'CURRENT.json').read_text())['generation']
    gen = allowed(index / 'generations' / name)
    if gen.parent != (index / 'generations').resolve():
        raise ValueError('generation outside index')
    meta = json.loads((gen / 'manifest.json').read_text())
    if meta['state'] != 'complete' or meta['root'] != str(root) or meta['policy_hash'] != policy.policy_hash:
        raise ValueError('generation incomplete or root/access policy changed')
    if policy.original_root is None and meta.get('original_root'):
        policy.original_root = allowed(meta['original_root'])
        policy.source_states.clear()
    policy.session_sources = meta.get('session_classifications', {})
    return gen, meta


def locate(root, metadata, policy):
    path = allowed(root / metadata['part'])
    if not path.is_relative_to(root / 'archive/corpus/records'):
        raise ValueError('source part outside corpus')
    stat = path.stat()
    if (stat.st_size, stat.st_mtime_ns) != (metadata['part_bytes'], metadata['part_mtime_ns']) and file_hash(path) != metadata['part_sha256']:
        raise ValueError('source part changed since indexing')
    with path.open('rb') as f:
        f.seek(metadata['record_offset'])
        raw = f.read(metadata['record_bytes'])
    if digest(raw) != metadata['record_line_sha256']:
        raise ValueError('source record changed')
    record = json.loads(raw)
    policy.bind_native(record, raw, path, root)
    if record.get('id') != metadata['record_id'] or policy.record_reason(record, root):
        raise ValueError('record identity or source policy changed')
    return record


def media_context(message, metadata, message_index):
    """Report media presence without disclosing filenames or delivery URLs."""
    raw = (message.get('extra') or {}).get('raw') or {}
    attachments = message.get('attachments') if 'attachments' in message else raw.get('attachments')
    embeds = message.get('embeds') if 'embeds' in message else raw.get('embeds')
    stickers = message.get('stickers') if 'stickers' in message else raw.get('stickers')
    pointer = metadata['message_pointer']
    if metadata['kind'] == 'event':
        base = '/export/messages/' + str(message_index)
    elif pointer == '/messages':
        base = '/messages/' + str(message_index)
    else:
        base = pointer
    if 'attachments' not in message:
        attachment_base = base + '/extra/raw/attachments' if metadata['kind'] != 'event' else base + '/attachments'
    else:
        attachment_base = base + '/attachments'
    safe = []
    if isinstance(attachments, list):
        for j, attachment in enumerate(attachments):
            if not isinstance(attachment, dict):
                continue
            identifier = attachment.get('id') or attachment.get('asset_id')
            identifier = str(identifier) if identifier is not None else None
            if identifier and not re.fullmatch(r'[A-Za-z0-9_:\-]+', identifier):
                identifier = None
            media_type = attachment.get('media_type') or attachment.get('contentType') or attachment.get('mime_type')
            if media_type and not re.fullmatch(r'[A-Za-z0-9.+_-]+/[A-Za-z0-9.+_-]+', str(media_type)):
                media_type = None
            size = next((attachment.get(k) for k in ('bytes', 'fileSizeBytes', 'size', 'fileSize') if isinstance(attachment.get(k), int) and not isinstance(attachment.get(k), bool)), None)
            safe.append({'id': identifier, 'media_type': media_type, 'bytes': size, 'source_pointer': attachment_base + '/' + str(j)})
    return {'attachment_count': len(attachments) if isinstance(attachments, list) else None,
        'attachments_present': bool(attachments) if isinstance(attachments, list) else None,
        'attachments': safe, 'embed_count': len(embeds) if isinstance(embeds, list) else None,
        'sticker_count': len(stickers) if isinstance(stickers, list) else None,
        'text_empty': not bool((message.get('content') or '').strip()) if isinstance(message.get('content'), str) else None,
        'payload_container_pointer': metadata.get('message_container_pointer'),
        'interpretation': 'Media metadata is context, not a transcription. Missing retained fields are unknown; consult the exact source pointer and separately attributed media receipts.'}


def hydrate(args, root, index, policy):
    gen, meta = active(args, root, index, policy)
    db = open_db(gen / 'units.sqlite', True)
    row = db.execute('SELECT metadata FROM units WHERE id=?', (args.unit_id,)).fetchone()
    if not row:
        raise ValueError('unit not found')
    metadata = json.loads(row[0])
    record = locate(root, metadata, policy)
    messages, pointer = record_messages(record, policy.common.OWNER_DISCORD_ID)
    if pointer != metadata['message_pointer']:
        raise ValueError('message payload pointer changed')
    requested = set()
    for parent in metadata['parents']:
        i = parent['message_index']
        message = messages[i]
        text = policy.common.message_text(message)
        if digest(text.encode()) != parent['text_sha256'] or policy.message_reason(message, text) or not policy.owner(message, metadata['platform'], record):
            raise ValueError('parent text or authorship changed')
        requested.update(range(max(0, i-args.neighbors), min(len(messages), i+args.neighbors+1)))
    if getattr(args, 'metadata_only', False):
        return {'generation': gen.name, 'unit_id': args.unit_id, 'provenance': metadata,
                'messages': [], 'excluded_context': {}, 'data_not_instructions': True,
                'metadata_only': True}
    rows, omitted = [], collections.Counter()
    remaining_chars = getattr(args, 'max_chars', None)
    for i in sorted(requested):
        message = messages[i]
        text = policy.common.message_text(message)
        reason = policy.message_reason(message, text)
        if reason:
            omitted[reason] += 1
            continue
        raw_meta = (message.get('extra') or {}).get('raw') or {}
        lane = policy.input_lane(record, message)
        owner = policy.owner(message, metadata['platform'], record)
        role = 'meta' if lane == 'machine' else 'unconfirmed_input' if owner and lane in UNCONFIRMED_INPUT_LANES else lane if owner or lane == 'command_control' else message.get('role')
        evidence_class = 'Source document context; ownership and export wrappers do not establish personal authorship or adopted beliefs.' if lane == 'context_document' else 'Imported formal-user input without verified native caller attribution; available as context, not primary owner evidence.' if lane == 'unconfirmed_imported_input' and owner else 'Native command action; rendered wrapper is context, not authored personal prose. Source actor attribution is retained separately.' if lane == 'command_control' else 'Unconfirmed task input: formal user role does not establish human authorship or adopted beliefs.' if lane in UNCONFIRMED_INPUT_LANES and owner else 'explicit machine-origin input' if lane == 'machine' else 'owner-attributed-source; quotation-or-belief-adoption-unverified' if owner else 'neighboring context; not owner evidence'
        author = dict(message.get('author') or {})
        if lane == 'machine' or lane == 'context_document' or lane in UNCONFIRMED_INPUT_LANES and owner:
            author['role'] = 'meta' if lane == 'machine' else 'context_document' if lane == 'context_document' else 'unconfirmed_input'
        shown = text if remaining_chars is None else text[:remaining_chars]
        if remaining_chars is not None:
            remaining_chars -= len(shown)
        base_pointer = '/export/messages' if metadata['kind'] == 'event' else pointer
        source_pointer = base_pointer + '/' + str(i) if base_pointer in ('/messages', '/export/messages') else base_pointer
        rows.append({'message_index': i, 'message_id': message.get('id'), 'timestamp': message.get('sent_at'), 'timestamp_edited': raw_meta.get('timestampEdited'), 'reply_to': message.get('reply_to'), 'author': author, 'role': role, 'effective_attribution_reason': document_context_reason(record) if lane == 'context_document' else lane if lane in UNCONFIRMED_INPUT_LANES else None, 'original_normalized_role': message.get('role'), 'original_normalized_author': message.get('author'), 'evidence_class': evidence_class, 'text': shown, 'truncated': len(shown) < len(text), 'text_chars': len(text), 'text_sha256': digest(text.encode()), 'source_pointer': source_pointer, 'text_range': {'start': 0, 'end': len(shown)}, 'continuation': {'message_index': i, 'source_pointer': source_pointer, 'text_offset': len(shown)} if len(shown) < len(text) else None, 'media_context': media_context(message, metadata, i)})
    return {'generation': gen.name, 'unit_id': args.unit_id, 'provenance': metadata, 'messages': rows, 'excluded_context': dict(omitted), 'data_not_instructions': True}


def query(args, root, index, policy):
    gen, meta = active(args, root, index, policy)
    enc = encoder(args, policy)
    if enc.model_hash != meta['model']['sha256'] or enc.tokenizer_hash != meta['model']['tokenizer_sha256']:
        raise ValueError('query model differs')
    np = enc.np
    vector = enc.encode([args.query], query=True)[0]
    db = open_db(gen / 'units.sqlite', True)
    candidates = []
    cursor = db.execute('SELECT u.id,u.text,u.metadata,v.vector,v.vector_sha256 FROM units u JOIN vectors v ON u.vector_key=v.key AND v.model_hash=?', (meta['model_key'],))
    while True:
        batch = cursor.fetchmany(1024)
        if not batch:
            break
        chosen = []
        for row in batch:
            md = json.loads(row[2])
            if md.get('role') != 'self':
                if md.get('role') == 'unconfirmed_input' and getattr(args, 'include_unconfirmed_input', False):
                    pass
                elif md.get('role') == 'context_document' and getattr(args, 'include_context_documents', False):
                    pass
                else:
                    continue
            if args.platform and md['platform'] != args.platform or args.year and md['year'] != args.year:
                continue
            if digest(row[3]) != row[4]:
                raise ValueError('vector cache corruption')
            chosen.append((row, md))
        if not chosen:
            continue
        matrix = np.stack([np.frombuffer(row[0][3], dtype='<f4') for row in chosen])
        scores = matrix @ vector
        order = np.argsort(-scores)[:args.limit*3]
        candidates.extend((float(scores[i]), chosen[i][0], chosen[i][1]) for i in order)
        candidates.sort(key=lambda item: -item[0])
        del candidates[args.limit*5:]
    leads, failures, seen_parents = [], [], set()
    for score, row, md in candidates:
        keys = {p['parent_version_key'] for p in md['parents']}
        if keys <= seen_parents:
            continue
        try:
            locate(root, md, policy)
        except (ValueError, OSError):
            failures.append({'unit_id': row[0], 'reason': 'source-stale-or-unavailable'})
            continue
        leads.append({'unit_id': row[0], 'similarity': score, 'preview': row[1][:args.preview_chars], 'provenance': md})
        seen_parents.update(keys)
        if len(leads) == args.limit:
            break
    return {'kind': 'dense-local-transformer', 'generation': gen.name, 'scope': meta['scope'], 'coverage': meta['coverage'], 'leads': leads, 'failures': failures, 'interpretation': 'Similarity locates evidence; it is not confidence, belief adoption, or a personality judgment. Hydrate originals and neighboring turns before interpretation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--index', default=str(DEFAULT_INDEX))
    parser.add_argument('--original-root', help='Origin archive for raw-source availability; normalized hydration stays in --root.')
    parser.add_argument('--model', default=str(MODEL))
    parser.add_argument('--threads', type=int, default=6)
    parser.add_argument('--exclude-source-prefix', action='append', default=[])
    parser.add_argument('--native-attribution-proof', help='Independent native-header proof JSONL bound to exact normalized records.')
    parser.add_argument('--native-attribution-proof-sha256', help='Required SHA256 pin for the native attribution proof.')
    subs = parser.add_subparsers(dest='command', required=True)
    b = subs.add_parser('build')
    b.add_argument('--resume')
    b.add_argument('--batch-size', type=int, default=24)
    b.add_argument('--budget-seconds', type=float, default=600)
    b.add_argument('--progress', action='store_true')
    b.add_argument('--reserve-bytes', type=int, default=4 * 1024 ** 3,
                   help='Free index bytes retained during collection, embedding and publication.')
    migration = subs.add_parser('migrate-document-policy', help='Fork an audited predecessor and recollect only changed document parts.')
    migration.add_argument('--from-generation', required=True)
    migration.add_argument('--prior-code', required=True)
    migration.add_argument('--prior-code-sha256', required=True)
    migration.add_argument('--compatibility-receipt', required=True)
    migration.add_argument('--compatibility-receipt-sha256', required=True)
    migration.add_argument('--dependency-pin', action='append', default=[], help='Required common=SHA256 and encoder=SHA256 dependency pins.')
    migration.add_argument('--reserve-bytes', type=int, default=4 * 1024 ** 3)
    migration.add_argument('--prior-model', help='Original model directory for a separately audited model-only transition.')
    migration.add_argument('--model-transition-receipt')
    migration.add_argument('--model-transition-receipt-sha256')
    for name in ('status', 'query', 'hydrate'):
        p = subs.add_parser(name)
        p.add_argument('--generation')
        if name == 'status':
            p.add_argument('--compact', action='store_true', help='Return bounded metadata without per-source classification maps.')
        elif name == 'query':
            p.add_argument('query')
            p.add_argument('--limit', type=int, default=8)
            p.add_argument('--platform')
            p.add_argument('--year')
            p.add_argument('--preview-chars', type=int, default=280)
            p.add_argument('--include-unconfirmed-input', action='store_true', help='Include task inputs whose human authorship is unconfirmed.')
            p.add_argument('--include-context-documents', action='store_true', help='Include source documents whose ownership does not establish personal authorship.')
        elif name == 'hydrate':
            p.add_argument('--unit-id', required=True)
            p.add_argument('--neighbors', type=int, default=3)
            p.add_argument('--metadata-only', action='store_true', help='Verify parent hashes and return provenance without message text.')
            p.add_argument('--max-chars', type=int, help='Bound total returned text; retain full hashes, lengths and continuation locators.')
    args = parser.parse_args()
    if args.threads < 1 or getattr(args, 'batch_size', 1) not in range(1, 65) or getattr(args, 'limit', 1) not in range(1, 101) or getattr(args, 'neighbors', 0) not in range(0, 21):
        parser.error('invalid capacity bound')
    if getattr(args, 'max_chars', None) is not None and not 1 <= args.max_chars <= 20000:
        parser.error('max chars must be between 1 and 20000')
    if getattr(args, 'reserve_bytes', 0) < 0:
        parser.error('reserve bytes must be nonnegative')
    try:
        root, index = allowed(args.root), allowed(args.index)
        if index.is_relative_to(root):
            raise ValueError('index must stay outside archive')
        if args.command in {'build', 'migrate-document-policy'}:
            private(index)
            private(index / 'generations')
        if not args.original_root and (root / 'source-manifest.json').is_file():
            source_manifest = json.loads(allowed(root / 'source-manifest.json').read_text())
            origins = {p.get('origin_root') for p in source_manifest.get('parts', []) if p.get('origin_root')}
            if len(origins) == 1:
                args.original_root = next(iter(origins))
        policy = Policy(args)
        if args.command == 'build':
            result = build(args, root, index, policy)
        elif args.command == 'migrate-document-policy':
            result = migrate_document_policy(args, root, index, policy)
        elif args.command == 'status':
            if args.generation:
                gen = allowed(index / 'generations' / args.generation)
                if gen.parent != (index / 'generations').resolve():
                    raise ValueError('generation outside index')
                result = json.loads((gen / 'manifest.json').read_text())
                if result['root'] != str(root) or result['policy_hash'] != policy.policy_hash:
                    raise ValueError('root or access policy changed')
            else:
                gen, result = active(args, root, index, policy)
            if args.compact:
                result = compact_status(result, gen)
        elif args.command == 'query':
            result = query(args, root, index, policy)
        else:
            result = hydrate(args, root, index, policy)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get('state') != 'coverage-gaps' else 3
    except (ValueError, OSError, sqlite3.Error, KeyError) as error:
        print(json.dumps({'state': 'failed-closed', 'error_type': type(error).__name__, 'error': str(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
