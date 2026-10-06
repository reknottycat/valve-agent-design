#!/usr/bin/env python3
"""Offline regression tests; run python -B [-O] artifact_storage/test_transport.py."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest import mock
import zlib
import transport as t

P = 'runs/20261006/TEST/file.bin'
Q = 'runs/20261006/TEST/second.bin'

class TransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = self.root / 'store'
        self.dest = self.root / 'dest'
        self.source = self.root / 'source'
        for p in (self.store, self.dest, self.source):
            p.mkdir()
    def tearDown(self):
        self.tmp.cleanup()
    def bundle(self, entries=None, raw=b'hello\x00world\xff', compression='auto'):
        entries = entries or [(P, raw)]
        packed = [t.make_entry(p, b, compression) for p, b in entries]
        return t.write_bundle(self.store, packed)
    def rewrite(self, manifest):
        (self.store / 'artifact_storage/manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    def refuse(self, manifest=None):
        if manifest is not None:
            self.rewrite(manifest)
        with self.assertRaises((t.TransportError, OSError, zlib.error)):
            t.restore(self.store, self.dest)
    def test_raw_roundtrip_multichunk(self):
        raw = random.Random(7).randbytes(2 * t.CHUNK_BYTES + 19)
        m = self.bundle(raw=raw, compression='raw')
        self.assertEqual(3, len(m['files'][0]['chunks']))
        r = t.restore(self.store, self.dest)
        self.assertEqual(1, r['created_files'])
        self.assertEqual(raw, (self.dest / P).read_bytes())
    def test_zlib_roundtrip_multimegabyte(self):
        raw = b'CAD\n0123456789' * 200000
        m = self.bundle(raw=raw)
        self.assertEqual('zlib', m['files'][0]['encoding'])
        t.restore(self.store, self.dest)
        self.assertEqual(raw, (self.dest / P).read_bytes())
    def test_zero_length_raw_and_zlib(self):
        self.bundle(entries=[(P, b''), (Q, b'')], compression='zlib')
        t.restore(self.store, self.dest)
        self.assertEqual(b'', (self.dest / P).read_bytes())
        self.assertEqual(b'', (self.dest / Q).read_bytes())
    def test_verify_only_no_dest_writes(self):
        self.bundle()
        result = t.restore(self.store, self.dest, verify_only=True)
        self.assertEqual(1, result['verified_files'])
        self.assertEqual([], list(self.dest.iterdir()))
    def test_verify_only_without_destination(self):
        self.bundle()
        self.assertEqual('verify-only', t.restore(self.store, verify_only=True)['mode'])
    def test_restore_requires_destination(self):
        self.bundle()
        with self.assertRaises(t.TransportError):
            t.restore(self.store)
    def test_existing_matching_skips(self):
        self.bundle()
        t.restore(self.store, self.dest)
        self.assertEqual(1, t.restore(self.store, self.dest)['existing_matching_files'])
    def test_existing_mismatch_batch_preflight(self):
        self.bundle(entries=[(P, b'first'), (Q, b'second')])
        target = self.dest / Q
        target.parent.mkdir(parents=True)
        target.write_bytes(b'changed')
        self.refuse()
        self.assertFalse((self.dest / P).exists())
        self.assertEqual(b'changed', target.read_bytes())
    def test_missing_final_chunk_batch_preflight(self):
        m = self.bundle(entries=[(P, b'first'), (Q, b'second')])
        (self.store / m['files'][1]['chunks'][0]['path']).unlink()
        self.refuse()
        self.assertFalse((self.dest / P).exists())
    def test_altered_final_chunk_batch_preflight(self):
        m = self.bundle(entries=[(P, b'first'), (Q, b'second')])
        (self.store / m['files'][1]['chunks'][0]['path']).write_bytes(b'xxxxxx')
        self.refuse()
        self.assertFalse((self.dest / P).exists())
    def test_bad_paths(self):
        values = ['/tmp/x', '../x', 'runs/20261006/../x', 'C:/tmp/x',
                  'runs/20261006/X\\x', 'runs/20261006/.git/config',
                  'runs/20261006/.GIT/config', 'runs/20261006//x',
                  'runs/20261006/./x', 'runs/20261005/X/x', 'runs/20261006/X/a\x00b']
        for path in values:
            with self.subTest(path=path), self.assertRaises(t.TransportError):
                t.make_entry(path, b'x')
    def test_duplicates_and_casefold(self):
        for paths in [(P, P), (P, P.upper()), (P, 'runs/20261006/test/other'),
                      (P, P + '/child'), (P + '/child', P)]:
            with self.subTest(paths=paths), self.assertRaises(t.TransportError):
                t.create_manifest([t.make_entry(p, b'x')[0] for p in paths])
    def test_size_types_and_bounds(self):
        original = self.bundle()
        for field in ('bytes', 'encoded_bytes'):
            for value in (True, False, -1, 1.0, float('nan'), float('inf'), '1', None, t.MAX_RAW_BYTES + 1):
                with self.subTest(field=field, value=value):
                    m = copy.deepcopy(original)
                    m['files'][0][field] = value
                    self.refuse(m)
    def test_chunk_size_bool_and_huge(self):
        original = self.bundle()
        for size in (True, -1, 0, t.CHUNK_BYTES + 1):
            m = copy.deepcopy(original)
            m['files'][0]['chunks'][0]['bytes'] = size
            self.refuse(m)
    def test_unsupported_codec(self):
        m = self.bundle()
        m['files'][0]['encoding'] = 'pickle'
        self.refuse(m)
    def test_wrong_git_blob_sha(self):
        m = self.bundle()
        m['files'][0]['git_blob_sha1'] = '0' * 40
        self.refuse(m)
    def test_zlib_expansion_limit(self):
        m = self.bundle(raw=b'A' * 1000000, compression='zlib')
        m['files'][0]['bytes'] = 1
        self.refuse(m)
        self.assertEqual([], list(self.dest.iterdir()))
    def test_zlib_trailing_and_truncated(self):
        for encoded in (zlib.compress(b'hello') + b'junk', zlib.compress(b'hello')[:-1],
                        zlib.compress(b'hello') + zlib.compress(b'other')):
            entry, _ = t.make_entry(P, b'hello', 'zlib')
            entry['encoded_bytes'] = len(encoded)
            entry['encoded_sha256'] = hashlib.sha256(encoded).hexdigest()
            entry['content_id'] = t.content_id(entry)
            chunk = {'path': f"artifact_storage/chunks/{entry['content_id']}/000000.bin",
                     'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest()}
            entry['chunks'] = [chunk]
            # Separate bundle directory per stream so immutable manifests do not collide.
            other = self.root / ('bad-' + entry['encoded_sha256'])
            other.mkdir()
            manifest = t.create_manifest([entry])
            chunk_path = other / chunk['path']
            chunk_path.parent.mkdir(parents=True)
            chunk_path.write_bytes(encoded)
            (other / 'artifact_storage/manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises((t.TransportError, zlib.error)):
                t.restore(other, self.dest)
    def test_chunk_path_escape(self):
        m = self.bundle()
        m['files'][0]['chunks'][0]['path'] = '../outside'
        self.refuse(m)
    def test_manifest_duplicate_keys(self):
        self.bundle()
        (self.store / 'artifact_storage/manifest.json').write_text('{"format":"a","format":"b"}')
        self.refuse()
    def test_source_symlink_leaf(self):
        real = self.source / P
        real.parent.mkdir(parents=True)
        outside = self.root / 'outside'
        outside.write_bytes(b'secret')
        real.symlink_to(outside)
        with self.assertRaises(OSError):
            t.split(self.source, self.store, [P])
        self.assertEqual([], list(self.store.iterdir()))
    def test_source_symlink_ancestor(self):
        (self.source / 'runs').symlink_to(self.dest, target_is_directory=True)
        with self.assertRaises(OSError):
            t.split(self.source, self.store, [P])
    def test_storage_symlink_chunk(self):
        m = self.bundle()
        path = self.store / m['files'][0]['chunks'][0]['path']
        data = path.read_bytes()
        outside = self.root / 'outside'
        outside.write_bytes(data)
        path.unlink()
        path.symlink_to(outside)
        self.refuse()
    def test_storage_symlink_ancestor(self):
        self.bundle()
        original = self.store / 'artifact_storage/chunks'
        relocated = self.root / 'relocated'
        original.rename(relocated)
        original.symlink_to(relocated, target_is_directory=True)
        self.refuse()
    def test_destination_symlink_leaf(self):
        self.bundle()
        path = self.dest / P
        path.parent.mkdir(parents=True)
        outside = self.root / 'outside'
        outside.write_bytes(b'hello\x00world\xff')
        path.symlink_to(outside)
        self.refuse()
        self.assertEqual(b'hello\x00world\xff', outside.read_bytes())
    def test_destination_symlink_ancestor(self):
        self.bundle()
        outside = self.root / 'outside'
        outside.mkdir()
        (self.dest / 'runs').symlink_to(outside, target_is_directory=True)
        self.refuse()
        self.assertEqual([], list(outside.iterdir()))
    def test_root_symlink_and_ancestor(self):
        self.bundle()
        link = self.root / 'alias'
        link.symlink_to(self.dest, target_is_directory=True)
        with self.assertRaises(OSError):
            t.restore(self.store, link)
        (self.dest / 'nested').mkdir()
        with self.assertRaises(OSError):
            t.restore(self.store, link / 'nested')
    def test_target_created_during_atomic_publish(self):
        self.bundle(raw=b'correct')
        real_link = os.link
        def race(src, dst, **kw):
            fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=kw['dst_dir_fd'])
            os.write(fd, b'modified')
            os.close(fd)
            return real_link(src, dst, **kw)
        with mock.patch.object(t.os, 'link', side_effect=race):
            self.refuse()
        self.assertEqual(b'modified', (self.dest / P).read_bytes())
        self.assertEqual([], list((self.dest / P).parent.glob('.valve-transport-*.tmp')))
    def test_direct_child_original_path(self):
        path = 'runs/20261006/direct.bin'
        self.bundle(entries=[(path, b'direct')])
        t.restore(self.store, self.dest)
        self.assertEqual(b'direct', (self.dest / path).read_bytes())
    def test_writer_rejects_oversized_payload(self):
        entry, blobs = t.make_entry(P, b'x', 'raw')
        blobs[0] = (blobs[0][0], b'x' * (t.CHUNK_BYTES + 1))
        with self.assertRaises(t.TransportError):
            t.write_bundle(self.store, [(entry, blobs)])
        self.assertEqual([], list(self.store.iterdir()))
    def test_writer_rejects_incorrect_raw_digest(self):
        entry, blobs = t.make_entry(P, b'x', 'zlib')
        entry['git_blob_sha1'] = '0' * 40
        with self.assertRaises(t.TransportError):
            t.write_bundle(self.store, [(entry, blobs)])
        self.assertEqual([], list(self.store.iterdir()))
    def test_split_does_not_modify_source(self):
        path = self.source / P
        path.parent.mkdir(parents=True)
        path.write_bytes(b'original\x00')
        t.split(self.source, self.store, [P])
        self.assertEqual(b'original\x00', path.read_bytes())
        t.restore(self.store, self.dest)
        self.assertEqual(path.read_bytes(), (self.dest / P).read_bytes())
    def test_split_existing_manifest_never_overwritten(self):
        m = self.bundle(raw=b'first')
        frozen = (self.store / 'artifact_storage/manifest.json').read_bytes()
        with self.assertRaises(t.TransportError):
            t.write_bundle(self.store, [t.make_entry(Q, b'second')])
        self.assertEqual(frozen, (self.store / 'artifact_storage/manifest.json').read_bytes())

if __name__ == '__main__':
    unittest.main(verbosity=2)
