import gzip
import json
import math
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT/'verification/valve-3d-cfd-57mm'
sys.path.insert(0, str(ROOT/'framework/tools'))
from foam11_gates import assess, liquid, mesh_checks, require_case


def log(v, name):
    return gzip.decompress((CASE/v/(name+'.log.gz')).read_bytes()).decode()


class HistoricalRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = runpy.run_path(str(CASE/'valve_3d_cfd.py'))
        cls.kw = dict(bbox_m=(-.6,-.145,-.145,1.2,.145,.332), tolerance_m=.001,
                      points=[(-.5,.00017,.00013),(1.1,.00017,.00013),(.320,.00017,.331),(.280,.00017,.331),(.3315,.00017,.160),(.2685,.00017,.160)], cells=498572)

    def test_fluid_units_and_pressure_basis(self):
        r=self.runner
        with self.assertRaises(ValueError): liquid(dict(r['STATE'],kinematic_viscosity_m2_s=.001))
        self.assertAlmostEqual(r['U_INLET']*r['D']/r['NU'],168344.0241,places=3)
        self.assertAlmostEqual(r['TARGET_DP_PA'],2403.82382,places=4)

    def test_truncated_mesh_never_clears_extent(self):
        g=mesh_checks(log('v18','checkMesh'),'',**self.kw)
        self.assertTrue(g['native_quality']); self.assertFalse(g['extent_in_metres']);self.assertFalse(g['foundation11_full_check'])

    def test_distinguish_coverage_connectivity_and_quality(self):
        for v,probes in [('v20',''),('v21',log('v21','probeCells'))]:
            g=mesh_checks(log(v,'checkMesh'),probes,**self.kw)
            self.assertTrue(g['extent_in_metres']);self.assertFalse(g['native_quality']);self.assertEqual(g['connected_fluid_points'],v=='v21')
        g=mesh_checks(log('v21','checkMesh'),probes.replace('0.3315','0.3305'),**self.kw)
        self.assertFalse(g['connected_fluid_points'])

    def test_good_case_then_break_version_and_patch_names(self):
        r=self.runner
        with tempfile.TemporaryDirectory() as tmp:
            w=Path(tmp); mesh=w/'mesh/constant/polyMesh';mesh.mkdir(parents=True)
            for n in ('points','faces','owner','neighbour'): (mesh/n).touch()
            (mesh/'boundary').write_bytes((CASE/'v21/boundary.txt').read_bytes());c=w/'solver';r['setup_solver_case'](w/'mesh',c,{})
            g=mesh_checks(log('v21','checkMesh'),log('v21','probeCells'),**self.kw)
            args=({'inlet':'patch','outlet':'patch','valve':'wall'},r['NU'])
            with self.assertRaisesRegex(ValueError,'native_quality'): require_case(c,g,*args)
            g['native_quality']=True  # synthetic positive control only
            require_case(c,g,*args)
            with self.assertRaises(ValueError): require_case(c,{},*args)
            p=c/'0/k';p.write_text(p.read_text().replace('    valve\n','    walls\n'))
            (c/'constant/momentumTransport').rename(c/'constant/turbulenceProperties')
            with self.assertRaises(ValueError) as err: require_case(c,g,*args)
            self.assertIn('0/k',str(err.exception));self.assertIn('momentumTransport',str(err.exception))

    def test_old_runs_do_not_decide_compliance(self):
        for v in ('v18','v19'):
            r=json.loads((CASE/v/'result.json').read_text()); self.assertTrue(r['success']); self.assertEqual(assess(r,r['limits']),'quality_not_passed')
        self.assertEqual(assess(dict(r,dp_Pa=float('nan')),r['limits']),'no_valid_result');self.assertEqual(assess(dict(r,residual_converged=True,dp_span=.001,kz=5),r['limits']),'within_study_limit');self.assertEqual(assess(dict(r,residual_converged=True,dp_span=.001,kz=7),r['limits']),'above_study_limit')

    def test_runner_holds_actual_v21_evidence_before_foamRun(self):
        # Replay the runner's wiring, not just the helper predicates. No network or solver.
        import shutil
        main=self.runner['main']; seen=[]
        def fake_run(cmd, cwd, dest, of=False):
            seen.append(cmd[0]); self.assertNotEqual(cmd[0],'foamRun','native mesh failure must block solver launch')
            if cmd[0]=='gmshToFoam':
                mesh=cwd/'constant/polyMesh';mesh.mkdir(); b=(CASE/'v21/boundary.txt').read_text().replace('type            wall;', 'type            patch;');(mesh/'boundary').write_text(b)
                for n in ('points','faces','owner','neighbour'): (mesh/n).touch()
            elif cmd[0]=='checkMesh':dest.write_text(log('v21','checkMesh'))
            elif cmd[0]=='topoSet': dest.write_text(log('v21','probeCells'))
        with tempfile.TemporaryDirectory() as tmp:
            import hashlib, os
            w=Path(tmp);(w/'out').mkdir();(w/'job').mkdir();meta=b'{}';data=gzip.compress(b'synthetic conversion input');realhash=hashlib.sha256
            def download(cmd,**kwargs): Path(cmd[cmd.index('-o')+1]).write_bytes(meta if cmd[-1].endswith('json') else data)
            # Keep production hash checks active, substituting fixture assets and digests.
            with patch.dict(os.environ,OUTPUT_DIR=str(w/'out')),patch.dict(main.__globals__,run=fake_run,install_openfoam=lambda w:None,ASSET_HASHES={'geometry_metadata.json':realhash(meta).hexdigest(),self.runner['MESH_ASSET']:realhash(data).hexdigest()}),patch('subprocess.run',download),patch('tempfile.mkdtemp',return_value=str(w/'job')):
                with self.assertRaisesRegex(ValueError,'native_quality'):main()
            r=json.loads((w/'out/result.json').read_text());self.assertFalse(r['solver_started']);self.assertEqual(r['study_assessment'],'not_evaluated');self.assertNotIn('foamRun',seen);self.assertTrue((w/'out/checkMesh.log.gz').exists())
