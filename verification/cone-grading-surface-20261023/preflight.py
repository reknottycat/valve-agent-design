import sys,json,math
sys.path.insert(0,'/workspace/shared/valve-gmsh-trial-20261023/vendor');import gmsh
from pathlib import Path
from cone_law import *
assert slant(Z0)==0 and slant(Z1)==L
assert abs(size(Z0)-HB)<1e-12 and abs(size(Z1)-HT)<1e-12
assert all(0<=slant(Z0+(Z1-Z0)*i/100)<=L for i in range(101))
for d,t in [(3,1),(2,118),(2,126),(2,119),(1,280),(1,282),(1,294)]:assert not applies(d,t)
gmsh.initialize();gmsh.model.occ.importShapes('/workspace/scratch/634aa36792d6/attachments/2618578e-bbba-4a39-81cb-899300c65163/AGR1_open_seal_omitted_proxy_main_mm.step');gmsh.model.occ.synchronize();out={}
for f,expected in TARGETS.items():
 boundary=gmsh.model.getBoundary([(2,f)],False,True);assert set(abs(t) for d,t in boundary)==expected;curves={}
 for e in expected:
  lo,hi=gmsh.model.getParametrizationBounds(1,e);xyz=gmsh.model.getValue(1,e,[lo[0]+(hi[0]-lo[0])*i/16 for i in range(17)]);pts=[xyz[i:i+3] for i in range(0,len(xyz),3)];curves[e]={'type':gmsh.model.getType(1,e),'adjacent_faces':gmsh.model.getAdjacencies(1,e)[0].tolist(),'slant_range_mm':[min(slant(p[2]) for p in pts),max(slant(p[2]) for p in pts)],'size_range_mm':[min(size(p[2]) for p in pts),max(size(p[2]) for p in pts)]}
 out[f]={'oriented_uncombined_boundary':boundary,'curves':curves}
Path(__file__).with_name('evidence').joinpath('preflight.json').write_text(json.dumps({'result':'PASS','units':'mm','h_bottom':HB,'h_top':HT,'L':L,'audit':out},indent=2));gmsh.finalize()
