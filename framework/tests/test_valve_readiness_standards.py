"""Synthetic read-only wiring tests; no fixture is physical or standards evidence."""
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
spec = importlib.util.spec_from_file_location('readiness_under_test', CONSUMER)
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
ROOT = os.environ.get('VALVE_STANDARDS_ROOT')
OLD_ROOT = os.environ.get('VALVE_OLD_STANDARDS_ROOT')


def manifest(root=ROOT, record='F-FLW-001', use='RESEARCH_REFERENCE'):
    return {'requested_action': 'inspect', 'standards': {
        'root': root, 'configuration_id': '522-35.4179',
        'references': [{'id': record, 'use': use}]}}


def inventory(root):
    root = Path(root)
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def cli(raw, *args):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'input.json'
        path.write_bytes(raw)
        return subprocess.run([sys.executable, '-I', '-B', str(CONSUMER), str(path), *args],
                              capture_output=True, text=True, timeout=15)


class ContractTests(unittest.TestCase):
    def test_legacy_inspect_is_explicitly_unchecked(self):
        result = R.audit({})
        self.assertTrue(result['preflight_pass'])
        self.assertEqual(result['standards']['status'], 'NOT_CHECKED')
        self.assertIsNone(result['standards']['source_use_pass'])
        self.assertFalse(result['engineering_release'])

    def test_solve_missing_declaration_is_incomplete(self):
        result = R.audit({'requested_action': 'solve'})
        self.assertEqual(result['standards']['status'], 'INCOMPLETE')
        self.assertFalse(result['requested_checks_pass'])

    def test_partial_and_unknown_fields_rejected(self):
        for value in [None, {}, {'root': '/missing'}, dict(manifest('x')['standards'], typo=True)]:
            with self.subTest(value=value), self.assertRaises(R.ReadinessError):
                R.audit({'standards': value})
        for meta in [{'standards_root': '/missing'}, {'domain_scope': ''}, {'execution_budget': None},
                     {'execution_budget': {'cells': True}}, {'execution_budget': {'cells': -1}},
                     {'source_note': []}, {1: 'x', 'unexpected': 'y'}, {'domain_scope': ('x',)},
                     {'domain_scope': float('nan')}, {'domain_scope': 'x' * (4 * 1024 * 1024)}]:
            with self.subTest(meta=str(meta)[:80]), self.assertRaises(R.ReadinessError):
                R.audit(meta)

    def test_bool_strings_do_not_pass(self):
        for name in ('boundary_conditions_verified', 'mesh_quality_pass', 'milestone_complete', 'pressure_stability_pass'):
            result = R.audit({name: 'true'})
            self.assertFalse(result['preflight_pass'])
            self.assertIn('INVALID_BOOLEAN:' + name, result['errors'])

    def test_refs_require_known_use_unique_explicit_ids(self):
        for refs in [[], [{'id': 'F-FLW-001'}], [{'id': 'F-FLW-001', 'use': True}],
                     [{'id': 'F-FLW-001', 'use': 'calculate'}],
                     [{'id': 'F-FLW-001', 'use': 'RESEARCH_REFERENCE'}] * 2]:
            meta = manifest('missing'); meta['standards']['references'] = refs
            with self.subTest(refs=refs), self.assertRaises(R.ReadinessError):
                R.audit(meta)

    def test_mismatched_variant_never_assesses_base(self):
        meta = manifest('missing'); meta['standards']['configuration_id'] += '-02'
        result = R.audit(meta)
        self.assertFalse(result['requested_checks_pass'])
        self.assertEqual(result['standards']['acceptance']['status'], 'NOT_CHECKED')
        for field in ('medium', 'variant_id', 'duty'):
            altered = manifest('missing'); altered['standards'][field] = 'brine'
            with self.subTest(field=field), self.assertRaises(R.ReadinessError):
                R.audit(altered)

    def test_cli_malformed_json_fail_closed(self):
        for raw in [b'not json', b'[]', b'{"standards":null}', b'{"a":1,"a":2}',
                    b'{"domain_scope":NaN}', b'{"domain_scope":1e999}', b'\xff',
                    b' ' * (4 * 1024 * 1024 + 1)]:
            with self.subTest(raw=raw[:60]):
                run = cli(raw)
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertEqual(json.loads(run.stderr)['status'], 'INVALID')

    def test_fifo_and_unsafe_case_paths_reject_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); fifo = root / 'fifo'; os.mkfifo(fifo)
            run = subprocess.run([sys.executable, '-I', '-B', str(CONSUMER), str(fifo)],
                                 capture_output=True, text=True, timeout=5)
            self.assertEqual(run.returncode, 2)
            (root / '0').mkdir(); (root / '0/U').symlink_to(fifo)
            with self.assertRaises(R.ReadinessError):
                R.audit({'requested_action': 'solve'}, root)
            (root / '0/U').unlink(); (root / '0/U').symlink_to('/etc/passwd')
            with self.assertRaises(R.ReadinessError):
                R.audit({'requested_action': 'solve'}, root)
            (root / '0/U').unlink(); (root / '0/U').write_bytes(b'x' * (4 * 1024 * 1024 + 1))
            # Large existence-only files remain compatible with the old preflight.
            result = R.audit({'requested_action': 'solve'}, root)
            self.assertNotIn('MISSING_FILE:0/U', result['errors'])
            (root / 'constant/polyMesh').mkdir(parents=True)
            (root / 'constant/polyMesh/points').write_bytes(b'x' * (4 * 1024 * 1024 + 1))
            result = R.audit({'requested_action': 'solve'}, root)
            self.assertNotIn('MISSING_MESH_FILE:points', result['errors'])
            (root / 'system').mkdir()
            (root / 'system/fvSolution').write_bytes(b'x' * (4 * 1024 * 1024 + 1))
            with self.assertRaises(R.ReadinessError):
                R.audit({'requested_action': 'solve'}, root)

    def test_import_is_read_only(self):
        before = inventory(CONSUMER.parents[1])
        with tempfile.TemporaryDirectory() as directory:
            run = subprocess.run([sys.executable, '-I', '-B', '-c',
                "import importlib.util; s=importlib.util.spec_from_file_location('r', " + repr(str(CONSUMER)) +
                "); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)"],
                cwd=directory, capture_output=True, text=True, timeout=5)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])
        self.assertEqual(before, inventory(CONSUMER.parents[1]))


