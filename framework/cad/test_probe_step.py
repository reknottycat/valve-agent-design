import unittest,json
from pathlib import Path
from probe_step import length_units,box_data
class Test(unittest.TestCase):
 def test_units(self):self.assertEqual(length_units('#1=( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.) );'),['.MILLI.,.METRE.'])
 def test_multiline_unit(self):self.assertEqual(length_units('#1=( LENGTH_UNIT()\n NAMED_UNIT(*)\n SI_UNIT(.MILLI.,.METRE.) );'),['.MILLI.,.METRE.'])
 def test_no_cross_entity_leak(self):self.assertEqual(length_units('#1=LENGTH_UNIT();\n#2=SI_UNIT($,.RADIAN.);'),[])
 def test_no_unit_not_assumed(self):self.assertEqual(length_units(''),[])
 def test_actual_scope_and_integrity(self):
  r=json.loads((Path(__file__).parent/'agr1_actual_probe.json').read_text())
  self.assertTrue(r['original_file_unchanged']);self.assertTrue(r['is_valid']);self.assertEqual(r['solid_count'],12);self.assertFalse(r['pose_or_final_fluid_proven'])
 def test_bbox_adapter(self):
  class B:xmin=0;ymin=0;zmin=0;xmax=1;ymax=2;zmax=3;xlen=1;ylen=2;zlen=3
  self.assertEqual(box_data(B())['length'],[1,2,3])
if __name__=='__main__':unittest.main()
