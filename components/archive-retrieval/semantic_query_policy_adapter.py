#!/usr/bin/env python3
"""Query a pinned archive backend without transferring every unit's full text.

The published backend, metadata and index remain unchanged. This adapter adds
a qualified whole-parent native control exclusion after source verification and
retains joined-row batches, vector checks, ranking and source verification.
It supports query, status and hydrate; it cannot build or migrate generations.
"""
from __future__ import annotations

import argparse
import contextlib
import gc
import hashlib
import importlib.util
import io
import json
import os
import re
from pathlib import Path
import sys
import time
from types import SimpleNamespace

sys.dont_write_bytecode = True

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_INTEGRITY = json.loads((PACKAGE_ROOT / 'assets/module-integrity.json').read_text())
BACKEND = Path(__file__).resolve().with_name('semantic_archive.py')
COMMON = BACKEND.with_name('common.py')
ENCODER = PACKAGE_ROOT / 'scripts/semantic_retrieve_portable.py'
VIEW = BACKEND.with_name('semantic_query_view.py')
ROLES = BACKEND.with_name('native_message_roles.py')
ROLES_SHA256 = _INTEGRITY['components/archive-retrieval/native_message_roles.py']
BASELINE_ADAPTER_SHA256 = _INTEGRITY['components/archive-retrieval/semantic_query_adapter.py']
VIEW_SHA256 = _INTEGRITY['components/archive-retrieval/semantic_query_view.py']
_policy_path = Path(os.environ.get('PYE_ARCHIVE_POLICY_FILE') or Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'protecting-your-energy/archive-policy.json').expanduser()
if os.environ.get('PYE_ARCHIVE_POLICY_FILE') and not _policy_path.exists():
    raise ValueError('configured archive policy is unavailable')
_private_policy = json.loads(_policy_path.read_text()) if _policy_path.exists() else {}
if not isinstance(_private_policy, dict):
    raise ValueError('archive policy must be an object')
NOTES_ACCOUNT_RULE = os.environ.get('PYE_NOTES_ACCOUNT_RULE') or _private_policy.get('notes_account_rule', '')
if not isinstance(NOTES_ACCOUNT_RULE, str):
    raise ValueError('notes_account_rule must be a string')
DOCUMENT_POLICY_ID = 'icloud-account-attribution-context-v1'
DOCUMENT_CONTEXT_REASON = 'saved-account-note-without-independent-authorship-basis'
PINS = (
    (ROLES, ROLES_SHA256),
    (BACKEND, _INTEGRITY['components/archive-retrieval/semantic_archive.py']),
    (COMMON, _INTEGRITY['components/archive-retrieval/common.py']),
    (ENCODER, _INTEGRITY['scripts/semantic_retrieve_portable.py']),
)


class ReadOnlyParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        self.add_argument('--query-mode', choices=('dense', 'lexical'), default='dense')
        self.add_argument('--scope-unit-id')
        self.add_argument('--scope-scan-budget', type=float, default=20)
        self.add_argument('--message-rerank', action='store_true')
        self.add_argument('--message-rerank-budget', type=float, default=30)
        self.add_argument('--query-view-manifest-sha256',
                          help='Independent SHA256 pin for the query view manifest.')
        parsed = super().parse_args(args, namespace)
        if parsed.command not in {'query', 'status', 'hydrate'}:
            self.error('this adapter supports only query, status and hydrate')
        if parsed.command == 'query':
            if parsed.message_rerank and (not parsed.scope_unit_id or parsed.query_mode != 'dense'
                    or not 1 <= parsed.message_rerank_budget <= 60):
                self.error('message reranking requires dense conversation scope and bounded budget')
            if parsed.scope_unit_id and (not re.fullmatch('[0-9a-f]{64}', parsed.scope_unit_id)
                    or parsed.query_mode != 'dense' or not 1 <= parsed.scope_scan_budget <= 30):
                self.error('conversation scope requires a valid unit, dense mode and bounded scan budget')
            pin = parsed.query_view_manifest_sha256
            if not isinstance(pin, str) or len(pin) != 64 or any(c not in '0123456789abcdef' for c in pin):
                self.error('query requires a lowercase hexadecimal query view manifest SHA256 pin')
        return parsed


def load_backend():
    sources = {}
    for path, expected in PINS:
        source = path.read_bytes()
        if hashlib.sha256(source).hexdigest() != expected:
            raise ValueError('query adapter dependency changed: ' + path.name)
        sources[path] = source
    spec = importlib.util.spec_from_file_location('pinned_semantic_archive', BACKEND)
    if spec is None or spec.loader is None:
        raise ValueError('query adapter backend cannot be loaded')
    backend = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = backend
    exec(compile(sources[BACKEND], str(BACKEND), 'exec'), backend.__dict__)
    parser_module = vars(argparse).copy()
    parser_module['ArgumentParser'] = ReadOnlyParser
    backend.argparse = SimpleNamespace(**parser_module)
    roles = SimpleNamespace()
    exec(compile(sources[ROLES], str(ROLES), 'exec'), roles.__dict__)
    backend.native_role_classifier = roles.classify_native_message
    backend.native_span_classifier = roles.classify_native_span
    backend.query = lambda args, root, index, policy: query(backend, args, root, index, policy)
    original_hydrate = backend.hydrate
    backend.hydrate = lambda args, root, index, policy: hydrate(
        backend, original_hydrate, args, root, index, policy)
    return backend


def load_view():
    source = VIEW.read_bytes()
    if hashlib.sha256(source).hexdigest() != VIEW_SHA256:
        raise ValueError('query view helper changed')
    spec = importlib.util.spec_from_file_location('pinned_semantic_query_view', VIEW)
    if spec is None or spec.loader is None:
        raise ValueError('query view helper cannot be loaded')
    helper = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = helper
    exec(compile(source, str(VIEW), 'exec'), helper.__dict__)
    return helper


