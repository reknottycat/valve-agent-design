import sys,json,numpy as np
sys.path.insert(0,'/workspace/shared/valve-gmsh-trial-20261023/vendor');import gmsh
from pathlib import Path
gmsh.initialize();gmsh.model.occ.importShapes('/workspace/scratch/634aa36792d6/attachments/2618578e-bbba-4a39-81cb-899300c65163/AGR1_open_seal_omitted_proxy_main_mm.step');gmsh.model.occ.synchronize();out={}
for f in [119,121,123,125]:
 lo,hi=gmsh.model.getParametrizationBounds(2,f);uv=(np.array(lo)+hi)/2;k1,k2,*_=gmsh.model.getPrincipalCurvatures(f,uv);out[str(f)]={'mid_parameter_principal_curvatures_per_mm':[float(k1[0]),float(k2[0])],'inverse_abs_principal_curvatures_mm':[float(1/abs(k1[0])),float(1/abs(k2[0]))]}
Path(__file__).with_name('curvature.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));gmsh.finalize()
