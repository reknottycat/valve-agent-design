#!/usr/bin/env python3
"""Read-only, fixed-protocol continuation log audit; never starts a solver."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from window_contract import WindowContract
from check_output import check


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if not __debug__:
        raise RuntimeError('Python optimization disables parser assertions; run without -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--ids', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='new file; never overwrite')
    args = parser.parse_args()
    paths = {'log':args.log, 'ids':args.ids, 'contract':args.contract}
    for role, path in paths.items():
        limit = 1048576 if role == 'log' else 16384
        if not path.is_file() or path.stat().st_size > limit:
            raise ValueError(role + ' missing or exceeds fixed input limit')
    before = {k:digest(p) for k,p in paths.items()}
    contract = WindowContract.from_json(args.contract)
    result = check(args.log, args.ids, contract)
    if before != {k:digest(p) for k,p in paths.items()}:
        raise ValueError('input changed during audit')
    envelope = {'evidence_scope':'saved log protocol/numerical consistency, not independent native execution authentication',
                'input_sha256':before, 'engineering_release':False,
                'starts_solver':False, 'authorizes_restart':False, 'observation':result}
    encoded = json.dumps(envelope, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(encoded)
    print('PASS: supported saved log audited; no solver, restart authorization or engineering release')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (AssertionError, ValueError, TypeError, KeyError, IndexError, OSError) as exc:
        print('AUDIT_REJECTED: ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
