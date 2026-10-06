# Lossless artifact transport — explicit restoration required

**The `.bin` chunks in this folder are transport bytes, not original CAD, mesh,
drawing, or image files.** They were introduced because large individual GitHub
connector uploads timed out. Do not rename a chunk to `.step`, `.msh`, or an image
extension. Restore the original files before using them or checking their frozen
scientific manifests.

**Restoration is Linux-only. Only Linux has been tested.** Read-only `--verify-only`
also requires POSIX `O_NOFOLLOW` and directory-descriptor APIs; Windows is not
supported, and macOS compatibility has not been verified.

## Clone, verify, restore

Use a normal Git clone of the authorized private repository, and check out the
intended research branch/commit. Run these commands from that clone's root with
Python 3.9 or later on **Linux with `/proc/self/fd` available**. Python's standard
library is sufficient; no package installation, network access, credentials,
model execution, or CAD software is used by the restorer.

```sh
# Read-only verification: checks every chunk and every reconstructed raw file.
python3 -B artifact_storage/restore_artifacts.py --storage-root . --verify-only

# Explicitly materialize original paths beneath this clone.
python3 -B artifact_storage/restore_artifacts.py --storage-root . --restore --destination .
```

An empty, existing directory may be supplied as `--destination` to restore a
separate copy. Verification can also take `--destination .` to check existing
original files without creating any. Both roots and all traversed directories
must be real directories, not symbolic links. Unsupported write environments
fail closed; use a Linux environment rather than disabling safety checks.

The combined `manifest.json` covers all 22 large artifacts from the frozen
snapshots below. For a historical stage whose later chunks are not present, use
`--manifest artifact_storage/manifests/C2.json` , `C3.json`, or `R0.json`. A missing chunk is
an error, never permission to fabricate or substitute an original.

## What is preserved

- The original project-relative path, byte count, full SHA256, and Git blob SHA1
- Exact original bytes, including image pixels, text line endings and CAD data
- The source frozen commit and ordered chunk paths, byte counts, and SHA256s
- The transport encoding, encoded byte count and SHA256

Each chunk is at most 400 KiB (409,600 bytes). The `auto` splitter uses ordinary
lossless zlib only when it reduces size; otherwise it stores raw bytes. It does
not recompress an image format, rewrite a drawing, simplify a model, remesh, or
modify engineering calculations. Frozen engineering/scientific manifests are
unchanged and still describe the original raw files. The separate transport
manifest describes how to recover those files.

This package covers **22 files, 20,725,188 original bytes**, stored as **47 chunks,
13,450,325 encoded bytes**. All 22 were reconstructed into a fresh empty directory,
checked against their full SHA256s, and compared byte-for-byte with the frozen Git
objects. A second restore skipped all 22 matching existing files. See
`verification-evidence.json`, `test-evidence.json`, and the regression tests.

Frozen sources:

- T04: `705e3574ade324c382552ff5ff46d992697cbf92`
- C2: `2566bdee5b52024036e0bbac559dd78f8a903a34`
- C3: `31662e66f0a14e426ab60b53c870f958a60f4ce1`
- Recovery: `102ee213568ffe1b8a36f9fd3ace45a4039cc6ed`
- C4: `79887e8e6fbfaf074262facb5cd9d8ed1b863d27`
- R0 calculation book: `dd306c88fe42e7903894ae54e0ad6b2bf49ff808`

C2 (17 files), C3 (3 files), and R0 (the 2 DOCX/PDF calculation-book originals)
contribute artifacts over the size threshold. The unfrozen C5 directory and
unavailable upstream assets are outside this manifest. This is a transport-integrity statement, not a
claim that an upstream snapshot is complete or an engineering result is valid.
Uncertain, unavailable, and unvalidated scientific results remain as recorded in
the project. Transport cannot recover a source that was never available.

## Safety and limits

All encoded and decoded assets, then all pre-existing target files, are checked
before any original file is published. Existing files with the expected exact
content are skipped. An existing mismatching file aborts restoration; there is
**no force/overwrite option**. New files are published atomically with a
no-replace hard link to the verified open staging inode. This prevents replacing
user modifications, even if a target appears during publication. A substituted
staging-name symlink cannot become the published file.

The restorer rejects absolute paths, `..`, backslashes/drive syntax, `.git`
segments, duplicate or casefold-colliding paths, symlinks and non-regular source
or target files, malformed sizes (including booleans/nonfinite numbers), unknown
codecs, bad hashes, missing chunks, truncated/trailing compressed streams and
expansion beyond the declared raw size. Hard limits are 512 MiB per original,
2 GiB per whole bundle (raw and encoded separately), 16 MiB manifest, 10,000
files, and 100,000 chunks. It never extracts an archive or executes a payload.

Publication is per-file atomic, not a multi-file filesystem transaction: a disk
failure or concurrent edit after preflight may leave some newly restored files
and stop. Existing files are never overwritten. Fix the failure, inspect any
reported conflicting edits, then rerun. As with ordinary filesystem tools, do
not run concurrently with a hostile same-user process that can rewrite open
inodes or move entire directories. Checksums prove consistency with this
manifest; they do not independently authenticate the manifest's origin.

## Reproducible local tools

```sh
python3 -B artifact_storage/test_transport.py
python3 -B -O artifact_storage/test_transport.py

# Package explicitly named files into an existing empty output directory.
python3 -B artifact_storage/split_artifacts.py --source-root . \
  --output-root /absolute/existing/output \
  runs/20261006/EXAMPLE/model.step
```

`build_frozen_bundle.py` is a separate optional builder. It uses read-only local
Git commands for the explicit frozen commit IDs above; it is never imported or
run by the restorer. The working tree, including unfrozen C5, is not an input.
`stage-publication-map.json` tells the publisher which original large paths can
be represented by each stage's chunks and which manifest goes with that stage.
An already-present matching original may remain in Git; restoration verifies
and skips it. Publish the combined manifest only with all referenced chunks.
