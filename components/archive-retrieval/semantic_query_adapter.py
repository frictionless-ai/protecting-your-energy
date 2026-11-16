#!/usr/bin/env python3
"""Query a pinned archive backend without transferring every unit's full text.

The published backend and its policy remain unchanged. This adapter retains the
backend's joined-row batches, vector checks, ranking and source verification.
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
from pathlib import Path
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_INTEGRITY = json.loads((PACKAGE_ROOT / 'assets/module-integrity.json').read_text())
BACKEND = Path(__file__).resolve().with_name('semantic_archive.py')
COMMON = BACKEND.with_name('common.py')
ENCODER = PACKAGE_ROOT / 'scripts/semantic_retrieve_portable.py'
VIEW = BACKEND.with_name('semantic_query_view.py')
VIEW_SHA256 = _INTEGRITY['components/archive-retrieval/semantic_query_view.py']
PINS = (
    (BACKEND, _INTEGRITY['components/archive-retrieval/semantic_archive.py']),
    (COMMON, _INTEGRITY['components/archive-retrieval/common.py']),
    (ENCODER, _INTEGRITY['scripts/semantic_retrieve_portable.py']),
)


class ReadOnlyParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        self.add_argument('--query-view-manifest-sha256',
                          help='Independent SHA256 pin for the query view manifest.')
        parsed = super().parse_args(args, namespace)
        if parsed.command not in {'query', 'status', 'hydrate'}:
            self.error('this adapter supports only query, status and hydrate')
        if parsed.command == 'query':
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
    backend.query = lambda args, root, index, policy: query(backend, args, root, index, policy)
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


def filtered_scan(view, model_key, args):
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
        invalid = view.execute('SELECT u.platform_present,u.year_present' + join
                               + base_where + ' AND (' + ' OR '.join(missing)
                               + ') ORDER BY u.ordinal LIMIT 1',
                               parameters + missing_parameters).fetchone()
        if invalid is not None:
            raise KeyError('platform' if args.platform and not invalid['platform_present'] else 'year')
    where = [base_where]
    if args.platform:
        where.append('u.platform=?')
        parameters.append(args.platform)
    if args.year:
        where.append('u.year=?')
        parameters.append(args.year)
    sql = '''SELECT u.ordinal AS original_ordinal,u.unit_id,u.vector_key,
        u.metadata_sha256,u.role,u.platform,u.year,u.platform_present,
        u.year_present,v.vector,v.vector_sha256''' + join + ' AND '.join(where) + ' ORDER BY u.ordinal'
    cursor = view.execute(sql, parameters)
    group, chosen = None, []
    while True:
        rows = cursor.fetchmany(1024)
        if not rows:
            break
        for row in rows:
            current = row['original_ordinal'] // 1024
            if group is not None and current != group:
                yield chosen
                chosen = []
            group = current
            chosen.append(row)
    if chosen:
        yield chosen


def query(backend, args, root, index, policy):
    gen, meta = backend.active(args, root, index, policy)
    enc = backend.encoder(args, policy)
    if enc.model_hash != meta['model']['sha256'] or enc.tokenizer_hash != meta['model']['tokenizer_sha256']:
        raise ValueError('query model differs')
    np = enc.np
    vector = enc.encode([args.query], query=True)[0]
    helper = load_view()
    db = backend.open_db(gen / 'units.sqlite', True)
    view = None
    verified_stat = None
    memo = LocateMemo()
    try:
        view, verified_stat = helper.open_view(index, gen, gen / 'units.sqlite', meta,
                                               args.query_view_manifest_sha256)
        candidates = []
        # SQL transfers eligible rows only; ordinal grouping keeps the exact
        # selected shape/order of each original 1024-row ranking batch.
        for batch in filtered_scan(view, meta['model_key'], args):
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
            scores = matrix @ vector
            order = np.argsort(-scores)[:args.limit*3]
            candidates.extend((float(scores[i]), chosen[i]) for i in order)
            candidates.sort(key=lambda item: -item[0])
            del candidates[args.limit*5:]

        rows = {}
        if candidates:
            ids = [projected['unit_id'] for _, projected in candidates]
            placeholders = ','.join('?' for _ in ids)
            rows = {row[0]: row for row in db.execute(
                'SELECT id,text,metadata,vector_key FROM units WHERE id IN (' + placeholders + ')', ids)}
        leads, failures, seen_parents = [], [], set()
        for score, projected in candidates:
            row = rows[projected['unit_id']]
            md = verify_metadata(backend, row, projected)
            keys = {p['parent_version_key'] for p in md['parents']}
            if keys <= seen_parents:
                continue
            try:
                memo.locate(backend, root, md, policy)
            except (ValueError, OSError):
                failures.append({'unit_id': row[0], 'reason': 'source-stale-or-unavailable'})
                continue
            leads.append({'unit_id': row[0], 'similarity': score, 'preview': row[1][:args.preview_chars], 'provenance': md})
            seen_parents.update(keys)
            if len(leads) == args.limit:
                break
        return {'kind': 'dense-local-transformer', 'generation': gen.name, 'scope': meta['scope'], 'coverage': meta['coverage'], 'leads': leads, 'failures': failures, 'interpretation': 'Similarity locates evidence; it is not confidence, belief adoption, or a personality judgment. Hydrate originals and neighboring turns before interpretation.'}
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
