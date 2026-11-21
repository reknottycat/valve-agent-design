import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'framework'))
from evidence_contract import validate


class ContractTests(unittest.TestCase):
    def base(self):
        return dict(artifact_id='synthetic',source='fixture',scope='local',
                    verification='text_read',claim='reported_observation',
                    input_refs=['fixture'],tool_version='test-1')
    def test_text_observation_allowed(self):
        self.assertEqual(validate(self.base()), [])
    def test_missing_identity(self):
        r=self.base();del r['source'];self.assertIn('missing:source', validate(r))
    def test_no_scope_promotion(self):
        r=self.base();r['claim_scope']='full_valve';self.assertTrue(validate(r))
    def test_no_bytes_from_text(self):
        r=self.base();r['claim']='byte_identity';self.assertTrue(validate(r))
    def test_gate_needs_evidence(self):
        r=self.base();r['gate_status']='pass';self.assertTrue(validate(r))
    def test_unknown_blocks_only_named_gate(self):
        r=self.base();r.update(gate_status='pass',gate_source='research threshold',observations=[1],unknowns_required_for_gate=['temperature']);self.assertTrue(validate(r))
    def test_scoped_research_gate(self):
        r=self.base();r.update(gate_status='pass',gate_source='research threshold',observations=[1]);self.assertEqual(validate(r),[])
    def test_no_manufacturing_inference(self):
        r=self.base();r['claim']='manufacturing_release';self.assertTrue(validate(r))

if __name__ == '__main__':unittest.main()
