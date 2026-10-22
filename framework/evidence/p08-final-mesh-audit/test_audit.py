import json,unittest
from pathlib import Path
class Test(unittest.TestCase):
 def setUp(self):self.r=json.loads(Path(__file__).with_name('result.json').read_text())
 def test_p08_printed_count_not_checkpoint(self):
  self.assertFalse(self.r['P08_counter_is_checkpoint']);self.assertTrue(self.r['P08_progress']['materialized_polyMesh_only_background']);self.assertFalse(self.r['P08_progress']['domain_retention_completed'])
 def test_r04_result_preserved_but_not_accepted(self):
  self.assertTrue(self.r['R04_generated_mesh_recoverable_by_index']);self.assertEqual(self.r['R04_native_quality']['failed_checks'],3);self.assertFalse(self.r['R04_quality_passed'])
 def test_stop_not_allocator_or_solver_failure(self):
  self.assertEqual(self.r['P08_stop']['signal'],'SIGTERM');self.assertFalse(self.r['P08_stop']['native_allocator_error_observed']);self.assertFalse(self.r['new_computation_executed'])
if __name__=='__main__':unittest.main()
