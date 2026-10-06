#!/usr/bin/env python3
"""Read-only hash/size verification. Does not build CAD, install, solve or synchronize."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inside_file(base, relative):
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError(f'Unsafe path: {relative}')
    target = base / rel
    if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(base.resolve()):
        raise ValueError(f'Missing or unsafe file: {relative}')
    return target


def verify(root, checkpoint, archive_dir=None):
    results = []
    for entry in checkpoint['frozen_directories']:
        base = root / entry['path']
        manifest = inside_file(base, 'artifact_manifest.json')
        if sha256(manifest) != entry['manifest_sha256']:
            raise ValueError(f'Manifest hash mismatch: {entry["path"]}')
        rows = json.loads(manifest.read_text(encoding='utf-8'))['files']
        if len(rows) != entry['file_count'] or len({row['path'] for row in rows}) != len(rows):
            raise ValueError(f'Manifest count/duplicate mismatch: {entry["path"]}')
        for row in rows:
            path = inside_file(base, row['path'])
            if type(row['bytes']) is not int or path.stat().st_size != row['bytes'] or sha256(path) != row['sha256']:
                raise ValueError(f'Artifact mismatch: {entry["path"]}/{row["path"]}')
        results.append({'directory': entry['path'], 'verified_files': len(rows)})
    archives = []
    if archive_dir is not None:
        for entry in checkpoint['archives']:
            path = inside_file(archive_dir, entry['filename'])
            if sha256(path) != entry['sha256']:
                raise ValueError(f'Archive hash mismatch: {entry["filename"]}')
            if path.suffix == '.zip':
                with zipfile.ZipFile(path) as archive:
                    bad = archive.testzip()
                    if bad is not None:
                        raise ValueError(f'Archive CRC mismatch: {bad}')
            archives.append(entry['filename'])
    return {'status': 'FROZEN_ARTIFACT_INTEGRITY_PASS', 'directories': results,
            'archives_verified': archives, 'archives_requested': archive_dir is not None,
            'engineering_acceptance': False, 'manufacturing_authorized': False,
            'solver_execution_performed': False, 'github_write_performed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--archive-dir', type=Path, help='Optional directory containing every pinned delivery archive')
    args = parser.parse_args()
    try:
        checkpoint = json.loads((Path(__file__).parent / 'state.json').read_text(encoding='utf-8'))
        result = verify(args.root, checkpoint, args.archive_dir)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(json.dumps({'status': 'FAIL', 'error': str(exc), 'manufacturing_authorized': False}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
