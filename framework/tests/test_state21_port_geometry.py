"""Synthetic parser/security tests and opt-in real entry regression.

VALVE_STATE21_PORT_INPUT supplies an external readiness manifest with the optional
geometry_binding. No full case, fields, CAD or process logs are shipped here.
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

TOOLS = Path(__file__).resolve().parents[1] / 'tools'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

R = load('port_readiness_test', TOOLS/'valve_readiness.py')
G = load('port_geometry_test', TOOLS/'state21_port_geometry.py')
B = load('port_flow_test', TOOLS/'state21_flow_binding.py')
LOCAL = os.environ.get('VALVE_STATE21_PORT_INPUT')

def blank():
    return {'formula_input_binding': {'profile': B.PROFILE,
        'paths': {r:'/missing-state21/'+r for r in B.ROLES},
        'geometry_binding': {'profile': G.PROFILE, 'paths': {r:'/missing-port/'+r for r in G.ROLES}}}}


def pin(raw):
    return {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}


class PortParserTests(unittest.TestCase):
    def test_missing_is_hold_without_false_measurement(self):
        f=R.audit(blank())['formula_input_binding']; g=f['geometry_binding']
        self.assertEqual(g['source_binding_status'],'HOLD'); self.assertIsNone(g['measurement'])
        self.assertNotIn('research_input_bindings',f)
        self.assertEqual(len(g['missing_reasons']),7)

    def test_declarations_exact_no_overrides(self):
        for k,v in [('rho',1000),('A',.03),('K',1),('lock',{}),('steady',True)]:
            m=blank(); m['formula_input_binding']['geometry_binding'][k]=v
            with self.subTest(k=k),self.assertRaises(R.ReadinessError):R.audit(m)
        for profile in (None,True,21,'native-simple-state20-ports/v1'):
            m=blank(); m['formula_input_binding']['geometry_binding']['profile']=profile
            with self.subTest(profile=profile),self.assertRaises(R.ReadinessError):R.audit(m)
        for paths in ({},None,{'p':'/p'}):
            m=blank(); m['formula_input_binding']['geometry_binding']['paths']=paths
            with self.assertRaises(R.ReadinessError):R.audit(m)

    def test_paths_reject_noncanonical_nonregular_and_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'x').write_text('x'); os.mkfifo(root/'fifo')
            (root/'link').symlink_to(root/'x'); (root/'parent').symlink_to(root,target_is_directory=True)
            for p in ('relative','//tmp/x','/tmp/../x','/tmp//x','/tmp/./x',None,True,str(root),
                      str(root/'fifo'),str(root/'link'),str(root/'parent'/'missing')):
                m=blank(); m['formula_input_binding']['geometry_binding']['paths']['p']=p
                with self.subTest(path=p),self.assertRaises(R.ReadinessError):R.audit(m)

    def test_single_descriptor_hash_and_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source'; raw=b'2\n(\n1\n2\n)\n'; p.write_bytes(raw)
            self.assertEqual(G.read_list(iter(G.lines(str(p),pin(raw))),{1},int),(2,{1:2}))
            bad=dict(pin(raw),sha256='0'*64)
            with self.assertRaisesRegex(ValueError,'digest/size'):list(G.lines(str(p),bad))
            with self.assertRaisesRegex(ValueError,'digest/size'):list(G.lines(str(p),pin(raw+b'x')))
            raw=b'x'*(G.MAX_LINE+1)+b'\n';p.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'line bound'):list(G.lines(str(p),pin(raw)))

    def test_changed_descriptor_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source';raw=b'one\ntwo\n';p.write_bytes(raw)
            it=G.lines(str(p),pin(raw));self.assertEqual(next(it),'one')
            p.write_bytes(b'one\nTWO\n')
            with self.assertRaises(ValueError):list(it)

    def test_parser_limits_and_nonfinite(self):
        for value in ('0','2000001','999999999999999999','-1','true'):
            with self.assertRaises(ValueError):G.count(value)
        for value in ('nan','inf','1e999'):
            with self.assertRaises(ValueError):G.finite(value)
        for value in ('4(0 1 2 3)','3(0 1)','3(-1 1 2)'):
            with self.assertRaises(ValueError):G.face(value)
        with self.assertRaises(ValueError):G.point('(1 2)')
        with self.assertRaises(ValueError):G.tail(iter(['x'*(G.MAX_TAIL+1)]))
        with self.assertRaises(ValueError):G.read_list(iter(['2','(','1','2',')']),{2},int)

    def test_synthetic_triangle_area_pressure_flux(self):
        p={'startFace':0,'nFaces':1,'name':'inlet','patch_id':0}
        r=G.summarize_port(p,{0:[0,1,2]},{0:(0,0,0),1:(0,1,0),2:(0,0,1)},
                           {0:4},{4:2},[-.5],True)
        self.assertEqual(r['area_sum_m2'],.5);self.assertEqual(r['normal'],(1.,0.,0.))
        self.assertEqual(r['pkin_area_mean_m2_s2'],2);self.assertEqual(r['phi_sum_m3_s'],-.5)

    def test_rehashed_lock_cannot_bless_sources(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'state21_port_geometry.py').write_bytes((TOOLS/'state21_port_geometry.py').read_bytes())
            lock=json.loads((TOOLS/'state21-ports.lock.json').read_bytes());lock['files']['p']['sha256']='0'*64
            (root/'state21-ports.lock.json').write_text(json.dumps(lock))
            module=load('tampered_port_lock',root/'state21_port_geometry.py')
            with self.assertRaisesRegex(R.ReadinessError,'immutable port input lock'):
                module.bind(blank()['formula_input_binding']['geometry_binding'],None,R._adapter)

    def test_api_nonfinite_not_json(self):
        for value in (float('nan'),float('inf'),object()):
            m=blank();m['formula_input_binding']['geometry_binding']['profile']=value
            with self.assertRaises(R.ReadinessError):R.audit(m)


@unittest.skipUnless(LOCAL,'set VALVE_STATE21_PORT_INPUT for real external byte entry tests')
class RealPortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=R._adapter._json(Path(LOCAL).read_bytes(),'external port manifest')
        cls.paths=cls.meta['formula_input_binding']['geometry_binding']['paths']
        cls.before={k:(Path(p).stat().st_size,Path(p).stat().st_mtime_ns) for k,p in cls.paths.items()}

    @classmethod
    def tearDownClass(cls):
        after={k:(Path(p).stat().st_size,Path(p).stat().st_mtime_ns) for k,p in cls.paths.items()}
        if after != cls.before:raise AssertionError('external source metadata changed')

    def test_real_entry_measurements_and_all_holds(self):
        r=R.audit(copy.deepcopy(self.meta));f=r['formula_input_binding'];g=f['geometry_binding'];m=g['measurement']
        self.assertEqual(g['source_binding_status'],'PASS');self.assertEqual(g['reconstruction_status'],'PASS')
        self.assertEqual(g['observer_crosscheck_status'],'PASS');self.assertEqual(len(g['comparison']),8)
        self.assertEqual(len(g['sources']),7);self.assertLess(sum(x['bytes'] for x in g['sources']),120000000)
        self.assertEqual(m['K_mesh_area'],115.96179557311874)
        self.assertEqual(m['nominal_research_reference']['K_same_saved_Qin_and_dp'],118.24579895993566)
        self.assertEqual(f['research_input_bindings']['RESEARCH_REFERENCE_A']['value'],.031415926535897934)
        for name,x,normal in [('inlet',-.6,[-1.,0.,0.]),('outlet',1.2,[1.,0.,0.])]:
            p=m['ports'][name];self.assertEqual(p['nFaces'],136);self.assertEqual(p['rim_vertex_count'],26)
            self.assertEqual(p['area_sum_m2'],.03111103635738251)
            self.assertEqual(p['area_weighted_centre_m'][0],x);self.assertEqual(list(p['normal']),normal)
            self.assertLess(p['plane_max_distance_m'],1e-15)
        self.assertFalse(r['requested_checks_pass']);self.assertFalse(r['engineering_release'])
        self.assertEqual(f['status'],'HOLD');self.assertEqual(f['applicability_status'],'HOLD')
        for k in ('Kv_m3_h','Cv','delta_p_Pa','rho_actual_kg_m3'):self.assertIsNone(f[k])
        for k in ('A','zeta','Kv'):self.assertIsNone(f['variable_bindings']['F-FLW-001'][k]['value'])
        self.assertFalse(m['CAD_identity_authenticated'])

    def test_cli_exit_two_and_bounded_output(self):
        p=subprocess.run([sys.executable,'-I','-B',str(TOOLS/'valve_readiness.py'),LOCAL],capture_output=True,text=True,timeout=30)
        self.assertEqual(p.returncode,2,p.stderr);self.assertFalse(p.stderr)
        self.assertLess(len(p.stdout),100000);self.assertEqual(json.loads(p.stdout)['formula_input_binding']['geometry_binding']['observer_crosscheck_status'],'PASS')

    def test_missing_geometry_holds_not_invalid(self):
        m=copy.deepcopy(self.meta);m['formula_input_binding']['geometry_binding']['paths']['points']='/missing-port-points'
        f=R.audit(m)['formula_input_binding'];self.assertEqual(f['source_binding_status'],'PASS')
        self.assertEqual(f['geometry_binding']['source_binding_status'],'HOLD');self.assertNotIn('research_input_bindings',f)

    def test_each_source_size_tamper_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            for role in self.paths:
                p=Path(d)/role;p.write_text('tampered')
                m=copy.deepcopy(self.meta);m['formula_input_binding']['geometry_binding']['paths'][role]=str(p)
                with self.subTest(role=role),self.assertRaisesRegex(R.ReadinessError,'digest/size'):R.audit(m)

    def test_same_size_plan_tamper_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'plan';raw=Path(self.paths['plan']).read_bytes();p.write_bytes(raw.replace(b'0.2,',b'0.3,',1))
            m=copy.deepcopy(self.meta);m['formula_input_binding']['geometry_binding']['paths']['plan']=str(p)
            with self.assertRaisesRegex(R.ReadinessError,'digest/size'):R.audit(m)

if __name__ == '__main__':unittest.main()
