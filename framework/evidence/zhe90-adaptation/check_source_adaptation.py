"""Read archived source-rule/mesh-log evidence; never certify final patch winding."""
import json,math,re,argparse,hashlib
from pathlib import Path

def inspect(rules, plan, block_dict, block_log):
    ports=[]
    for role in ('inlet','outlet'):
        rows=[r for r in rules['regions'] if r['role']==role]
        if len(rows)!=1:raise ValueError('expected one source face for '+role)
        r=rows[0];b=r['finite_support_bbox_xyz_minmax_mm']
        if len(b)!=6 or any(not math.isfinite(x) for x in b):raise ValueError('invalid bbox')
        axis=[i for i in range(3) if abs(b[i+3]-b[i])<1e-7]
        expected=plan['domain'][role+'_x_m']
        ports.append({'role':role,'source_face':r['original_finite_face_fingerprint_tag'],
          'source_planar_axis':axis,'coordinate_m':b[0]*.001,
          'source_x_matches_R1':axis==[0] and math.isclose(b[0]*.001,expected,abs_tol=1e-9),
          'source_area_m2':r['CAD_area_mm2']*1e-6,
          'area_matches_DN200':math.isclose(r['CAD_area_mm2']*1e-6,math.pi*.2**2/4,abs_tol=1e-12),
          'unoriented_plane_normal_axis':[1,0,0] if axis==[0] else None,
          'final_mesh_outward_normal_verified':False})
    return {'schema':'valve.source_adaptation/v1','source_ports':ports,
      'background_mm_to_m_scale_in_dictionary':bool(re.search(r'convertToMeters\s+0\.001\s*;',block_dict)),
      'historical_blockMesh_applied_scale': 'Creating points with scale 0.001' in block_log,
      'historical_blockMesh_only_background_patch': 'name: background_boundary' in block_log,
      'disc_lift_R1_research_mm':plan['pose']['disc_lift_mm'],
      'disc_lift_P08_measured_mm':None,
      'disc_lift_match_verified':False,
      'scope':'Original source bbox/area and historical background log readback, not current geometry or final mesh validation.',
      'missing_pose_evidence':'P08 supplement has no disc/seat datum correspondence or transform measurement to establish 57mm lift.',
      'missing_normal_evidence':'Need retained mesh faces/owner/points or oriented source triangles with fluid-side association; bbox only establishes unoriented plane.',
      'new_solver_run':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('plan',type=Path);a=p.parse_args()
 paths=[a.source/'ACTUAL_REGENERATED_SURFACE_NATIVE_REGION_RULES_A01.json',a.plan,a.source/'case_native_m/system/blockMeshDict',a.source/'native_run_A01/evidence/blockMesh.log']
 text=[f.read_text() for f in paths];r=inspect(json.loads(text[0]),json.loads(text[1]),text[2],text[3]);r['inputs']=[{'name':str(f.name),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in paths];print(json.dumps(r,indent=2))
