import json,math,unittest,tempfile
from pathlib import Path
from check_ports import inspect
class Test(unittest.TestCase):
 def test_wrong_input_hash_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bad.step';p.write_text('not pinned geometry')
   with self.assertRaises(ValueError):inspect(p)
 def test_saved_actual_port_facts(self):
  r=json.loads(Path(__file__).with_name('p08_port_actual.json').read_text())
  self.assertEqual(r['faces'],132);self.assertEqual(r['step_length_unit_declarations'],['.MILLI.,.METRE.'])
  self.assertEqual(len(r['port_candidates']),2)
  for f in r['port_candidates']:
   self.assertAlmostEqual(f['area_mm2'],math.pi*100**2)
   self.assertFalse(f['normal_plus_0_1mm_inside_solid']);self.assertTrue(f['normal_minus_0_1mm_inside_solid'])
 def test_saved_scope_not_overclaimed(self):
  r=json.loads(Path(__file__).with_name('p08_port_actual.json').read_text())
  self.assertFalse(r['disc_lift_57mm_proven']);self.assertFalse(r['mapping_to_final_mesh_patches_proven']);self.assertTrue(r['input_unchanged'])
if __name__=='__main__':unittest.main()