@unittest.skipUnless(ROOT, 'Set VALVE_STANDARDS_ROOT to the exact current external selected-file snapshot')
class CurrentIntegration(unittest.TestCase):
    def test_current_nine_hold_twentyseven_null_and_quarantine(self):
        before = inventory(ROOT)
        result = R.audit(manifest())
        standards = result['standards']
        self.assertEqual(standards['status'], 'CHECKED')
        self.assertEqual(standards['acceptance']['status'], 'HOLD')
        self.assertEqual(len(standards['acceptance']['checks']), 9)
        self.assertTrue(all(row['finding'] == 'HOLD' for row in standards['acceptance']['checks']))
        self.assertEqual(len(standards['pending_numeric_limits']), 27)
        self.assertTrue(all(row['value'] is None for row in standards['pending_numeric_limits']))
        self.assertTrue(result['requested_checks_pass'])
        self.assertFalse(standards['identity_binding']['configuration_authenticated'])
        adapter = R._adapter.StandardsAdapter(ROOT)
        entries = adapter.query()['results']
        quarantined = [row for row in entries if row['provenance']['id'].startswith(('D-', 'DV-'))]
        self.assertEqual(len(quarantined), 15)
        self.assertTrue(all(not row['upstream_calc_eligibility']['usable'] for row in quarantined))
        self.assertEqual(before, inventory(ROOT))

    def test_references_change_actual_source_use_result(self):
        for record in ('F-FLW-001', 'D-GBT15530-PN6-RF', 'DV-THERM-001'):
            for use in R.USES:
                with self.subTest(record=record, use=use):
                    result = R.audit(manifest(record=record, use=use))
                    self.assertEqual(result['requested_checks_pass'], use == 'RESEARCH_REFERENCE')
                    self.assertTrue(result['preflight_pass'])
                    self.assertFalse(result['engineering_release'])
                    self.assertFalse(result['solver_started'])
        result = R.audit(manifest(record='F-MAT-002', use='CALCULATION_SUPPORT'))
        self.assertTrue(result['standards']['source_use_pass'])
        self.assertFalse(result['standards']['project_applicability']['approved'])
        self.assertEqual(result['standards']['acceptance']['status'], 'HOLD')

    def test_unknown_record_and_bad_source_rejected(self):
        with self.assertRaises(R.ReadinessError):
            R.audit(manifest(record='F-UNKNOWN-999'))
        for root in ('/does/not/exist', '\x00'):
            with self.subTest(root=root), self.assertRaises(R.ReadinessError):
                R.audit(manifest(root=root))

    @unittest.skipUnless(OLD_ROOT, 'Set VALVE_OLD_STANDARDS_ROOT for old-snapshot rejection')
    def test_old_source_cannot_be_blessed(self):
        with self.assertRaises(R.ReadinessError):
            R.audit(manifest(root=OLD_ROOT))

    def test_real_cli_and_unchanged_case(self):
        with tempfile.TemporaryDirectory() as directory:
            case = Path(directory)
            for name in ['0/U', '0/p', 'system/controlDict', 'system/fvSchemes', 'system/fvSolution',
                         'constant/transportProperties'] + ['constant/polyMesh/' + n for n in ('points','faces','owner','neighbour','boundary')]:
                path = case / name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('synthetic fixture, not physical evidence')
            (case / 'system/fvSolution').write_text('solvers { p { solver PCG; } }')
            before = inventory(case)
            meta = manifest(); meta.update(requested_action='solve', domain_scope='synthetic',
                boundary_conditions_verified=True, mesh_stage='retained_fluid_mesh', mesh_quality_pass=True)
            for use, expected in [('RESEARCH_REFERENCE', 0), ('CALCULATION_SUPPORT', 2)]:
                meta['standards']['references'][0]['use'] = use
                run = cli(json.dumps(meta).encode(), '--case', str(case))
                self.assertEqual(run.returncode, expected, run.stderr)
                result = json.loads(run.stdout)
                self.assertTrue(result['preflight_pass'])
                self.assertFalse(result['solver_started'])
                self.assertEqual(result['standards']['acceptance']['status'], 'HOLD')
            self.assertEqual(before, inventory(case))


if __name__ == '__main__':
    unittest.main()
