#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]


def main():
    registry=json.loads((BASE/'T11/source_register.json').read_text());sources={s['id']:s for s in registry['sources']}
    if len(sources)!=len(registry['sources']):raise ValueError('Duplicate source IDs')
    for source in sources.values():
        if source.get('sha256'):
            file=(BASE.parent/source['path']).resolve()
            if not file.is_relative_to(BASE.parent.resolve()):raise ValueError('Source path outside design scope')
            if hashlib.sha256(file.read_bytes()).hexdigest()!=source['sha256']:raise ValueError('Source changed '+source['id'])
    data=json.loads((BASE/'T11/interface_candidates.json').read_text())
    groups=[data['common'],data['packing_gland']['values']]+[r['values'] for r in data['bonnet_joint_candidates']]
    for group in groups:
        for key,row in group.items():
            if row['source'] not in sources:raise ValueError('Unknown dimension source '+key)
    for row in data['drive_nut_candidates']:
        if row['source'] not in sources:raise ValueError('Unknown drive source')
        if row['source']=='NORELEM_INDEX' and row['kind']!='UNVERIFIED_SENSITIVITY_ENVELOPE':
            raise ValueError('Indexed lead upgraded to controlled evidence')
    dimensions=json.loads((BASE/'T40/dimension_register.json').read_text())['dimensions']
    ids={d['id'] for d in dimensions}
    if len(ids)!=len(dimensions) or any(d['manufacturing_controlled'] for d in dimensions):raise ValueError('Unapproved dimension control')
    drawings=json.loads((BASE/'T40/drawing_register.json').read_text())['drawings']
    for drawing in drawings:
        if drawing['manufacturing_issue_ready'] or not set(drawing['dimension_ids'])<=ids:raise ValueError('Drawing source/issue gate failed')
    frozen=BASE.parent/'C2';manifest=json.loads((frozen/'artifact_manifest.json').read_text())
    for row in manifest['files']:
        if hashlib.sha256((frozen/row['path']).read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Frozen C2 was modified '+row['path'])
    result={'status':'PASS','source_ids':len(sources),'dimension_groups':len(dimensions),'drawing_structures':len(drawings),
            'frozen_C2_files_verified':len(manifest['files']),'manufacturing_authorized':False}
    (BASE/'T22/source_check.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
