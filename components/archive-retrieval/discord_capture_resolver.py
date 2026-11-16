#!/usr/bin/env python3
"""Resolve already retrieved Discord parents to verified original captures."""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
import types

sys.dont_write_bytecode = True
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
HELPER = Path(os.environ.get('PYE_ARCHIVE_ACCESS_HELPER') or PACKAGE_ROOT / 'scripts/archive_access.py').expanduser()
COMMON = Path(__file__).with_name('common.py')
_INTEGRITY = json.loads((PACKAGE_ROOT / 'assets/module-integrity.json').read_text())
HELPER_SHA = _INTEGRITY['scripts/archive_access.py']
COMMON_SHA = _INTEGRITY['components/archive-retrieval/common.py']
RECORD_LIMIT = 128 * 1024 * 1024
SOURCE_LIMIT = 64 * 1024 * 1024
TOTAL_LIMIT = 256 * 1024 * 1024
CATALOG_LIMIT = 8 * 1024 * 1024
PARENT_LIMIT = 64
HINT_LIMIT = 512
MESSAGE_LIMIT = 500000
INPUT_LIMIT = 2 * 1024 * 1024
OUTPUT_LIMIT = 256 * 1024
SHA = re.compile(r'[0-9a-f]{64}\Z')
ID = re.compile(r'[1-9][0-9]{0,39}\Z')


class ResolveError(ValueError):
    pass


def require(condition, diagnostic):
    if not condition:
        raise ResolveError(diagnostic)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'resolver-json-duplicate-key')
            result[key] = value
        return result
    def constant(_):
        raise ResolveError('resolver-json-nonfinite')
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        if isinstance(error, ResolveError):
            raise
        raise ResolveError('resolver-json-invalid') from None
    require(isinstance(value, dict), 'resolver-json-object-required')
    return value


def identifier(value):
    value = str(value) if type(value) is int else value
    require(isinstance(value, str) and bool(ID.fullmatch(value)), 'resolver-message-id-invalid')
    return value


def instant(value):
    require(isinstance(value, str) and len(value) <= 96, 'resolver-timestamp-invalid')
    try:
        parsed = datetime.fromisoformat(value[:-1] + '+00:00' if value.endswith('Z') else value)
    except ValueError:
        raise ResolveError('resolver-timestamp-invalid') from None
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, 'resolver-timestamp-not-aware')
    return parsed.astimezone(timezone.utc)


def checkpoint(state):
    require(time.monotonic() <= state['deadline'], 'resolver-budget-exhausted')


def load_pinned(path, expected, name):
    require(not path.is_symlink(), 'resolver-dependency-location-invalid')
    raw = path.read_bytes()
    require(digest(raw) == expected, 'resolver-dependency-hash-mismatch')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def open_source(path, helper):
    require(path.is_absolute() and '..' not in path.parts and not helper.guarded(path),
            'resolver-source-path-guarded-or-invalid')
    common = load_pinned(COMMON, COMMON_SHA, 'resolver_allowed_source_policy')
    require(any(path.is_relative_to(root) for root in [Path.home(), *common.ALLOWED_SOURCE_ROOTS]),
            'resolver-source-outside-configured-roots')
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = following
        return os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    finally:
        os.close(directory)


def read_source(path, helper, state, ceiling, offset=0, count=None):
    checkpoint(state)
    path = Path(path).expanduser()
    fd = open_source(path, helper)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode), 'resolver-source-not-regular')
        count = before.st_size if count is None else count
        require(type(count) is int and type(offset) is int and offset >= 0
                and 0 < count <= ceiling and offset + count <= before.st_size,
                'resolver-source-range-over-limit-or-invalid')
        require(state['bytes_read'] + count <= TOTAL_LIMIT, 'resolver-cumulative-byte-budget-exhausted')
        chunks, cursor = [], 0
        while cursor < count:
            checkpoint(state)
            raw = os.pread(fd, min(1024 * 1024, count - cursor), offset + cursor)
            require(bool(raw), 'resolver-source-read-incomplete')
            chunks.append(raw)
            cursor += len(raw)
            state['bytes_read'] += len(raw)
        after = os.fstat(fd)
        fresh = open_source(path, helper)
        try:
            current = os.fstat(fresh)
        finally:
            os.close(fresh)
        version = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
        require(version(before) == version(after) == version(current), 'resolver-source-changed-during-read')
    finally:
        os.close(fd)
    checkpoint(state)
    raw = b''.join(chunks)
    return raw, {'path': str(path), 'sha256': digest(raw), 'bytes': count,
                 'byte_range': [offset, offset + count], 'stable_read_verified': True,
                 'no_symlink_traversal': True}


