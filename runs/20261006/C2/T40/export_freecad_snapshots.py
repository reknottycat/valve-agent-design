#!/usr/bin/python3
"""Native neutral-geometry review snapshots; CadQuery source remains the parametric master."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.append('/usr/lib/freecad-python3/lib')
import FreeCAD as App
import Part

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'T40/out'
NAMES=('body','seat_ring','disc_guide','bonnet','packing','stem','handwheel')


def main():
    OUT.mkdir(exist_ok=True);results={}
    for state in ('closed','open'):
        doc=App.newDocument('C2_'+state)
        for name in NAMES:
            path=BASE/'T12/out'/state/(name+'.step')
            shape=Part.Shape();shape.read(str(path))
            if not shape.isValid() or len(shape.Solids)!=1:raise RuntimeError('Invalid exchanged part '+name)
            obj=doc.addObject('Part::Feature',name);obj.Label=name;obj.Shape=shape
            obj.addProperty('App::PropertyString','DesignStatus');obj.DesignStatus='STUDY_NOT_FOR_MANUFACTURE'
            obj.addProperty('App::PropertyString','SourceSTEP_SHA256');obj.SourceSTEP_SHA256=hashlib.sha256(path.read_bytes()).hexdigest()
            obj.addProperty('App::PropertyString','MasterParameters');obj.MasterParameters='T11/parameters.json + T12/build_lift_model.py; this is a geometry snapshot'
        doc.recompute();path=OUT/('C2_'+state+'.FCStd');doc.saveAs(str(path));App.closeDocument(doc.Name)
        check=App.openDocument(str(path))
        if len(check.Objects)!=len(NAMES) or not all(x.Shape.isValid() for x in check.Objects):raise RuntimeError('FCStd reopen failed')
        results[state]={'parts':len(check.Objects),'valid':True,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        App.closeDocument(check.Name)
    (OUT/'freecad_report.json').write_text(json.dumps({'version':App.Version(),'snapshot_scope':'Neutral geometry only, not CadQuery feature history','states':results},indent=2))
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
