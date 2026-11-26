# coding: utf-8
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

CAD = Path(__file__).resolve().parents[1]/'cad/p08-pose'
spec = importlib.util.spec_from_file_location('pose_inputs', CAD/'qualify_inputs.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


class ProductPoseInputs(unittest.TestCase):
    def test_a_final_step_and_wrong_source_are_not_an_assembly(self):
        keys = mod.pins(); raw = json.loads(mod.REPORT.read_bytes())
        for row in raw['source_manifest']['sources']:
            self.assertEqual(keys['source/'+row['file']], row['sha256'])
        self.assertIn('build_fluid_domain.py', keys); self.assertIn('INPUTS.json', keys)
        with tempfile.TemporaryDirectory() as tmp:
            w=Path(tmp); (w/'source').mkdir()
            (w/'source/disc_AGR1.step').write_bytes(b'another revision')
            (w/mod.REFERENCE).parent.mkdir(); (w/mod.REFERENCE).write_bytes(b'valid-looking name, wrong geometry')
            r=mod.qualify(w); self.assertFalse(r['originals_verified']); self.assertFalse(r['reference_step_verified'])
            self.assertEqual(r['inputs']['source/disc_AGR1.step'],'wrong_bytes'); self.assertEqual(r['inputs']['build_fluid_domain.py'],'missing')
        archived = json.loads((CAD/'source_recovery.json').read_bytes()); self.assertEqual(set(archived['inputs']),set(keys))
        self.assertEqual(archived['originals_verified'], all(v=='verified' for v in archived['inputs'].values()))

    def test_reference_measurements_match_independent_geometry_report(self):
        reference=json.loads((CAD/'measured_reference.json').read_bytes()); self.assertEqual(reference['step_sha256'],mod.pins()[mod.REFERENCE])
        historic=json.loads(mod.REPORT.read_bytes())['geometry_results']['domains']['AGR1_open_seal_omitted_proxy']
        main=historic['components'][historic['main_index']]; self.assertTrue(main['connects_both_ports'])
        self.assertTrue(math.isclose(reference['main_fluid_volume_mm3'],main['volume_mm3'],rel_tol=1e-7))
        for port,x in [('inlet',-600.),('outlet',1200.)]:
            self.assertAlmostEqual(reference['ports'][port]['center_mm'][0],x,6)
            self.assertAlmostEqual(reference['ports'][port]['area_mm2'],main[port+'_faces'][0]['area_mm2'],6)
        self.assertAlmostEqual(reference['guide_wall_distance_mm'],1.,5)
        self.assertEqual([s['fluid'] for s in reference['guide_section']], [False,True,False]*2)
