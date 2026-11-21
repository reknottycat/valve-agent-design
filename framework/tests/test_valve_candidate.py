import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from valve_candidate import propose
class TestCandidate(unittest.TestCase):
 def test_exact_noop_preserves(self):
  a={'regions':[{'name':'x','level':6,'cell_size_mm':.1}]};before=copy.deepcopy(a)
  r=propose(a,{},6.4);self.assertEqual(a,before);self.assertEqual(r['changes'],[])
 def test_size_not_level_copied(self):
  a={'regions':[{'name':'x','level':6}]}
  r=propose(a,{'x':{'target_h_mm':.1,'rationale':'synthetic test only'}},3.2)
  self.assertEqual(r['changes'][0]['candidate_levels'],[5,5]);self.assertEqual(a['regions'][0]['level'],6)
 def test_unknown_name(self):
  with self.assertRaises(ValueError):propose({'regions':[]},{'x':{}},6.4)
 def test_no_blind_coarsening(self):
  with self.assertRaises(ValueError):propose({'regions':[{'name':'x','level':6}]},{'x':{'target_h_mm':1}},6.4)
 def test_minmax_only(self):
  r=propose({'regions':[{'name':'x','min_level':1,'max_level':2}]},{'x':{'target_h_mm':.1,'rationale':'test'}},6.4)
  self.assertEqual(r['changes'][0]['old_levels'],[1,2])
 def test_bad_target(self):
  for h in (True,False,0,-1,float('inf'),float('nan'),10**1000):
   with self.subTest(h=str(h)[:20]),self.assertRaises(ValueError):
    propose({'regions':[{'name':'x','level':6}]},{'x':{'target_h_mm':h,'rationale':'test'}},6.4)
 def test_blank_rationale(self):
  with self.assertRaises(ValueError):propose({'regions':[{'name':'x','level':6}]},{'x':{'target_h_mm':.1,'rationale':'  '}},6.4)
 def test_extreme_ratio(self):
  with self.assertRaises(ValueError):propose({'regions':[{'name':'x','level':6}]},{'x':{'target_h_mm':1e-300,'rationale':'test'}},1e300)
 def test_bad_background(self):
  for h in (True,0,float('nan'),10**1000):
   with self.assertRaises(ValueError):propose({'regions':[]},{},h)
 def test_missing_source_level(self):
  with self.assertRaises(ValueError):propose({'regions':[{'name':'x'}]},{'x':{'target_h_mm':.1,'rationale':'test'}},6.4)
if __name__=='__main__':unittest.main()
