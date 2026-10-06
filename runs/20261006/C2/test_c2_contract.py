import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE=Path(__file__).resolve().parent
for folder in ('T06','T12','T15','T22'):
    sys.path.insert(0,str(BASE/folder))
from validate_inputs import validate_variant
from build_lift_model import load_parameters,pose
from study_calculations import calculate
from validate_lift_model import checked_overlap_value,check_disc_contacts
import validate_lift_model


class C2ContractTests(unittest.TestCase):
    def test_source_reference_and_free_disc_lift_separated(self):
        p,d,_=load_parameters()
        self.assertEqual(d['values']['stem_travel']['kind'],'DRAWING_REFERENCE')
        self.assertEqual(d['values']['disc_max_lift']['kind'],'DESIGN_ASSUMPTION')
        self.assertNotIn('disc_inclination',p)

    def test_nonfinite_boolean_results_rejected(self):
        for valid,volume in [(False,0),(True,float('nan')),(True,float('inf')),(True,-1),(True,True)]:
            with self.assertRaises(ValueError):checked_overlap_value(valid,volume)

    def test_body_contact_is_rejected_even_without_volume_overlap(self):
        failures=check_disc_contacts(0,0,{'body':1.,'seat_ring':100.,'stem':10.},100.,10.)
        self.assertIn('UNINTENDED_DISC_BODY_CONTACT',failures)

    def test_missing_screw_stop_contact_rejected(self):
        self.assertIn('STOP_CONTACT_MISSING',check_disc_contacts(0,0,{'body':0.,'seat_ring':100.,'stem':0.},100.,10.))

    def test_free_disc_cannot_touch_retracted_stem(self):
        self.assertIn('FREE_LIFT_CONTACT',check_disc_contacts(5,57,{'body':0.,'seat_ring':0.,'stem':1.},100.,10.))

    def test_valid_contact_classification(self):
        self.assertEqual(check_disc_contacts(0,0,{'body':0.,'seat_ring':100.,'stem':10.},100.,10.),[])

    def test_brine_cannot_leak_into_base_variant(self):
        matrix=json.loads((BASE/'T06/variant_input_matrix.json').read_text())
        base=copy.deepcopy(next(v for v in matrix['variants'] if v['designation']=='522-35.4179'))
        validate_variant(base)
        base['service_cases'].append({'medium':'28% CaCl2','source_note':5})
        with self.assertRaises(ValueError):validate_variant(base)

    def test_catalog_pressure_cannot_freeze_source_pressure(self):
        matrix=json.loads((BASE/'T06/variant_input_matrix.json').read_text())
        v=copy.deepcopy(matrix['variants'][0]);v['design_pressure_MPa']=.63
        with self.assertRaises(ValueError):validate_variant(v)

    def test_calculations_never_select_pressure_or_material(self):
        _,d,_=load_parameters();r=calculate(d)
        self.assertIsNone(r['pressure_selected_MPa']);self.assertIsNone(r['material_grade_selected'])
        self.assertFalse(r['manufacturing_authorized'])
        self.assertAlmostEqual(r['kinematics']['screw_revolutions_for_reference_travel'],9.5)
        self.assertAlmostEqual(r['normalized_static_relations']['adverse_pressure_closing_force_N_per_MPa'],math.pi*200**2/4)

    def test_failed_rebuild_cannot_leave_previous_pass(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'geometry_check.json';path.write_text('{"geometry_gate":"PASS"}')
            with patch.object(validate_lift_model,'make_model',side_effect=RuntimeError('injected build failure')):
                with self.assertRaises(RuntimeError):validate_lift_model.validate(Path(d))
            self.assertEqual(json.loads(path.read_text())['geometry_gate'],'RUNNING')


if __name__=='__main__':unittest.main()