def facet_matches(present, value, wanted, name):
    if not wanted:
        return True
    if not present:
        raise KeyError(name)
    # Explicit null remains unequal to the CLI's string facet arguments.
    return value == wanted


def projected_value(metadata, name):
    value = metadata.get(name)
    return value if isinstance(value, str) else None


def verify_metadata(backend, row, projected):
    if row[3] != projected['vector_key'] or backend.digest(row[2].encode('utf-8')) != projected['metadata_sha256']:
        raise ValueError('query view candidate binding differs')
    metadata = json.loads(row[2])
    if not isinstance(metadata, dict):
        raise ValueError('unit metadata must be an object')
    for name in ('role', 'platform', 'year'):
        if projected_value(metadata, name) != projected[name]:
            raise ValueError('query view candidate fields differ')
    for name in ('platform', 'year'):
        if int(name in metadata) != projected[name + '_present']:
            raise ValueError('query view candidate presence differs')
    return metadata


class LocateMemo:
    """Retain one successful large decode within a query, never raw bytes.

    The 256 MiB ceiling bounds source bytes, not the decoded Python heap.
    Smaller records do not displace a larger verified record.
    """
    def __init__(self):
        self.clear()

    def clear(self):
        self.key = self.record = None
        self.size = 0

    def locate(self, backend, root, metadata, policy):
        original_json = backend.json
        decoded = None
        try:
            key = (id(policy), str(root.resolve()),
                   str(backend.allowed(root / metadata['part'])),
                   metadata['record_offset'], metadata['record_bytes'],
                   metadata['record_id'], metadata['record_line_sha256'])

            def loads(raw, *args, **kwargs):
                nonlocal decoded
                # Frozen locate has already read and checked these exact bytes.
                if (isinstance(raw, bytes) and not args and not kwargs
                        and key == self.key and len(raw) == self.size):
                    self.record.pop(backend.NATIVE_ATTRIBUTION, None)
                    decoded = self.record
                else:
                    if isinstance(raw, bytes) and len(raw) >= 1024 ** 2 and not args and not kwargs:
                        # Plain JSON decoding creates acyclic containers. Keep
                        # collection suspension local to this default decoder.
                        was_enabled = gc.isenabled()
                        if was_enabled:
                            gc.disable()
                        try:
                            decoded = original_json.loads(raw)
                        finally:
                            if was_enabled:
                                gc.enable()
                    else:
                        decoded = original_json.loads(raw, *args, **kwargs)
                return decoded

            proxy = vars(original_json).copy()
            proxy['loads'] = loads
            backend.json = SimpleNamespace(**proxy)
            record = backend.locate(root, metadata, policy)
            size = metadata['record_bytes']
            if (record is decoded and 1024 ** 2 <= size <= 256 * 1024 ** 2
                    and size >= self.size):
                self.key, self.record, self.size = key, record, size
            return record
        except BaseException:
            self.clear()
            raise
        finally:
            backend.json = original_json


def filtered_scan(view, model_key, args, *, with_vectors=True, scope_units=None):
    """Filter scalars while retaining each row's original 1024-row batch ID."""
    roles = ['self']
    if getattr(args, 'include_unconfirmed_input', False):
        roles.append('unconfirmed_input')
    if getattr(args, 'include_context_documents', False):
        roles.append('context_document')
    placeholders = ','.join('?' for _ in roles)
    base_where = 'v.model_hash=? AND u.role IN (' + placeholders + ')'
    parameters = [model_key, *roles]
    join = ' FROM units u JOIN vectors v ON u.vector_key=v.key WHERE '
    missing, missing_parameters = [], []
    if args.platform:
        missing.append('u.platform_present=0')
    if args.year:
        if args.platform:
            missing.append('(u.platform=? AND u.year_present=0)')
            missing_parameters.append(args.platform)
        else:
            missing.append('u.year_present=0')
    if missing:
        invalid_rows = view.execute('SELECT u.unit_id,u.metadata_sha256,u.platform_present,u.year_present' + join
                               + base_where + ' AND (' + ' OR '.join(missing)
                               + ') ORDER BY u.ordinal' + (' LIMIT 1' if scope_units is None else ''),
                               parameters + missing_parameters)
        for invalid in invalid_rows:
            if scope_units is not None:
                expected = scope_units.get(invalid['unit_id'])
                if expected is None:
                    continue
                if expected != invalid['metadata_sha256']:
                    raise ValueError('scoped query view metadata binding differs')
            raise KeyError('platform' if args.platform and not invalid['platform_present'] else 'year')
    where = [base_where]
    if args.platform:
        where.append('u.platform=?')
        parameters.append(args.platform)
    if args.year:
        where.append('u.year=?')
        parameters.append(args.year)
    transfer_vectors = with_vectors and scope_units is None
    sql = '''SELECT u.ordinal AS original_ordinal,u.unit_id,u.vector_key,
        u.metadata_sha256,u.role,u.platform,u.year,u.platform_present,
        u.year_present''' + (',v.vector,v.vector_sha256' if transfer_vectors else '') + join + ' AND '.join(where) + ' ORDER BY u.ordinal'
    cursor = view.execute(sql, parameters)
    group, chosen = None, []
    while True:
        rows = cursor.fetchmany(1024)
        if not rows:
            break
        for row in rows:
            if scope_units is not None:
                expected = scope_units.get(row['unit_id'])
                if expected is None:
                    continue
                if row['metadata_sha256'] != expected:
                    raise ValueError('scoped query view metadata binding differs')
                if with_vectors:
                    cached = view.execute('SELECT vector,vector_sha256 FROM vectors WHERE key=? AND model_hash=?',
                                          (row['vector_key'], model_key)).fetchone()
                    if cached is None:
                        raise ValueError('scoped vector unavailable')
                    row = {**dict(row), **dict(cached)}
            current = row['original_ordinal'] // 1024
            if group is not None and current != group:
                yield chosen
                chosen = []
            group = current
            chosen.append(row)
    if chosen:
        yield chosen


