#!/usr/bin/env python3
"""Offline, byte-exact chunk transport. Standard library only; POSIX Python 3.9+.

Restoration is opt-in. Chunks are encoded transport bytes, not usable CAD files.
No network, credentials, payload execution, or overwrite option exists.
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import tempfile
import zlib

FORMAT = 'valve-artifact-transport-v1'
CHUNK_BYTES = 400 * 1024
MAX_RAW_BYTES = 512 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_FILES = 10000
MAX_CHUNKS = 100000
IO_BYTES = 1024 * 1024
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
HEX40 = re.compile(r'[0-9a-f]{40}\Z')

class TransportError(ValueError):
    pass

def need(condition, message):
    if not condition:
        raise TransportError(message)

def number(value, name, maximum, minimum=0):
    need(type(value) is int and minimum <= value <= maximum,
         f'{name}: expected integer in [{minimum}, {maximum}]')
    return value

def digest(value, name, git=False):
    need(type(value) is str and (HEX40 if git else HEX64).fullmatch(value),
         f'{name}: invalid digest')
    return value

def path_parts(value, project=False):
    need(type(value) is str and 0 < len(value) <= 4096, 'Invalid path string')
    need(not value.startswith('/') and '\\' not in value and ':' not in value,
         f'Absolute, backslash, or drive path rejected: {value!r}')
    parts = value.split('/')
    for part in parts:
        need(part not in ('', '.', '..') and part.casefold() != '.git',
             f'Unsafe path segment: {value!r}')
        need(not any(ord(c) < 32 or ord(c) == 127 for c in part), 'Control character in path')
        need(not part.endswith((' ', '.')), 'Trailing dot/space in path')
    if project:
        need(len(parts) >= 3 and parts[:2] == ['runs', '20261006'],
             f'Original path outside runs/20261006: {value}')
    return parts

class PathSet:
    """Reject duplicates, component case collisions and file/directory conflicts."""
    def __init__(self):
        self.spelling = {}
        self.files = set()
        self.dirs = set()
    def add(self, path):
        parts = path_parts(path)
        names = ['/'.join(parts[:i]) for i in range(1, len(parts) + 1)]
        for name in names:
            folded = name.casefold()
            need(folded not in self.spelling or self.spelling[folded] == name,
                 f'Casefold collision: {name}')
            self.spelling[folded] = name
        need(path not in self.files and path not in self.dirs, f'Duplicate/conflicting path: {path}')
        need(not any(p in self.files for p in names[:-1]), f'File used as ancestor: {path}')
        self.files.add(path)
        self.dirs.update(names[:-1])

def support_check():
    need(os.name == 'posix' and hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY'),
         'Secure dir-fd restoration requires POSIX with O_NOFOLLOW; no unsafe fallback')

class SafeRoot:
    """Directory-fd traversal rejects symlinks in root, all ancestors and leaves."""
    def __init__(self, root):
        support_check()
        raw = os.fspath(root)
        need(type(raw) is str and '\x00' not in raw, 'Invalid root')
        need('..' not in raw.split('/'), 'Parent traversal in root argument')
        absolute = os.path.abspath(raw)
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in absolute.split('/')[1:]:
                if part:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd)
                    fd = child
        except BaseException:
            os.close(fd)
            raise
        self.fd = fd
    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
    def __enter__(self):
        return self
    def __exit__(self, *_):
        self.close()
    def parent(self, relative, create=False):
        parts = path_parts(relative)
        fd = os.dup(self.fd)
        try:
            for part in parts[:-1]:
                if create:
                    try:
                        os.mkdir(part, 0o755, dir_fd=fd)
                    except FileExistsError:
                        pass
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
            return fd, parts[-1]
        except BaseException:
            os.close(fd)
            raise
    def read(self, relative, limit):
        parent, leaf = self.parent(relative)
        try:
            fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        finally:
            os.close(parent)
        with os.fdopen(fd, 'rb') as f:
            need(stat.S_ISREG(os.fstat(f.fileno()).st_mode), f'Not a regular file: {relative}')
            need(os.fstat(f.fileno()).st_size <= limit, f'Oversized file: {relative}')
            data = f.read(limit + 1)
            need(len(data) <= limit, f'Oversized file: {relative}')
            return data
    def match(self, relative, size, sha256):
        """Return False only for a genuinely absent file/ancestor; reject all others."""
        try:
            parent, leaf = self.parent(relative)
        except FileNotFoundError:
            return False
        try:
            try:
                fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            except FileNotFoundError:
                return False
            with os.fdopen(fd, 'rb') as f:
                info = os.fstat(f.fileno())
                need(stat.S_ISREG(info.st_mode), f'Target is not regular: {relative}')
                need(info.st_size == size, f'Existing target differs: {relative}')
                h = hashlib.sha256()
                count = 0
                while True:
                    block = f.read(IO_BYTES)
                    if not block:
                        break
                    count += len(block)
                    need(count <= size, f'Existing target changed: {relative}')
                    h.update(block)
                need(count == size and h.hexdigest() == sha256, f'Existing target differs: {relative}')
                return True
        finally:
            os.close(parent)
    def publish(self, relative, source, size, sha256):
        """Atomic link publication cannot replace an existing leaf, even during a race."""
        if self.match(relative, size, sha256):
            return False
        need(sys.platform.startswith('linux') and os.path.isdir('/proc/self/fd'),
             'Atomic descriptor-anchored publication requires Linux /proc/self/fd; no unsafe fallback')
        parent, leaf = self.parent(relative, create=True)
        temp = '.valve-transport-' + secrets.token_hex(16) + '.tmp'
        made = False
        try:
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=parent)
            made = True
            with os.fdopen(fd, 'wb') as f:
                source.seek(0)
                count = 0
                h = hashlib.sha256()
                while True:
                    data = source.read(IO_BYTES)
                    if not data:
                        break
                    count += len(data)
                    need(count <= size, 'Staged source exceeded declared size')
                    h.update(data)
                    f.write(data)
                need(count == size and h.hexdigest() == sha256, 'Staged source changed')
                f.flush()
                os.fsync(f.fileno())
                os.fchmod(f.fileno(), 0o644)
                try:
                    # Link the verified open inode, never a replaceable source pathname.
                    # /proc/self/fd is the Linux kernel descriptor view. If the named
                    # staging inode was unlinked, Linux refuses rather than linking a
                    # substituted file or symlink. Existing destinations still fail EEXIST.
                    os.link(f'/proc/self/fd/{f.fileno()}', leaf, src_dir_fd=parent,
                            dst_dir_fd=parent, follow_symlinks=True)
                    os.fsync(parent)
                    return True
                except FileExistsError:
                    need(self.match(relative, size, sha256), f'Target appeared during publication: {relative}')
                    return False
        finally:
            if made:
                os.unlink(temp, dir_fd=parent)
            os.close(parent)

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, f'Duplicate JSON key: {key}')
        result[key] = value
    return result

def content_id(entry):
    return hashlib.sha256(('\0'.join([entry['path'], entry['sha256'], entry['encoding'],
                                     entry['encoded_sha256']])).encode('utf-8')).hexdigest()

def validate_manifest(manifest):
    need(type(manifest) is dict and manifest.get('format') == FORMAT, 'Unsupported manifest format')
    need(manifest.get('original_path_prefix') == 'runs/20261006/', 'Unsupported destination prefix')
    need(number(manifest.get('chunk_bytes'), 'chunk_bytes', CHUNK_BYTES, 1) == CHUNK_BYTES,
         'Unsupported chunk size')
    entries = manifest.get('files')
    need(type(entries) is list and len(entries) <= MAX_FILES, 'Invalid file list')
    originals, chunks = PathSet(), PathSet()
    total, encoded_total, total_chunks = 0, 0, 0
    for entry in entries:
        need(type(entry) is dict, 'Invalid file entry')
        path_parts(entry.get('path'), project=True)
        originals.add(entry['path'])
        raw = number(entry.get('bytes'), 'bytes', MAX_RAW_BYTES)
        encoded = number(entry.get('encoded_bytes'), 'encoded_bytes', MAX_RAW_BYTES)
        total += raw
        encoded_total += encoded
        need(encoded_total <= MAX_TOTAL_BYTES, 'Total encoded bytes exceed hard limit')
        need(total <= MAX_TOTAL_BYTES, 'Total raw bytes exceed hard limit')
        digest(entry.get('sha256'), 'sha256')
        digest(entry.get('encoded_sha256'), 'encoded_sha256')
        digest(entry.get('git_blob_sha1'), 'git_blob_sha1', git=True)
        need(entry.get('encoding') in ('raw', 'zlib'), 'Unsupported codec')
        if entry['encoding'] == 'raw':
            need(encoded == raw and entry['encoded_sha256'] == entry['sha256'], 'Raw encoding metadata mismatch')
        if 'source_commit' in entry:
            digest(entry['source_commit'], 'source_commit', git=True)
        cid = digest(entry.get('content_id'), 'content_id')
        need(cid == content_id(entry), 'Content namespace mismatch')
        parts = entry.get('chunks')
        need(type(parts) is list and len(parts) <= MAX_CHUNKS, 'Invalid chunks')
        need(len(parts) == (encoded + CHUNK_BYTES - 1) // CHUNK_BYTES, 'Incorrect chunk count')
        total_chunks += len(parts)
        need(total_chunks <= MAX_CHUNKS, 'Too many chunks')
        summed = 0
        for index, chunk in enumerate(parts):
            need(type(chunk) is dict, 'Invalid chunk')
            expected_path = f'artifact_storage/chunks/{cid}/{index:06d}.bin'
            need(chunk.get('path') == expected_path, 'Invalid or unordered chunk path')
            chunks.add(chunk['path'])
            size = number(chunk.get('bytes'), 'chunk bytes', CHUNK_BYTES, 1)
            need(size == min(CHUNK_BYTES, encoded - summed), 'Incorrect chunk boundary')
            digest(chunk.get('sha256'), 'chunk sha256')
            summed += size
        need(summed == encoded, 'Encoded byte count mismatch')
    return entries

def load_manifest(root, relative):
    data = root.read(relative, MAX_MANIFEST_BYTES)
    try:
        result = json.loads(data.decode('utf-8'), object_pairs_hook=unique_object,
                            parse_constant=lambda x: (_ for _ in ()).throw(TransportError('Nonfinite JSON number')))
    except (UnicodeError, json.JSONDecodeError) as e:
        raise TransportError(f'Invalid manifest JSON: {e}') from e
    validate_manifest(result)
    return result

def decode_asset(root, entry, output):
    raw_sha = hashlib.sha256()
    git_sha = hashlib.sha1(f"blob {entry['bytes']}\0".encode('ascii'))
    encoded_sha = hashlib.sha256()
    written = 0
    decoder = zlib.decompressobj() if entry['encoding'] == 'zlib' else None
    def consume(data):
        nonlocal written
        written += len(data)
        need(written <= entry['bytes'], f"Decompression exceeds declared raw size: {entry['path']}")
        raw_sha.update(data)
        git_sha.update(data)
        output.write(data)
    for chunk in entry['chunks']:
        data = root.read(chunk['path'], chunk['bytes'])
        need(len(data) == chunk['bytes'] and hashlib.sha256(data).hexdigest() == chunk['sha256'],
             f"Chunk missing, altered or truncated: {chunk['path']}")
        encoded_sha.update(data)
        if decoder is None:
            consume(data)
        else:
            pending = data
            while pending:
                block = decoder.decompress(pending, min(IO_BYTES, entry['bytes'] - written + 1))
                pending = decoder.unconsumed_tail
                consume(block)
                need(not decoder.unused_data, 'Trailing or concatenated zlib stream rejected')
    if decoder is not None:
        need(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
             'Incomplete or extra zlib stream')
    need(encoded_sha.hexdigest() == entry['encoded_sha256'], 'Encoded SHA256 mismatch')
    need(written == entry['bytes'] and raw_sha.hexdigest() == entry['sha256'],
         f"Restored raw size/SHA256 mismatch: {entry['path']}")
    need(git_sha.hexdigest() == entry['git_blob_sha1'], f"Git blob SHA1 mismatch: {entry['path']}")
    output.seek(0)

def restore(storage_root, destination=None, manifest_path='artifact_storage/manifest.json', verify_only=False):
    need(verify_only or destination is not None, 'Explicit --destination is required for restore')
    staged = []
    target = None
    try:
        with SafeRoot(storage_root) as storage:
            manifest = load_manifest(storage, manifest_path)
            entries = manifest['files']
            # Validate every encoded and raw asset before any original target is published.
            for entry in entries:
                tmp = tempfile.TemporaryFile('w+b')
                staged.append((entry, tmp))
                decode_asset(storage, entry, tmp)
            if destination is not None:
                target = SafeRoot(destination)
                for entry in entries:
                    target.match(entry['path'], entry['bytes'], entry['sha256'])
            created = 0
            if not verify_only:
                for entry, tmp in staged:
                    created += target.publish(entry['path'], tmp, entry['bytes'], entry['sha256'])
            return {'mode': 'verify-only' if verify_only else 'restore', 'verified_files': len(entries),
                    'verified_raw_bytes': sum(e['bytes'] for e in entries),
                    'created_files': created, 'existing_matching_files': 0 if verify_only else len(entries) - created}
    finally:
        if target is not None:
            target.close()
        for _, f in staged:
            f.close()

def make_entry(path, raw, compression='auto', source_commit=None):
    path_parts(path, project=True)
    need(type(raw) is bytes and len(raw) <= MAX_RAW_BYTES, 'Raw asset exceeds size limit')
    need(compression in ('auto', 'raw', 'zlib'), 'Unsupported compression request')
    compressed = zlib.compress(raw, 9) if compression != 'raw' else raw
    use_zlib = compression == 'zlib' or (compression == 'auto' and len(compressed) < len(raw))
    encoded = compressed if use_zlib else raw
    need(len(encoded) <= MAX_RAW_BYTES, 'Encoded size exceeds hard limit')
    entry = {'path': path, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
             'git_blob_sha1': hashlib.sha1(f'blob {len(raw)}\0'.encode('ascii') + raw).hexdigest(),
             'encoding': 'zlib' if use_zlib else 'raw', 'encoded_bytes': len(encoded),
             'encoded_sha256': hashlib.sha256(encoded).hexdigest(), 'chunks': []}
    if source_commit is not None:
        entry['source_commit'] = digest(source_commit, 'source_commit', git=True)
    entry['content_id'] = content_id(entry)
    blobs = []
    for index, start in enumerate(range(0, len(encoded), CHUNK_BYTES)):
        data = encoded[start:start + CHUNK_BYTES]
        chunk = {'path': f"artifact_storage/chunks/{entry['content_id']}/{index:06d}.bin",
                 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        entry['chunks'].append(chunk)
        blobs.append((chunk, data))
    return entry, blobs

def create_manifest(entries):
    manifest = {'format': FORMAT, 'original_path_prefix': 'runs/20261006/', 'chunk_bytes': CHUNK_BYTES,
                'notice': 'LOSSLESS TRANSPORT ONLY. Chunks are not original usable files. Run the offline restorer explicitly. Frozen scientific manifests are unchanged.',
                'files': entries}
    validate_manifest(manifest)
    return manifest

def write_bundle(output_root, packed, manifest_path='artifact_storage/manifest.json'):
    import io
    need(type(packed) is list and len(packed) <= MAX_FILES, 'Invalid packed asset list')
    manifest = create_manifest([entry for entry, _ in packed])
    blob_map = {}
    for entry, blobs in packed:
        need(type(blobs) is list and len(blobs) == len(entry['chunks']), 'Chunk payload count mismatch')
        for expected, pair in zip(entry['chunks'], blobs):
            need(type(pair) in (tuple, list) and len(pair) == 2, 'Invalid chunk payload')
            chunk, data = pair
            need(chunk == expected and type(data) is bytes and len(data) == expected['bytes'],
                 'Chunk payload metadata/size mismatch')
            need(hashlib.sha256(data).hexdigest() == expected['sha256'], 'Chunk payload SHA256 mismatch')
            blob_map[chunk['path']] = data
    class MemoryRoot:
        def read(self, path, limit):
            data = blob_map[path]
            need(len(data) <= limit, 'Oversized in-memory chunk')
            return data
    for entry, _ in packed:
        with tempfile.TemporaryFile('w+b') as raw_check:
            decode_asset(MemoryRoot(), entry, raw_check)
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    need(len(manifest_bytes) <= MAX_MANIFEST_BYTES, 'Manifest too large')
    # All entries are validated before bundle files are added; existing files are never overwritten.
    writes = [(chunk['path'], data) for _, blobs in packed for chunk, data in blobs]
    writes.append((manifest_path, manifest_bytes))
    paths = PathSet()
    for path, _ in writes:
        paths.add(path)
    with SafeRoot(output_root) as output:
        for path, data in writes:
            output.match(path, len(data), hashlib.sha256(data).hexdigest())
        for path, data in writes:
            output.publish(path, io.BytesIO(data), len(data), hashlib.sha256(data).hexdigest())
    return manifest

def split(source_root, output_root, paths, compression='auto', manifest_path='artifact_storage/manifest.json'):
    packed = []
    seen = PathSet()
    total = 0
    with SafeRoot(source_root) as source:
        for path in paths:
            path_parts(path, project=True)
            seen.add(path)
            need(len(packed) < MAX_FILES, 'Too many files')
            raw = source.read(path, MAX_RAW_BYTES)
            total += len(raw)
            need(total <= MAX_TOTAL_BYTES, 'Total raw bytes exceed hard limit')
            packed.append(make_entry(path, raw, compression))
    return write_bundle(output_root, packed, manifest_path)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    pack = commands.add_parser('split', help='Package explicitly named original files without modifying them')
    pack.add_argument('--source-root', required=True)
    pack.add_argument('--output-root', required=True, help='Existing directory')
    pack.add_argument('--compression', choices=['auto', 'raw', 'zlib'], default='auto')
    pack.add_argument('--manifest', default='artifact_storage/manifest.json')
    pack.add_argument('paths', nargs='+', help='Project-relative paths below runs/20261006/')
    unpack = commands.add_parser('restore', help='Verify transport; restore only when explicitly requested')
    unpack.add_argument('--storage-root', required=True, help='Clone or bundle root')
    unpack.add_argument('--manifest', default='artifact_storage/manifest.json')
    mode = unpack.add_mutually_exclusive_group(required=True)
    mode.add_argument('--verify-only', action='store_true')
    mode.add_argument('--restore', action='store_true')
    unpack.add_argument('--destination', help='Existing root directory for original paths')
    args = parser.parse_args(argv)
    try:
        if args.command == 'split':
            result = split(args.source_root, args.output_root, args.paths, args.compression, args.manifest)
            print(json.dumps({'files': len(result['files']), 'manifest': args.manifest}))
        else:
            print(json.dumps(restore(args.storage_root, args.destination, args.manifest, args.verify_only)))
        return 0
    except (TransportError, OSError, zlib.error) as exc:
        print(f'Transport refused: {exc}', file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
