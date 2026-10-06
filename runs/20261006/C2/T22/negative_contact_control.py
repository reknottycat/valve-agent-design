#!/usr/bin/env python3
"""Observed-red model test: remove seat protrusion and reject unintended body contact."""
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'T12'))
from build_lift_model import load_parameters,make_model,pose
from validate_lift_model import contact_area,check_disc_contacts


def main():
    p,_,_=load_parameters();p['seat_proud_height']=0.;p['seat_face_z']=p['chamber_floor_z']
    model=make_model(p);parts=pose(model)
    contacts={n:contact_area(parts['disc_guide'],parts[n]) for n in ('body','seat_ring','stem')}
    failures=check_disc_contacts(0,0,contacts,math.pi*(p['seat_od']**2-p['bore']**2)/4,math.pi*p['stem_od']**2/4)
    result={'control':'remove_seat_protrusion','classification':'EXPECTED_RED',
            'actual_planar_contact_areas_mm2':contacts,'gate_failures':failures,
            'passed_negative_control':'UNINTENDED_DISC_BODY_CONTACT' in failures}
    target=HERE/'out/negative_contact_control.json';target.parent.mkdir(exist_ok=True);target.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    if not result['passed_negative_control']:raise SystemExit(1)


if __name__=='__main__':main()