def conversation_scope(backend, db, root, policy, args):
    """Resolve one captured conversation before ranking, without index writes."""
    uid = getattr(args, 'scope_unit_id', None)
    if not uid:
        return None, None
    started = time.monotonic()
    deadline = started + args.scope_scan_budget
    row = db.execute('SELECT metadata FROM units WHERE id=?', (uid,)).fetchone()
    if row is None:
        raise ValueError('scope anchor unavailable')
    md = json.loads(row[0])
    source = md.get('source', {})
    session, path, sha = md.get('session_key'), source.get('archive_path'), source.get('source_sha256')
    kind = md.get('kind')
    supported = kind == 'conversation' or (kind == 'event' and md.get('platform') == 'discord'
                    and source.get('family') == 'discord_channel_snapshot')
    if (not supported or not isinstance(session, str) or not session
            or not isinstance(path, str) or not path or not isinstance(sha, str)
            or not re.fullmatch('[0-9a-f]{64}', sha)):
        raise ValueError('scope requires captured conversation metadata')
    backend.locate(root, md, policy)
    units = {}
    db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 10000)
    try:
        cursor = db.execute("SELECT id,metadata FROM units WHERE json_extract(metadata,'$.kind')=? AND json_extract(metadata,'$.session_key')=? AND json_extract(metadata,'$.source.archive_path')=? AND json_extract(metadata,'$.source.source_sha256')=?", (kind, session, path, sha))
        for identifier, raw in cursor:
            if time.monotonic() >= deadline:
                raise ValueError('scope metadata scan budget exhausted')
            units[identifier] = backend.digest(raw.encode('utf-8'))
    except Exception as error:
        if time.monotonic() >= deadline:
            raise ValueError('scope metadata scan budget exhausted') from error
        raise
    finally:
        db.set_progress_handler(None, 0)
    if uid not in units:
        raise ValueError('scope anchor metadata selection differs')
    return units, {'scope_unit_id': uid, 'session_key': session, 'source_archive_path': path,
        'source_sha256': sha, 'selected_capture_units': len(units),
        'metadata_scan_seconds': round(time.monotonic() - started, 3),
        'metadata_scan_budget_seconds': args.scope_scan_budget,
        'filter_stage': 'before vector matrices and both ranking truncation stages',
        'selected_normalized_units': len(units), 'raw_capture_membership_verified': False,
        'scope': 'Exact normalized conversation provenance group; not verified raw capture membership or all participant history',
        'anchor_normalized_source_verified': True, 'original_bytes_verified': False}


def rerank_messages(backend, enc, vector, leads, records, policy, args):
    """Score verified eligible normalized parent windows; never cache or alter sources."""
    started = time.monotonic()
    deadline = started + args.message_rerank_budget
    texts, links = {}, {}
    for lead in leads:
        if time.monotonic() >= deadline:
            raise ValueError('message rerank deferred: time budget exhausted before complete scoring')
        uid = lead['unit_id']
        md = lead['provenance']
        record = records[uid]
        messages, _ = backend.record_messages(record, policy.common.OWNER_DISCORD_ID)
        linked = set()
        for parent in md['parents']:
            message = messages[parent['message_index']]
            text = policy.common.message_text(message)
            native = parent.get('native_message_policy', {})
            if (parent.get('attribution_class') != 'self' or md.get('role') != 'self'
                    or native.get('owner_evidence_eligible') is False
                    or native.get('matched_control_characters', 0)
                    or parent.get('primary_owner_evidence') is False
                    or not policy.owner(message, md['platform'], record)
                    or policy.message_reason(message, text)):
                continue
            left, right = parent['char_start'], parent['char_end']
            if (backend.digest(text.encode()) != parent['text_sha256']
                    or str(message.get('id')) != parent['message_id']
                    or not 0 <= left < right <= len(text)):
                raise ValueError('message rerank parent binding differs')
            window = text[left:right]
            if len(enc.tokenizer.encode(window).ids) > enc.limit:
                raise ValueError('message rerank deferred: eligible parent exceeds tokenizer bound')
            key = backend.digest(window.encode())
            texts.setdefault(key, window)
            linked.add(key)
            if len(texts) > 1024:
                raise ValueError('message rerank deferred: distinct parent window bound exceeded')
        links[uid] = linked
    keys = list(texts)
    values = []
    for offset in range(0, len(keys), 16):
        if time.monotonic() >= deadline:
            raise ValueError('message rerank deferred: time budget exhausted before complete scoring')
        values.extend(enc.encode([texts[k] for k in keys[offset:offset + 16]], query=False))
    if time.monotonic() >= deadline:
        raise ValueError('message rerank deferred: time budget exhausted before complete scoring')
    scores = {key: float(values[index] @ vector) for index, key in enumerate(keys)}
    ranked = []
    for lead in leads:
        if not links[lead['unit_id']]:
            continue
        score = max(scores[key] for key in links[lead['unit_id']])
        ranked.append({**lead, 'packed_similarity': lead['similarity'], 'parent_similarity': score,
            'similarity': score, 'ranking_method': 'maximum-eligible-normalized-parent-window-cosine'})
    ranked.sort(key=lambda row: -row['similarity'])
    return ranked, {'status': 'complete', 'candidate_units': len(leads),
        'scored_candidate_units': len(ranked), 'distinct_parent_windows': len(keys),
        'encoded_parent_windows': len(values), 'parent_window_limit': 1024,
        'seconds': round(time.monotonic() - started, 3), 'budget_seconds': args.message_rerank_budget,
        'rank_scope': 'Top50 packed candidates after source and native-role qualification; not complete capture recall',
        'raw_capture_membership_verified': False, 'index_or_cache_writes': False}


