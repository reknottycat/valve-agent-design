import copy
import json
import unittest
from pathlib import Path
from validate_package import validate_data, validate_example, ROOT

class PackageGuards(unittest.TestCase):
    def setUp(self):
        self.matrix=json.loads((ROOT/'engineering-input-matrix.json').read_text())
        self.sources=json.loads((ROOT/'source-register.json').read_text())
    def reject(self):self.assertTrue(validate_data(self.matrix,self.sources))
    def test_baseline(self):self.assertEqual(validate_data(self.matrix,self.sources),[])
    def test_release_is_blocked(self):self.matrix['engineering_release']=True;self.reject()
    def test_runtime_is_blocked(self):self.matrix['solver_executed']=True;self.reject()
    def test_candidate_adoption_is_blocked(self):self.matrix['rows'][0]['adopted_for_candidate']=True;self.reject()
    def test_unknown_source_is_rejected(self):self.matrix['rows'][0]['source_ids']=['missing'];self.reject()
    def test_missing_unit_is_rejected(self):self.matrix['rows'][0]['unit']='';self.reject()
    def test_unresolved_value_is_null(self):self.matrix['rows'][0]['value']=123;self.reject()
    def test_derived_requires_assumptions(self):
        next(r for r in self.matrix['rows'] if r['status']=='derived-under-assumptions')['assumptions']=[];self.reject()
    def test_no_public_value_into_original(self):
        next(r for r in self.matrix['rows'] if r['status']=='published-otherproduct')['track']='original-R1';self.reject()
    def test_no_cross_manufacturer_mix(self):
        r=next(r for r in self.matrix['rows'] if r['status']=='published-otherproduct');r['source_ids']=['PUB-ILSHIN'];self.reject()
    def test_product_performance_must_stay_null(self):self.matrix['product_performance']['loss_coefficient']=6;self.reject()
    def test_spring_choice_not_silently_selected(self):self.matrix['candidate_configuration_gates']['public-perlwitz-017960-DN200']['spring_selection']='none';self.reject()
    def test_original_needs_original_source(self):
        r=next(r for r in self.matrix['rows'] if r['status']=='confirmed-original');r['source_ids']=['PUB-MESON'];self.reject()
    def test_unknown_status_is_rejected(self):self.matrix['rows'][0]['status']='VERIFIED';self.reject()
    def test_educational_example_arithmetic(self):
        e=json.loads((ROOT/'educational-kv-example.json').read_text());self.assertEqual(validate_example(e,self.sources),[])
    def test_educational_example_cannot_be_product(self):
        e=json.loads((ROOT/'educational-kv-example.json').read_text());e['actual_valve_result']=True;self.assertTrue(validate_example(e,self.sources))
    def test_educational_example_arithmetic_error_rejected(self):
        e=json.loads((ROOT/'educational-kv-example.json').read_text());e['outputs']['CdA']['value']*=1000;self.assertTrue(validate_example(e,self.sources))
if __name__=='__main__':unittest.main()