def allowed_message(message, settings, helper, common):
    author = message.get('author')
    if not isinstance(author, dict) or helper.restricted(message) or helper.restricted(author):
        return False
    access = settings.get('access', {})
    require(isinstance(access, dict), 'resolver-access-settings-invalid')
    excluded_authors = set(map(str, access.get('excluded_author_ids', []))) | common.EXCLUDED_IDS
    return (str(message.get('id')) not in set(map(str, access.get('excluded_message_ids', [])))
            and str(author.get('id')) not in excluded_authors
            and author.get('name') not in common.EXCLUDED_NAMES)


def original_path(settings, value, helper):
    require(isinstance(value, str), 'resolver-candidate-locator-invalid')
    root = Path(settings['archive_root']).expanduser()
    apparent = Path(value).expanduser()
    if not apparent.is_absolute():
        apparent = root / apparent
    else:
        for prior_value in settings.get('source_roots', []):
            prior = Path(prior_value).expanduser()
            if apparent.is_relative_to(prior):
                apparent = root / apparent.relative_to(prior)
                break
    resolved = helper.source_path(settings, value)
    require(apparent == resolved, 'resolver-original-path-aliased')
    for prefix in settings.get('dense', {}).get('excluded_source_prefixes', []):
        require(not any(prefix in candidate for candidate in (value, str(apparent))), 'resolver-original-source-excluded')
    return apparent


def edit_scope(message, created, cutoff):
    seen, nulls, invalid = [], 0, False
    aliases = {}
    for key in ('timestampEdited', 'timestamp_edited', 'edited_at'):
        if key not in message:
            aliases[key] = 'absent'
        elif message[key] is None:
            aliases[key] = 'null'
            nulls += 1
        else:
            try:
                seen.append(instant(message[key]))
                aliases[key] = 'value'
            except ResolveError:
                aliases[key] = 'invalid'
                invalid = True
    values = set(seen)
    state = ('invalid' if invalid else 'conflict' if len(values) > 1 or (seen and nulls)
             else 'observed-edit' if seen else 'no-reported-edit-at-capture' if nulls else 'absent-unknown')
    edited = next(iter(values)) if state == 'observed-edit' else None
    decision = 'not-requested'
    if cutoff is not None:
        decision = ('exclude-created-after-cutoff' if created > cutoff else
                    'exclude-current-content-edited-after-cutoff' if edited is not None and edited > cutoff else
                    'unknown-edit-history' if state in ('invalid', 'conflict', 'absent-unknown') else
                    'not-excluded-by-observed-timestamps')
    return {'state': state, 'edit_instant_utc': edited.isoformat() if edited else None,
            'alias_states': aliases, 'cutoff_decision': decision,
            'historical_content_availability_proven': False}


