#!/usr/bin/env python3
"""P08-PACK-C01. Concept-only solids, mm. No production or solver release."""
from pathlib import Path
import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import ezdxf, math, json

out=Path(__file__).resolve().parent
# All bodies placed in project coordinates; the sleeve is a NEW design placeholder,
# not a copy of the original cover. The lower bore and shoulder enter the proxy domain.
cx=300

def ring(ro,ri,z,h):
    return cq.Workplane('XY').workplane(offset=z).center(cx,0).circle(ro).circle(ri).extrude(h).val()
rod=ring(18,0.000001,322,58) # subtract near-zero core avoided below
rod=cq.Workplane('XY').workplane(offset=322).center(cx,0).circle(18).extrude(58).val()
sleeve_low=ring(26,18.2,322,10)
sleeve_high=ring(26,22,332,30)
sleeve=sleeve_low.fuse(sleeve_high).clean()
rings=[ring(22,18,332+i*2.97,2.97) for i in range(5)]
follower=ring(21.9,18.2,346.85,20)
parts=[rod,sleeve,*rings,follower]
compound=cq.Compound.makeCompound(parts)
cq.exporters.export(compound,str(out/'P08_PACK_C01_concept.step'))
read=cq.importers.importStep(str(out/'P08_PACK_C01_concept.step')).val()
# intersections check pairwise volumetric overlap (touching is permitted)
overlaps=[]
for i,a in enumerate(parts):
 for j,b in enumerate(parts[i+1:],i+1):
  v=a.intersect(b).Volume()
  if abs(v)>1e-6: overlaps.append([i,j,v])

expected=math.pi*(22**2-18**2)
checks={
 'design_id':'P08-PACK-C01','units':'mm','state':'CONCEPT_ONLY_NOT_FOR_MANUFACTURE_OR_ACCEPTANCE',
 'source':'GA1 A05 inherited nominal values; new sleeve is proposed not source geometry',
 'pose':'nominal fixed open57; rod local cylinder envelope is illustrative, not imported stem',
 'model_assembly_centroid_xy_mm':[300,0],
 'source_face80_area_mm2':502.65482457436735,
 'candidate_ring_footprint_area_mm2':expected,'face80_area_difference_mm2':expected-502.65482457436735,
 'source_face_mapping':'see original_comparison.json for exact imported planar face comparison; no final-mesh mapping',
 'free_stack_mm':19.8,'compressed_stack_mm':14.85,'axial_compression_fraction':0.25,'per_ring_height_mm':2.97,
 'sleeve_inner_diameter_below_shoulder_mm':36.4,'sleeve_inner_diameter_above_shoulder_mm':44,'sleeve_outer_diameter_envelope_mm':52,
 'shoulder_z_mm':332,'sleeve_bottom_z_mm':322,'sleeve_top_z_mm':362,'follower_bottom_z_mm':346.85,'follower_top_z_mm':366.85,
 'rod_sleeve_radial_clearance_mm':0.2,'follower_bore_radial_clearance_mm':0.1,'follower_stem_radial_clearance_mm':0.2,
 'part_count':len(parts),'all_parts_cad_valid':all(s.isValid() for s in parts),'readback_solid_count':len(read.Solids()),'readback_is_valid':read.isValid(),
 'positive_volume_intersections_mm3':overlaps,'no_volume_interference':not overlaps,
 'limitations':['Local illustrative sleeve is unconnected to actual cover; attachment, pressure load path and integration unverified.',
 'Shoulder occupies former proxy-fluid annulus below z332; CFD geometry and mesh must be regenerated or formally mapped.',
 '36.4 mm bore leaves 0.2 mm radial gap against nominal rod; packing contact and leakage are not proved.',
 'Packing shapes are compressed envelopes, not a material deformation, compression ratio or leak prediction.',
 'Rod is a local 36 mm cylinder proxy. Exact open57 stem solid not verified in this run; original planar face compared separately.',
 'No actual external pressure/environment, tolerance, strength, seal qualification, or CFD solution is established.']}
(out/'checks.json').write_text(json.dumps(checks,indent=2,ensure_ascii=False)+'\n')

# Exact 2D central section: x relative to spindle, z absolute. A section of the
# sleeve, rod, follower and 5 nominal compressed rings. Outline is diagrammatic.
fig,ax=plt.subplots(figsize=(11.7,8.3)); ax.set_aspect('equal')
def rect(x0,z0,w,h,color,hatch=None):
 ax.add_patch(Rectangle((x0,z0),w,h,facecolor=color,edgecolor='#162535',linewidth=.9,hatch=hatch))
rect(-18,322,36,58,'#d9e2ea')
for sign in [-1,1]:
 x0=18.2 if sign==1 else -26
 rect(x0,322,7.8,10,'#c7d5df','///')
 x0=22 if sign==1 else -26
 rect(x0,332,4,30,'#c7d5df','///')
 for i in range(5): rect(18 if sign==1 else -22,332+i*2.97,4,2.97,'#e9b86f','...')
 rect(18.2 if sign==1 else -21.9,346.85,3.7,20,'#9cb4c7','\\\\')
