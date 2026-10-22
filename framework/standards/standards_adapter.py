"""Read-only, pinned standards research retrieval. Never an engineering release gate."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

REPOSITORY = "reknottycat/standards-kb"
COMMIT = "7eda528a8795b8fbd850d6d35ac67e198de5810a"
GRADES = {"E0", "E1", "E2", "E3"}
STATUSES = {"VERIFIED_CLAUSE", "UNVERIFIED_CLAUSE", "PENDING_VERIFICATION", "CONFLICT", "SUPERSEDED"}
LAYERS = {"formulas": "F-", "parameters": "P-", "data": "D-"}
NOTICE = "Research retrieval only; a query hit or structural validation is not engineering acceptance or release."


class AdapterError(ValueError):
    """Input rejected without partial results."""


def _pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise AdapterError(f"Duplicate JSON key: {key}")
        obj[key] = value
    return obj


def _bad_constant(value):
    raise AdapterError(f"Non-JSON numeric constant: {value}")


def _json(raw, label):
    try:
        return json.loads(raw, object_pairs_hook=_pairs, parse_constant=_bad_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise AdapterError(f"Invalid JSON in {label}: {exc}") from exc


def _read(path):
    try:
        return path.read_bytes()
    except OSError as exc:
        raise AdapterError(f"Missing/unreadable expected file: {path}") from exc


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _file_path(root, relative):
    if not isinstance(relative, str):
        raise AdapterError("Manifest paths must be strings")
    parts = PurePosixPath(relative).parts
    if (len(parts) != 3 or parts[0] != "kb" or parts[1] not in LAYERS
            or not parts[2].endswith(".json") or "\\" in relative or ".." in parts):
        raise AdapterError(f"Unsupported record path: {relative}")
    path = root.joinpath(*parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise AdapterError(f"Record path escapes snapshot: {relative}")
    return path, parts[1]


class StandardsAdapter:
    """Load ALL manifest-listed inputs atomically; expose only research responses.

    Manifest hashes anchor bytes to a reviewed manifest, not independently to GitHub.
    The manifest must be created/reviewed from the exact pinned upstream commit.
    """

    def __init__(self, root, manifest_path):
        root = Path(root)
        manifest_raw = _read(Path(manifest_path))
        manifest = _json(manifest_raw, "manifest")
        if not isinstance(manifest, dict) or manifest.get("repository") != REPOSITORY or manifest.get("commit") != COMMIT:
            raise AdapterError("Manifest repository/commit does not match pinned upstream")
        if manifest.get("scope") != "selected_files":
            raise AdapterError("Manifest must declare selected_files scope (not full-repository coverage)")
        files = manifest.get("files")
        if not isinstance(files, dict) or not files:
            raise AdapterError("Manifest must list nonempty expected files and SHA256 hashes")
        records = {}
        for relative, expected_hash in sorted(files.items()):
            if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                raise AdapterError(f"Invalid SHA256 for {relative}")
            path, layer = _file_path(root, relative)
            raw = _read(path)
            actual_hash = _digest(raw)
            if actual_hash != expected_hash:
                raise AdapterError(f"SHA256 mismatch: {relative}")
            obj = _json(raw, relative)
            entries = obj.get("entries") if layer == "data" and isinstance(obj, dict) else obj
            if not isinstance(entries, list) or not entries:
                raise AdapterError(f"Expected nonempty record array in {relative}")
            if layer == "data" and not isinstance(obj, dict):
                raise AdapterError(f"Expected data wrapper in {relative}")
            for entry in entries:
                if not isinstance(entry, dict):
                    raise AdapterError(f"Non-object record in {relative}")
                eid = entry.get("id")
                if not isinstance(eid, str) or not eid.startswith(LAYERS[layer]) or not eid[len(LAYERS[layer]):].strip():
                    raise AdapterError(f"Invalid record ID in {relative}: {eid!r}")
                if eid in records:
                    raise AdapterError(f"Duplicate record ID: {eid}")
                ev = entry.get("evidence")
                if not isinstance(ev, dict) or not isinstance(ev.get("grade"), str) or ev["grade"] not in GRADES or not isinstance(ev.get("status"), str) or ev["status"] not in STATUSES:
                    raise AdapterError(f"Missing/invalid original evidence.grade or evidence.status: {eid}")
                if not isinstance(entry.get("source"), dict):
                    raise AdapterError(f"Missing source object: {eid}")
                # Preserve all upstream values, including conflicting metadata: do not repair or promote.
                records[eid] = {
                    "record": copy.deepcopy(entry),
                    "provenance": {"repository": REPOSITORY, "commit": COMMIT,
                                   "path": relative, "id": eid, "file_sha256": actual_hash,
                                   "record_sha256": _digest(json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())},
                    "research_retrievable": True,
                    "engineering_release": False,
                    "engineering_acceptance": "NOT_ASSESSED",
                    "notice": NOTICE,
                }
        self._records = records
        self._manifest_hash = _digest(manifest_raw)

    def query(self, text="", *, record_id=None):
        """Deterministic literal search; no formula evaluation, ranking, or grade promotion."""
        if not isinstance(text, str):
            raise AdapterError("Query text must be a string")
        if record_id is not None and not isinstance(record_id, str):
            raise AdapterError("Record ID must be a string")
        matches = []
        for eid, result in sorted(self._records.items()):
            if record_id is not None and eid != record_id:
                continue
            if text.casefold() not in json.dumps(result["record"], ensure_ascii=False).casefold():
                continue
            matches.append(copy.deepcopy(result))
        return {"results": matches, "count": len(matches), "scope": "selected_files",
                "repository": REPOSITORY, "commit": COMMIT, "manifest_sha256": self._manifest_hash,
                "engineering_release": False, "engineering_acceptance": "NOT_ASSESSED", "notice": NOTICE}


def main(argv=None):
    parser = argparse.ArgumentParser(description=NOTICE)
    parser.add_argument("--root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--id", dest="record_id")
    parser.add_argument("--query", default="")
    args = parser.parse_args(argv)
    try:
        result = StandardsAdapter(args.root, args.manifest).query(args.query, record_id=args.record_id)
    except AdapterError as exc:
        print(json.dumps({"error": str(exc), "results": [], "engineering_release": False,
                          "engineering_acceptance": "NOT_ASSESSED", "notice": NOTICE}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
