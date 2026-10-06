#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def validate_variant(row):
    notes=row['applicable_notes']
    if len(notes)!=len(set(notes)) or any(type(n) is not int or not 1<=n<=31 for n in notes):
        raise ValueError('Invalid note applicability list')
    for case in row['service_cases']:
        if case['source_note'] not in notes:raise ValueError('Service case comes from inapplicable variant note')
    if row['design_pressure_MPa'] is not None or row['proof_pressure_MPa'] is not None:
        raise ValueError('This source review does not establish design/proof pressure')
    if row['material_grades_status']!='UNSPECIFIED_IN_REVIEWED_DRAWING':
        raise ValueError('Catalog analogy cannot become drawing material specification')


def main():
    matrix=json.loads((HERE/'variant_input_matrix.json').read_text())
    for row in matrix['variants']:validate_variant(row)
    manifest=json.loads((HERE/'source_manifest.json').read_text())
    for row in manifest['files']:
        path=HERE/row['file']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('Source hash mismatch '+row['file'])
    variants={v['designation']:v for v in matrix['variants']}
    if 5 in variants['522-35.4179']['applicable_notes'] or 5 not in variants['522-35.4179-02']['applicable_notes']:
        raise ValueError('Brine variant scope regressed')
    print(f"Verified {len(variants)} variant rows and {len(manifest['files'])} local source evidence hashes; no pressure/material frozen")


if __name__=='__main__':main()
