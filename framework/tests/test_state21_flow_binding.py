"""Contract tests. External genuine evidence is optional; no process fixture is shipped.

Set VALVE_STATE21_INPUT to a local manifest with reviewed realpaths and current
standards. Synthetic mutations test rejection, never physical validation.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CONSUMER = Path(__file__).resolve().parents[1] / 'tools/valve_readiness.py'
spec = importlib.util.spec_from_file_location('flow_readiness_under_test', CONSUMER)
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
BINDING = CONSUMER.with_name('state21_flow_binding.py')
spec = importlib.util.spec_from_file_location('binding_under_test', BINDING)
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
LOCAL = os.environ.get('VALVE_STATE21_INPUT')


def blank():
    return {'formula_input_binding': {'profile': B.PROFILE,
            'paths': {role: '/not-present-state21/' + role for role in B.ROLES}}}


class FlowContractTests(unittest.TestCase):
    def test_missing_sources_hold_not_invalid_or_success(self):
        r = R.audit(blank())
        f = r['formula_input_binding']
        self.assertEqual(f['source_binding_status'], 'HOLD')
        self.assertIsNone(f['observation'])
        self.assertIsNone(f['variable_bindings']['F-FLW-001']['A']['candidate_value'])
        self.assertIsNone(f['variable_bindings']['F-FLW-001']['zeta']['observed_proxy_K'])
        self.assertIsNone(f['variable_bindings']['F-FLW-001']['rho_ref']['value'])
        self.assertFalse(r['requested_checks_pass'])
        self.assertTrue(r['preflight_pass'])
        self.assertIn('MISSING_EXPLICIT_CURRENT_FFLW001_002_DECLARATIONS', f['missing_reasons'])

    def test_missing_sources_do_not_claim_observed_model(self):
        f=R.audit(blank())['formula_input_binding']
        self.assertFalse(any(x.startswith('LAMINAR') for x in f['missing_reasons']))

    def test_no_flow_keeps_legacy_inspect(self):
        r = R.audit({})
        self.assertTrue(r['requested_checks_pass'])
        self.assertNotIn('formula_input_binding', r)

    def test_unknown_old_profiles_and_boolean_state_rejected(self):
        for value in ('native-simple-state20/v1', 'native-simple-state19/v1', '', None, True, 21):
            m = blank(); m['formula_input_binding']['profile'] = value
            with self.subTest(value=value), self.assertRaises(R.ReadinessError): R.audit(m)

    def test_input_override_not_supported(self):
        for key, value in {'state': 20, 'stage': 'before_relax', 'units': 'Pa', 'rho': 1000,
                           'rho_ref': 1000, 'pressure': .3, 'A': .03, 'DN': 200,
                           'Qin': 1, 'K': True, 'steady': True, 'engineering_release': True,
                           'lock': {}, 'source_status': 'VERIFIED_CLAUSE'}.items():
            m = blank(); m['formula_input_binding'][key] = value
            with self.subTest(key=key), self.assertRaises(R.ReadinessError): R.audit(m)

    def test_path_shape_rejected(self):
        for path in ('relative', '/x/../y', '//x/y', '/x//y', '', None, True):
            m = blank(); m['formula_input_binding']['paths']['raw_log'] = path
            with self.subTest(path=path), self.assertRaises(R.ReadinessError): R.audit(m)

    def test_exact_roles_required(self):
        for edit in ('missing', 'extra', 'none'):
            m = blank(); p = m['formula_input_binding']['paths']
            if edit == 'missing': p.pop('model')
            if edit == 'extra': p['density'] = '/rho'
            if edit == 'none': m['formula_input_binding']['paths'] = None
            with self.subTest(edit=edit), self.assertRaises(R.ReadinessError): R.audit(m)

    def test_non_regular_symlink_and_oversize_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); os.mkfifo(root/'fifo')
            (root/'large').write_bytes(b'x' * (4 * 1024 * 1024 + 1))
            (root/'link').symlink_to(root/'large')
            (root/'dirlink').symlink_to(root, target_is_directory=True)
            for path in (root, root/'fifo', root/'large', root/'link', root/'dirlink'/'missing'):
                m = blank(); m['formula_input_binding']['paths']['raw_log'] = str(path)
                with self.subTest(path=path), self.assertRaises(R.ReadinessError): R.audit(m)

    def test_rehashed_profile_lock_cannot_bless_alternate_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); module=root/'state21_flow_binding.py'; module.write_bytes(BINDING.read_bytes())
            lock=json.loads(BINDING.with_name('state21-input.lock.json').read_bytes())
            lock['files']['raw_log']['sha256']='0'*64
            (root/'state21-input.lock.json').write_text(json.dumps(lock))
            spec=importlib.util.spec_from_file_location('changed_lock_test',module)
            changed=importlib.util.module_from_spec(spec);spec.loader.exec_module(changed)
            with self.assertRaisesRegex(R.ReadinessError,'immutable input lock mismatch'):
                changed.bind(blank()['formula_input_binding'],{},R._adapter)

    def test_duplicate_nan_and_false_status_json_invalid(self):
        for raw in (b'{"formula_input_binding":{},"formula_input_binding":{}}',
                    b'{"formula_input_binding":{"profile":NaN}}',
                    b'{"formula_input_binding":{"profile":1e999}}'):
            with self.assertRaises(R.ReadinessError): R._adapter._json(raw, 'negative')


@unittest.skipUnless(LOCAL, 'set VALVE_STATE21_INPUT for real external byte entry tests')
class RealExternalFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = R._adapter._json(Path(LOCAL).read_bytes(), 'local external manifest')
        cls.paths = cls.meta['formula_input_binding']['paths']
        cls.before = {r: hashlib.sha256(Path(p).read_bytes()).hexdigest() for r, p in cls.paths.items()}

    @classmethod
    def tearDownClass(cls):
        after = {r: hashlib.sha256(Path(p).read_bytes()).hexdigest() for r, p in cls.paths.items()}
        if after != cls.before: raise AssertionError('External evidence was changed')

    def test_real_audit_binds_actual_state21_hold(self):
        r = R.audit(copy.deepcopy(self.meta)); f = r['formula_input_binding']; o = f['observation']
        self.assertEqual(f['source_binding_status'], 'PASS')
        self.assertEqual(f['applicability_status'], 'HOLD')
        self.assertEqual(len(f['sources']), 7)
        self.assertEqual(o['state'], 21)
        self.assertAlmostEqual(o['inputs']['K']['value'], 115.96179557311865)
        self.assertEqual(o['inputs']['Qin_m3_s']['value'], -1.6340464601299483e-6)
        self.assertEqual(o['pressure_dimensions'], [0,2,-2,0,0,0,0])
        self.assertEqual(o['numerics']['p_relaxation'], .3)
        self.assertFalse(o['steady_evidence']['sustained_steady'])
        self.assertFalse(f['configuration_authenticated'])
        self.assertFalse(f['legacy_case_preflight_performed_by_binding'])
        self.assertTrue(r['preflight_pass']); self.assertFalse(r['requested_checks_pass'])
        self.assertFalse(r['engineering_release'])
        for key in ('Kv_m3_h','Cv','delta_p_Pa','rho_actual_kg_m3'): self.assertIsNone(f[key])
        self.assertEqual([x['id'] for x in f['formulas']], list(B.FORMULAS))
        self.assertTrue(all(x['source_status']=='UNVERIFIED_CLAUSE' for x in f['formulas']))

    @unittest.skipUnless(os.environ.get('VALVE_P08_INPUT'), 'set VALVE_P08_INPUT for original P08 regression')
    def test_original_p08_unchanged_and_not_upgraded(self):
        path=Path(os.environ['VALVE_P08_INPUT']); before=path.read_bytes()
        r=R.audit(R._adapter._json(before,'original P08'))
        self.assertFalse(r['preflight_pass']); self.assertFalse(r['requested_checks_pass'])
        self.assertIn('MESH_QUALITY_NOT_PASSED',r['errors'])
        self.assertIn('CASE_BYTES_NOT_CHECKED',r['errors'])
        self.assertEqual(r['standards']['status'],'INCOMPLETE')
        self.assertNotIn('formula_input_binding',r)
        self.assertEqual(before,path.read_bytes())

    def test_formula_variable_bindings_are_candidates_not_substitutions(self):
        f=R.audit(copy.deepcopy(self.meta))['formula_input_binding']; b=f['variable_bindings']
        a=b['F-FLW-001']['A']; z=b['F-FLW-001']['zeta']
        self.assertIsNone(a['value']); self.assertEqual(a['candidate_value'],0.031111036357382521)
        self.assertEqual(a['candidate_source']['locator'],'ports.21')
        self.assertIsNone(z['value']); self.assertEqual(z['observed_proxy_K'],115.96179557311865)
        self.assertEqual(b['F-FLW-001']['rho_ref']['value'],1000)
        self.assertIsNone(b['F-FLW-001']['Kv']['value'])
        self.assertIsNone(b['F-FLW-002']['Kv']['value'])
        self.assertIsNone(b['F-FLW-002']['Cv_US']['value'])

    def test_cli_isolated_real_entry_exit2_hold(self):
        p = subprocess.run([sys.executable,'-I','-B',str(CONSUMER),LOCAL], capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,2,p.stderr)
        r=json.loads(p.stdout); self.assertEqual(r['formula_input_binding']['status'],'HOLD')
        self.assertFalse(r['requested_checks_pass']); self.assertFalse(p.stderr)

    def test_missing_current_formula_declarations_hold(self):
        for refs in (None, [{'id':'F-FLW-001','use':'RESEARCH_REFERENCE'}]):
            m=copy.deepcopy(self.meta)
            if refs is None: m.pop('standards')
            else: m['standards']['references']=refs
            f=R.audit(m)['formula_input_binding']
            self.assertEqual(f['source_binding_status'],'PASS')
            self.assertIn('MISSING_EXPLICIT_CURRENT_FFLW001_002_DECLARATIONS',f['missing_reasons'])
            self.assertIsNone(f['rho_ref'])

    def test_ineligible_normative_declaration_does_not_promote(self):
        m=copy.deepcopy(self.meta); m['standards']['references'][0]['use']='NORMATIVE_BASIS'
        r=R.audit(m)
        self.assertFalse(r['standards']['source_use_pass']); self.assertFalse(r['requested_checks_pass'])
        self.assertIsNone(r['formula_input_binding']['Kv_m3_h'])

    def test_each_changed_source_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as d:
            for role,path in self.paths.items():
                altered=Path(d)/role; altered.write_bytes(Path(path).read_bytes()+b'\n')
                m=copy.deepcopy(self.meta);m['formula_input_binding']['paths'][role]=str(altered)
                with self.subTest(role=role),self.assertRaisesRegex(R.ReadinessError,'digest/size'):R.audit(m)

    def test_precise_forged_observation_mutations_fail_digest(self):
        # Local adversarial bytes, not fixtures blessed by a caller-rehashed lock.
        original=json.loads(Path(self.paths['observation']).read_bytes())
        mutations=[('old_state',lambda x:x['ports'].__setitem__('21',x['ports']['20'])),
                   ('false_steady',lambda x:x.__setitem__('sustained_nonlinear_steady_convergence',True)),
                   ('bool_K',lambda x:x['ports']['21'].__setitem__('K',True)),
                   ('zero_area',lambda x:x['ports']['21'].__setitem__('Ain_m2',0)),
                   ('mm2_area',lambda x:x['ports']['21'].__setitem__('Ain_m2',31111.036)),
                   ('signed_Q_reversed',lambda x:x['ports']['21'].__setitem__('Qin_m3_s',1.63404646e-6)),
                   ('relaxation_as_pressure',lambda x:x['ports']['21'].__setitem__('DeltaPkin_m2_s2',.3)),
                   ('Pa_label',lambda x:x['ports']['21'].__setitem__('DeltaP_Pa',.00015995)),
                   ('stage',lambda x:x['native_stages']['actual_final_phi']['21'].__setitem__('actual_corr',1)),
                   ('release',lambda x:x.__setitem__('engineering_release',True))]
        with tempfile.TemporaryDirectory() as d:
            for label, mutate in mutations:
                doc=copy.deepcopy(original);mutate(doc);path=Path(d)/'observation.json';path.write_text(json.dumps(doc))
                m=copy.deepcopy(self.meta);m['formula_input_binding']['paths']['observation']=str(path)
                with self.subTest(label=label),self.assertRaisesRegex(R.ReadinessError,'digest/size'): R.audit(m)

    def test_internal_parser_checks_not_only_hashes(self):
        # Unit-level parser defenses; bypassing authentication is deliberately NOT a public API.
        files={r:Path(p).read_bytes() for r,p in self.paths.items()}
        for old,new in [(b'CONT_PORTS 21 ',b'CONT_PORTS 20 '),
                        (b'static_area_mean_kinematic_inlet_reference',b'total_pressure_Pa'),
                        (b'CONT_STATE_END 21 ',b'CONT_STATE_END 20 ')]:
            changed=dict(files);changed['raw_log']=changed['raw_log'].replace(old,new)
            with self.subTest(old=old),self.assertRaises(R.ReadinessError):B._extract(changed,R._adapter)


if __name__ == '__main__': unittest.main()
