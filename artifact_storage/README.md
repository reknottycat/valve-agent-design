# C2 artifact transport — explicit restoration required

**This historical C2 stage contains exactly 17 original files represented by 38
lossless chunks. The chunks are transport data, not directly usable original
files. Restoration is Linux-only; only Linux has been tested.**

The 17 originals contain 15,130,044 bytes. Their transport contains 11,006,932
bytes in chunks no larger than 409,600 bytes (400 KiB). They come from frozen
C2 commit `2566bdee5b52024036e0bbac559dd78f8a903a34`. `manifest.json` is an exact
copy of `manifests/C2.json`; both refer only to the 38 chunks included here.
C3 artifacts and later calculation-book artifacts are not part of this stage.

## Verify and restore

After cloning the private project repository and checking out this C2 stage,
run from the clone root with Python 3.9+ on Linux with `/proc/self/fd`:

```sh
python3 -B artifact_storage/restore_artifacts.py --storage-root . --verify-only
python3 -B artifact_storage/restore_artifacts.py --storage-root . --restore --destination .
```

The destination must already exist. Use an empty directory as `--destination`
for a separate copy. Verification alone does not create original files.
Read-only `--verify-only` also requires POSIX `O_NOFOLLOW` and directory-descriptor
APIs. Windows is unsupported; macOS compatibility has not been verified.

The restorer uses only Python's standard library, without network access,
credentials, installation, CAD/model execution or archive extraction. It checks
every chunk and every decoded original before publishing any original target.
Existing matching files are verified and skipped. Existing different files
cause a refusal; there is no overwrite option. New files are published
atomically without replacing an existing target. Publication requires Linux
`/proc/self/fd`; unsupported write environments fail closed.

Original paths, byte counts, SHA256 and Git blob SHA1 are preserved. Optional
zlib compresses raw file bytes losslessly; it does not edit images, simplify CAD,
or change text line endings. Frozen scientific manifests remain unchanged.
Path traversal, absolute/drive paths, `.git`, casefold collisions, symbolic
links, non-regular files, malformed sizes, unknown codecs, missing/altered
chunks, and compressed streams exceeding declared raw size are rejected.
Hard limits are 512 MiB per file, 2 GiB per bundle for raw and encoded bytes,
16 MiB per manifest, 10,000 files and 100,000 chunks.

Publication is atomic per file, not a batch rollback transaction. A disk failure
or concurrent change after preflight can stop after some new files have been
created; none of the existing files will be overwritten. Do not run concurrently
with a hostile process able to modify open inodes or move entire directories.
Checksums establish consistency with the manifest, not independent authenticity.

## Evidence and local tests

`verification-evidence.json` records fresh-directory reconstruction of all 17
originals, byte-for-byte equality with their frozen Git objects, and matching
second-run skips. `test-evidence.json` records the 33 included regression tests
passing both normally and with Python optimization:

```sh
python3 -B artifact_storage/test_transport.py
python3 -B -O artifact_storage/test_transport.py
```

The splitter can package explicitly named files below `runs/20261006/` without
changing them; see `python3 -B artifact_storage/split_artifacts.py --help`.

This stage's integrity checks do not claim an upstream snapshot is complete or
that the engineering is validated. Unavailable sources cannot be reconstructed
from this transport. Scientific uncertainty and release restrictions remain as
recorded in the project. Later stages can add their own transport manifests and
replace the combined manifest when all their referenced chunks are present.
