#!/usr/bin/env python3
"""Build and verify a compact, immutable view of a published archive index.

The view copies exact vectors and scalar unit projections. It contains no unit
text or full provenance metadata, and never changes the source generation.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import struct
import sys
import uuid

sys.dont_write_bytecode = True
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_INTEGRITY = json.loads((PACKAGE_ROOT / 'assets/module-integrity.json').read_text())
BACKEND = Path(__file__).resolve().with_name('semantic_archive.py')
PINS = {'backend': _INTEGRITY['components/archive-retrieval/semantic_archive.py'],
        'common': _INTEGRITY['components/archive-retrieval/common.py'],
        'encoder': _INTEGRITY['scripts/semantic_retrieve_portable.py']}
BASE_SCAN_SQL = '''SELECT u.id,u.vector_key,u.metadata FROM units u JOIN vectors v
    ON u.vector_key=v.key AND v.model_hash=?'''
ORIGINAL_SCAN_SQL = 'SELECT u.id,u.text,u.metadata,v.vector,v.vector_sha256 FROM units u JOIN vectors v ON u.vector_key=v.key AND v.model_hash=?'
VIEW_SCAN_SQL = '''SELECT u.unit_id,u.vector_key,u.metadata_sha256,u.role,
    u.platform,u.year,u.platform_present,u.year_present,v.vector,v.vector_sha256
    FROM units u JOIN vectors v ON u.vector_key=v.key AND v.model_hash=?
    ORDER BY u.ordinal'''
SCHEMA = '''
    CREATE TABLE units(ordinal INTEGER PRIMARY KEY,unit_id TEXT UNIQUE NOT NULL,
        vector_key TEXT NOT NULL,metadata_sha256 TEXT NOT NULL,role TEXT,
        platform TEXT,year TEXT,platform_present INTEGER NOT NULL,
        year_present INTEGER NOT NULL);
    CREATE TABLE vectors(key TEXT PRIMARY KEY,vector BLOB NOT NULL,
        vector_sha256 TEXT NOT NULL,model_hash TEXT NOT NULL);
'''


def file_hash(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def load_backend():
    paths = {'backend': BACKEND, 'common': BACKEND.with_name('common.py'),
             'encoder': PACKAGE_ROOT / 'scripts/semantic_retrieve_portable.py'}
    backend_bytes = None
    for name, path in paths.items():
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != PINS[name]:
            raise ValueError('query view dependency changed: ' + name)
        if name == 'backend':
            backend_bytes = raw
    spec = importlib.util.spec_from_file_location('query_view_frozen_backend', BACKEND)
    if spec is None or spec.loader is None:
        raise ValueError('query view backend cannot be loaded')
    module = importlib.util.module_from_spec(spec)
    exec(compile(backend_bytes, str(BACKEND), 'exec'), module.__dict__)
    return module


def fingerprint(path):
    value = Path(path).stat()
    return {name: getattr(value, 'st_' + name) for name in
            ('dev', 'ino', 'size', 'mtime_ns', 'ctime_ns')}


def paths(backend, index, gen, base_db_path):
    index, gen, base = map(backend.allowed, (index, gen, base_db_path))
    if gen.parent != backend.allowed(index / 'generations') or base != gen / 'units.sqlite':
        raise ValueError('query view source outside generation')
    views = backend.allowed(index / 'query-views')
    view = backend.allowed(views / gen.name)
    if views.parent != index or view.parent != views:
        raise ValueError('query view outside index')
    for name in ('view.sqlite', 'manifest.json'):
        if backend.allowed(view / name).parent != view:
            raise ValueError('query view file outside view')
    for suffix in ('-wal', '-shm', '-journal'):
        if Path(str(base) + suffix).exists():
            raise ValueError('published base database has a journal')
    return index, gen, base, views, view


def validate_meta(backend, index, meta):
    root = backend.allowed(meta['root'])
    if str(root) != meta['root'] or index.is_relative_to(root):
        raise ValueError('query view root boundary differs')
    if meta['state'] != 'complete' or meta.get('dependency_hashes') != {k: v for k, v in PINS.items() if k != 'backend'}:
        raise ValueError('query view requires pinned complete generation')
    if meta['model']['dim'] != 384:
        raise ValueError('query view requires 384-dimensional vectors')
    key = backend.digest(backend.packed({k: v for k, v in meta['model'].items() if k != 'threads'}).encode())
    if key != meta['model_key']:
        raise ValueError('query view model key differs')


def read_manifest(backend, view, expected_sha256):
    if not isinstance(expected_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise ValueError('query view requires its independently pinned manifest SHA256')
    raw = backend.allowed(view / 'manifest.json').read_bytes()
    if backend.digest(raw) != expected_sha256:
        raise ValueError('query view manifest changed')
    manifest = json.loads(raw)
    if manifest.get('schema_version') != 1 or manifest.get('state') != 'complete':
        raise ValueError('query view incomplete or unsupported')
    if manifest.get('pins') != PINS or manifest.get('builder_sha256') != file_hash(Path(__file__)):
        raise ValueError('query view code binding differs')
    if manifest.get('sqlite_version') != sqlite3.sqlite_version:
        raise ValueError('query view SQLite runtime differs')
    return manifest


def verify_base(index, gen, base_db_path, meta, expected_manifest_sha256):
    """Recheck source binding before and after querying; never read unit text."""
    backend = load_backend()
    index, gen, base, _, view = paths(backend, index, gen, base_db_path)
    validate_meta(backend, index, meta)
    manifest = read_manifest(backend, view, expected_manifest_sha256)
    if (manifest['generation'] != gen.name or manifest['root'] != meta['root']
            or manifest['policy_hash'] != meta['policy_hash']
            or manifest['model_key'] != meta['model_key']
            or manifest['model'] != meta['model']
            or manifest['native_attribution_proof_sha256'] != meta.get('native_attribution_proof_sha256')
            or manifest['units'] != meta['units']):
        raise ValueError('query view generation binding differs')
    if fingerprint(base) != manifest['base_database_stat']:
        raise ValueError('query view base database changed')
    raw = backend.allowed(gen / 'manifest.json').read_bytes()
    if backend.digest(raw) != manifest['base_manifest_sha256'] or json.loads(raw) != meta:
        raise ValueError('query view original generation manifest changed')
    return manifest


def open_view(index, gen, base_db_path, meta, expected_manifest_sha256):
    """Return an immutable connection and the stat captured during verification."""
    manifest = verify_base(index, gen, base_db_path, meta, expected_manifest_sha256)
    backend = load_backend()
    _, _, _, _, view = paths(backend, index, gen, base_db_path)
    database = backend.allowed(view / 'view.sqlite')
    before = fingerprint(database)
    if file_hash(database) != manifest['view_database_sha256'] or fingerprint(database) != before:
        raise ValueError('query view database changed')
    connection = backend.open_db(database, True)
    connection.row_factory = sqlite3.Row
    try:
        if fingerprint(database) != before:
            raise ValueError('query view database changed while opening')
    except BaseException:
        connection.close()
        raise
    return connection, before


def verify_view(index, gen, base_db_path, meta, expected_manifest_sha256, verified_stat):
    """Recheck the source and the verified view before returning query results."""
    manifest = verify_base(index, gen, base_db_path, meta, expected_manifest_sha256)
    backend = load_backend()
    _, _, _, _, view = paths(backend, index, gen, base_db_path)
    if fingerprint(backend.allowed(view / 'view.sqlite')) != verified_stat:
        raise ValueError('query view database changed during query')
    return manifest


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def build(args):
    backend = load_backend()
    root, index = backend.allowed(args.root), backend.allowed(args.index)
    if index.is_relative_to(root):
        raise ValueError('index must stay outside archive')
    policy = backend.Policy(args)
    gen, meta = backend.active(args, root, index, policy)
    index, gen, base, views, final = paths(backend, index, gen, gen / 'units.sqlite')
    validate_meta(backend, index, meta)
    backend.require_build_space(index, args.reserve_bytes, 1200 * 1024 ** 2)
    backend.private(views)
    descriptor = os.open(views / '.build.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        if os.path.lexists(final):
            raise ValueError('query view already exists; no overwrite or rebuild')
        source_stat = fingerprint(base)
        source_sha = file_hash(base)
        source_manifest = backend.allowed(gen / 'manifest.json').read_bytes()
        if fingerprint(base) != source_stat or json.loads(source_manifest) != meta:
            raise ValueError('source changed before query view collection')
        temporary = views / (gen.name + '.building-' + uuid.uuid4().hex)
        backend.private(temporary)
        target = temporary / 'view.sqlite'
        old = backend.open_db(base, True)
        new = backend.open_db(target)
        source_digest = hashlib.sha256()
        projection_order_digest = hashlib.sha256()
        original_order_digest = hashlib.sha256()
        units = vectors = 0
        try:
            new.execute('PRAGMA temp_store=MEMORY')
            new.executescript(SCHEMA)
            base_units = old.execute('SELECT count(*) FROM units').fetchone()[0]
            base_vectors = old.execute('SELECT count(*) FROM vectors').fetchone()[0]
            distinct_vectors = old.execute('SELECT count(DISTINCT vector_key) FROM units').fetchone()[0]
            if base_units != meta['units'] or base_vectors != distinct_vectors:
                raise ValueError('source generation coverage differs')
            if args.expected_units is not None and base_units != args.expected_units:
                raise ValueError('source unit count differs from operator pin')
            if args.expected_vectors is not None and base_vectors != args.expected_vectors:
                raise ValueError('source vector count differs from operator pin')
            original_plan = list(old.execute('EXPLAIN QUERY PLAN ' + ORIGINAL_SCAN_SQL, (meta['model_key'],)))
            projection_plan = list(old.execute('EXPLAIN QUERY PLAN ' + BASE_SCAN_SQL, (meta['model_key'],)))
            if original_plan != projection_plan:
                raise ValueError('query view projection changed original join traversal plan')
            for unit_id, vector_key, raw_metadata in old.execute(BASE_SCAN_SQL, (meta['model_key'],)):
                metadata = json.loads(raw_metadata)
                if not isinstance(metadata, dict):
                    raise ValueError('unit metadata root must be an object')
                for name in ('role', 'platform', 'year'):
                    value = metadata.get(name)
                    if value is not None and not isinstance(value, str):
                        raise ValueError('unit projection requires string or null: ' + name)
                    if isinstance(value, str):
                        value.encode('utf-8')
                metadata_sha = backend.digest(raw_metadata.encode('utf-8'))
                projection = (units, unit_id, vector_key, metadata_sha,
                              metadata.get('role'), metadata.get('platform'), metadata.get('year'),
                              int('platform' in metadata), int('year' in metadata))
                new.execute('INSERT INTO units VALUES(?,?,?,?,?,?,?,?,?)', projection)
                source_digest.update((backend.packed(projection) + '\n').encode('utf-8'))
                projection_order_digest.update((backend.packed(unit_id) + '\n').encode('utf-8'))
                units += 1
                if units % 4096 == 0:
                    new.commit()
                    backend.require_build_space(index, args.reserve_bytes)
            for key, vector, vector_sha, model_key in old.execute('SELECT key,vector,vector_sha256,model_hash FROM vectors'):
                if model_key != meta['model_key'] or len(vector) != 384 * 4 or backend.digest(vector) != vector_sha:
                    raise ValueError('source vector binding or bytes differ')
                values = struct.unpack('<384f', vector)
                if not all(math.isfinite(value) for value in values):
                    raise ValueError('source vector is not finite')
                norm = math.sqrt(math.fsum(value * value for value in values))
                if not 0.999 <= norm <= 1.001:
                    raise ValueError('source vector norm differs')
                new.execute('INSERT INTO vectors VALUES(?,?,?,?)', (key, vector, vector_sha, model_key))
                vectors += 1
                if vectors % 4096 == 0:
                    new.commit()
                    backend.require_build_space(index, args.reserve_bytes)
            new.commit()
            if units != base_units or vectors != base_vectors:
                raise ValueError('query view coverage differs')
            original_cursor = old.execute(ORIGINAL_SCAN_SQL, (meta['model_key'],))
            original_units = 0
            while True:
                original_batch = original_cursor.fetchmany(1024)
                if not original_batch:
                    break
                for original_row in original_batch:
                    original_order_digest.update((backend.packed(original_row[0]) + '\n').encode('utf-8'))
                    original_units += 1
            if original_units != units or original_order_digest.digest() != projection_order_digest.digest():
                raise ValueError('query view ordinal stream differs from original query')
            missing = new.execute('SELECT count(*) FROM units u LEFT JOIN vectors v ON u.vector_key=v.key WHERE v.key IS NULL').fetchone()[0]
            if missing or new.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('query view database integrity differs')
        finally:
            old.close()
            new.close()
        if (fingerprint(base) != source_stat or file_hash(base) != source_sha
                or fingerprint(base) != source_stat
                or backend.allowed(gen / 'manifest.json').read_bytes() != source_manifest):
            raise ValueError('source changed during query view collection')
        load_backend()
        with target.open('rb') as stream:
            os.fsync(stream.fileno())
        manifest = {'schema_version': 1, 'state': 'complete', 'generation': gen.name,
                    'root': meta['root'], 'policy_hash': meta['policy_hash'],
                    'model_key': meta['model_key'], 'model': meta['model'],
                    'native_attribution_proof_sha256': meta.get('native_attribution_proof_sha256'),
                    'pins': PINS, 'builder_sha256': file_hash(Path(__file__)),
                    'base_manifest_sha256': backend.digest(source_manifest),
                    'base_database_sha256': source_sha, 'base_database_stat': source_stat,
                    'view_database_sha256': file_hash(target), 'units': units, 'vectors': vectors,
                    'projection_source_sha256': source_digest.hexdigest(),
                    'original_unit_order_sha256': original_order_digest.hexdigest(),
                    'projection_unit_order_sha256': projection_order_digest.hexdigest(),
                    'sqlite_version': sqlite3.sqlite_version,
                    'original_join_plan': original_plan, 'projection_join_plan': projection_plan,
                    'source_sql': BASE_SCAN_SQL, 'view_sql': VIEW_SCAN_SQL,
                    'projection': 'json.loads object, last duplicate key; projected fields must be string or null; key-presence flags preserved',
                    'ordering': 'Ordinal enumerates the frozen generation join traversal; query uses ordinal ascending',
                    'created_at': backend.now()}
        backend.atomic(temporary / 'manifest.json', manifest)
        sync_directory(temporary)
        backend.require_build_space(index, args.reserve_bytes)
        if os.path.lexists(final):
            raise ValueError('query view appeared during collection; no overwrite')
        os.rename(temporary, final)
        sync_directory(views)
        return {'state': 'complete', 'view_path': str(final), 'units': units, 'vectors': vectors,
                'manifest_sha256': file_hash(final / 'manifest.json'),
                'view_database_sha256': manifest['view_database_sha256']}
    finally:
        os.close(descriptor)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--index', required=True)
    parser.add_argument('--original-root')
    parser.add_argument('--generation')
    parser.add_argument('--exclude-source-prefix', action='append', default=[])
    parser.add_argument('--native-attribution-proof')
    parser.add_argument('--native-attribution-proof-sha256')
    parser.add_argument('--expected-units', type=int)
    parser.add_argument('--expected-vectors', type=int)
    parser.add_argument('--reserve-bytes', type=int, default=4 * 1024 ** 3)
    args = parser.parse_args()
    if args.reserve_bytes < 4 * 1024 ** 3:
        parser.error('reserve bytes must retain at least 4 GiB')
    try:
        print(json.dumps(build(args), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError, UnicodeError) as error:
        print(json.dumps({'state': 'failed-closed', 'error_type': type(error).__name__, 'error': str(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
