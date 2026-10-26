"""Isolated candidate arithmetic/binding tests; never standards or engineering validation."""
import hashlib
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
SOURCE = json.loads((ROOT / 'source-records.json').read_text())

def entry(eid, layer='formulas'):
    return next(r['record'] for r in SOURCE['records']
                if r['id'] == eid and r['path'].startswith('kb/' + layer + '/'))

class SourceAndCandidateChecks(unittest.TestCase):
    def test_source_pin_and_fingerprints(self):
        self.assertEqual(SOURCE['commit'], '2937b5901b26d02456b95545ab2c1a059676e82a')
        for r in SOURCE['records']:
            b = json.dumps(r['record'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
            self.assertEqual(hashlib.sha256(b).hexdigest(), r['canonical_record_sha256'])

    def test_original_status_preserved(self):
        for r in SOURCE['records']:
            if r['path'].startswith('kb/formulas/'):
                self.assertEqual(r['record']['evidence']['status'], 'UNVERIFIED_CLAUSE')
                self.assertEqual(r['record']['evidence']['grade'], 'E1')

    def test_lame_original_conflict_and_candidate_algebra(self):
        r = entry('F-STR-002')
        self.assertEqual(r['expression']['canonical'], 'sigma_theta_inner = p * (b^2 + a^2) / (b^2 - a^2)')
        self.assertEqual(r['expression']['rearranged_forms'][0], 'sigma_theta_inner = p * (1 + a^2 / (b^2 - a^2))')
        self.assertEqual(r['usage']['sample']['inputs'], {'p': 1.0, 'a': 100.0, 'b': 112.0})
        p, a, b = 1.0, 100.0, 112.0
        canonical = p * (b*b + a*a) / (b*b - a*a)
        old_rearrangement = p * (1 + a*a / (b*b - a*a))
        candidate_rearrangement = p * (1 + 2*a*a / (b*b - a*a))
        self.assertAlmostEqual(canonical, 8.861635220125786)
        self.assertNotAlmostEqual(canonical, old_rearrangement)
        self.assertNotAlmostEqual(canonical, 1.1299)
        self.assertAlmostEqual(canonical, candidate_rearrangement)

    def test_lame_scale_unit_invariance(self):
        for a, b in [(100.0, 112.0), (0.100, 0.112)]:
            self.assertAlmostEqual((b*b+a*a)/(b*b-a*a), 8.861635220125786)
        # Matching length units cancel; p and resulting stress share MPa.

    def test_flow_original_conflict_candidate_unit_chain(self):
        r = entry('F-FLW-001')
        self.assertEqual(r['expression']['canonical'], 'Kv = A * 3600 * sqrt(2 * 1e5 / (zeta * rho)) / 1000')
        self.assertEqual(r['usage']['sample']['inputs'], {'D_mm': 200.0, 'zeta': 6.0, 'rho': 1000.0})
        area_m2 = math.pi * (200 / 1000)**2 / 4
        velocity_m_s = math.sqrt(2 * 1e5 / (6 * 1000))
        flow_m3_h = area_m2 * velocity_m_s * 3600
        self.assertAlmostEqual(flow_m3_h, 652.9677711243186)
        self.assertAlmostEqual(flow_m3_h/1000, 0.6529677711243186)
        self.assertEqual(round(flow_m3_h), 653)
        # This is the stated water-reference sample only, not a universal Kv model.

    def test_hand_force_candidate_result_binding(self):
        r = entry('F-DRV-002')
        m = entry('F-DRV-002', 'ontology')
        self.assertEqual(r['expression']['solved_for'], 'F_hand')
        self.assertEqual(m['result_quantity'], 'Q:DRIVE:LEVER_RATIO')
        self.assertEqual(m['variables']['F_hand'], 'Q:DRIVE:HAND_FORCE')
        self.assertNotEqual(m['result_quantity'], m['variables'][r['expression']['solved_for']])
        # Candidate change is result_quantity -> existing Q:DRIVE:HAND_FORCE.
        self.assertEqual(m['variables'][r['expression']['solved_for']], 'Q:DRIVE:HAND_FORCE')

    def test_cv_candidate_result_binding(self):
        r = entry('F-FLW-002')
        m = entry('F-FLW-002', 'ontology')
        self.assertEqual(r['expression']['solved_for'], 'Cv_US')
        self.assertEqual(m['result_quantity'], 'Q:FLOW:FLOW_COEFFICIENT_KV')
        self.assertEqual(m['variables']['Cv_US'], 'Q:FLOW:FLOW_COEFFICIENT_CV')

    def test_seal_symbol_discrepancy_remains_explicit(self):
        r = entry('F-SEAL-002')
        self.assertIn('w_seal', r['expression']['rearranged_forms'][0])
        self.assertIn('w_seat', {v['symbol'] for v in r['variables']})
        self.assertNotIn('w_seal', {v['symbol'] for v in r['variables']})

if __name__ == '__main__':
    unittest.main()
