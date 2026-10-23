import hashlib,json,unittest
from pathlib import Path
R=Path(__file__).resolve().parent
class EvidenceTests(unittest.TestCase):
 def get(self,n): return json.loads((R/'evidence'/n).read_text())
 def test_geometry_source_and_bijection(self):
  d=self.get('geometry.json'); self.assertEqual(d['source_sha256'],'a9aeb45996a388a3d894f69605205c70c25edd154adc6d3c71658329a730e787');self.assertEqual((d['volumes'],d['surfaces']),(1,132));self.assertEqual(len({x['source_face'] for x in d['mapping']}),132);self.assertFalse(d['healing_requested'])
 def test_saved_surface_hash_and_size(self):
  d=self.get('surface.json');p=R/'surface.msh';self.assertEqual(p.stat().st_size,d['bytes']);self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),d['msh_sha256']);self.assertFalse(d['engineering_release'])
 def test_readback_topology_without_overclaim(self):
  d=self.get('surface-readback.json');self.assertEqual(d['triangles'],157086);self.assertEqual(d['physical_group_mismatches'],[]);self.assertEqual(d['edge_incidence_counts'],{'2':235629});self.assertEqual(d['connected_surface_components'],2);self.assertLess(d['component_oriented_volumes_mm3'][0],0);self.assertGreater(d['component_oriented_volumes_mm3'][1],0);self.assertFalse(d['volume_mesh_created']);self.assertFalse(d['self_intersections_tested'])
 def test_volume_failure_not_resource_failure(self):
  d=self.get('volume-receipt.json');self.assertEqual(d['returncode'],1);self.assertIsNone(d['stop_reason']);self.assertLess(d['sampled_peak_rss_bytes'],2*1024**3);self.assertIn('PLC Error:  A segment and a facet intersect at point',(R/'evidence/volume.log').read_text());self.assertFalse((R/'candidate.msh').exists())
 def test_reuse_limitation_disclosed(self):
  d=self.get('readonly-localization.json');self.assertFalse(d['exact_saved_surface_reuse_established']);self.assertTrue(d['log_contains_1d_and_2d_generation_after_merge']);self.assertFalse(d['source_cad_invalid_proven']);self.assertFalse(d['failure_surface_saved'])
 def test_gate_history_not_erased(self):
  d=self.get('volume-continuation-decision.json');self.assertTrue(d['initial_gate_declined_3d']);self.assertTrue(d['no_automatic_retry']);self.assertFalse(self.get('surface.json')['eligible_for_bounded_volume_trial'])
if __name__=='__main__':unittest.main()
