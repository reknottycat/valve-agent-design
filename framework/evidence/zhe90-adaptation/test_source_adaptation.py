import unittest
from check_source_adaptation import inspect
class Test(unittest.TestCase):
 def data(self):
  rows=[{'role':r,'original_finite_face_fingerprint_tag':i,'CAD_area_mm2':31415.926535897932,'finite_support_bbox_xyz_minmax_mm':[x,-100,-100,x,100,100]} for r,i,x in [('inlet',79,-600),('outlet',34,1200)]]
  return {'regions':rows},{'domain':{'inlet_x_m':-.6,'outlet_x_m':1.2},'pose':{'disc_lift_mm':57}}
 def test_valid_scale_not_final_proof(self):
  a,b=self.data();r=inspect(a,b,'convertToMeters 0.001;','Creating points with scale 0.001')
  self.assertTrue(all(p['source_x_matches_R1'] for p in r['source_ports']));self.assertFalse(r['disc_lift_match_verified']);self.assertFalse(r['source_ports'][0]['final_mesh_outward_normal_verified'])
 def test_wrong_units(self):
  a,b=self.data();a['regions'][0]['finite_support_bbox_xyz_minmax_mm'][0]=-.6;a['regions'][0]['finite_support_bbox_xyz_minmax_mm'][3]=-.6
  r=inspect(a,b,'','');self.assertFalse(r['source_ports'][0]['source_x_matches_R1']);self.assertFalse(r['historical_blockMesh_applied_scale'])
 def test_duplicate_port_rejected(self):
  a,b=self.data();a['regions'].append(a['regions'][0])
  with self.assertRaises(ValueError):inspect(a,b,'','')
if __name__=='__main__':unittest.main()