def document_source_policy(record):
    """Scope the correction to the known account-only Notes importer assertion.

    This does not decide whether the owner composed or adopted a saved note.
    Independent explicit authorship assertions retain their existing policy.
    """
    source = record.get('source') or {}
    extra = record.get('extra') or {}
    ir = extra.get('ir_v2_meta') or {}
    if (record.get('kind') != 'document' or record.get('type') != 'doc.note'
            or source.get('platform') != 'icloud' or source.get('family') != 'icloud_notes'
            or ir.get('self_labels_verified') is not True
            or ir.get('self_label_rule') != NOTES_ACCOUNT_RULE):
        return None
    wrapped = extra.get('wrapped_message') or {}
    raw = (wrapped.get('extra') or {}).get('raw') or {}
    if any(meta.get('authorship_verified') is True
           and isinstance(meta.get('authorship_basis'), str)
           and meta['authorship_basis'].strip()
           and meta['authorship_basis'].strip() != NOTES_ACCOUNT_RULE for meta in (raw, ir)):
        return None
    return {'schema_version': 1, 'policy_id': DOCUMENT_POLICY_ID,
        'source_kind': 'document', 'record_type': 'doc.note',
        'platform': 'icloud', 'source_family': 'icloud_notes',
        'effective_input_lane': 'context_document', 'primary_owner_evidence': False,
        'reason': DOCUMENT_CONTEXT_REASON,
        'archived_account_attribution': {'self_labels_verified': True,
            'self_label_rule': NOTES_ACCOUNT_RULE,
            'account_field_present': 'account' in source,
            'account_value_present': source.get('account') is not None},
        'authorship_established': False, 'adoption_established': False,
        'interpretation': 'Account attribution alone establishes neither composition nor adoption; actual authorship and adoption remain unresolved, not denied.',
        'frozen_provenance_preserved_separately': True, 'original_origin_verified': False}


def qualify_document_parents(backend, record, metadata, policy, receipt):
    """Verify the original normalized bindings before applying a document lane."""
    if (metadata.get('kind') != record.get('kind')
            or metadata.get('platform') != record['source']['platform']
            or metadata.get('source') != record['source']):
        raise ValueError('document policy source binding changed')
    messages, pointer = backend.record_messages(record, policy.common.OWNER_DISCORD_ID)
    if pointer != metadata['message_pointer']:
        raise ValueError('document policy message pointer changed')
    parents, qualifications = [], []
    for parent in metadata['parents']:
        i = parent['message_index']
        if type(i) is not int or not 0 <= i < len(messages):
            raise ValueError('document policy parent index invalid')
        message = messages[i]
        text = policy.common.message_text(message)
        left, right = parent['char_start'], parent['char_end']
        if (backend.digest(text.encode('utf-8')) != parent['text_sha256']
                or str(message.get('id')) != parent['message_id']
                or message.get('sent_at') != parent.get('timestamp')
                or type(left) is not int or type(right) is not int
                or not 0 <= left < right <= len(text)
                or policy.message_reason(message, text)
                or not policy.owner(message, metadata['platform'], record)):
            raise ValueError('document policy full parent binding changed')
        qualification = {'message_index': i, 'message_id': parent['message_id'],
            'text_sha256': parent['text_sha256'], 'matched_character_range': [left, right],
            'effective_role': 'context_document', 'effective_input_lane': 'context_document',
            'primary_owner_evidence': False, 'authorship_established': False,
            'adoption_established': False, 'normalized_full_parent_verified': True}
        qualifications.append(qualification)
        parents.append({**parent, 'frozen_role': parent.get('role'),
            'frozen_attribution_class': parent.get('attribution_class'),
            'role': 'context_document', 'attribution_class': 'context_document',
            'author': {**(parent.get('author') or {}), 'role': 'context_document'},
            'primary_owner_evidence': False, 'source_policy': qualification})
    if not parents:
        raise ValueError('document policy indexed parents missing')
    receipt = {**receipt, 'parent_classifications': qualifications,
        'normalized_source_record_verified': True,
        'qualification_scope': 'Exact normalized record and full indexed parent hashes; account-only importer label, not independent author identity or original capture proof.'}
    effective = {**metadata, 'parents': parents, 'frozen_role': metadata.get('role'),
        'frozen_input_attribution_class': metadata.get('input_attribution_class'),
        'role': 'context_document', 'input_lane': 'context_document',
        'input_attribution_class': 'context_document', 'primary_owner_evidence': False,
        'effective_attribution_reason': DOCUMENT_CONTEXT_REASON,
        'evidence_class': 'Saved account-attributed Notes context; composition and adoption remain unresolved.'}
    return effective, None, receipt


def policy_fields(native_policy, document_policy):
    if document_policy is not None:
        return {'source_policy': document_policy}
    return {'native_message_policy': native_policy}


def document_query_receipt(args, classified, excluded, returned):
    return {'schema_version': 1, 'policy_id': DOCUMENT_POLICY_ID,
        'scope': 'Verified candidate normalized Notes records only; account-only labels are nonprimary document context.',
        'classified_candidate_units': classified,
        'excluded_context_document_units': excluded, 'returned_context_document_units': returned,
        'include_context_documents': bool(args.include_context_documents),
        'filter_stage': 'after pinned frozen-role candidate scan, ranking/matching and source verification',
        'candidate_limit': 50 if getattr(args, 'message_rerank', False) else args.limit * 5, 'refill_after_exclusion': False,
        'frozen_index_roles_unchanged': True, 'all_index_units_classified': False,
        'original_origin_verified': False,
        'coverage_meaning': 'Frozen publication counters remain unchanged; candidate filtering can leave fewer leads and does not establish archive absence.'}