def resolve_original_parents(settings, verified_provenance, cutoff=None, candidate_limit=8, budget=30, *,
                             helper_io=None, helper_sha256=None, expected_helper_sha256=None):
    """Return exact-version mappings, not excerpts or a semantic search result."""
    result = {'status': 'unavailable', 'mappings': [], 'unresolved_parent_ids': [], 'attempts': [],
              'coverage_complete': False, 'source_bodies_returned': False,
              'historical_content_availability_proven': False}
    state = {'deadline': time.monotonic() + budget if type(budget) in (int, float) else 0,
             'bytes_read': 0}
    try:
        require(type(candidate_limit) is int and 1 <= candidate_limit <= 16
                and type(budget) in (int, float) and 1 <= budget <= 120, 'resolver-limits-invalid')
        require(isinstance(settings, dict) and isinstance(verified_provenance, dict), 'resolver-input-invalid')
        cutoff_time = instant(cutoff) if cutoff is not None else None
        if helper_io is None:
            require(helper_sha256 is None, 'resolver-helper-sha-requires-injected-io')
            helper_pin = HELPER_SHA if expected_helper_sha256 is None else expected_helper_sha256
            require(isinstance(helper_pin, str) and SHA.fullmatch(helper_pin), 'resolver-expected-helper-sha-invalid')
            helper = load_pinned(HELPER, helper_pin, 'discord_resolver_archive_helper')
            helper_verification = ('package-manifest helper source independently loaded by resolver' if expected_helper_sha256 is None
                                   else 'explicit expected helper source SHA independently loaded and verified by resolver')
            helper_verified = True
        else:
            require(expected_helper_sha256 is None, 'resolver-expected-helper-sha-incompatible-with-injected-io')
            require(isinstance(helper_sha256, str) and SHA.fullmatch(helper_sha256), 'resolver-injected-helper-sha-invalid')
            getter = helper_io.get if isinstance(helper_io, dict) else lambda name: getattr(helper_io, name, None)
            callbacks = {name: getter(name) for name in ('guarded', 'restricted', 'source_path',
                         'generic_provenance', 'normalized_message_view')}
            require(all(callable(callback) for callback in callbacks.values()), 'resolver-injected-helper-io-invalid')
            callback = getter('verified_capture')
            require(callback is None or callable(callback), 'resolver-injected-capture-callback-invalid')
            helper = types.SimpleNamespace(**callbacks, verified_capture=callback)
            previously_read = getter('bytes_already_read')
            if previously_read is not None:
                require(type(previously_read) is int and 0 <= previously_read <= TOTAL_LIMIT,
                        'resolver-injected-byte-budget-invalid')
                state['bytes_read'] = previously_read
            helper_pin = helper_sha256
            helper_verification = 'caller-provided helper IO and asserted source SHA; source not independently loaded by resolver'
            helper_verified = False
        common = load_pinned(COMMON, COMMON_SHA, 'discord_resolver_common')
        provenance = helper.generic_provenance(settings, verified_provenance)
        require(provenance.get('platform') == 'discord' and provenance.get('kind') == 'conversation'
                and provenance.get('message_pointer') == '/messages', 'resolver-normalized-format-unsupported')
        parents = provenance['parents']
        require(0 < len(parents) <= PARENT_LIMIT, 'resolver-parent-count-over-limit')
        part = Path(provenance['part'])
        normalized_root = Path(settings['dense']['root']).expanduser()
        if not part.is_absolute():
            part = normalized_root / part
        require(part == Path(provenance['normalized_path'])
                and part.is_relative_to(normalized_root / 'archive/corpus/records'), 'resolver-normalized-path-aliased')
        raw, normalized_pin = read_source(part, helper, state, RECORD_LIMIT,
            provenance.get('record_offset'), provenance.get('record_bytes'))
        require(normalized_pin['sha256'] == provenance.get('record_line_sha256'), 'resolver-normalized-record-hash-mismatch')
        record = strict_json(raw)
        del raw
        require(record.get('id') == provenance.get('record_id') and not helper.restricted(record)
                and not helper.restricted(record.get('extra') or {}),
                'resolver-normalized-record-identity-or-access-mismatch')
        messages = helper.normalized_message_view(record, '/messages')
        targets = {}
        hints = []
        merge_meta = (record.get('extra') or {}).get('dce_append_merge') or {}
        runs = merge_meta.get('applied_runs') or []
        require(isinstance(runs, list) and len(runs) <= HINT_LIMIT, 'resolver-lineage-over-limit')
        for parent in parents:
            checkpoint(state)
            index, mid = parent.get('message_index'), identifier(parent.get('message_id'))
            require(type(index) is int and 0 <= index < len(messages), 'resolver-parent-index-invalid')
            message = messages[index]
            require(isinstance(message, dict) and identifier(message.get('id')) == mid
                    and allowed_message(message, settings, helper, common), 'resolver-normalized-parent-identity-or-access-mismatch')
            text, author = message.get('content'), message.get('author')
            require(isinstance(text, str) and isinstance(author, dict)
                    and digest(text.encode('utf-8')) == parent.get('text_sha256'), 'resolver-normalized-parent-text-mismatch')
            actor = identifier(author.get('id'))
            require(actor == identifier((parent.get('author') or {}).get('id'))
                    and instant(message.get('sent_at')) == instant(parent.get('timestamp')),
                    'resolver-normalized-parent-actor-or-time-mismatch')
            left, right = parent.get('char_start'), parent.get('char_end')
            require(type(left) is int and type(right) is int and 0 <= left < right <= len(text),
                    'resolver-parent-span-invalid')
            target = {'message_id': mid, 'text_sha256': parent['text_sha256'], 'actor_id': actor,
                      'timestamp': parent['timestamp'], 'normalized_message_index': index}
            require(mid not in targets or targets[mid] == target, 'resolver-parent-id-conflict')
            targets[mid] = target
            extra = message.get('extra') or {}
            observations = extra.get('metadata_observations') or []
            require(isinstance(observations, list) and len(observations) <= HINT_LIMIT, 'resolver-message-lineage-over-limit')
            for observation in observations:
                proof = observation.get('source_proof', {}) if isinstance(observation, dict) else {}
                if isinstance(proof, dict):
                    hints.append((proof.get('source_archive_path'), proof.get('source_file_sha256'), 'normalized-message-observation'))
            first_run = extra.get('first_observed_in')
            for run in runs:
                if isinstance(run, dict) and first_run and run.get('run_id') == first_run:
                    hints.append((run.get('export_archive_path'), run.get('export_sha256'), 'normalized-first-observed-run'))
        result['unresolved_parent_ids'] = list(targets)
        source = provenance.get('source') or {}
        hints.append((source.get('archive_path'), source.get('source_sha256'), 'published-primary-source'))
        lineage = (record.get('provenance') or {}).get('wasDerivedFrom') or []
        require(isinstance(lineage, list) and len(lineage) <= HINT_LIMIT, 'resolver-record-lineage-over-limit')
        for run in runs:
            if isinstance(run, dict):
                hints.append((run.get('export_archive_path'), run.get('export_sha256'), 'normalized-applied-run'))
        for prior in lineage:
            if isinstance(prior, dict):
                hints.append((prior.get('archive_path'), prior.get('sha256'), 'normalized-source-lineage'))
        channel = merge_meta.get('channel_id')
        ir_meta = (record.get('extra') or {}).get('ir_v2_meta') or (record.get('extra') or {}).get('ir_v1_meta') or {}
        if not channel and isinstance(ir_meta, dict):
            channel = ir_meta.get('channel_id') or (ir_meta.get('channel') or {}).get('id')
        if not channel:
            match = re.search(r'(?:\[|/)([0-9]{15,25})(?:\]\.json|\.json)$', source.get('archive_path', ''))
            channel = match.group(1) if match else None
        require(channel is not None, 'resolver-structured-channel-unavailable')
        channel = identifier(channel)
        catalog_pin = None
        if settings.get('catalog'):
            catalog_raw, catalog_pin = read_source(Path(settings['catalog']).expanduser(), helper, state, CATALOG_LIMIT)
            catalog = strict_json(catalog_raw)
            rows = catalog.get('sources')
            require(isinstance(rows, list) and len(rows) <= 100000, 'resolver-catalog-schema-invalid-or-over-limit')
            for row in rows:
                checkpoint(state)
                if (isinstance(row, dict) and not helper.restricted(row)
                        and str(row.get('channel_id')) == channel):
                    hints.append((row.get('source'), row.get('source_hash_report'), 'catalog-discovery-only'))
        require(len(hints) <= HINT_LIMIT * PARENT_LIMIT + HINT_LIMIT * 3 + 100000, 'resolver-candidate-hints-over-limit')
        candidates, seen, discovery_failures = [], set(), 0
        for value, expected, basis in hints:
            checkpoint(state)
            if not isinstance(value, str) or not isinstance(expected, str) or not SHA.fullmatch(expected):
                discovery_failures += 1
                continue
            try:
                path = original_path(settings, value, helper)
            except (ValueError, OSError):
                discovery_failures += 1
                continue
            key = (str(path), expected)
            if key not in seen:
                seen.add(key)
                candidates.append({'path': str(path), 'expected_sha256': expected, 'discovery_basis': basis})
        matches = {mid: [] for mid in targets}
        exhausted = False
        for candidate in candidates[:candidate_limit]:
            attempt = {**candidate, 'status': 'unavailable', 'matched_parent_ids': []}
            result['attempts'].append(attempt)
            try:
                raw, pin = read_source(Path(candidate['path']), helper, state, SOURCE_LIMIT)
                require(pin['sha256'] == candidate['expected_sha256'], 'resolver-original-file-hash-mismatch')
                export = strict_json(raw)
                del raw
                require(identifier((export.get('channel') or {}).get('id')) == channel, 'resolver-original-channel-mismatch')
                originals = export.get('messages')
                require(isinstance(originals, list) and len(originals) <= MESSAGE_LIMIT, 'resolver-original-message-array-invalid-or-over-limit')
                selected = {}
                for index, message in enumerate(originals):
                    checkpoint(state)
                    require(isinstance(message, dict), 'resolver-original-message-object-invalid')
                    mid = str(message.get('id')) if type(message.get('id')) is int else message.get('id')
                    if isinstance(mid, str) and mid in targets:
                        require(mid not in selected, 'resolver-original-target-id-duplicate')
                        selected[mid] = (index, message)
                mismatches, excluded, cutoff_unavailable = [], [], []
                for mid, (index, message) in selected.items():
                    checkpoint(state)
                    target = targets[mid]
                    if not allowed_message(message, settings, helper, common):
                        excluded.append(mid)
                        continue
                    text, author = message.get('content'), message.get('author')
                    try:
                        created = instant(message.get('timestamp'))
                        identical = (isinstance(text, str) and digest(text.encode('utf-8')) == target['text_sha256']
                                     and identifier(author.get('id')) == target['actor_id']
                                     and created == instant(target['timestamp']))
                    except ResolveError:
                        identical = False
                    if not identical:
                        mismatches.append(mid)
                        continue
                    scope = edit_scope(message, created, cutoff_time)
                    mapping = {**target, 'source': candidate['path'], 'source_sha256': pin['sha256'],
                               'original_json_pointer': f'/messages/{index}',
                               'discovery_basis': candidate['discovery_basis'],
                               'original_parent_match_verified': True, 'edit_scope': scope,
                               'context_hydrated': False, 'counts_as_new_authored_effort': False}
                    if scope['cutoff_decision'].startswith('exclude-') or scope['cutoff_decision'] == 'unknown-edit-history':
                        excluded.append(mid)
                        cutoff_unavailable.append({'message_id': mid, 'edit_scope': scope})
                        continue
                    matches[mid].append(mapping)
                    attempt['matched_parent_ids'].append(mid)
                attempt.update(status='fresh-original-checked', source_pin=pin,
                               missing_parent_ids=[mid for mid in targets if mid not in selected],
                               mismatched_parent_ids=mismatches, excluded_or_cutoff_unavailable_ids=excluded,
                               cutoff_unavailable=cutoff_unavailable)
                callback = getattr(helper, 'verified_capture', None)
                if callback is not None and attempt['matched_parent_ids']:
                    callback(export, pin)
            except (ResolveError, OSError, ValueError, TypeError, KeyError, OverflowError, AttributeError, RecursionError) as error:
                attempt['diagnostic'] = str(error) if isinstance(error, ResolveError) else 'resolver-original-candidate-unavailable'
                if isinstance(error, ResolveError) and str(error) in ('resolver-budget-exhausted', 'resolver-cumulative-byte-budget-exhausted'):
                    exhausted = True
                    break
        # Multiple matching captures are equivalent candidates, not a latest preference.
        for mid in targets:
            if matches[mid]:
                result['mappings'].append({'message_id': mid, 'matching_captures': matches[mid],
                                          'context_selection': 'prefer a shared verified capture; no latest default'})
        result['unresolved_parent_ids'] = [mid for mid in targets if not matches[mid]]
        result['coverage_complete'] = not result['unresolved_parent_ids']
        shared = set.intersection(*(set((mapping['source'], mapping['source_sha256'])
                                       for mapping in matches[mid]) for mid in targets)) if result['coverage_complete'] else set()
        result.update({'status': 'verified-original-parent-mappings' if result['coverage_complete'] else 'partial-original-parent-mappings',
            'shared_matching_capture_versions': [{'source': path, 'source_sha256': source_sha}
                                                 for path, source_sha in sorted(shared)],
            'shared_matching_captures': sorted({path for path, _ in shared}),
            'receipt': {'helper_sha256': helper_pin, 'helper_io_verification': helper_verification,
                'helper_source_independently_verified_by_resolver': helper_verified, 'common_sha256': COMMON_SHA,
                'bytes_read_before_resolver': previously_read if helper_io is not None and previously_read is not None else 0,
                'module_sha256': digest(Path(__file__).read_bytes()), 'normalized_record': normalized_pin,
                'catalog_discovery_pin': catalog_pin, 'catalog_is_source_authentication': False,
                'selected_parent_ids': list(targets), 'candidate_sources_discovered': len(candidates),
                'candidate_sources_attempted': len(result['attempts']),
                'candidate_sources_deferred': max(0, len(candidates) - len(result['attempts'])),
                'discovery_hints_without_usable_proof': discovery_failures,
                'bytes_read': state['bytes_read'], 'budget_exhausted': exhausted or time.monotonic() > state['deadline'],
                'limits': {'candidate_sources': candidate_limit, 'parents': PARENT_LIMIT,
                    'normalized_record_bytes': RECORD_LIMIT, 'original_bytes': SOURCE_LIMIT,
                    'cumulative_bytes': TOTAL_LIMIT, 'catalog_bytes': CATALOG_LIMIT,
                    'budget_seconds': budget, 'deadline_kind': 'cooperative checks between OS reads and JSON parsing'},
                'qualifiers': ['Exact original-version supplement after semantic retrieval; not a semantic search.',
                    'Catalog and lineage discover candidates; originals are independently hash-checked.',
                    'Capture time, exporter null and earlier edit timestamps do not prove historical content availability.',
                    'Only selected parents were matched; neighboring context needs separate hydration.',
                    'Budget/candidate exhaustion or missing proof does not establish archive absence.']}})
        serialize(result)
    except (ResolveError, OSError, ValueError, TypeError, KeyError, OverflowError, ImportError, AttributeError, RecursionError) as error:
        result['diagnostic'] = str(error) if isinstance(error, ResolveError) else 'resolver-source-or-provenance-unavailable'
        result['coverage_complete'] = False
        if isinstance(error, ResolveError) and str(error) == 'resolver-output-over-limit':
            result = {'status': 'unavailable', 'diagnostic': 'resolver-output-over-limit',
                      'coverage_complete': False, 'source_bodies_returned': False}
    return result


