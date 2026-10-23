from candidate_law import *
from pathlib import Path
import json
results={}
for lo,hi in ARCS:
 for a in [lo,(lo+hi)/2,hi]:
  for z in [Z0,(Z0+Z1)/2,Z1]:assert distance(300+R*math.cos(a),R*math.sin(a),z)<1e-10
 a=(lo+hi)/2
 for dr in [-.1,.1]:assert abs(distance(300+(R+dr)*math.cos(a),(R+dr)*math.sin(a),21.975)-abs(dr))<1e-9
 assert abs(distance(300+R*math.cos(a),R*math.sin(a),23)-1)<1e-9
# Full infinite cylinder would incorrectly report zero inside the angular gap.
falsezero=distance(412.5,0,21.975);assert falsezero>.9
for dim in [0,3]:assert apply(dim,1,412.5,0,21.975,25)==25
for p in [(300,0,21.975),(412.5,0,100),(300,0,0)]:
 for lc in [.05,.25,1,4,25]:assert apply(2,1,*p,lc)==lc
for lc in [.05,.1,.25,1,25]:assert apply(2,37,397.427857925739,-56.25000000001796,21.975,lc)<=lc
results={'result':'PASS','full_cylinder_false_zero_actual_finite_distance_mm':falsezero,'cutoff_mm':CUTOFF,'dim3_unchanged':True,'farfield_exact_inert':True,'existing_stricter_lc_preserved':True,'endpoints_and_axial_clips_tested':True,'units':'mm','no_meshing':True}
Path(__file__).with_name('law-tests.json').write_text(json.dumps(results,indent=2));print(results)