def qualify_parents(backend, record, metadata, policy):
    """Return effective matched provenance and a separate qualification receipt."""
    document_policy = document_source_policy(record)
    if document_policy is not None:
        return qualify_document_parents(backend, record, metadata, policy, document_policy)
    messages, pointer = backend.record_messages(record, policy.common.OWNER_DISCORD_ID)
    if pointer != metadata['message_pointer']:
        raise ValueError('native policy message pointer changed')
    qualifications, parents = [], []
    for parent in metadata['parents']:
        i = parent['message_index']
        if type(i) is not int or not 0 <= i < len(messages):
            raise ValueError('native policy parent index invalid')
        message = messages[i]
        text = policy.common.message_text(message)
        if backend.digest(text.encode('utf-8')) != parent['text_sha256']:
            raise ValueError('native policy full parent text changed')
        result = backend.native_span_classifier(message, metadata['platform'],
                                                parent['char_start'], parent['char_end'])
        qualifications.append({'message_index': i, 'message_id': message.get('id'),
                               'text_sha256': parent['text_sha256'], **result})
        effective = {**parent, 'native_message_policy': result,
                     'frozen_role': parent.get('role'),
                     'frozen_attribution_class': parent.get('attribution_class')}
        if result['effective_role'] is not None:
            effective.update(role=result['effective_role'],
                             attribution_class=result['effective_input_attribution_class'],
                             author={**(parent.get('author') or {}), 'role': result['effective_role']},
                             primary_owner_evidence=False)
        parents.append(effective)
    if not qualifications:
        raise ValueError('native policy indexed parents missing')
    eligible = [row for row in qualifications if row['owner_evidence_eligible']]
    controls = [row for row in qualifications if not row['owner_evidence_eligible']]
    mixed = bool(controls and eligible) or any(row['effective_input_attribution_class'] == 'unconfirmed_input'
                                              for row in qualifications)
    effective = {**metadata, 'parents': parents}
    primary = (metadata.get('role') == 'self' and metadata.get('primary_owner_evidence') is not False
               and any(parent.get('attribution_class') == 'self'
                       and parent['native_message_policy']['effective_role'] is None for parent in parents))
    if not primary and any(row['effective_role'] is not None for row in qualifications):
        lane = 'unconfirmed_input' if eligible else 'command_control'
        effective.update(role='unconfirmed_input' if eligible else 'meta',
                         input_attribution_class=lane, primary_owner_evidence=False,
                         effective_attribution_reason='native-message-source-role-policy')
    receipt = {'helper_sha256': ROLES_SHA256,
            'policy_scope': 'full normalized Codex messages and exact matched parent spans; no original origin/adoption proof',
            'owner_evidence_eligible': bool(eligible), 'mixed_control_content': mixed,
            'owner_eligibility_meaning': 'not wholly excluded as native control; not proof of identity or all-span authorship',
            'effective_eligible_parent_indices': list(dict.fromkeys(row['message_index'] for row in eligible)),
            'effective_eligible_parent_ids': list(dict.fromkeys(row['message_id'] for row in eligible)),
            'excluded_control_parent_indices': list(dict.fromkeys(row['message_index'] for row in controls)),
            'excluded_control_parent_ids': list(dict.fromkeys(row['message_id'] for row in controls)),
            'parent_classifications': qualifications,
            'frozen_provenance_preserved_separately': True, 'original_origin_verified': False,
            'requires_hydration_policy_overlay': any(row['effective_role'] is not None for row in qualifications)}
    return effective, receipt, None


def project_control_text(backend, row, classification):
    """Keep exact non-control fragments; separate source hashes from display."""
    start, end = row['text_range']['start'], row['text_range']['end']
    ranges = classification['matched_control_ranges']
    if not classification['owner_evidence_eligible'] and not ranges:
        ranges = [[start, end]]
    if not ranges:
        return row
    pieces, cursor = [], start
    for left, right in ranges:
        if cursor < left:
            pieces.append({'source_character_range': [cursor, left],
                           'text': row['text'][cursor-start:left-start]})
        cursor = max(cursor, right)
    if cursor < end:
        pieces.append({'source_character_range': [cursor, end], 'text': row['text'][cursor-start:end-start]})
    shown = '\n'.join(piece['text'] for piece in pieces)
    return {**row, 'text': shown, 'text_range': None, 'display_segments': pieces,
            'display_text_sha256': backend.digest(shown.encode('utf-8')),
            'text_sha256_scope': 'Full normalized source message before policy display projection',
            'policy_display_projection': True, 'control_text_suppressed': True,
            'original_display_range': row['text_range'],
            'display_join_convention': 'Newline between retained source fragments; not contiguous source text',
            'display_scope': 'Control spans omitted; exact retained source ranges supplied; original source remains unchanged'}


