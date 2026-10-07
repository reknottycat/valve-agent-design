import copy
import json
from pathlib import Path
import tempfile
import unittest
import flow_verify as gate

class GateTests(unittest.TestCase):
    def setUp(self):
        self.manifest=json.loads(gate.MANIFEST.read_text())
        self.native=gate.REPO/'runs/20261006/CALCULATIONS/R1/sources_new/MESH_V2/stage_evidence/native_final.log'

    def test_all_pinned_sources_and_property_inputs(self):
        self.assertEqual(len(gate.source_check(self.manifest)),13)
        plan=json.loads((gate.REPO/self.manifest['sources'][0]['path']).read_text())
        for key,value in plan['selected_study_property_state'].items():
            self.assertEqual(self.manifest['selected'][key],value)
        for key,value in plan['cases'][0].items():
            self.assertEqual(self.manifest['selected'][key],value)

    def test_tampered_source_cannot_be_adopted(self):
        entry=self.manifest['sources'][0]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/entry['path'];p.parent.mkdir(parents=True)
            p.write_bytes((gate.REPO/entry['path']).read_bytes()+b' ')
            with self.assertRaisesRegex(RuntimeError,'Fixed source changed'):
                gate.source_check({'sources':[entry]},Path(td))

    def test_changed_selected_duty_cannot_reuse_valid_source_hashes(self):
        changed=copy.deepcopy(self.manifest)
        changed['selected']['inlet_fixed_face_speed_m_s']*=2
        with self.assertRaisesRegex(RuntimeError,'Selected case differs'):
            gate.source_check(changed)

    def test_original_warning_log_is_accepted_with_warning(self):
        result=gate.check_mesh_log(self.native)
        self.assertEqual(result['status'],'PASS_WITH_RETAINED_WARNINGS')
        self.assertEqual(result['metrics']['faces_over_70_degrees'],54)

    def test_quality_drift_or_old_failure_is_rejected(self):
        original=self.native.read_text()
        for before,after in [('faces: 54.','faces: 55.'),('77.471484007812791','78.1'),
                             ('0.0010289095826444307','0.0009'),('Mesh OK.','Failed 1 mesh checks.'),
                             ('OPENFOAM=1912','OPENFOAM=2506'),('cells:            411099','cells:            411100')]:
            with self.subTest(after=after), tempfile.TemporaryDirectory() as td:
                p=Path(td)/'log';p.write_text(original.replace(before,after))
                with self.assertRaises(RuntimeError):gate.check_mesh_log(p)

    def test_nonfinite_and_blown_up_final_fields_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);out=root/'5000';out.mkdir()
            for value in ['nan','1']:
                (out/'U').write_text('FoamFile {format ascii;} internalField uniform ('+value+' 0 0);')
                with self.assertRaises(RuntimeError):gate.finite_fields(root,self.manifest)

    def test_zero_or_missing_final_solution_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'0').mkdir()
            with self.assertRaisesRegex(RuntimeError,'No final solved fields'):gate.finite_fields(root,self.manifest)

if __name__=='__main__':unittest.main()
