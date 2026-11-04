"""Research-only fluid arithmetic; external real entry tests never ship fixtures."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
R = load('fluid_readiness', TOOLS/'valve_readiness.py')
G = load('fluid_geometry', TOOLS/'state21_port_geometry.py')
B = load('fluid_binding', TOOLS/'state21_flow_binding.py')
LOCAL = os.environ.get('VALVE_STATE21_PORT_INPUT')


class FluidArithmetic(unittest.TestCase):
    def test_units_and_known_arithmetic(self):
        rho, mu, nu = 1024.9109328963, .0010766289252529323, 1.0504609627009073e-6
        self.assertEqual(mu/rho, nu)
        self.assertEqual(rho*1.599501972386503e-7, .00016393470586881226)
        self.assertNotEqual(1000*1.599501972386503e-7, .00016393470586881226)

    def test_absent_observer_or_geometry_never_scales(self):
        self.assertIsNone(B._research_fluid_binding({}, None, R._adapter))
        for key in ('source_binding_status','reconstruction_status','observer_crosscheck_status'):
            m = dict.fromkeys(('source_binding_status','reconstruction_status','observer_crosscheck_status'),'PASS')
            m[key] = 'HOLD'
            self.assertIsNone(B._research_fluid_binding(m, {}, R._adapter))


@unittest.skipUnless(LOCAL, 'set VALVE_STATE21_PORT_INPUT for real external fluid entry tests')
class RealFluid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = json.loads(Path(LOCAL).read_bytes())
        cls.result = R.audit(copy.deepcopy(cls.meta))
        cls.f = cls.result['formula_input_binding']
        cls.plan_path = cls.meta['formula_input_binding']['geometry_binding']['paths']['plan']
        cls.plan = json.loads(Path(cls.plan_path).read_bytes())

    def test_real_api_closes_only_conditional_research(self):
        f=self.f; r=f['research_fluid_binding']
        self.assertEqual(r['conditional_research_pressure_difference_Pa'], .00016393470586881226)
        self.assertEqual(r['nu_from_mu_over_rho_m2_s'], r['run_nu_m2_s'])
        self.assertEqual(r['assumptions'], self.plan['selected_study_property_state'])
        for key in ('Kv_m3_h','Cv','delta_p_Pa','rho_actual_kg_m3'): self.assertIsNone(f[key])
        for key in ('A','zeta','Kv'): self.assertIsNone(f['variable_bindings']['F-FLW-001'][key]['value'])
        self.assertEqual(f['status'],'HOLD');self.assertFalse(self.result['engineering_release'])
        self.assertEqual(f['rho_ref']['value'],1000)
        self.assertFalse(r['actual_duty_or_measurement']);self.assertFalse(r['assumptions']['pressure_correction_implemented'])
        self.assertEqual(r['assumptions']['minus_2C_phase_and_property_gate'],'UNRESOLVED')

    def test_real_isolated_cli_executes_conversion(self):
        p=subprocess.run([sys.executable,'-I','-B',str(TOOLS/'valve_readiness.py'),LOCAL],capture_output=True,text=True,timeout=30)
        self.assertEqual(p.returncode,2,p.stderr);self.assertFalse(p.stderr)
        self.assertEqual(json.loads(p.stdout)['formula_input_binding']['research_fluid_binding'], self.f['research_fluid_binding'])

    def test_exact_state_flags_provenance_and_reference_pressure(self):
        mutations={'density_kg_m3':1000., 'temperature_C':-2., 'salinity_g_kg':.035,
                   'pressure_MPa_absolute':.63, 'dynamic_viscosity_Pa_s':1.0766,
                   'kinematic_viscosity_m2_s':1e-6,'actual_duty_or_measurement':True,
                   'pressure_correction_implemented':True,'minus_2C_phase_and_property_gate':'PASS'}
        for key,value in mutations.items():
            p=copy.deepcopy(self.plan);p['selected_study_property_state'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):G.research_fluid_state(p)
        p=copy.deepcopy(self.plan);p['selected_study_property_state']['unit']='kg/L'
        with self.assertRaises(ValueError):G.research_fluid_state(p)
        p=copy.deepcopy(self.plan);p['sources']['property_data_sha256']='0'*64
        with self.assertRaises(ValueError):G.research_fluid_state(p)
        p=copy.deepcopy(self.plan);p['pressure_interpretation']['field']='p in Pa'
        with self.assertRaises(ValueError):G.research_fluid_state(p)

    def test_model_viscosity_and_pressure_units_must_reconcile(self):
        for field,value in [('value',1e-6),('unit','Pa*s')]:
            obs=copy.deepcopy(self.f['observation']);obs['model']['nu'][field]=value
            with self.assertRaises(R.ReadinessError):B._research_fluid_binding(self.f['geometry_binding'],obs,R._adapter)
        obs=copy.deepcopy(self.f['observation']);obs['pressure_dimensions']=[1,-1,-2,0,0,0,0]
        with self.assertRaises(R.ReadinessError):B._research_fluid_binding(self.f['geometry_binding'],obs,R._adapter)
        obs=copy.deepcopy(self.f['observation']);obs['inputs']['DeltaPkin_m2_s2']['unit']='Pa'
        with self.assertRaises(R.ReadinessError):B._research_fluid_binding(self.f['geometry_binding'],obs,R._adapter)

    def test_missing_observer_or_geometry_and_original_mode(self):
        for role in ('observer_source','transport'):
            m=copy.deepcopy(self.meta);m['formula_input_binding']['paths'][role]='/missing-fluid-source'
            f=R.audit(m)['formula_input_binding'];self.assertNotIn('research_fluid_binding',f)
        m=copy.deepcopy(self.meta);m['formula_input_binding']['geometry_binding']['paths']['plan']='/missing-fluid-plan'
        self.assertNotIn('research_fluid_binding',R.audit(m)['formula_input_binding'])
        m=copy.deepcopy(self.meta);del m['formula_input_binding']['geometry_binding']
        self.assertNotIn('research_fluid_binding',R.audit(m)['formula_input_binding'])

    def test_no_arbitrary_state_inputs(self):
        for name in ('rho','temperature_C','selected_study_property_state','research_fluid_binding'):
            m=copy.deepcopy(self.meta);m['formula_input_binding'][name]=1000
            with self.assertRaises(R.ReadinessError):R.audit(m)

    def test_changed_plan_density_rejected_by_existing_pin(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'plan';raw=Path(self.plan_path).read_bytes()
            changed=raw.replace(b'1024.9109328963',b'1000.0000000000');self.assertEqual(len(raw),len(changed))
            path.write_bytes(changed)
            m=copy.deepcopy(self.meta);m['formula_input_binding']['geometry_binding']['paths']['plan']=str(path)
            with self.assertRaisesRegex(R.ReadinessError,'digest/size'):R.audit(m)

    def test_pressure_scaling_independent_of_capacity_source_declarations(self):
        m=copy.deepcopy(self.meta);del m['standards']
        f=R.audit(m)['formula_input_binding']
        self.assertEqual(f['research_fluid_binding'],self.f['research_fluid_binding'])
        self.assertIsNone(f['rho_ref']);self.assertEqual(f['formulas'],[])

if __name__ == '__main__': unittest.main()
