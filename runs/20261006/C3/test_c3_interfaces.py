import copy
import json
from pathlib import Path
import sys
import unittest

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'T11'))
from check_interfaces import evaluate,joint_metrics,unwrap


class InterfaceTests(unittest.TestCase):
    def data(self):return json.loads((BASE/'T11/interface_candidates.json').read_text())

    def test_candidates_remain_unselected(self):
        r=evaluate(self.data());self.assertIsNone(r['selection']);self.assertFalse(r['manufacturing_authorized'])

    def test_pressure_cannot_be_invented(self):
        d=self.data();d['global_unknowns']['design_pressure_MPa']=.6
        with self.assertRaises(ValueError):evaluate(d)

    def test_torque_cannot_be_invented(self):
        d=self.data();d['bonnet_joint_candidates'][0]['unresolved']['tightening_torque_Nm']=50
        with self.assertRaises(ValueError):evaluate(d)

    def test_material_selection_not_implicit(self):
        d=self.data();d['packing_gland']['unresolved']['packing_material']='PTFE'
        with self.assertRaises(ValueError):evaluate(d)

    def test_selected_hardware_rejected(self):
        d=self.data();d['bonnet_joint_candidates'][0]['selected']=True
        with self.assertRaises(ValueError):evaluate(d)

    def test_inherited_datum_drift_rejected(self):
        d=self.data();d['common']['handwheel_hub_closed_bottom_z']['value']=500
        with self.assertRaises(ValueError):evaluate(d)

    def test_wrong_units_rejected(self):
        d=self.data();d['common']['stem_d']['unit']='m'
        with self.assertRaises(ValueError):evaluate(d)

    def test_nan_and_bool_dimensions_rejected(self):
        for bad in (float('nan'),True):
            d=self.data();d['common']['stem_d']['value']=bad
            with self.assertRaises(ValueError):evaluate(d)

    def test_unverified_origin_not_promoted_to_standard(self):
        d=self.data();d['bonnet_joint_candidates'][0]['values']['bolt_hole_d']['kind']='STANDARD_APPROVED'
        with self.assertRaises(ValueError):evaluate(d)

    def test_washer_overhang_is_a_real_negative_control(self):
        d=self.data();c=next(x for x in d['bonnet_joint_candidates'] if x['id']=='J8-20')
        c['values']['flange_od']['value']=420
        r=joint_metrics(unwrap(d['common']),c)
        self.assertEqual(r['fit_gate'],'FAIL');self.assertIn('washer_to_flange_edge_mm',r['failures'])

    def test_hole_gasket_conflict_rejected(self):
        d=self.data();c=d['bonnet_joint_candidates'][0];c['values']['gasket_od']['value']=360
        self.assertIn('gasket_to_hole_gap_mm',joint_metrics(unwrap(d['common']),c)['failures'])

    def test_catalog_envelopes_do_not_silently_pass(self):
        r=evaluate(self.data());values={x['id']:x for x in r['drive_candidates']}
        self.assertEqual(values['D40-custom']['packaging_gate'],'PASS')
        self.assertEqual(values['D54-index-scenario']['packaging_gate'],'FAIL')
        self.assertEqual(values['D70-vendor-envelope']['packaging_gate'],'FAIL')
        self.assertEqual(values['D54-index-scenario']['additional_axial_space_required_mm'],7)

    def test_washer_must_have_positive_ring_width(self):
        d=self.data();c=d['bonnet_joint_candidates'][0];c['values']['washer_od']['value']=10
        self.assertIn('washer_radial_band_mm',joint_metrics(unwrap(d['common']),c)['failures'])

    def test_washer_cannot_cross_pressure_opening(self):
        d=self.data();c=d['bonnet_joint_candidates'][0]
        c['values']['washer_od']['value']=100;c['values']['flange_od']['value']=500
        self.assertIn('washer_to_pressure_opening_gap_mm',joint_metrics(unwrap(d['common']),c)['failures'])

    def test_adjacent_washers_cannot_overlap(self):
        d=self.data();c=d['bonnet_joint_candidates'][0];c['bolt_count']=32
        self.assertIn('adjacent_washer_gap_mm',joint_metrics(unwrap(d['common']),c)['failures'])

    def test_packing_cannot_exceed_follower_axial_space(self):
        d=self.data();d['packing_gland']['values']['packing_height']['value']=40
        with self.assertRaises(ValueError):evaluate(d)

    def test_gland_stud_must_fit_its_hole(self):
        d=self.data();d['packing_gland']['values']['gland_stud_nominal_d']['value']=20
        with self.assertRaises(ValueError):evaluate(d)

    def test_drive_nut_must_surround_stem(self):
        d=self.data();d['drive_nut_candidates'][0]['body_od']=30
        with self.assertRaises(ValueError):evaluate(d)

    def test_candidate_paths_are_bounded(self):
        for unsafe in ('../C2','a/b','..','/tmp/x'):
            d=self.data();d['drive_nut_candidates'][0]['id']=unsafe
            with self.assertRaises(ValueError):evaluate(d)

    def test_duplicate_candidate_ids_rejected(self):
        d=self.data();d['drive_nut_candidates'][1]['id']=d['drive_nut_candidates'][0]['id']
        with self.assertRaises(ValueError):evaluate(d)

    def test_missing_unknown_fields_do_not_pass_vacuously(self):
        for section in ('global','joint','packing'):
            d=self.data()
            if section=='global':d['global_unknowns']={}
            if section=='joint':d['bonnet_joint_candidates'][0]['unresolved']={}
            if section=='packing':d['packing_gland']['unresolved']={}
            with self.assertRaises(ValueError):evaluate(d)


if __name__=='__main__':unittest.main()
