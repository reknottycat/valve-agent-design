"""Read-only current standards research API/CLI. Never an engineering release gate."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import stat
from pathlib import Path, PurePosixPath
import re
import sys
from types import MappingProxyType, ModuleType

# Load the project helper by its exact sibling source, including under python -I.
# It is part of this reviewed adapter release, not an upstream or sys.path plugin.
_helper_path = Path(__file__).with_name('trusted_upstream.py')
_runtime = ModuleType('_standards_trusted_upstream')
_runtime.__file__ = str(_helper_path)
exec(compile(_helper_path.read_bytes(), str(_helper_path), 'exec', dont_inherit=True), _runtime.__dict__)
FrozenPath, load_modules = _runtime.FrozenPath, _runtime.load_modules

REPOSITORY = 'reknottycat/standards-kb'
COMMIT = '19d586bb53cb452325d815313a895a1dfafa868b'
LOCK_SHA256 = 'ca5e450dcc1fa21b00f1eb75ed513ed29e201190ead439818d69833e8d0c1780'
DEFAULT_LOCK = Path(__file__).with_name('upstream.lock.json')
MAX_INPUT_BYTES = 4 * 1024 * 1024  # Resource bound per file, not an engineering threshold.
CARD_PATH = 'kb/acceptance/AC-VALVE-001.json'
GRADES = {'E0', 'E1', 'E2', 'E3'}
STATUSES = {'VERIFIED_CLAUSE', 'UNVERIFIED_CLAUSE', 'PENDING_VERIFICATION', 'CONFLICT', 'SUPERSEDED'}
LAYERS = {'formulas': 'F-', 'parameters': 'P-', 'data': 'D-', 'derived': 'DV-'}
NOTICE = ('Research retrieval and recorded-evidence readiness only; upstream calculation '
          'eligibility is not applicability to this bronze valve or engineering release.')


class AdapterError(ValueError):
    """Input rejected without partial results."""


def _pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise AdapterError(f'Duplicate JSON key: {key}')
        obj[key] = value
    return obj


def _bad_constant(value):
    raise AdapterError(f'Non-JSON numeric constant: {value}')


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise AdapterError(f'Non-finite JSON number: {value}')
    return number


def _json(raw, label):
    try:
        return json.loads(raw, object_pairs_hook=_pairs, parse_constant=_bad_constant,
                          parse_float=_finite_float)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise AdapterError(f'Invalid JSON in {label}: {exc}') from exc


def _read(path):
    """Bounded regular-file read; never block opening a FIFO/device as an input."""
    fd = None
    try:
        flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(path, flags)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise AdapterError(f'Expected a regular input file: {path}')
        if info.st_size > MAX_INPUT_BYTES:
            raise AdapterError(f'Input exceeds {MAX_INPUT_BYTES} byte resource limit: {path}')
        with os.fdopen(fd, 'rb') as stream:
            fd = None
            raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise AdapterError(f'Input grew beyond resource limit: {path}')
        return raw
    except (OSError, ValueError, RuntimeError) as exc:
        if isinstance(exc, AdapterError):
            raise
        raise AdapterError(f'Missing/unreadable/unsafe input file: {path}: {exc}') from exc
    finally:
        if fd is not None:
            os.close(fd)


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def _file_path(root, relative):
    if not isinstance(relative, str):
        raise AdapterError('Lock paths must be strings')
    path = PurePosixPath(relative)
    if (path.is_absolute() or '..' in path.parts or '\\' in relative
            or path.as_posix() != relative or not path.parts):
        raise AdapterError(f'Unsafe dependency path: {relative}')
    try:
        target = root.joinpath(*path.parts)
        if not target.resolve().is_relative_to(root.resolve()):
            raise AdapterError(f'Dependency path escapes snapshot: {relative}')
        return target
    except (OSError, ValueError, RuntimeError) as exc:
        if isinstance(exc, AdapterError):
            raise
        raise AdapterError(f'Unsafe snapshot path: {relative}: {exc}') from exc


def _entries(files):
    """Strict ingestion of all four layers; never upstream's permissive glob loader."""
    records = {}
    for relative, raw in sorted(files.items()):
        parts = PurePosixPath(relative).parts
        if len(parts) != 3 or parts[0] != 'kb' or parts[1] not in LAYERS:
            continue
        layer = parts[1]
        obj = _json(raw, relative)
        if layer == 'data' and not isinstance(obj, dict):
            raise AdapterError(f'Expected data wrapper in {relative}')
        entries = obj.get('entries') if layer == 'data' and isinstance(obj, dict) else obj
        if not isinstance(entries, list) or not entries:
            raise AdapterError(f'Expected nonempty record array in {relative}')
        for entry in entries:
            if not isinstance(entry, dict):
                raise AdapterError(f'Non-object record in {relative}')
            eid = entry.get('id')
            if not isinstance(eid, str) or not eid.startswith(LAYERS[layer]) or not eid[len(LAYERS[layer]):].strip():
                raise AdapterError(f'Invalid record ID in {relative}: {eid!r}')
            if eid in records:
                raise AdapterError(f'Duplicate record ID: {eid}')
            ev = entry.get('evidence')
            if (not isinstance(ev, dict) or not isinstance(ev.get('grade'), str)
                    or ev['grade'] not in GRADES or not isinstance(ev.get('status'), str)
                    or ev['status'] not in STATUSES):
                raise AdapterError(f'Missing/invalid evidence: {eid}')
            if not isinstance(entry.get('source'), dict):
                raise AdapterError(f'Missing source object: {eid}')
            records[eid] = (entry, relative)
    return records


