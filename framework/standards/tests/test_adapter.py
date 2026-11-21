import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from standards_adapter import AdapterError, COMMIT, REPOSITORY, StandardsAdapter, main


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'kb/formulas/example.json'
        self.path.parent.mkdir(parents=True)
        self.manifest = self.root / 'manifest.json'
        self.entry = {'id': 'F-TEST-001', 'source': {'clause': 'synthetic', 'body_status': 'PAYWALL'},
                      'applicability': {'not_valid_when': ['real engineering']},
                      'evidence': {'grade': 'E1', 'status': 'UNVERIFIED_CLAUSE'}}
        self.write([self.entry])

    def write(self, obj=None, raw=None, extra=None):
        self.path.write_text(json.dumps(obj) if raw is None else raw)
        files = {'kb/formulas/example.json': hashlib.sha256(self.path.read_bytes()).hexdigest()}
        files.update(extra or {})
        self.manifest.write_text(json.dumps({'repository': REPOSITORY, 'commit': COMMIT,
                                           'scope': 'selected_files', 'files': files}))

    def load(self):
        return StandardsAdapter(self.root, self.manifest)

    def test_e1_research_preserves_complete_record(self):
        result = self.load().query('synthetic')['results'][0]
        self.assertEqual(result['record'], self.entry)
        self.assertTrue(result['research_retrievable'])
        self.assertFalse(result['engineering_release'])
        self.assertEqual(result['provenance']['commit'], COMMIT)

    def test_every_grade_and_clause_status_remains_research_only(self):
        for grade in ('E0', 'E1', 'E2', 'E3'):
            for status in ('VERIFIED_CLAUSE', 'UNVERIFIED_CLAUSE', 'PENDING_VERIFICATION', 'CONFLICT', 'SUPERSEDED'):
                with self.subTest(grade=grade, status=status):
                    self.entry['evidence'] = {'grade': grade, 'status': status}
                    self.write([self.entry])
                    result = self.load().query()['results'][0]
                    self.assertEqual(result['record']['evidence'], self.entry['evidence'])
                    self.assertFalse(result['engineering_release'])

    def test_output_mutation_cannot_promote_internal_record(self):
        adapter = self.load()
        adapter.query()['results'][0]['record']['evidence']['grade'] = 'E3'
        self.assertEqual(adapter.query()['results'][0]['record']['evidence']['grade'], 'E1')

    def test_duplicate_ids_fail(self):
        self.write([self.entry, self.entry])
        with self.assertRaisesRegex(AdapterError, 'Duplicate record ID'):
            self.load()

    def test_invalid_json_and_duplicate_keys_fail(self):
        for raw in ('[', '[NaN]', '[Infinity]', '{"entries":[],"entries":[]}'):
            with self.subTest(raw=raw):
                self.write(raw=raw)
                with self.assertRaises(AdapterError):
                    self.load()

    def test_empty_or_bad_shapes_fail(self):
        for obj in ([], {}, [None], [{'id': 'F-TEST-001'}]):
            with self.subTest(obj=obj):
                self.write(obj)
                with self.assertRaises(AdapterError):
                    self.load()

    def test_missing_file_fails(self):
        self.path.unlink()
        with self.assertRaisesRegex(AdapterError, 'Missing/unreadable'):
            self.load()

    def test_hash_mismatch_fails(self):
        self.path.write_text('[]')
        with self.assertRaisesRegex(AdapterError, 'SHA256 mismatch'):
            self.load()

    def test_pin_mismatch_fails(self):
        manifest = json.loads(self.manifest.read_text())
        manifest['commit'] = 'main'
        self.manifest.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(AdapterError, 'pinned upstream'):
            self.load()

    def test_missing_expected_second_file_does_not_return_partial_results(self):
        self.write([self.entry], extra={'kb/parameters/missing.json': '0' * 64})
        with self.assertRaises(AdapterError):
            self.load()

    def test_missing_or_invalid_grade_status_fails(self):
        for ev in ({'grade': 'E1'}, {'status': 'VERIFIED_CLAUSE'}, {'grade': [], 'status': 'VERIFIED_CLAUSE'}):
            self.entry['evidence'] = ev
            self.write([self.entry])
            with self.assertRaises(AdapterError):
                self.load()

    def test_path_escape_fails(self):
        self.write([self.entry], extra={'../outside.json': '0' * 64})
        with self.assertRaises(AdapterError):
            self.load()

    def test_data_wrapper_preserved(self):
        self.path = self.root / 'kb/data/example.json'
        self.path.parent.mkdir()
        self.entry['id'] = 'D-TEST-001'
        self.path.write_text(json.dumps({'entries': [self.entry]}))
        self.manifest.write_text(json.dumps({'repository': REPOSITORY, 'commit': COMMIT, 'scope': 'selected_files',
            'files': {'kb/data/example.json': hashlib.sha256(self.path.read_bytes()).hexdigest()}}))
        self.assertEqual(self.load().query()['results'][0]['record'], self.entry)

    def test_no_hit_is_not_release(self):
        result = self.load().query(record_id='F-ABSENT-001')
        self.assertEqual(result['results'], [])
        self.assertFalse(result['engineering_release'])

    def test_nested_upstream_release_cannot_override_adapter(self):
        self.entry['engineering_release'] = True
        self.entry['evidence'] = {'grade': 'E3', 'status': 'VERIFIED_CLAUSE'}
        self.write([self.entry])
        result = self.load().query()
        self.assertTrue(result['results'][0]['record']['engineering_release'])
        self.assertFalse(result['results'][0]['engineering_release'])
        self.assertFalse(result['engineering_release'])

    def test_duplicate_ids_across_files_fail(self):
        other = self.path.parent / 'second.json'
        other.write_text(json.dumps([self.entry]))
        self.write([self.entry], extra={'kb/formulas/second.json': hashlib.sha256(other.read_bytes()).hexdigest()})
        with self.assertRaisesRegex(AdapterError, 'Duplicate record ID'):
            self.load()

    def test_empty_manifest_fails(self):
        manifest = json.loads(self.manifest.read_text())
        manifest['files'] = {}
        self.manifest.write_text(json.dumps(manifest))
        with self.assertRaises(AdapterError):
            self.load()

    def test_symlink_escape_fails(self):
        with tempfile.TemporaryDirectory() as outside:
            other = Path(outside) / 'external.json'
            other.write_bytes(self.path.read_bytes())
            self.path.unlink()
            self.path.symlink_to(other)
            with self.assertRaisesRegex(AdapterError, 'escapes snapshot'):
                self.load()

    def test_cli_failure_nonzero_without_stdout(self):
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO
        self.path.unlink()
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(['--root', str(self.root), '--manifest', str(self.manifest)])
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), '')
        self.assertEqual(json.loads(err.getvalue())['results'], [])


if __name__ == '__main__':
    unittest.main()
