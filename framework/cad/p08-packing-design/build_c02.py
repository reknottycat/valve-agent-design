#!/usr/bin/env python3
"""C02 variant: add integral shoulder to GA1 bonnet; cut pinned proxy fluid."""
import cadquery as cq, hashlib,json,sys
from pathlib import Path
P=Path(__file__).resolve().parent; root=Path(sys.argv[1]); bp=root/'GA1/valve-assembly-GA1-20261009/cad/fully_open';sp=root/'AGR1_open_seal_omitted_proxy_main_mm.step'
def imp(p):return cq.importers.importStep(str(p)).val()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ring(ro,ri,z,h):return cq.Workplane('XY').workplane(offset=z).center(300,0).circle(ro).circle(ri).extrude(h).val()
assert sha(sp)=='a9aeb45996a388a3d894f69605205c70c25edd154adc6d3c71658329a730e787'
cover=imp(bp/'bonnet_GA1_derivative.step');fluid=imp(sp); shoulder=ring(22,18.2,322,10)
common=cover.intersect(shoulder).Volume();modified=cover.fuse(shoulder).clean()
cut=fluid.cut(shoulder).clean(); removed=fluid.intersect(shoulder).Volume()
cq.exporters.export(modified,str(P/'P08_PACK_C02_modified_GA1_bonnet.step'))
cq.exporters.export(cut,str(P/'P08_PACK_C02_derived_proxy_fluid.step'))
modified_rt=imp(P/'P08_PACK_C02_modified_GA1_bonnet.step');cut_rt=imp(P/'P08_PACK_C02_derived_proxy_fluid.step')
checks={}
for name in ['stem_GA1.step','gland_follower.step','packing_ring_1.step','packing_ring_2.step','packing_ring_3.step','packing_ring_4.step','packing_ring_5.step']:
 obj=imp(bp/name); checks[name]={'file_sha256':sha(bp/name),'shoulder_overlap_mm3':shoulder.intersect(obj).Volume(),'modified_cover_overlap_mm3':modified.intersect(obj).Volume()}
res={'design_id':'P08-PACK-C02','state':'PROVISIONAL_NOT_MANUFACTURE_NOT_CFD_RELEASE','source_cover_file':'bonnet_GA1_derivative.step','source_cover_sha256':sha(bp/'bonnet_GA1_derivative.step'),'source_proxy_fluid_sha256':sha(sp),'new_shoulder_xyz':'center (300,0); z322–332, r18.2–22 mm','original_cover_shoulder_overlap_mm3':common,'cover_volume_mm3_before':cover.Volume(),'shoulder_volume_mm3':shoulder.Volume(),'fused_cover_volume_mm3':modified.Volume(),'fused_cover_valid':modified.isValid(),'fused_cover_number_solids':len(modified.Solids()),'fused_cover_readback_valid':modified_rt.isValid(),'fused_cover_readback_number_solids':len(modified_rt.Solids()),'proxy_fluid_removed_mm3':removed,'proxy_fluid_before_mm3':fluid.Volume(),'proxy_fluid_after_mm3':cut.Volume(),'fluid_volume_balance_mm3':fluid.Volume()-removed-cut.Volume(),'cut_fluid_valid':cut.isValid(),'cut_fluid_number_solids':len(cut.Solids()),'cut_fluid_readback_valid':cut_rt.isValid(),'cut_fluid_readback_number_solids':len(cut_rt.Solids()),'pose':'GA1 A05 fully_open only','component_checks':checks,'limitations':['GA1 bonnet differs from FDG1 cover; no proof of real physical configuration or exact cover-fluid mutual consistency.','No stress, fatigue, wall thickness, casting or manufacturing validation.','Packing is material envelope only; no contact, preload or leakage model.','D40 stem head cannot pass D36.4 bore: assembly sequence and insertion from below are unverified.','No face mapping, mesh or field generation. Rebuild and remap CFD case before use.','External environment and actual operating flow not known; no fabricated product performance.']}
(P/'c02_checks.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