def hydrate(backend, original_hydrate, args, root, index, policy):
    """Return effective matched provenance for metadata and full hydration."""
    original_locate = backend.locate
    captured = None
    def locate(*parameters):
        nonlocal captured
        captured = original_locate(*parameters)
        return captured
    backend.locate = locate
    try:
        result = original_hydrate(args, root, index, policy)
    finally:
        backend.locate = original_locate
    if captured is None:
        raise ValueError('native hydration policy source unavailable')
    metadata = result['provenance']
    effective, qualified, document_policy = qualify_parents(backend, captured, metadata, policy)
    messages, _ = backend.record_messages(captured, policy.common.OWNER_DISCORD_ID)
    parent_indices = {parent['message_index'] for parent in effective['parents']}
    rows = []
    for original in result['messages']:
        i = original['message_index']
        if type(i) is not int or not 0 <= i < len(messages):
            raise ValueError('native hydration policy context index invalid')
        if document_policy is not None:
            rows.append({**original, 'original_display_attribution': {
                key: original.get(key) for key in ('role', 'author', 'evidence_class', 'effective_attribution_reason')},
                'role': 'context_document', 'effective_input_attribution_class': 'context_document',
                'author': {**(original.get('author') or {}), 'role': 'context_document'},
                'effective_attribution_reason': DOCUMENT_CONTEXT_REASON,
                'evidence_class': effective['evidence_class'], 'source_policy': document_policy,
                'owner': False, 'primary_owner_evidence': False,
                'indexed_source_parent': i in parent_indices, 'indexed_owner_parent': False})
            continue
        source_range = original['text_range']
        classification = backend.native_span_classifier(messages[i], metadata['platform'],
                                                        source_range['start'], source_range['end'])
        matched = [parent['native_message_policy'] for parent in effective['parents']
                   if parent['message_index'] == i]
        # Indexed control-only spans cannot regain owner status from surrounding prose.
        if matched and all(not item['owner_evidence_eligible'] for item in matched):
            classification = {**classification, 'owner_evidence_eligible': False,
                              'effective_role': 'meta', 'effective_input_attribution_class': 'command_control'}
        row = {**original, 'native_message_policy': {**classification, 'helper_sha256': ROLES_SHA256},
               'indexed_source_parent': i in parent_indices}
        safe_parent = any(parent['message_index'] == i and parent.get('attribution_class') == 'self'
                          and parent['native_message_policy']['effective_role'] is None
                          and parent.get('primary_owner_evidence') is not False for parent in effective['parents'])
        row['indexed_owner_parent'] = (safe_parent and original['role'] == 'self'
                                      and classification['effective_role'] is None
                                      and effective.get('primary_owner_evidence') is not False)
        if classification['effective_role'] is not None:
            row['original_display_attribution'] = {
                key: original.get(key) for key in ('role', 'author', 'evidence_class', 'effective_attribution_reason')}
            row.update(role=classification['effective_role'],
                       effective_input_attribution_class=classification['effective_input_attribution_class'],
                       author={**original.get('author', {}), 'role': classification['effective_role']},
                       effective_attribution_reason=classification['classification'],
                       evidence_class='Native control/mixed context; not an all-span owner authorship or adoption claim.')
            row = project_control_text(backend, row, classification)
        rows.append(row)
    return {**result, 'provenance': effective, 'frozen_provenance': metadata,
            'messages': rows, **policy_fields(qualified, document_policy)}


