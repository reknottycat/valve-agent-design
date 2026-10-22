"""Optional actual-byte integration test; never silently substitutes synthetic data."""
import json
import os
from pathlib import Path
import sys
import unittest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from standards_adapter import StandardsAdapter


@unittest.skipUnless(os.environ.get('STANDARDS_KB_SNAPSHOT'), 'Set STANDARDS_KB_SNAPSHOT to independently retrieved pinned snapshot')
class PinnedRecordTests(unittest.TestCase):
    def test_original_record_and_evidence_preserved(self):
        root = Path(os.environ['STANDARDS_KB_SNAPSHOT'])
        original = json.loads((root / 'kb/data/ГОСТ_1536-76.json').read_bytes())
        expected = next(e for e in original['entries'] if e['id'] == 'D-GOST1536-PN063')
        adapter = StandardsAdapter(root, BASE / 'pinned-gost1536.manifest.json')
        response = adapter.query(record_id='D-GOST1536-PN063')
        self.assertEqual(response['count'], 1)
        record = response['results'][0]['record']
        self.assertEqual(record, expected)
        self.assertEqual(record['evidence']['grade'], 'E1')
        self.assertEqual(record['evidence']['status'], 'UNVERIFIED_CLAUSE')
        self.assertNotIn('As', record['row_keys']['200'])
        self.assertFalse(response['engineering_release'])
        self.assertFalse(response['results'][0]['engineering_release'])
        self.assertEqual(adapter.query()['count'], len(original['entries']))
