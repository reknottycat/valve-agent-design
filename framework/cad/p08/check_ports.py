"""Read pinned P08 CAD only; source face numbers are hypotheses, not final CFD patches."""
import hashlib,json,sys,re
import OCP
from pathlib import Path
import cadquery as cq
PIN='a9aeb45996a388a3d894f69605205c70c25edd154adc6d3c71658329a730e787'
def inspect(path):
 p=Path(path); digest=hashlib.sha256(p.read_bytes()).hexdigest()
 if digest!=PIN:raise ValueError('Input differs from pinned P08 STEP')
 shape=cq.importers.importStep(str(p)).val(); candidates=[]
 for i,f in enumerate(shape.Faces(),1):
  b=f.BoundingBox()
  if b.xlen<1e-4 and (abs(b.xmin+600)<1e-4 or abs(b.xmin-1200)<1e-4):
   n=f.normalAt();c=f.Center()
   candidates.append({'import_face_index_1based':i,'area_mm2':f.Area(),'center_mm':c.toTuple(),'cad_oriented_normal':n.toTuple(),'normal_plus_0_1mm_inside_solid':shape.Solids()[0].isInside(c+n.multiply(0.1)), 'normal_minus_0_1mm_inside_solid':shape.Solids()[0].isInside(c-n.multiply(0.1)), 'geometry_type':f.geomType(),'x_min_mm':b.xmin,'x_max_mm':b.xmax})
 return {'input_sha256':digest,'input_name':p.name,'cadquery_version':cq.__version__,'ocp_version':OCP.__version__,'step_length_unit_declarations':sorted(set(re.findall(r'LENGTH_UNIT\(\)[^;]*?SI_UNIT\(([^)]*)\)',p.read_text(errors='replace'),re.S))),'volume_mm3':shape.Volume(),'bbox_lengths_mm':[shape.BoundingBox().xlen,shape.BoundingBox().ylen,shape.BoundingBox().zlen],'valid':shape.isValid(),'solids':len(shape.Solids()),'shells':len(shape.Shells()),'faces':len(shape.Faces()),'port_candidates':candidates,'face_index_mapping_to_original_FDG1_proven':False,'mapping_to_final_mesh_patches_proven':False,'disc_lift_57mm_proven':False,'input_unchanged':hashlib.sha256(p.read_bytes()).hexdigest()==digest,'no_geometry_mutation_or_meshing':True}
if __name__=='__main__':print(json.dumps(inspect(sys.argv[1]),indent=2))
