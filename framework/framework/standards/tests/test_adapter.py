"""Synthetic rejection cases and opt-in exact-current-snapshot integration.

No test fixture is engineering evidence. No standards contents are vendored.
"""
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('current_adapter', HERE / 'standards_adapter.py')
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


def inventory(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


class StrictInputs(unittest.TestCase):
    def test_json_rejects_duplicate_nonfinite_and_overflow(self):
        for raw in [b'{"x":1,"x":2}', b'{"x":NaN}', b'[Infinity]', b'[-Infinity]',
                    b'{"nested":[1e999]}', b'[-1e999]']:
            with self.subTest(raw=raw), self.assertRaises(A.AdapterError):
                A._json(raw, 'synthetic')

    def test_strict_record_ingestion(self):
        base = {'id': 'F-SYNTHETIC', 'source': {},
                'evidence': {'grade': 'E1', 'status': 'UNVERIFIED_CLAUSE'}}
        for records in [[], [None], [base, base], [dict(base, id='D-wrong')],
                        [dict(base, source=None)], [dict(base, evidence={})]]:
            with self.subTest(records=records), self.assertRaises(A.AdapterError):
                A._entries({'kb/formulas/synthetic.json': json.dumps(records).encode()})
        with self.assertRaisesRegex(A.AdapterError, 'Duplicate record ID'):
            A._entries({f'kb/formulas/{x}.json': json.dumps([base]).encode() for x in ('a', 'b')})

    def test_data_layer_requires_wrapper(self):
        data = {'id': 'D-SYNTHETIC', 'source': {},
                'evidence': {'grade': 'E1', 'status': 'UNVERIFIED_CLAUSE'}}
        with self.assertRaisesRegex(A.AdapterError, 'data wrapper'):
            A._entries({'kb/data/synthetic.json': json.dumps([data]).encode()})
        self.assertIn('D-SYNTHETIC', A._entries({
            'kb/data/synthetic.json': json.dumps({'entries': [data]}).encode()}))

    def test_bad_api_paths_are_structured_errors(self):
        for root, manifest in [(None, A.DEFAULT_LOCK), ('\x00', A.DEFAULT_LOCK), ('.', '\x00')]:
            with self.subTest(root=root, manifest=manifest), self.assertRaises(A.AdapterError):
                A.StandardsAdapter(root, manifest)

    def test_paths_reject_escape_and_noncanonical(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel in ['/etc/passwd', '../file', 'kb/../file', 'kb\\file', 'kb//file', './file', 7]:
                with self.subTest(rel=rel), self.assertRaises(A.AdapterError):
                    A._file_path(root, rel)
            (root / 'escape').symlink_to(root.parent, target_is_directory=True)
            with self.assertRaisesRegex(A.AdapterError, 'escapes'):
                A._file_path(root, 'escape/file')

    def test_frozen_path_only_exposes_locked_bytes(self):
        path = A.FrozenPath({'a/b.json': b'{"x":1}'})
        self.assertEqual((path / 'a' / 'b.json').read_text(), '{"x":1}')
        for rel in ['../a', '/a', 'a\\b']:
            with self.assertRaises(ValueError):
                path / rel
        with self.assertRaisesRegex(ValueError, 'unlocked'):
            (path / 'missing').read_bytes()
        self.assertFalse(hasattr(path, 'write_text'))


class CurrentSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get('STANDARDS_KB_SNAPSHOT')
        if not path:
            raise unittest.SkipTest('set STANDARDS_KB_SNAPSHOT for current upstream integration')
        cls.root = Path(path).resolve()
        cls.before = inventory(cls.root)
        cls.adapter_before = inventory(HERE)
        cls.lock = json.loads(A.DEFAULT_LOCK.read_text())
        cls.files = {p: (cls.root / p).read_bytes() for p in cls.lock['files']}
        cls.adapter = A.StandardsAdapter(cls.root)

    @classmethod
    def tearDownClass(cls):
        if inventory(cls.root) != cls.before:
            raise AssertionError('upstream snapshot bytes/file inventory changed')
        if inventory(HERE) != cls.adapter_before:
            raise AssertionError('adapter files changed or bytecode was created')

    def run_cli(self, *args, env=None):
        return subprocess.run([sys.executable, '-I', '-B', str(HERE / 'standards_adapter.py'),
                               '--root', str(self.root), *args], capture_output=True,
                              text=True, check=False, env=env, timeout=10)

    def changed_read(self, changed):
        real = A._read
        def read(path):
            try:
                rel = str(Path(path).relative_to(self.root))
            except ValueError:
                return real(path)
            if rel in changed:
                if changed[rel] is None:
                    raise A.AdapterError('Missing/unreadable expected file: ' + rel)
                return changed[rel]
            return real(path)
        return mock.patch.object(A, '_read', side_effect=read)

    def test_exact_lock_and_95_records(self):
        self.assertEqual(hashlib.sha256(A.DEFAULT_LOCK.read_bytes()).hexdigest(), A.LOCK_SHA256)
        result = self.adapter.query()
        self.assertEqual(result['count'], 95)
        self.assertEqual(result['commit'], '19d586bb53cb452325d815313a895a1dfafa868b')
        self.assertEqual(sum(r['upstream_calc_eligibility']['usable'] for r in result['results']), 44)
        self.assertTrue(all(not r['engineering_release'] and not r['project_applicability']['approved']
                            for r in result['results']))
        self.assertEqual(result['formula_input_metadata_check']['status'], 'PASS')
        self.assertFalse(result['formula_input_metadata_check']['global_input_guard'])

    def test_current_corrected_record_identities(self):
        expected = {
            'F-STR-002': 'sigma_theta_inner = p * (b^2 + a^2) / (b^2 - a^2)',
            'F-FLW-001': 'Kv = A * 3600 * sqrt(2 * 1e5 / (zeta * rho_ref))',
            'F-DRV-002': 'F_hand = 1000 * T_drive / L_arm',
            'F-FLW-002': 'Cv_US = 1.156 * Kv',
            'F-MAT-001': 'utilization = sigma_max / sigma_allow',
            'F-BOLT-001': 'sigma_pressure_nominal = p * A_effective / (n * As)',
        }
        for eid, formula in expected.items():
            with self.subTest(eid=eid):
                hit = self.adapter.query(record_id=eid)['results'][0]
                self.assertEqual(hit['record']['expression']['canonical'], formula)
                self.assertEqual(hit['provenance']['id'], eid)
        hit = self.adapter.query(record_id='F-FLW-001')['results'][0]
        check = hit['research_consistency']
        self.assertEqual(check['consistency'], 'CONSISTENT_AT_RECORDED_SAMPLE')
        self.assertAlmostEqual(check['witness']['canonical_Kv_m3_h'], 652.9677711243186)
        self.assertAlmostEqual(check['witness']['inverse_zeta'], 6)
        self.assertEqual(hit['source_status'], 'UNVERIFIED_CLAUSE')
        self.assertFalse(hit['upstream_calc_eligibility']['usable'])

    def test_13_flange_tables_and_2_related_derivations_quarantined(self):
        records = self.adapter.query()['results']
        blocked = [r for r in records if r['upstream_calc_eligibility']['block_reason'] == 'FLANGE_ENGINEERING_USE_SUSPENDED']
        self.assertEqual(len(blocked), 15)
        tables = [r for r in blocked if r['record']['id'].startswith('D-')]
        self.assertEqual(len(tables), 13)
        self.assertTrue(any(r['source_status'] == 'VERIFIED_CLAUSE' for r in tables))
        self.assertTrue(all(not r['upstream_calc_eligibility']['usable'] for r in blocked))
        for r in records:
            if r['source_status'] != 'VERIFIED_CLAUSE':
                self.assertFalse(r['upstream_calc_eligibility']['usable'])

    def test_current_card_nine_hold_27_empty_limits(self):
        result = self.adapter.assess_acceptance()
        card = result['acceptance']
        self.assertEqual(card['card_id'], 'AC-VALVE-001')
        self.assertEqual(card['card_sha256'], 'd9b67c1faa7770c4c683cba94b6800a87b5252b560f16c5fcf51b3a24b511b91')
        self.assertEqual(card['status'], 'HOLD')
        self.assertEqual([c['finding'] for c in card['checks']], ['HOLD'] * 9)
        self.assertEqual(len(result['pending_numeric_limits']), 27)
        self.assertTrue(all(x[k] is None for x in result['pending_numeric_limits']
                            for k in ('value', 'source_locator', 'approval_record')))
        self.assertFalse(result['engineering_release'])
        self.assertFalse(result['card_binding']['configuration_hash_authentication'])

    def test_returned_objects_are_detached(self):
        result = self.adapter.query(record_id='F-FLW-001')
        result['results'][0]['record']['expression']['canonical'] = 'wrong'
        result['results'][0]['upstream_calc_eligibility']['usable'] = True
        result['formula_input_metadata_check']['status'] = 'BROKEN'
        card = self.adapter.assess_acceptance()
        card['acceptance']['checks'][0]['finding'] = 'PASS'
        card['pending_numeric_limits'][0]['value'] = 123
        self.test_current_corrected_record_identities()
        self.test_current_card_nine_hold_27_empty_limits()
        self.assertEqual(self.adapter.query()['formula_input_metadata_check']['status'], 'PASS')

    def test_all_real_upstream_guards_are_called(self):
        real_load = A.load_modules
        calls = {}
        def traced(files):
            modules = real_load(files)
            for name, method in [('kb_entries', 'entry_usable_for_calc'), ('flw001_contract', 'assess'),
                                 ('valve_completion_contract', 'check_entry'), ('formula_input_contract', 'validate'),
                                 ('acceptance_card', 'assess'), ('acceptance_card', 'validate_valve_variant'),
                                 ('acceptance_card', 'protocol_issues'), ('source_closure_contract', 'check_documented_requirements')]:
                original = getattr(modules[name], method)
                spy = mock.Mock(wraps=original)
                setattr(modules[name], method, spy)
                calls[name + '.' + method] = spy
            return modules
        with mock.patch.object(A, 'load_modules', side_effect=traced):
            adapter = A.StandardsAdapter(self.root)
            adapter.query(record_id='F-FLW-001')
            adapter.assess_acceptance()
        self.assertGreaterEqual(calls['kb_entries.entry_usable_for_calc'].call_count, 95)
        self.assertEqual(calls['valve_completion_contract.check_entry'].call_count, 95)
        self.assertEqual(calls['acceptance_card.protocol_issues'].call_count, 9)
        for key in ['flw001_contract.assess', 'formula_input_contract.validate', 'acceptance_card.assess',
                    'acceptance_card.validate_valve_variant', 'source_closure_contract.check_documented_requirements']:
            self.assertEqual(calls[key].call_count, 1, key)

    def test_each_missing_or_drifted_dependency_fails_before_execution(self):
        for rel, raw in self.files.items():
            for replacement in (None, raw + b'\n'):
                with self.subTest(rel=rel, missing=replacement is None), self.changed_read({rel: replacement}), \
                        mock.patch.object(A, 'load_modules') as run:
                    with self.assertRaises(A.AdapterError):
                        A.StandardsAdapter(self.root)
                    run.assert_not_called()

    def test_manifest_rehash_cannot_bless_drift(self):
        for field, value in [('commit', '7eda528a8795b8fbd850d6d35ac67e198de5810a'), ('repository', 'other')]:
            lock = copy.deepcopy(self.lock)
            lock[field] = value
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / 'lock.json'; p.write_text(json.dumps(lock))
                with self.assertRaisesRegex(A.AdapterError, 'Production lock'):
                    A.StandardsAdapter(self.root, p)
        lock = copy.deepcopy(self.lock)
        lock['files']['tools/kb_entries.py'] = hashlib.sha256(b'raise RuntimeError("malicious")').hexdigest()
        lock['files']['kb/formulas/seed_core.json'] = hashlib.sha256(b'[]').hexdigest()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'lock.json'; p.write_text(json.dumps(lock))
            with self.assertRaisesRegex(A.AdapterError, 'Production lock'):
                A.StandardsAdapter(self.root, p)

    def test_old_formula_and_cross_variant_rejected_at_real_entry(self):
        core = json.loads(self.files['kb/formulas/seed_core.json'])
        next(e for e in core if e['id'] == 'F-FLW-001')['expression']['canonical'] += ' / 1000'
        card = json.loads(self.files[A.CARD_PATH])
        card['configuration']['source_bound_duty'] = {
            'variant_id': '522-35.4179', 'medium': '28% calcium chloride solution',
            'temperature_degC': [-40, 50], 'drawing_note': 5}
        variants = {'kb/formulas/seed_core.json': json.dumps(core).encode(),
                    A.CARD_PATH: json.dumps(card).encode()}
        for rel, raw in variants.items():
            with self.subTest(rel=rel), self.changed_read({rel: raw}), self.assertRaisesRegex(A.AdapterError, 'SHA256 mismatch'):
                A.StandardsAdapter(self.root)
        rules = A.load_modules(self.files)
        entries = {eid: record for eid, (record, _) in A._entries(self.files).items()}
        with self.assertRaisesRegex(ValueError, 'variant duty mismatch'):
            rules['acceptance_card'].assess(card, entries)
        # A renamed card is also rejected by production byte identity, not treated
        # as an arbitrary-candidate validator (upstream special guards use the ID).
        card['id'] = 'OTHER'
        with self.changed_read({A.CARD_PATH: json.dumps(card).encode()}), self.assertRaises(A.AdapterError):
            A.StandardsAdapter(self.root)

    def test_explicit_use_flags_are_not_promoted(self):
        rules = A.load_modules(self.files)
        baseline = {'id': 'F-SYNTHETIC', 'evidence': {'status': 'VERIFIED_CLAUSE'}}
        for flag in [{'record_only': True}, {'engineering_use_prohibited': True},
                     {'record_only': 'false'}, {'engineering_use_prohibited': 0}]:
            with self.subTest(flag=flag):
                self.assertFalse(rules['kb_entries'].entry_usable_for_calc(dict(baseline, **flag)))
        self.assertFalse(rules['kb_entries'].entry_usable_for_calc({'id': 'F-SYNTHETIC', 'evidence': {'status': 'CONFLICT'}}))

    def test_verified_bytes_not_reread_after_validation(self):
        real = A._read
        seen = {}
        def once(path):
            key = str(path)
            seen[key] = seen.get(key, 0) + 1
            if seen[key] != 1:
                raise AssertionError('input reread after validation: ' + key)
            return real(path)
        with mock.patch.object(A, '_read', side_effect=once):
            adapter = A.StandardsAdapter(self.root)
            adapter.query(); adapter.assess_acceptance()
        self.assertEqual(len(seen), 21)

    def test_upstream_module_poison_and_pyc_are_not_used(self):
        poison = types.ModuleType('poison')
        poison.entry_usable_for_calc = lambda e: True
        names = A._runtime.MODULES
        with mock.patch.dict(sys.modules, {name: poison for name in names}):
            adapter = A.StandardsAdapter(self.root)
            self.assertFalse(adapter.query(record_id='D-GOST1536-PN063')['results'][0]['upstream_calc_eligibility']['usable'])
            self.assertEqual(adapter.assess_acceptance()['acceptance']['status'], 'HOLD')
        with tempfile.TemporaryDirectory() as td:
            for name in names:
                Path(td, name + '.py').write_text('raise RuntimeError("not trusted")')
                Path(td, name + '.pyc').write_bytes(b'not trusted bytecode')
            env = dict(os.environ, PYTHONPATH=td)
            result = self.run_cli('--id', 'F-FLW-001', env=env)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_yaml_impersonation_is_rejected(self):
        poison = types.ModuleType('yaml')
        poison.__spec__ = importlib.util.spec_from_file_location('yaml', '/tmp/untrusted_yaml.py')
        poison.__file__ = '/tmp/untrusted_yaml.py'
        with mock.patch.dict(sys.modules, yaml=poison), self.assertRaisesRegex(A.AdapterError, 'untrusted yaml'):
            A.StandardsAdapter(self.root)

    def test_actual_cli_query_acceptance_invalid(self):
        query = self.run_cli('--id', 'F-FLW-001')
        self.assertEqual(query.returncode, 0, query.stderr)
        self.assertEqual(json.loads(query.stdout)['count'], 1)
        acceptance = self.run_cli('--acceptance')
        self.assertEqual(acceptance.returncode, 1, acceptance.stderr)
        self.assertEqual(json.loads(acceptance.stdout)['acceptance']['status'], 'HOLD')
        invalid = self.run_cli('--acceptance', '--id', 'F-FLW-001')
        self.assertEqual(invalid.returncode, 2)
        self.assertEqual(invalid.stdout, '')
        self.assertEqual(json.loads(invalid.stderr)['status'], 'INVALID')

    def test_actual_cli_nonregular_oversize_and_loop_fail_without_hanging(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            fifo = d / 'fifo'; os.mkfifo(fifo)
            huge = d / 'huge'
            with huge.open('wb') as stream:
                stream.truncate(A.MAX_INPUT_BYTES + 1)
            loop = d / 'loop'; loop.symlink_to(loop)
            for target in [fifo, huge, d, loop]:
                with self.subTest(manifest=str(target)):
                    proc = self.run_cli('--manifest', str(target))
                    self.assertEqual(proc.returncode, 2, proc.stderr)
                    self.assertEqual(proc.stdout, '')
                    self.assertEqual(json.loads(proc.stderr)['status'], 'INVALID')
            # Snapshot loop and a FIFO in the first expected snapshot path.
            snapshot = d / 'snapshot'
            first = snapshot / sorted(self.files)[0]
            first.parent.mkdir(parents=True)
            os.mkfifo(first)
            for root in [loop, snapshot]:
                with self.subTest(root=str(root)):
                    proc = self.run_cli('--root', str(root))
                    self.assertEqual(proc.returncode, 2, proc.stderr)
                    self.assertEqual(proc.stdout, '')
                    self.assertEqual(json.loads(proc.stderr)['status'], 'INVALID')

    def test_old_snapshot_is_not_current(self):
        old = os.environ.get('STANDARDS_KB_OLD_SNAPSHOT')
        if not old:
            self.skipTest('set STANDARDS_KB_OLD_SNAPSHOT for real old-snapshot rejection')
        with self.assertRaises(A.AdapterError):
            A.StandardsAdapter(old)
        proc = subprocess.run([sys.executable, '-I', '-B', str(HERE / 'standards_adapter.py'),
                               '--root', old, '--id', 'D-GOST1536-PN063'],
                              capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, '')
        self.assertFalse(json.loads(proc.stderr)['engineering_release'])


if __name__ == '__main__':
    unittest.main()