class StandardsAdapter:
    """Same research API, now pinned to reviewed code, complete records and card.

    A caller-supplied manifest must be byte-identical to the production lock.
    Rehashing changed/old snapshot files cannot bless a different implementation.
    All dependency bytes are captured and authenticated before upstream execution.
    """
    def __init__(self, root, manifest_path=DEFAULT_LOCK):
        try:
            root = Path(root)
            manifest_raw = _read(Path(manifest_path))
        except (TypeError, ValueError, OSError, RuntimeError) as exc:
            if isinstance(exc, AdapterError):
                raise
            raise AdapterError(f'Invalid snapshot/lock path: {exc}') from exc
        manifest = _json(manifest_raw, 'upstream lock')
        if _digest(manifest_raw) != LOCK_SHA256:
            raise AdapterError('Production lock SHA256 mismatch; arbitrary manifests are not trusted')
        if manifest.get('repository') != REPOSITORY or manifest.get('commit') != COMMIT or manifest.get('scope') != 'selected_files':
            raise AdapterError('Lock repository/commit/scope does not match pinned upstream')
        files = {}
        for relative, expected_hash in sorted(manifest['files'].items()):
            if not isinstance(expected_hash, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_hash):
                raise AdapterError(f'Invalid SHA256 for {relative}')
            raw = _read(_file_path(root, relative))
            if _digest(raw) != expected_hash:
                raise AdapterError(f'SHA256 mismatch: {relative}')
            files[relative] = raw
        # Parse ALL JSON strictly, including card/mapping, before running code.
        for relative, raw in files.items():
            if relative.endswith('.json'):
                _json(raw, relative)
        records = _entries(files)
        frozen = MappingProxyType(files)
        try:
            rules = load_modules(frozen)
            metadata = rules['formula_input_contract'].validate(FrozenPath(frozen))
            checks = {}
            for eid, (entry, _) in records.items():
                issues = rules['valve_completion_contract'].check_entry(entry)
                if issues:
                    raise AdapterError(f'Upstream valve model contract rejected {eid}: {issues}')
                if eid == 'F-FLW-001':
                    checks[eid] = rules['flw001_contract'].assess(entry)
                    if checks[eid]['consistency'] != 'CONSISTENT_AT_RECORDED_SAMPLE' or checks[eid]['codes']:
                        raise AdapterError('Current F-FLW-001 consistency contract rejected')
            card = _json(files[CARD_PATH], CARD_PATH)
            if card.get('id') != 'AC-VALVE-001':
                raise AdapterError('Only the pinned AC-VALVE-001 baseline is supported')
            # Use the same strict record set, never permissive upstream load_entries.
            assessment = rules['acceptance_card'].assess(card, {k: v[0] for k, v in records.items()})
            self._records = {}
            kb = rules['kb_entries']
            for eid, (entry, relative) in records.items():
                self._records[eid] = {
                    'record': copy.deepcopy(entry),
                    'provenance': {'repository': REPOSITORY, 'commit': COMMIT, 'path': relative,
                                   'id': eid, 'file_sha256': _digest(files[relative]),
                                   'record_sha256': _digest(_canonical(entry))},
                    'research_retrievable': True,
                    'source_status': kb.entry_status(entry), 'source_grade': kb.entry_grade(entry),
                    'upstream_calc_eligibility': {
                        'usable': kb.entry_usable_for_calc(entry),
                        'block_reason': kb.engineering_use_block_reason(entry),
                        'scope': 'Upstream source-status/use quarantine only; not a project calculation approval'},
                    'project_applicability': {'status': 'NOT_ASSESSED', 'approved': False,
                                              'configuration_id': card['configuration']['id']},
                    'engineering_release': False, 'engineering_acceptance': 'NOT_ASSESSED',
                    'notice': NOTICE,
                }
                if eid in checks:
                    self._records[eid]['research_consistency'] = checks[eid]
            # acceptance_card checks flange quarantine but not every explicit use flag.
            # Apply the single upstream eligibility rule to calculation/normative refs.
            for row in assessment['checks']:
                for reference in row['entry_evidence']:
                    eid = reference['id']
                    if reference['role'] in ('NORMATIVE_BASIS', 'CALCULATION_SUPPORT'):
                        usable = self._records[eid]['upstream_calc_eligibility']['usable'] if eid in self._records else False
                        reference['upstream_usable_for_calculation'] = usable
                        if not usable:
                            row['reasons'].append('ADAPTER_UPSTREAM_CALCULATION_INELIGIBLE:' + eid)
                            row['finding'] = 'HOLD'
            if any(r['required'] and r['finding'] == 'HOLD' for r in assessment['checks']) and assessment['status'] != 'FAIL':
                assessment['status'] = 'HOLD'
            self._acceptance = assessment
            self._metadata = metadata
            self._pending_limits = [copy.deepcopy(x) for c in card['checks']
                                    for x in c['protocol']['pending_numeric_limits']]
            self._card_file_sha256 = _digest(files[CARD_PATH])
        except AdapterError:
            raise
        except Exception as exc:
            raise AdapterError(f'Upstream guard/dependency rejected inputs: {exc}') from exc
        self._manifest_hash = _digest(manifest_raw)

    def _context(self):
        return {'scope': 'selected_files', 'repository': REPOSITORY, 'commit': COMMIT,
                'manifest_sha256': self._manifest_hash, 'record_count': len(self._records),
                'formula_input_metadata_check': copy.deepcopy(self._metadata),
                'engineering_release': False, 'engineering_acceptance': 'NOT_ASSESSED', 'notice': NOTICE}

    def query(self, text='', *, record_id=None):
        """Literal research retrieval, retaining original source evidence and limitations."""
        if not isinstance(text, str) or (record_id is not None and not isinstance(record_id, str)):
            raise AdapterError('Query text and record ID must be strings')
        matches = [copy.deepcopy(result) for eid, result in sorted(self._records.items())
                   if (record_id is None or eid == record_id)
                   and text.casefold() in json.dumps(result['record'], ensure_ascii=False).casefold()]
        return dict(self._context(), results=matches, count=len(matches))

    def assess_acceptance(self):
        """Assess only locked current-card bytes. No external card/configuration API."""
        return dict(self._context(), acceptance=copy.deepcopy(self._acceptance),
                    pending_numeric_limits=copy.deepcopy(self._pending_limits),
                    card_binding={'mode': 'PINNED_BASELINE_ONLY', 'path': CARD_PATH,
                                  'file_sha256': self._card_file_sha256,
                                  'configuration_hash_authentication': False},
                    project_applicability={'status': 'UNCONFIRMED', 'approved': False,
                                           'configuration_id': '522-35.4179'})


def main(argv=None):
    parser = argparse.ArgumentParser(description=NOTICE)
    parser.add_argument('--root', required=True)
    parser.add_argument('--manifest', default=str(DEFAULT_LOCK), help='Must equal the production lock bytes')
    parser.add_argument('--id', dest='record_id')
    parser.add_argument('--query', default='')
    parser.add_argument('--acceptance', action='store_true', help='Assess the pinned current baseline card')
    args = parser.parse_args(argv)
    try:
        if args.acceptance and (args.record_id is not None or args.query):
            raise AdapterError('--acceptance cannot be combined with a record query')
        adapter = StandardsAdapter(args.root, args.manifest)
        result = adapter.assess_acceptance() if args.acceptance else adapter.query(args.query, record_id=args.record_id)
    except AdapterError as exc:
        print(json.dumps({'error': str(exc), 'status': 'INVALID', 'results': [],
                          'engineering_release': False, 'engineering_acceptance': 'NOT_ASSESSED',
                          'notice': NOTICE}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if args.acceptance and result['acceptance']['status'] != 'READY_FOR_REVIEW' else 0


if __name__ == '__main__':
    sys.exit(main())
