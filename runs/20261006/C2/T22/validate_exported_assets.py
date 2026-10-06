#!/usr/bin/env python3
"""Read every delivered STEP back and compare with a freshly rebuilt native model."""
import hashlib
import json
from pathlib import Path
import sys

import cadquery as cq

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'T12'))
from build_lift_model import load_parameters,make_model,pose,fluid_domain
from validate_lift_model import measure
from geometry_gate import check_exchange,step_length_unit


def main():
    p,_,sha=load_parameters();model=make_model(p);records=[];errors=[]
    root=HERE.parent/'T12/out'
    build=json.loads((root/'build_report.json').read_text())
    if build['parameters_sha256']!=sha:raise ValueError('Stale export parameters')
    if build['builder_code_sha256']!=hashlib.sha256((HERE.parent/'T12/build_lift_model.py').read_bytes()).hexdigest():
        raise ValueError('Stale export builder')
    for name,lift,stop in [('closed',0.,0.),('check_closed',0.,p['stem_travel']),('open',p['disc_max_lift'],p['stem_travel'])]:
        parts=pose(model,lift,stop);expected={key:value.val() for key,value in parts.items()}
        expected['assembly']=cq.Compound.makeCompound(list(expected.values()))
        expected['fluid_domain_mm']=fluid_domain(model,parts).val()
        for key,native in expected.items():
            file=root/name/(key+'.step');path=str(file.relative_to(root))
            digest=hashlib.sha256(file.read_bytes()).hexdigest()
            if build['asset_hashes'].get(path)!=digest:raise ValueError('Export changed '+path)
            readback=cq.importers.importStep(str(file)).val()
            check=check_exchange(measure(native),measure(readback))
            unit=step_length_unit(file)
            records.append({'file':path,'sha256':digest,'exchange':check,'unit':unit,'solid_count':len(readback.Solids())})
            if check['status']!='PASS' or unit['unit']!='mm':errors.append(path)
    report={'schema':'valve.c2-export-check/1.0','parameters_sha256':sha,'status':'PASS' if not errors else 'FAIL',
            'files_checked':len(records),'failures':errors,'records':records,'manufacturing_authorized':False}
    (HERE/'out/asset_roundtrip_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))
    return 0 if not errors else 2


if __name__=='__main__':raise SystemExit(main())
