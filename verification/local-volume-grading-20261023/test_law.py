import math,json,random
from pathlib import Path
from volume_law import *
res={'tests':[],'full_torus_false_zero_counterexamples':[]}
for i,arc in enumerate(ARCS):
 R,Z,a,lo,hi=arc
 for label,t in [('lower',lo),('middle',(lo+hi)/2),('upper',hi)]:
  rho=R+a*math.cos(t);z=Z+a*math.sin(t);d=arc_distance(rho,z,arc);assert d<1e-10,(label,d)
  res['tests'].append({'arc':i,'location':label,'distance_mm':d})
 t=(lo+hi)/2
 for eps in [.001,.05]:
  d=arc_distance(R+(a+eps)*math.cos(t),Z+(a+eps)*math.sin(t),arc);assert abs(d-eps)<1e-10
 t=0 if i==0 else math.pi;rho=R+a*math.cos(t);z=Z+a*math.sin(t);full=abs(math.hypot(rho-R,z-Z)-a);finite=arc_distance(rho,z,arc);assert full<1e-10 and finite>.1
 res['full_torus_false_zero_counterexamples'].append({'arc':i,'rho_mm':rho,'z_mm':z,'full_torus_distance_mm':full,'finite_trimmed_distance_mm':finite})
 for dim,tag in [(0,1),(1,280),(1,282),(2,118),(2,119),(2,125),(2,126),(3,2)]:
  for lc in [.05,.1,1,4,25]:assert apply(dim,tag,300+R,0,Z-a,lc)==lc
 for lc in [.05,.1,1,4,25]:assert apply(3,1,300+R,0,Z-a,lc)<=lc
assert abs(apply(3,1,300+ARCS[0][0],0,79,25)-H0)<1e-10
for x,y,z in [(0,0,0),(1000,0,79),(300,0,500)]:
 assert distance(x,y,z)>CUTOFF
 for lc in [.05,1,4,25]:assert apply(3,1,x,y,z,lc)==lc
res.update({'scope_non_volume_unchanged':True,'existing_stricter_lc_preserved':True,'far_field_exactly_inert':True,'units':'All coordinates and sizes in mm; same original source CAD','h0_mm':H0,'cutoff_mm':CUTOFF,'result':'PASS'})
Path(__file__).with_name('evidence').joinpath('law-tests.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