ax.axhline(332,color='#e54a36',linestyle='--',linewidth=1)
ax.axvline(0,color='gray',linestyle='-.',linewidth=.8)
ax.set_xlim(-60,90); ax.set_ylim(316,385); ax.set_xlabel('x - 300 (mm)'); ax.set_ylabel('z (mm)')
ax.set_title('P08-PACK-C01 / Local axial section, candidate only',fontsize=15,loc='left')
ax.text(32,376,'Stem nominal OD 36',fontsize=10)
t_sleeve=ax.text(32,371,'Sleeve OD 52: new placeholder',fontsize=10)
ax.text(32,366,'Follower OD 43.8 / ID 36.4',fontsize=10)
ax.text(32,359,'5 packing rings: OD 44 / ID 36',fontsize=10)
ax.text(32,353,'Compressed stack 14.85; z332–346.85',fontsize=10)
ax.text(32,347,'Stem-to-bore radial gap 0.20',fontsize=10)
ax.text(32,341,'Bore diameter 44 to z362',fontsize=10)
ax.text(32,335,'z332 shoulder / source face80 plane',fontsize=10,color='#ba281b')
ax.text(32,329,'New shoulder in former proxy flow space',fontsize=10)
t_hold=ax.text(32,323,'Sleeve attachment and leakage unresolved',fontsize=10)
ax.text(0.01,-.12,'CONCEPT ONLY • No manufacturing release • Not a validated physical seal',transform=ax.transAxes,color='#a22',fontsize=11)
ax.grid(alpha=.12);fig.tight_layout();fig.savefig(out/'P08_PACK_C01_section.svg')
ax.set_title('P08-PACK-C02 / Local axial section, candidate only',fontsize=15,loc='left')
t_sleeve.set_text('Integral bonnet shoulder: local schematic')
t_hold.set_text('D40 head assembly / leakage unresolved')
fig.savefig(out/'P08_PACK_C02_section.svg'); fig.savefig('/tmp/p08-c02.png',dpi=140); plt.close(fig)
# Editable DXF shapes; same project coordinates, not a production drawing.
doc=ezdxf.new('R2010');m=doc.modelspace()
def box(x,z,w,h,layer):m.add_lwpolyline([(x,z),(x+w,z),(x+w,z+h),(x,z+h)],close=True,dxfattribs={'layer':layer})
for l in ['STEM','SLEEVE','PACKING','FOLLOWER','NOTES']: doc.layers.new(l)
box(-18,322,36,58,'STEM')
for sign in [-1,1]:
 box(18.2 if sign==1 else -26,322,7.8,10,'SLEEVE');box(22 if sign==1 else -26,332,4,30,'SLEEVE')
 for i in range(5):box(18 if sign==1 else -22,332+i*2.97,4,2.97,'PACKING')
 box(18.2 if sign==1 else -21.9,346.85,3.7,20,'FOLLOWER')
m.add_line((-30,332),(30,332),dxfattribs={'layer':'NOTES'})
for i,t in enumerate(['P08-PACK-C01 CONCEPT ONLY, mm','x is relative to centre x=300','NEW SHOULDER IN PROXY FLUID: integration unverified','STEM D36; BORE D36.4 / D44; SLEEVE OD52','5 PACKING RINGS D36/44; z332–346.85','FOLLOWER D36.4/43.8; z346.85–366.85','DO NOT MANUFACTURE: leakage, retention, load path unknown']):
 m.add_text(t,dxfattribs={'height':2,'insert':(32,376-i*5),'layer':'NOTES'})
doc.saveas(out/'P08_PACK_C01_section.dxf')
print(json.dumps(checks,indent=2,ensure_ascii=False))
# C02 uses same local cross-section but represents a clipped GA1 bonnet, not an inserted sleeve.
c02=ezdxf.readfile(out/'P08_PACK_C01_section.dxf')
replacements={
 'P08-PACK-C01 CONCEPT ONLY, mm':'P08-PACK-C02 CONCEPT ONLY, mm',
 'NEW SHOULDER IN PROXY FLUID: integration unverified':'INTEGRAL GA1 BONNET SHOULDER; LOCAL SECTION ONLY',
 'STEM D36; BORE D36.4 / D44; SLEEVE OD52':'STEM D36; BORE D36.4 / D44; BONNET SECTION CLIPPED AT D52',
 'DO NOT MANUFACTURE: leakage, retention, load path unknown':'NOT FOR MANUFACTURE: D40 HEAD ASSEMBLY, LEAKAGE UNVERIFIED'}
for e in c02.modelspace().query('TEXT'):
 if e.dxf.text in replacements:e.dxf.text=replacements[e.dxf.text]
c02.saveas(out/'P08_PACK_C02_section.dxf')
