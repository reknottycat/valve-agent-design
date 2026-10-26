#!/usr/bin/env python3
"""Read-only package consistency checks. Not a CAD/CFD/FEA or standards validator."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {'confirmed-original', 'published-otherproduct', 'derived-under-assumptions', 'unresolved'}
SLOTS = {'materials', 'key_dimensions', 'tolerances', 'loads', 'strength_contact', 'sealing'}

def validate_data(matrix, register):
    errors = []
    def check(ok, msg):
        if not ok: errors.append(msg)
    for k in ['engineering_release','manufacturing_authorized','solver_executed','original_inputs_modified','candidate_adoption_authorized']:
        check(matrix.get(k) is False, f'{k} must remain false')
    check(matrix.get('selected_public_candidate') is None, 'candidate not authorized for adoption')
    check(all(v is None for v in matrix.get('product_performance', {}).values()), 'product performance must remain unresolved')
    check(set(matrix.get('product_performance', {})) == {'Q_m3_s','pressure_drop_Pa','loss_coefficient','seat_leakage'}, 'missing product performance null gates')
    sources = {s['id']: s for s in register['sources']}
    check(len(sources) == len(register['sources']), 'duplicate source ID')
    for s in sources.values():
        check(s.get('url','').startswith('https://'), f"{s['id']}: source URL missing")
        for k in ['locator','revision','limitations','redistribution']:
            check(bool(s.get(k)), f"{s['id']}: missing {k}")
    rows=matrix.get('rows',[])
    check(len({r['id'] for r in rows}) == len(rows), 'duplicate field ID')
    check({r['slot'] for r in rows} == SLOTS, 'six-slot coverage required')
    for r in rows:
        tag=r.get('id','?');status=r.get('status')
        check(status in STATUSES, f'{tag}: invalid classification')
        check(r.get('adopted_for_original') is False and r.get('adopted_for_candidate') is False, f'{tag}: adoption forbidden by default')
        check(bool(r.get('unit')) and isinstance(r.get('unit'),str), f'{tag}: explicit unit/category required')
        check(bool(r.get('limitations')),f'{tag}: missing limitations')
        ids=r.get('source_ids',[])
        check(bool(ids) and all(s in sources for s in ids), f'{tag}: unresolved source reference')
        if status=='unresolved': check(r.get('value') is None,f'{tag}: unresolved value must be null')
        else: check(r.get('value') is not None,f'{tag}: classified evidence value missing')
        if status=='derived-under-assumptions': check(bool(r.get('assumptions')),f'{tag}: derived value needs assumptions')
        if status=='confirmed-original':
            check(r.get('track')=='original-R1',f'{tag}: original classification on wrong track')
            check(all(sources[s]['kind']=='original_evidence_review' for s in ids if s in sources),f'{tag}: original fact needs original evidence review')
        if status=='published-otherproduct':
            check(r.get('track','').startswith('public-'),f'{tag}: public value assigned to original')
            check(all(sources[s]['kind']=='manufacturer_catalog' and r.get('track') in sources[s].get('allowed_tracks',[]) for s in ids if s in sources), f'{tag}: cross-product source mix')
    config=matrix.get('candidate_configuration_gates',{})
    check(config.get('public-perlwitz-017960-DN200',{}).get('spring_selection','MISSING') is None,'Perlwitz spring must remain undecided')
    check(config.get('public-ilshin-F7353-DN200',{}).get('disc_seat_material_option','MISSING') is None,'IL SHIN material option must remain undecided')
    return errors

def validate_example(example, register):
    errors=[]
    for k in ['engineering_release','adopted_for_original','adopted_for_candidate','actual_valve_result']:
        if example.get(k) is not False:errors.append(f'educational example: {k} must remain false')
    if example.get('track')!='educational-only' or example.get('status')!='derived-under-assumptions':errors.append('educational example classification changed')
    if not example.get('assumptions'):errors.append('educational assumptions missing')
    ids={s['id'] for s in register['sources']}
    if not example.get('source_ids') or not set(example['source_ids'])<=ids:errors.append('educational source missing')
    try:
        i=example['inputs'];o=example['outputs']
        q=i['Kv']['value']*math.sqrt(i['delta_p']['value']/i['SG']['value'])
        cda=(q/3600)/math.sqrt(2*i['delta_p']['value']*1e5/i['rho']['value'])
        if i['delta_p']['unit']!='bar' or i['rho']['unit']!='kg/m³' or o['Q']['unit']!='m³/h' or o['CdA']['unit']!='m²' or o['CdA_mm2']['unit']!='mm²':errors.append('educational unit convention changed')
        if not all(math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-15) for a,b in [(q,o['Q']['value']),(cda,o['CdA']['value']),(cda*1e6,o['CdA_mm2']['value'])]):errors.append('educational arithmetic inconsistent')
    except (KeyError,TypeError,ValueError,ZeroDivisionError):errors.append('invalid educational input')
    return errors

def validate_manifest(root):
    errors=[]
    manifest=root/'evidence-manifest.json'
    if not manifest.exists():return ['evidence-manifest.json missing']
    data=json.loads(manifest.read_text())
    entries=data['files']
    names=[e['path'] for e in entries]
    if len(names)!=len(set(names)):errors.append('manifest duplicate path')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='evidence-manifest.json' and '__pycache__' not in p.parts}
    if set(names)!=actual:errors.append('manifest file set mismatch')
    for e in entries:
        path=Path(e['path'])
        if path.is_absolute() or '..' in path.parts:errors.append('unsafe manifest path');continue
        p=root/path
        if not p.is_file():errors.append(f'missing {path}');continue
        b=p.read_bytes()
        if len(b)!=e['bytes'] or hashlib.sha256(b).hexdigest()!=e['sha256']:errors.append(f'fingerprint mismatch {path}')
    return errors

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--no-manifest',action='store_true');args=parser.parse_args()
    matrix=json.loads((ROOT/'engineering-input-matrix.json').read_text());register=json.loads((ROOT/'source-register.json').read_text())
    errors=validate_data(matrix,register)
    errors+=validate_example(json.loads((ROOT/'educational-kv-example.json').read_text()),register)
    if not args.no_manifest:errors+=validate_manifest(ROOT)
    for e in errors:print('FAIL:',e)
    if errors:return 1
    print(f'PASS: {len(matrix["rows"])} classified fields, {len(register["sources"])} sources; adoption and release gates remain false.')
    print('Scope: record/source/unit/default-gate consistency only, not physical validation or standard approval.')
    return 0
if __name__=='__main__':raise SystemExit(main())
