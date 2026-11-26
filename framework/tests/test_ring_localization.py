"""Compare all independently located defects, not just the native error counts."""
import csv
from collections import Counter
import io
import json
from pathlib import Path
import re
import unittest
import zipfile

DATA = Path(__file__).resolve().parents[2]/'verification/valve-3d-cfd-57mm/ring-localization'


def coord(row): return tuple(round(float(x), 5) for x in row)

def labels(z, name):
    m=re.search(rb'\n\s*(\d+)\s*\(\s*([\d\s]+?)\s*\)',z.read(name)); n=int(m[1]); values=set(map(int,m[2].split()))
    if n!=len(values): raise ValueError(name)
    return values


class RingLocalization(unittest.TestCase):
    def test_locations_from_both_methods_and_local_trial(self):
        with zipfile.ZipFile(DATA/'native-baseline.zip') as z, zipfile.ZipFile(DATA/'independent-replay.zip') as independent:
            native=list(csv.DictReader(io.StringIO(z.read('locations_mm.csv').decode())))
            for kind,filename,setname,expected in [('cell','local_cells.csv','underdeterminedCells',4657),('face','local_faces.csv','lowWeightFaces',16)]:
                rows=[r for r in native if r['kind']==kind];self.assertEqual(len(rows),expected)
                self.assertEqual({int(r['native_id']) for r in rows},labels(z,setname))
                cloud=Counter(coord([r[n] for n in ('x_mm','y_mm','z_mm')]) for r in rows)
                self.assertEqual(cloud,Counter(coord(r) for r in csv.reader(io.StringIO(independent.read(filename).decode()))))
            self.assertEqual(len(labels(z,'twoInternalFacesCells') & labels(z,'underdeterminedCells')),4213)
            r=json.loads(independent.read('ring_opt.json'));self.assertEqual(r['parents_with_all_four_passing'],2502);self.assertGreaterEqual(r['lowest_optimized_child_determinant'],.001)

    def test_native_candidate_is_not_cleared_by_local_improvement(self):
        with zipfile.ZipFile(DATA/'native-candidate.zip') as z:
            log=z.read('checkMesh.log').decode()
            self.assertIn('Failed 2 mesh checks.',log);self.assertNotIn('Mesh OK.',log)
            for name,expected in [('small determinant',2155),('small interpolation weight',16)]:
                self.assertRegex(log, name+r'[^\n]+: '+str(expected)+r'\b')
            self.assertRegex(log,r'severely non-orthogonal[^\n]+9018')
