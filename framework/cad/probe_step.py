#!/usr/bin/env python3
"""Read STEP only: no healing, booleans, meshing, export or solver invocation."""
import argparse,hashlib,json,time,re
from pathlib import Path

def box_data(b):
 return {'min':[b.xmin,b.ymin,b.zmin],'max':[b.xmax,b.ymax,b.zmax],'length':[b.xlen,b.ylen,b.zlen]}
def length_units(text):
 return sorted(set(re.findall(r"LENGTH_UNIT\(\)[^;]*?SI_UNIT\(([^)]*)\)",text,re.S)))

def probe(path, scope):
 import cadquery as cq
 import OCP
 path=Path(path);before=hashlib.sha256(path.read_bytes()).hexdigest();t=time.monotonic()
 shape=cq.importers.importStep(str(path)).val()
 solids=shape.Solids()
 result={'schema':'valve.readonly_step_probe/v1','input_name':path.name,'input_bytes':path.stat().st_size,'sha256':before,'scope':scope,'STEP_length_SI_declarations':length_units(path.read_text(errors='replace')),'cadquery_version':cq.__version__,'OCP_version':getattr(OCP,'__version__',None),'shape_type':shape.ShapeType(),'is_valid':shape.isValid(),'solid_count':len(solids),'face_count':len(shape.Faces()),'shell_count':len(shape.Shells()),'bbox_imported_units':box_data(shape.BoundingBox()),'sum_solid_volume_imported_units_cubed':sum(s.Volume() for s in solids),'solids':[{'index':i,'is_valid':s.isValid(),'face_count':len(s.Faces()),'volume_imported_units_cubed':s.Volume(),'bbox_imported_units':box_data(s.BoundingBox())} for i,s in enumerate(solids)],'elapsed_seconds':time.monotonic()-t,'original_file_unchanged':before==hashlib.sha256(path.read_bytes()).hexdigest(),'boolean_operations':False,'meshing':False,'solver_started':False,'pose_or_final_fluid_proven':False}
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('step');p.add_argument('--scope',required=True);a=p.parse_args();print(json.dumps(probe(a.step,a.scope),indent=2))
