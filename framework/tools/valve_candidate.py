#!/usr/bin/env python3
"""Make a separate, explicit refinement proposal, never mutate input or run CFD."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path


# Numerical support bound of this proposal serializer, NOT an engineering target.
MAX_SUPPORTED_LEVEL = 30

def positive_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(name + ' must be a real number, not bool')
    try:
        value = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(name + ' is outside supported numeric range') from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError(name + ' must be finite and positive')
    return value

def propose(rules, targets, background_mm):
    background_mm = positive_number(background_mm, 'background_mm')
    known={r['name'] for r in rules['regions']}
    if set(targets)-known: raise ValueError('unknown surface name')
    result=copy.deepcopy(rules);changes=[]
    for r in result['regions']:
        if r['name'] not in targets:continue
        spec=targets[r['name']]
        h=positive_number(spec.get('target_h_mm'), 'target_h_mm')
        rationale=spec.get('rationale')
        if not isinstance(rationale,str) or not rationale.strip():
            raise ValueError('explicit physical rationale required')
        # Difference of logs avoids ratio overflow/underflow.
        level=max(0,math.ceil(math.log2(background_mm)-math.log2(h)))
        if level > MAX_SUPPORTED_LEVEL:
            raise ValueError('requested level exceeds serializer support (30), not a physical mesh limit')
        old=[r.get('min_level',r.get('level')),r.get('max_level',r.get('level'))]
        if any(isinstance(x,bool) or not isinstance(x,int) or x < 0 or x > MAX_SUPPORTED_LEVEL for x in old) or old[0] > old[1]:
            raise ValueError('source requires level or valid min_level/max_level integers in 0..30')
        r.update(level=level,min_level=level,max_level=level,cell_size_mm=background_mm/(2**level))
        r.pop('angle_refinement_cell_size_mm',None)
        changes.append({'name':r['name'],'old_levels':old,'candidate_levels':[level,level], 'rationale':spec['rationale']})
    return {'schema':'valve.refinement_proposal/v1','proposal_only':True,'geometry_modified':False,
            'mesh_generated':False,'flow_paths_verified':False,'source_rules':result,'changes':changes,
            'next_validation':['finite geometry error','retained connected fluid paths','checkMesh','physical boundary input','flow and grid sensitivity']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rules',type=Path);p.add_argument('targets',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--background-mm',required=True,type=float)
    a=p.parse_args(); source=a.rules.read_bytes()
    report=propose(json.loads(source),json.loads(a.targets.read_text()),a.background_mm)
    report['source_rules_sha256']=hashlib.sha256(source).hexdigest()
    # Exclusive creation prevents overwriting any original or previous candidate.
    with a.output.open('x') as f:json.dump(report,f,indent=2)
