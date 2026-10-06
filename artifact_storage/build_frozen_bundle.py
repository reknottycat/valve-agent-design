#!/usr/bin/env python3
"""Rebuild this transport from explicitly frozen, local Git objects only.

Git is used solely as an offline read-only object source. This builder is not
imported or invoked by the standard-library restorer; no remote commands occur.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import transport as t

STAGES = [
    ('T04', '705e3574ade324c382552ff5ff46d992697cbf92'),
    ('C2', '2566bdee5b52024036e0bbac559dd78f8a903a34'),
    ('C3', '31662e66f0a14e426ab60b53c870f958a60f4ce1'),
    ('recovery', '102ee213568ffe1b8a36f9fd3ace45a4039cc6ed'),
    ('C4', '79887e8e6fbfaf074262facb5cd9d8ed1b863d27'),
    ('R0', 'dd306c88fe42e7903894ae54e0ad6b2bf49ff808'),
]

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])

def build(repo, output):
    t.SafeRoot(repo).close()
    t.SafeRoot(output).close()
    packed = []
    seen = {}
    stage_map = []
    for stage, commit in STAGES:
        data = git(repo, 'ls-tree', '-rlz', commit, '--', 'runs/20261006/')
        stage_entries = []
        for record in data.split(b'\0'):
            if not record:
                continue
            header, path_bytes = record.split(b'\t', 1)
            mode, kind, sha, size = header.decode('ascii').split()
            path = path_bytes.decode('utf-8')
            if int(size) <= t.CHUNK_BYTES:
                continue
            t.need(kind == 'blob' and mode in ('100644', '100755'), 'Nonregular source object rejected')
            t.path_parts(path, project=True)
            if path in seen:
                t.need(seen[path] == sha, f'Frozen path changed between snapshots: {path}')
                continue
            raw = git(repo, 'cat-file', 'blob', sha)
            t.need(len(raw) == int(size), 'Git source size mismatch')
            entry, chunks = t.make_entry(path, raw, source_commit=commit)
            t.need(entry['git_blob_sha1'] == sha, 'Git source identity mismatch')
            seen[path] = sha
            packed.append((entry, chunks))
            stage_entries.append(entry)
        if stage_entries:
            t.write_bundle(output, [(e, c) for e, c in packed if e in stage_entries],
                           f'artifact_storage/manifests/{stage}.json')
        stage_map.append({'stage': stage, 'frozen_commit': commit,
                          'manifest_path': f'artifact_storage/manifests/{stage}.json' if stage_entries else None,
                          'transport_original_paths': [e['path'] for e in stage_entries],
                          'transport_chunk_paths': [c['path'] for e in stage_entries for c in e['chunks']]})
    manifest = t.write_bundle(output, packed)
    evidence = {'format': 'valve-transport-evidence-v1', 'frozen_stages': dict(STAGES),
                'excluded': ['unfrozen C5', 'unavailable upstream assets'],
                'artifact_count': len(packed), 'raw_bytes': sum(e['bytes'] for e, _ in packed),
                'encoded_bytes': sum(e['encoded_bytes'] for e, _ in packed),
                'chunk_count': sum(len(e['chunks']) for e, _ in packed),
                'largest_chunk_bytes': max((c['bytes'] for e, _ in packed for c in e['chunks']), default=0),
                'fresh_restore_verified': False, 'per_file': []}
    with tempfile.TemporaryDirectory(prefix='valve-transport-verification-') as dest:
        evidence['verify_only'] = t.restore(output, verify_only=True)
        evidence['first_restore'] = t.restore(output, dest)
        evidence['second_restore'] = t.restore(output, dest)
        for entry, _ in packed:
            raw = (Path(dest) / entry['path']).read_bytes()
            actual = hashlib.sha256(raw).hexdigest()
            t.need(actual == entry['sha256'] and len(raw) == entry['bytes'], 'Fresh restore mismatch')
            # Compare again against Git, independently of the manifest's raw SHA256.
            original = git(repo, 'cat-file', 'blob', entry['git_blob_sha1'])
            t.need(raw == original, 'Fresh restore differs from exact Git blob bytes')
            evidence['per_file'].append({'path': entry['path'], 'bytes': len(raw), 'sha256': actual,
                                         'git_blob_sha1': entry['git_blob_sha1'], 'exact_git_bytes_equal': True})
        evidence['fresh_restore_verified'] = True
    stage_path = Path(output) / 'artifact_storage' / 'stage-publication-map.json'
    evidence_path = Path(output) / 'artifact_storage' / 'verification-evidence.json'
    for path, obj in [(stage_path, stage_map), (evidence_path, evidence)]:
        payload = (json.dumps(obj, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
        relative = path.relative_to(output).as_posix()
        import io
        with t.SafeRoot(output) as root:
            root.publish(relative, io.BytesIO(payload), len(payload), hashlib.sha256(payload).hexdigest())
    return {k: v for k, v in evidence.items() if k != 'per_file'}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository', required=True)
    p.add_argument('--output', required=True, help='Existing destination directory')
    args = p.parse_args()
    print(json.dumps(build(Path(args.repository), Path(args.output)), indent=2))
