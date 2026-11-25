"""Replay measured data only: no apt installation or CFD execution in CI."""
import bisect
import gzip
import json
import math
from pathlib import Path
import re
import unittest
import zipfile

EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence/official-ball-valve'


def read_series(archive, name):
    rows = [tuple(map(float, line.split())) for line in archive.read(name+'.dat').decode().splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if not all(len(r)==2 and all(map(math.isfinite,r)) for r in rows): raise ValueError(name)
    return tuple(zip(*rows))


class OfficialBallValve(unittest.TestCase):
    def test_both_geometries_reach_end_and_balance(self):
        result=json.loads((EVIDENCE/'result.json').read_text())
        self.assertEqual([c['lPipe'] for c in result['cases']],[50,60]); self.assertTrue(result['passed'])
        for c in result['cases']:
            length=c['lPipe']; d=length/100
            with self.subTest(length=length), zipfile.ZipFile(EVIDENCE/f'lPipe{length}.zip') as z:
                mesh=gzip.decompress(z.read('log.checkMesh.gz')).decode()
                self.assertIn('Mesh OK.',mesh)
                for name,axis,pos in [('inlet',0,-d),('lowerOutlet',1,-d),('upperOutlet',1,d)]:
                    line=re.search(r'^\s*'+name+r'\s+\d+\s+\d+[^\n]+',mesh,re.M)[0]
                    box=re.findall(r'\(([^()]+)\)',line)[-2:];self.assertEqual([float(v.split()[axis]) for v in box],[pos,pos])
                log=gzip.decompress(z.read('log.foamRun.gz')).decode();self.assertRegex(log,r'(?m)^Time = 1s?\s*$');self.assertIn('\nEnd\n',log)
                series=[read_series(z,p+'FlowRate') for p in ('inlet','lowerOutlet','upperOutlet')]; t=series[0][0]
                self.assertEqual((t[0],t[-1]),(0,1));self.assertTrue(all(a<b for a,b in zip(t,t[1:])));self.assertEqual(len(t),c['samples'])
                for times,_ in series:self.assertEqual(t,times)
                def integral(v):return math.fsum((b-a)*(x+y)/2 for a,b,x,y in zip(t,t[1:],v,v[1:]))
                qin=integral([-x for x in series[0][1]]);self.assertGreater(qin,0);self.assertAlmostEqual(qin,c['net_inlet_volume_m3'],12)
                imbalance=integral([abs(a+b+c) for a,b,c in zip(*(s[1] for s in series))])/qin
                self.assertLessEqual(imbalance,.001);self.assertAlmostEqual(imbalance,c['integrated_absolute_flux_imbalance'],12)
                press=[read_series(z,n+'Pressure') for n in ('inlet','lowerOutlet','upperOutlet')]
                for ts,_ in press:self.assertEqual(ts,t)
                for stamp,row in c['phase_samples'].items():
                    x=float(stamp);j=bisect.bisect_left(t,x);self.assertGreater(j,0)
                    def phase(v):return v[j-1]+(v[j]-v[j-1])*(x-t[j-1])/(t[j]-t[j-1])
                    for outlet,idx in [('lower',1),('upper',2)]:
                        self.assertAlmostEqual(phase(press[0][1])-phase(press[idx][1]),row[f'inlet_minus_{outlet}_kinematic_pressure_m2_s2'],9)
        a,b=result['cases'];self.assertNotEqual(a['geometry_mesh_sha256'],b['geometry_mesh_sha256'])
        self.assertNotAlmostEqual(a['net_inlet_volume_m3'],b['net_inlet_volume_m3'],6)
        k='inlet_minus_lower_kinematic_pressure_m2_s2';self.assertGreater(abs(a['phase_samples']['0.25'][k]-b['phase_samples']['0.25'][k]),1e-5)
