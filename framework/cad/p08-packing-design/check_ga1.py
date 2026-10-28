#!/usr/bin/env python3
from pathlib import Path
import cadquery as cq,json,hashlib,sys
P=Path(__file__).resolve().parent; base=Path(sys.argv[1])
def ring(ro,ri,z,h):return cq.Workplane('XY').workplane(offset=z).center(300,0).circle(ro).circle(ri).extrude(h).val()
sleeve_low=ring(26,18.2,322,10);sleeve_high=ring(26,22,332,30);sleeve=sleeve_low.fuse(sleeve_high).clean();parts={}
for name in ['stem_GA1.step','bonnet_GA1_derivative.step','gland_follower.step','packing_ring_1.step','packing_ring_2.step','packing_ring_3.step','packing_ring_4.step','packing_ring_5.step']:
 p=base/name;s=cq.importers.importStep(str(p)).val();b=s.BoundingBox();parts[name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bbox_mm':[b.xmin,b.ymin,b.zmin,b.xmax,b.ymax,b.zmax],'intersection_with_proposed_sleeve_mm3':s.intersect(sleeve).Volume(),'is_valid':s.isValid()}
stem=cq.importers.importStep(str(base/'stem_GA1.step')).val()
local=cq.Workplane('XY').workplane(offset=322).center(300,0).circle(18).extrude(58).val()
common=stem.intersect(local).Volume()
result={'local_stem_proxy':{'z_range_mm':[322,380], 'candidate_volume_mm3':local.Volume(),'common_with_ga1_stem_mm3':common,'candidate_minus_stem_mm3':local.Volume()-common, 'method':'volume within finite local cylinder; no full-stem equivalence claimed'},'ga1_pose':'fully_open','source_scope':'GA1 A05 study geometry, not approved actual hardware','new_sleeve_is_unattached':True,'results':parts}
(P/'ga1_comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
