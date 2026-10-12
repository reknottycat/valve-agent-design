#!/usr/bin/env python3
"""Verify engineering index structure and optional restored source bytes; never run a solver."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import re
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-root', type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
docs = root / 'docs/engineering'
evidence = json.loads((docs / 'EVIDENCE_INDEX.json').read_text())
replay = json.loads((docs / 'REPLAY_INDEX.json').read_text())
products = json.loads((docs / 'PRODUCT_INDEX.json').read_text())
branches = json.loads((docs / 'BRANCH_PLAN.json').read_text())
assert evidence['record_kind'] == 'RETROSPECTIVE_INDEX_COMPILED_NOW_NOT_BACKDATED_GIT_HISTORY'
assert replay['frozen_R1_commit'] == 'aa80b87b6ee9617754101a238f70bec99393ad9a'
assert replay['new_worklog_commit'] is None, 'Use the actual checkout and publication receipt, not an invented self-reference.'
assert not branches['R1_mutation_or_main_merge_requested_by_this_plan']
verified = []
for name, item in evidence['sources'].items():
    relative = PurePosixPath(item['archive_relative_path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    assert re.fullmatch(r'[0-9a-f]{64}', item['sha256'])
    assert isinstance(item['bytes'], int) and item['bytes'] >= 0
    if args.source_root:
        source_root = args.source_root.resolve()
        p = source_root / relative
        assert p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(source_root), str(p)
        assert p.stat().st_size == item['bytes'], name
        digest = hashlib.sha256()
        with p.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        assert digest.hexdigest() == item['sha256'], name
        verified.append(name)
for item in products['drive_products']:
    assert item['url'].startswith('https://drive.google.com/'), item['url']
    assert 'token=' not in item['url'].lower() and 'signature=' not in item['url'].lower()
    if 'sha256' in item:
        assert re.fullmatch(r'[0-9a-f]{64}', item['sha256'])
for row in replay['executed_commands']:
    assert row['automatic_execution_by_index'] is False
try:
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, timeout=5)
    commit = head.stdout.strip() if head.returncode == 0 else None
except (FileNotFoundError, subprocess.TimeoutExpired):
    commit = None
print(json.dumps({
    'index_structure': 'PASS', 'evidence_entries': len(evidence['sources']),
    'source_files_verified': len(verified), 'product_links': len(products['drive_products']),
    'checkout_commit_observed': commit, 'scientific_solver_invoked': False,
    'engineering_or_manufacturing_acceptance_granted': False,
}, indent=2))