def lexical_query(backend, args, root, index, policy):
    """Literal supplement over the same pinned publication; no encoder call."""
    if not isinstance(args.query, str) or not args.query.strip() or len(args.query) > 1000:
        raise ValueError('lexical query must contain 1 to 1000 literal characters')
    pattern = re.compile(re.escape(args.query), re.IGNORECASE | re.ASCII)
    gen, meta = backend.active(args, root, index, policy)
    helper = load_view()
    db = backend.open_db(gen / 'units.sqlite', True)
    view = verified_stat = None
    memo = LocateMemo()
    cap = args.limit * 5
    scanned = prefiltered = classified = 0
    complete = False
    leads, failures, excluded, seen = [], [], [], set()
    document_classified, document_excluded, document_returned = 0, [], []
    try:
        view, verified_stat = helper.open_view(index, gen, gen / 'units.sqlite', meta,
                                               args.query_view_manifest_sha256)
        candidates = []
        for batch in filtered_scan(view, meta['model_key'], args, with_vectors=False):
            ids = [item['unit_id'] for item in batch]
            slots = ','.join('?' for _ in ids)
            rows = {row[0]: row for row in db.execute(
                'SELECT id,text,metadata,vector_key FROM units WHERE id IN (' + slots + ') '
                'AND instr(lower(text),lower(?))>0', [*ids, args.query])}
            scanned += len(batch)
            for projected in batch:
                row = rows.get(projected['unit_id'])
                if row is None:
                    continue
                prefiltered += 1
                if len(candidates) < cap:
                    candidates.append((row, projected))
            if len(candidates) == cap:
                break
        else:
            complete = True
        for row, projected in candidates:
            md = verify_metadata(backend, row, projected)
            keys = {(p['parent_version_key'], p['char_start'], p['char_end']) for p in md['parents']}
            if keys <= seen:
                continue
            try:
                record = memo.locate(backend, root, md, policy)
                effective, source_roles, document_policy = qualify_parents(backend, record, md, policy)
                messages, _ = backend.record_messages(record, policy.common.OWNER_DISCORD_ID)
                if document_policy is not None:
                    document_classified += 1
                    if not args.include_context_documents:
                        document_excluded.append(row[0])
                        continue
                else:
                    classified += 1
                matches = []
                for parent in md['parents']:
                    i = parent['message_index']
                    if type(i) is not int or not 0 <= i < len(messages):
                        raise ValueError('lexical parent index invalid')
                    message = messages[i]
                    full = policy.common.message_text(message)
                    if backend.digest(full.encode('utf-8')) != parent['text_sha256']:
                        raise ValueError('lexical full parent text changed')
                    if message.get('id') is not None and str(message['id']) != parent['message_id']:
                        raise ValueError('lexical parent identity changed')
                    if message.get('sent_at') != parent.get('timestamp'):
                        raise ValueError('lexical parent timestamp changed')
                    if policy.message_reason(message, full) or not policy.owner(message, md['platform'], record):
                        continue
                    if args.year and str(parent.get('timestamp') or '')[:4] != args.year:
                        continue
                    lane = 'context_document' if document_policy is not None else policy.input_lane(record, message)
                    if lane != 'self' and not (
                            lane in backend.UNCONFIRMED_INPUT_LANES and args.include_unconfirmed_input or
                            lane == 'context_document' and args.include_context_documents):
                        continue
                    start, end = parent['char_start'], parent['char_end']
                    for match in pattern.finditer(full[start:end]):
                        left, right = start + match.start(), start + match.end()
                        if document_policy is not None:
                            exact_fields = {'source_policy': {'policy_id': DOCUMENT_POLICY_ID,
                                'effective_input_lane': 'context_document', 'primary_owner_evidence': False,
                                'authorship_established': False, 'adoption_established': False,
                                'matched_character_range': [left, right]}}
                        else:
                            exact = backend.native_span_classifier(message, md['platform'], left, right)
                            if not exact['owner_evidence_eligible'] or exact['matched_control_characters']:
                                continue
                            if exact['effective_input_attribution_class'] == 'unconfirmed_input' and not args.include_unconfirmed_input:
                                continue
                            exact_fields = {'native_message_policy': exact}
                        matches.append({'message_index': parent['message_index'],
                            'message_id': parent['message_id'], 'parent_version_key': parent['parent_version_key'],
                            'text_sha256': parent['text_sha256'], 'character_range': [left, right],
                            **exact_fields, 'input_lane': lane,
                            'full_parent_hash_verified': True})
                        if len(matches) == 8:
                            break
                    if len(matches) == 8:
                        break
                if not matches:
                    excluded.append(row[0])
                    continue
            except (ValueError, OSError):
                failures.append({'unit_id': row[0], 'reason': 'source-stale-or-unavailable'})
                continue
            leads.append({'unit_id': row[0], 'similarity': None, 'preview': '',
                'preview_suppressed_by_policy': True, 'provenance': effective,
                'frozen_provenance': md, **policy_fields(source_roles, document_policy),
                'lexical_match_spans': matches, 'literal_match_verified': True})
            if document_policy is not None:
                document_returned.append(row[0])
            seen.update(keys)
            if len(leads) == args.limit:
                break
        return {'kind': 'lexical-published-policy-view', 'generation': gen.name,
            'scope': meta['scope'], 'coverage': meta['coverage'], 'leads': leads, 'failures': failures,
            'vector_semantic_verified': False, 'encoder_instantiated': False,
            'lexical_execution': {'match': 'contiguous literal substring with ASCII case insensitivity; no wildcard or token expansion',
                'ordering': 'published unit ordinal ascending, never semantic ranking',
                'scanned_eligible_units': scanned, 'prefiltered_units': prefiltered,
                'candidate_limit': cap, 'candidate_units': len(candidates),
                'eligible_scan_complete': complete, 'refill_after_exclusion': False,
                'exact_matches_per_unit_cap': 8, 'year_scope': 'unit first-parent year AND exact matched-parent timestamp year; not historical edit eligibility',
                'cutoff_applied': False, 'no_hit_means_archive_absence': False},
            'native_message_policy': {'helper_sha256': ROLES_SHA256,
                'baseline_adapter_sha256': BASELINE_ADAPTER_SHA256,
                'scope': 'bounded literal candidates; exact retained parent match ranges requalified',
                'classified_candidate_units': classified, 'excluded_control_or_nonmatching_units': excluded,
                'all_index_units_classified': False, 'original_origin_verified': False,
                'hydration_requirement': 'Use existing policy-overlay hydration before interpreting source or neighboring turns.'},
            'source_policy': document_query_receipt(args, document_classified,
                                                   document_excluded, document_returned),
            'interpretation': 'Literal matches locate evidence, not adoption or personal identity. Hydrate originals; incomplete or empty results cannot establish absence.'}
    finally:
        memo.clear()
        try:
            if verified_stat is not None:
                helper.verify_view(index, gen, gen / 'units.sqlite', meta,
                                   args.query_view_manifest_sha256, verified_stat)
            else:
                helper.verify_base(index, gen, gen / 'units.sqlite', meta,
                                   args.query_view_manifest_sha256)
        finally:
            if view is not None:
                view.close()
            db.close()


