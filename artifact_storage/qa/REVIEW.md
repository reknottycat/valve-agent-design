# Independent transport safety review

Reviewed: 2026-10-06 UTC  
Implementation: `artifact_storage/transport.py`  
Final tested implementation SHA-256: `efe99bd3cc0d5599c1110a23885e24cba4e26715fd24855f2b29c5307142041f`

## Result

37 independent tests passed (31 baseline tests and 6 regression tests, with additional parameterized subcases). No unresolved defect was found within the requested transport threat model. The reviewer changed only files and isolated fixtures under `artifact_storage/qa`; no implementation, engineering repository, or remote writes were performed.

## Verified behavior

- Raw, zlib, and automatic compression round-trip arbitrary bytes, empty files, multi-chunk incompressible data, and multi-megabyte highly compressed data without loss
- Chunk files are at most 409600 bytes; exact expected boundaries, counts, sizes, and SHA-256 hashes are checked
- Original paths are confined to `runs/20261006/`; direct child files are supported
- Absolute paths, traversal, backslashes, drive syntax, `.git` variants, duplicate/casefold paths, file/ancestor collisions, control characters, and ambiguous trailing dot/space paths are rejected
- Boolean, negative, floating-point, nonfinite, string, null, and oversized size values are rejected, as are unsupported codecs and duplicate JSON keys
- Missing, altered, truncated, wrong-raw-hash, and wrong-Git-hash payloads fail before any destination publication
- Zlib expansion beyond declared raw size, incomplete streams, trailing garbage, and concatenated streams are rejected
- All assets are decoded and verified before publication; a later pre-existing destination mismatch also prevents earlier new files being published
- Source and destination leaf/ancestor/root symlinks are rejected, including manifest and chunk symlinks; FIFOs are rejected without blocking
- Existing matching files are preserved; existing different files are never overwritten
- A destination file or symlink appearing at link time is not overwritten
- Named staging-file deletion or substitution cannot publish an unverified symlink; a renamed verified staging inode remains correctly anchored
- Non-Linux publication fails closed before new paths are created

## Findings resolved during review

1. Initial named staging-file publication could link a substituted symlink after closing the verified staging file. Publication now retains the descriptor and links the verified inode through Linux `/proc/self/fd` with no-overwrite link semantics. Reproductions cover both removal and renamed retained-inode cases
2. Initial public `write_bundle` accepted supplied chunk bytes independently of declared metadata and could write an oversized invalid chunk. The writer now verifies blob correspondence, byte counts, encoded hashes, decoded content, and raw/Git hashes before publication
3. Initial path validation incorrectly rejected direct child files under the authorized prefix. The prefix check now accepts those files

## Operational limits

New-file publication requires Linux with `/proc/self/fd`; verify-only reading uses the POSIX no-follow directory-descriptor implementation. Publication is atomic per file. It is not a transaction that rolls back earlier new files if a later destination changes concurrently after complete preflight. The checks do not claim protection against an adversary able to change the running process, kernel, or already-open verified inode contents with the same effective privileges.

## Reproduction

Run from the bundle or clone root:

    python artifact_storage/qa/adversarial_review.py
    python artifact_storage/qa/edge_regressions.py

Outputs are recorded in `adversarial-results.txt` and `edge-results.txt`.
