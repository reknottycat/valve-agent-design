#!/usr/bin/env python3
"""Compare candidate to exact pinned P08 proxy; mm, area in mm², volume in mm³."""
import hashlib,json,sys
from pathlib import Path
import cadquery as cq
P=Path(__file__).resolve().parent
source=Path(sys.argv[1])
h=hashlib.sha256(source.read_bytes()).hexdigest()
assert h=='a9aeb45996a388a3d894f69605205c70c25edd154adc6d3c71658329a730e787',h
fluid=cq.importers.importStep(str(source)).val()
faces=fluid.Faces()
# CAD source faces in old report are 1-based. Identify by geometry, not blind index.
candidates=[]
for i,f in enumerate(faces,1):
 bb=f.BoundingBox()
 if abs(bb.zmin-332)<1e-5 and abs(bb.zmax-332)<1e-5 and abs(f.Area()-502.65482457436735)<1e-4:
  candidates.append((i,f))
assert len(candidates)==1,[x[0] for x in candidates]
i,face=candidates[0]
ring_bottom=cq.Workplane('XY').workplane(offset=332).center(300,0).circle(22).circle(18).extrude(2.97).val().Faces()
rb=[f for f in ring_bottom if abs(f.BoundingBox().zmin-332)<1e-5 and abs(f.BoundingBox().zmax-332)<1e-5][0]
inter=face.intersect(rb).Area(); af=face.Area(); ar=rb.Area()
# Recreate candidate pieces for names to avoid relying on STEP solid enumeration.
def ring(ro,ri,z,h):return cq.Workplane('XY').workplane(offset=z).center(300,0).circle(ro).circle(ri).extrude(h).val()
parts={'new_sleeve_shoulder':ring(26,18.2,322,10),'new_sleeve_wall':ring(26,22,332,30),
       'packing_compressed_envelope':ring(22,18,332,14.85),
       'follower':ring(21.9,18.2,346.85,20),
       'stem_envelope':cq.Workplane('XY').workplane(offset=322).center(300,0).circle(18).extrude(58).val()}
vols={k:fluid.intersect(s).Volume() for k,s in parts.items()}
bb=face.BoundingBox()
result={'source_sha256':h,'source_solid_valid':fluid.isValid(),'source_face_count':len(faces),'identified_face_1based':i,'face_bbox_mm':[bb.xmin,bb.ymin,bb.zmin,bb.xmax,bb.ymax,bb.zmax],'source_face_area_mm2':af,'candidate_bottom_area_mm2':ar,'common_area_mm2':inter,'source_minus_common_area_mm2':af-inter,'candidate_minus_common_area_mm2':ar-inter,'candidate_solid_intersection_with_proxy_fluid_mm3':vols,'scope':'Exact face-to-candidate planar overlap and candidate solids against fluid only. This does not compare to source cover, stem solids or establish leakage, attachment, manufacturing or mesh-patch correspondence.'}
(P/'original_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