def query(backend, args, root, index, policy):
    if args.query_mode == 'lexical':
        return lexical_query(backend, args, root, index, policy)
    gen, meta = backend.active(args, root, index, policy)
    enc = backend.encoder(args, policy)
    if enc.model_hash != meta['model']['sha256'] or enc.tokenizer_hash != meta['model']['tokenizer_sha256']:
        raise ValueError('query model differs')
    np = enc.np
    message_rerank = getattr(args, 'message_rerank', False)
    vector = enc.encode([args.query], query=True)[0]
    helper = load_view()
    db = backend.open_db(gen / 'units.sqlite', True)
    view = None
    verified_stat = None
    memo = LocateMemo()
    try:
        view, verified_stat = helper.open_view(index, gen, gen / 'units.sqlite', meta,
                                               args.query_view_manifest_sha256)
        scope_units, scope_receipt = conversation_scope(backend, db, root, policy, args)
        candidates = []
        scored_units = 0
        # SQL transfers eligible rows only; ordinal grouping keeps the exact
        # selected shape/order of each original 1024-row ranking batch.
        for batch in filtered_scan(view, meta['model_key'], args, scope_units=scope_units):
            chosen = []
            for row in batch:
                role = row['role']
                if role != 'self':
                    if role == 'unconfirmed_input' and getattr(args, 'include_unconfirmed_input', False):
                        pass
                    elif role == 'context_document' and getattr(args, 'include_context_documents', False):
                        pass
                    else:
                        continue
                if not facet_matches(row['platform_present'], row['platform'], args.platform, 'platform'):
                    continue
                if not facet_matches(row['year_present'], row['year'], args.year, 'year'):
                    continue
                if backend.digest(row['vector']) != row['vector_sha256']:
                    raise ValueError('vector cache corruption')
                chosen.append(row)
            if not chosen:
                continue
            matrix = np.stack([np.frombuffer(row['vector'], dtype='<f4') for row in chosen])
            scored_units += len(chosen)
            scores = matrix @ vector
            order = np.argsort(-scores)[:50 if message_rerank else args.limit*3]
            candidates.extend((float(scores[i]), chosen[i]) for i in order)
            candidates.sort(key=lambda item: -item[0])
            del candidates[50 if message_rerank else args.limit*5:]

        rows = {}
        if candidates:
            ids = [projected['unit_id'] for _, projected in candidates]
            placeholders = ','.join('?' for _ in ids)
            rows = {row[0]: row for row in db.execute(
                'SELECT id,text,metadata,vector_key FROM units WHERE id IN (' + placeholders + ')', ids)}
        leads, failures, seen_parents = [], [], set()
        excluded_units, mixed_units = [], []
        classified_candidates = 0
        document_classified, document_excluded, document_returned = 0, [], []
        rerank_records = {}
        for score, projected in candidates:
            row = rows[projected['unit_id']]
            md = verify_metadata(backend, row, projected)
            keys = {(p['parent_version_key'], p['char_start'], p['char_end']) for p in md['parents']}
            if keys <= seen_parents:
                continue
            try:
                record = memo.locate(backend, root, md, policy)
                effective, source_roles, document_policy = qualify_parents(backend, record, md, policy)
                if document_policy is not None:
                    document_classified += 1
                else:
                    classified_candidates += 1
            except (ValueError, OSError):
                failures.append({'unit_id': row[0], 'reason': 'source-stale-or-unavailable'})
                continue
            if document_policy is not None:
                if not args.include_context_documents:
                    document_excluded.append(row[0])
                    continue
                document_returned.append(row[0])
            else:
                if not source_roles['owner_evidence_eligible']:
                    excluded_units.append(row[0])
                    continue
                if source_roles['mixed_control_content']:
                    mixed_units.append(row[0])
            suppress = document_policy is not None or source_roles['requires_hydration_policy_overlay']
            leads.append({'unit_id': row[0], 'similarity': score, 'preview': '' if suppress else row[1][:args.preview_chars],
                          'preview_suppressed_by_policy': suppress,
                          'provenance': effective, 'frozen_provenance': md,
                          **policy_fields(source_roles, document_policy)})
            seen_parents.update(keys)
            if message_rerank:
                rerank_records[row[0]] = record
            if not message_rerank and len(leads) == args.limit:
                break
        rerank_receipt = None
        if message_rerank:
            leads, rerank_receipt = rerank_messages(backend, enc, vector, leads, rerank_records, policy, args)
            leads = leads[:args.limit]
        return {'kind': 'dense-local-transformer', 'generation': gen.name, 'scope': meta['scope'], 'coverage': meta['coverage'], 'leads': leads, 'failures': failures,
                'conversation_scope': {**scope_receipt, 'scored_units': scored_units} if scope_receipt is not None else None,
                'message_reranking': rerank_receipt,
                'source_policy': document_query_receipt(args, document_classified,
                                                       document_excluded, document_returned),
                'native_message_policy': {
                    'helper_sha256': ROLES_SHA256, 'baseline_adapter_sha256': BASELINE_ADAPTER_SHA256,
                    'scope': 'bounded ranked candidate parents only; frozen index coverage unchanged',
                    'classified_candidate_units': classified_candidates,
                    'excluded_control_units': excluded_units, 'mixed_units': mixed_units,
                    'candidate_limit': 50 if message_rerank else args.limit * 5, 'refill_after_exclusion': False,
                    'all_index_units_classified': False, 'original_origin_verified': False,
                    'dedup_scope': 'exact parent-version and character-range; retains later genuine spans',
                    'whole_control_parent_rule': 'Exclude only if every indexed parent is control; preserve genuine or unresolved parents in mixed units.',
                    'hydration_requirement': 'Apply the same whole-message policy to parents and neighbors before treating any span as owner evidence.'}, 'interpretation': 'Similarity locates evidence; it is not confidence, belief adoption, or a personality judgment. Hydrate originals and neighboring turns before interpretation.'}
    finally:
        memo.clear()
        try:
            if verified_stat is not None:
                try:
                    # verify_view includes the complete verify_base check.
                    helper.verify_view(index, gen, gen / 'units.sqlite', meta,
                                       args.query_view_manifest_sha256, verified_stat)
                except BaseException:
                    helper.verify_base(index, gen, gen / 'units.sqlite', meta,
                                       args.query_view_manifest_sha256)
                    raise
            else:
                helper.verify_base(index, gen, gen / 'units.sqlite', meta,
                                   args.query_view_manifest_sha256)
        finally:
            try:
                if view is not None:
                    view.close()
            finally:
                db.close()


def main():
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            try:
                return load_backend().main()
            except (ValueError, OSError) as error:
                print(json.dumps({'state': 'failed-closed', 'error_type': type(error).__name__, 'error': str(error)}))
                return 2
    finally:
        captured = output.getvalue()
        if captured:
            try:
                value = json.loads(captured)
            except json.JSONDecodeError:
                # Preserve argparse help and any other non-JSON stdout unchanged.
                sys.stdout.write(captured)
            else:
                print(json.dumps(value, separators=(',', ':'), ensure_ascii=False))


if __name__ == '__main__':
    raise SystemExit(main())