def serialize(result):
    raw = (json.dumps(result, indent=2, ensure_ascii=True) + '\n').encode('utf-8')
    require(len(raw) <= OUTPUT_LIMIT, 'resolver-output-over-limit')
    return raw


def main():
    parser = argparse.ArgumentParser(description='Resolve verified Discord parent IDs to original captures; no source bodies returned.')
    parser.add_argument('--helper-sha256', help='Exact expected installed helper SHA; defaults to the package manifest pin.')
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(INPUT_LIMIT + 1)
        require(len(raw) <= INPUT_LIMIT, 'resolver-input-over-limit')
        payload = strict_json(raw)
        result = resolve_original_parents(payload.get('settings'), payload.get('verified_provenance'),
            cutoff=payload.get('cutoff'), candidate_limit=payload.get('candidate_limit', 8), budget=payload.get('budget', 30),
            expected_helper_sha256=args.helper_sha256)
        sys.stdout.buffer.write(serialize(result))
        return 0 if result['coverage_complete'] else 1
    except (ResolveError, OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        error = sys.exc_info()[1]
        print(json.dumps({'status': 'unavailable', 'diagnostic': str(error) if isinstance(error, ResolveError)
                          else 'resolver-operational-input-unavailable', 'coverage_complete': False,
                          'source_bodies_returned': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
