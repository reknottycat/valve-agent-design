import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

BASE=Path(__file__).resolve().parent
for folder in ('T06','T15','T19'):sys.path.insert(0,str(BASE/folder))
import basis_gate
import calculate_loads as calc
import extract_pressure_faces as geometry
import seawater_study as water


class C4StudyTests(unittest.TestCase):
    def setUp(self):
        self.basis=json.loads((BASE/'T06/research_basis.json').read_text())
        self.areas=json.loads((BASE/'T19/pressure_areas.json').read_text())
        self.params=json.loads((BASE.parent/'C2/T11/parameters.json').read_text())
        self.interfaces=json.loads((BASE.parent/'C3/T11/interface_candidates.json').read_text())

    def rejected_basis(self,change):
        change(self.basis)
        with self.assertRaises((ValueError,KeyError)):basis_gate.validate(self.basis,False)

    def test_current_basis_and_source_pins(self):
        self.assertEqual(basis_gate.validate(self.basis)['study_input_gate'],'PASS')

    def test_base_not_brine(self):
        self.rejected_basis(lambda b:b['target'].update(medium='28% calcium chloride'))

    def test_wrong_variant_rejected(self):
        self.rejected_basis(lambda b:b['target'].update(designation='522-35.4179-02'))

    def test_MPa_misread_rejected(self):
        self.rejected_basis(lambda b:b['pressure_unit_conversion'].update(catalog_converted_MPa=6.3))

    def test_gauge_absolute_mixing_rejected(self):
        self.rejected_basis(lambda b:b['selected_study_inputs']['internal_design_pressure'].update(unit='MPa(abs)'))

    def test_pressure_false_rating_rejected(self):
        self.rejected_basis(lambda b:b['selected_study_inputs']['internal_design_pressure'].update(kind='MANUFACTURER_CERTIFIED'))

    def test_nan_rejected(self):
        self.rejected_basis(lambda b:b['selected_study_inputs']['internal_design_pressure'].update(value=float('nan')))

    def test_boolean_rejected(self):
        self.rejected_basis(lambda b:b['selected_study_inputs']['internal_design_pressure'].update(value=True))

    def test_unknown_cannot_disappear(self):
        self.rejected_basis(lambda b:b['unresolved'].pop('physical_proof_pressure_MPa'))

    def test_no_physical_proof_selection(self):
        self.rejected_basis(lambda b:b['unresolved'].update(physical_proof_pressure_MPa=.945))

    def test_no_allowable_selection(self):
        self.rejected_basis(lambda b:b['unresolved'].update(material_allowable_stresses_MPa=100))

    def test_no_implicit_release(self):
        self.rejected_basis(lambda b:b['release'].update(manufacturing_authorized=True))

    def test_no_solver_restart(self):
        self.rejected_basis(lambda b:b['release'].update(solver_execution_allowed=True))

    def test_overload_not_physical_proof(self):
        self.rejected_basis(lambda b:b['pressure_sensitivity'][-1].update(kind='PROOF_TEST'))

    def test_duplicate_cases_rejected(self):
        self.rejected_basis(lambda b:b['pressure_sensitivity'][1].update(id=b['pressure_sensitivity'][0]['id']))

    def test_empty_friction_rejected(self):
        self.rejected_basis(lambda b:b['thread_study'].update(friction_coefficients=[]))

    def test_inverted_collar_rejected(self):
        self.rejected_basis(lambda b:b['collar_study'].update(inner_d_mm=70))

    def test_boolean_starts_rejected(self):
        self.rejected_basis(lambda b:b['thread_study'].update(starts_assumed=True))

    def test_frictionless_work_identity(self):
        r=calc.screw_model(1000,33,6,15,0)
        self.assertAlmostEqual(r['thread_torque_Nm'],1000*.006/(2*math.pi))
        self.assertAlmostEqual(r['thread_efficiency'],1.)
        self.assertFalse(r['static_self_lock_model'])

    def test_friction_increases_torque(self):
        values=[calc.screw_model(19792,33,6,15,mu)['thread_torque_Nm'] for mu in (0,.03,.08,.15,.25)]
        self.assertEqual(values,sorted(values))

    def test_self_lock_is_conditional(self):
        self.assertFalse(calc.screw_model(1000,33,6,15,.03)['static_self_lock_model'])
        self.assertTrue(calc.screw_model(1000,33,6,15,.15)['static_self_lock_model'])

    def test_force_scaling(self):
        a=calc.screw_model(1000,33,6,15,.15)['thread_torque_Nm']
        b=calc.screw_model(2000,33,6,15,.15)['thread_torque_Nm']
        self.assertAlmostEqual(b,2*a)

    def test_bad_screw_numeric_rejected(self):
        for value in (True,float('nan'),float('inf'),-1):
            with self.subTest(value=value),self.assertRaises(ValueError):calc.screw_model(value,33,6,15,.15)

    def test_pressure_sides_not_only_differential(self):
        coeff={'inlet':31415.9265,'outlet':-40828.1381}
        self.assertNotEqual(calc.pressure_force(coeff,.63,.63),calc.pressure_force(coeff,0,0))
        self.assertEqual(.63-.63,0-0)

    def test_negative_gauge_not_silently_accepted(self):
        with self.assertRaises(ValueError):calc.pressure_force({'inlet':1,'outlet':-1},-.1,0)

    def test_current_area_report(self):calc.pressure_area_integrity(self.areas)

    def test_pressure_unit_drift_rejected(self):
        self.areas['length_unit']='m'
        with self.assertRaises(ValueError):calc.pressure_area_integrity(self.areas)

    def test_wrong_pressure_face_sign_rejected(self):
        self.areas['poses']['closed']['parts']['disc_guide']['inlet']['faces'][0]['outward_normal_z'] *= -1
        with self.assertRaises(ValueError):calc.pressure_area_integrity(self.areas)

    def test_missing_pressure_face_rejected(self):
        self.areas['poses']['closed']['parts']['disc_guide']['inlet']['faces']=[]
        with self.assertRaises(ValueError):calc.pressure_area_integrity(self.areas)

    def test_nonfinite_area_rejected(self):
        self.areas['poses']['closed']['parts']['disc_guide']['inlet']['axial_force_coefficient_N_per_MPa']=float('nan')
        with self.assertRaises(ValueError):calc.pressure_area_integrity(self.areas)

    def test_closed_bypass_rejected(self):
        with self.assertRaises(ValueError):geometry.classify_compartments([],600)

    def test_unknown_boolean_area_rejected(self):
        for value in (True,float('nan'),float('inf'),-1):
            with self.subTest(value=value),self.assertRaises(ValueError):geometry.checked_number(value,'area',True)

    def test_stale_pass_invalidated_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);(base/'T19').mkdir();out=base/'T19/pressure_areas.json'
            out.write_text('{"status":"GEOMETRIC_PRESSURE_AREA_PASS"}')
            with mock.patch.object(geometry,'BASE',base),mock.patch.object(geometry,'measure',side_effect=ValueError('injected geometry failure')):
                with self.assertRaises(ValueError):geometry.main()
            self.assertEqual(json.loads(out.read_text())['status'],'FAIL')

    def test_empty_step_provenance_rejected(self):
        self.areas['input_asset_sha256']={}
        with self.assertRaises(ValueError):calc.pressure_area_integrity(self.areas)

    def test_wrong_parameter_provenance_rejected(self):
        self.areas['parameters_sha256']='0'*64
        with self.assertRaises(ValueError):calc.pressure_area_integrity(self.areas)

    def test_property_dataset_recomputes(self):
        d=json.loads((BASE/'T06/seawater_study_cases.json').read_text())
        self.assertEqual(water.validate_dataset(d)['reference_points'],9)

    def test_tampered_negative_density_rejected(self):
        d=json.loads((BASE/'T06/seawater_study_cases.json').read_text());d['rows'][0]['density_kg_m3']=-999
        with self.assertRaises(ValueError):water.validate_dataset(d)

    def test_tampered_positive_density_rejected(self):
        d=json.loads((BASE/'T06/seawater_study_cases.json').read_text());d['rows'][0]['density_kg_m3']=999
        with self.assertRaises(ValueError):water.validate_dataset(d)

    def test_duplicate_property_point_rejected(self):
        d=json.loads((BASE/'T06/seawater_study_cases.json').read_text());d['rows'][1]=copy.deepcopy(d['rows'][0])
        with self.assertRaises(ValueError):water.validate_dataset(d)

    def test_nonfinite_viscosity_rejected(self):
        d=json.loads((BASE/'T06/seawater_study_cases.json').read_text());d['rows'][0]['dynamic_viscosity_Pa_s']=float('nan')
        with self.assertRaises(ValueError):water.validate_dataset(d)

    def test_fake_pressure_correction_rejected(self):
        d=json.loads((BASE/'T06/seawater_study_cases.json').read_text());d['rows'][0]['pressure_correction_applied']=True
        with self.assertRaises(ValueError):water.validate_dataset(d)

    def test_property_reference_point(self):
        rho,mu,nu=water.rho_mu(20,35)
        self.assertAlmostEqual(rho,1024.9109328963,places=8)
        self.assertAlmostEqual(mu,1.0766289252529323e-3,places=12)
        self.assertAlmostEqual(nu,mu/rho,places=15)

    def test_cold_property_not_extrapolated(self):
        with self.assertRaises(ValueError):water.rho_mu(-2,35)

    def test_property_pressure_not_design_pressure(self):
        with self.assertRaises(ValueError):water.rho_mu(20,35,.731325)

    def test_property_numeric_invalid(self):
        for value in (True,float('nan'),float('inf')):
            with self.subTest(value=value),self.assertRaises(ValueError):water.rho_mu(value,35)

    def test_property_salinity_domain(self):
        with self.assertRaises(ValueError):water.rho_mu(20,0)

    def test_load_matrix_contact_gate(self):
        report=calc.calculate(self.basis,self.areas,self.params,self.interfaces)
        self.assertEqual(len(report['cases']),20)
        rows={r['case']:r for r in report['cases']}
        d=rows['selected-study/forward-free-diagnostic']
        self.assertEqual(d['pressure_only_unilateral_contact'],'WOULD_REQUIRE_TENSILE_SEAT_REACTION')
        self.assertLess(d['pressure_only_equilibrium_seat_reaction_z_N'],0)
        self.assertIsNone(rows['selected-study/forward-held']['actual_drive_force_N'])
        self.assertFalse(report['manufacturing_authorized'])
        self.assertEqual(len(report['drive_sensitivity']['rows']),12)
        self.assertEqual(len(report['joint_pressure_diameter_sensitivity']),9)
        for row in report['joint_pressure_diameter_sensitivity']:
            self.assertIsNone(row['preload_N']);self.assertIsNone(row['actual_bolt_load_N'])


if __name__=='__main__':unittest.main()
