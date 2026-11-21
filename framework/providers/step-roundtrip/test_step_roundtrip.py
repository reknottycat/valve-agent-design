import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from step_roundtrip import compatible, match_solids, run, units

ROOT=Path(__file__).parent

def item(x=0):
    return {"valid":True,"faces":6,"shells":1,"edges":12,"vertices":8,"volume_mm3":1000.0,"centroid_mm":[x,0,0],"bbox_mm":[x-5,-5,-5,x+5,5,5]}

class ComparisonTests(unittest.TestCase):
    def test_reordering_is_bijective(self):
        self.assertEqual(match_solids([item(0),item(20)],[item(20),item(0)]),[{"source_index":0,"roundtrip_index":1},{"source_index":1,"roundtrip_index":0}])
    def test_matching_cannot_reuse_output_solid(self):
        self.assertIsNone(match_solids([item(),item()],[item(),item(50)]))
    def test_empty_or_missing_solids_fail(self):
        self.assertIsNone(match_solids([],[]))
        self.assertIsNone(match_solids([item()],[item(),item()]))
    def test_topology_change_fails(self):
        b=item();b['edges']=13
        self.assertFalse(compatible(item(),b))
    def test_invalid_or_nonfinite_fails(self):
        for field, value in [('valid',False),('volume_mm3',float('nan')),('centroid_mm',[0,float('inf'),0])]:
            b=item();b[field]=value
            self.assertFalse(compatible(item(),b))
    def test_coordinate_delta_beyond_budget_fails(self):
        b=item();b['centroid_mm'][0]=2e-5
        self.assertFalse(compatible(item(),b))
    def test_volume_delta_beyond_budget_fails(self):
        b=item();b['volume_mm3']+=0.002
        self.assertFalse(compatible(item(),b))
    def test_serialization_noise_within_budget_passes(self):
        b=item();b['volume_mm3']+=1e-5;b['bbox_mm'][0]+=1e-8
        self.assertTrue(compatible(item(),b))
    def test_source_hash_mismatch_fails_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.step';source.write_text('not the pinned source')
            output=Path(d)/'out'
            with self.assertRaisesRegex(ValueError,'SHA256'):
                run(source,output,'0'*64,12,'test')
            self.assertFalse(output.exists())
    def test_ambiguous_or_unsupported_units_fail_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.step';source.write_text('LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT($,.METRE.);')
            output=Path(d)/'out'
            with self.assertRaisesRegex(ValueError,'millimetre'):
                run(source,output,hashlib.sha256(source.read_bytes()).hexdigest(),12,'test')
            self.assertFalse(output.exists())
    def test_saved_actual_report_has_matched_twelve_solids(self):
        report_path=ROOT/'result.json'
        if not report_path.exists(): report_path=ROOT/'actual'/'result.json'
        r=json.loads(report_path.read_text())
        self.assertEqual(r['source']['sha256'],'4720192e2fb9d4c26b9a4b2be521d29508667eda67bd9301a9273df11c570fff')
        self.assertEqual(len(r['source_solids']),12)
        self.assertEqual(len(r['output_solids']),12)
        self.assertEqual(len(match_solids(r['source_solids'],r['output_solids'])),12)
        self.assertTrue(r['numerical_roundtrip_passed'])
        self.assertTrue(r['original_file_unchanged'])
        self.assertFalse(r['engineering_release'])
        self.assertFalse(r['meshing_or_solver_started'])

if __name__=='__main__': unittest.main()
