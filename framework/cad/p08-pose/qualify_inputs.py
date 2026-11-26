# coding: utf-8
"""Check exact inputs for replaying the FDG1 assembly. Does not execute any recovered code."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE / 'FDG1_验证摘要.json'
REFERENCE = 'output/AGR1_open_seal_omitted_proxy_main_mm.step'


def pins():
    report_bytes = REPORT.read_bytes()
    chain = json.loads((HERE / 'pose_chain.json').read_bytes())
    reviewed = next(row for row in chain['sources'] if row['name'] == REPORT.name)
    if hashlib.sha256(report_bytes).hexdigest() != reviewed['sha256']:
        raise ValueError('Historical source review changed; verify provenance before rebuilding.')
    report = json.loads(report_bytes)
    review = report['independent_export_review']
    tested = review['tested_hashes']
    locked = {k: v for k, v in tested.items() if k.startswith('source/') or k in ('build_fluid_domain.py', 'INPUTS.json', REFERENCE)}
    for row in report['source_manifest']['sources']:
        name, digest = row['file'], row['sha256']
        if Path(name).name != name or review['source_identity'][name]['actual_sha256'] != digest:
            raise ValueError('Source identity mismatch: '+name)
        if locked.setdefault('source/'+name, digest) != digest:
            raise ValueError('Conflicting source hashes: '+name)
    return locked


def qualify(directory):
    status = {}
    for name, digest in sorted(pins().items()):
        path = directory / name
        status[name] = ('missing' if not path.is_file() else 'verified' if hashlib.sha256(path.read_bytes()).hexdigest() == digest else 'wrong_bytes')
    return {'inputs': status, 'originals_verified': all(v == 'verified' for v in status.values()),
            'reference_step_verified': status[REFERENCE] == 'verified'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('directory', type=Path)
    r = qualify(parser.parse_args().directory); print(json.dumps(r, indent=2)); raise SystemExit(0 if r['originals_verified'] else 2)
