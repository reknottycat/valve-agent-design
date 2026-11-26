"""A repair to cell connectivity must not move walls or hide a different failure."""
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'framework/tools'))
from frozen_poly_repair import compare, envelope, nonortho


class FrozenMesh(unittest.TestCase):
    def test_reject_actual_ring_candidate_side_effect(self):
        folder=ROOT/'verification/valve-3d-cfd-57mm/ring-localization'
        with zipfile.ZipFile(folder/'native-baseline.zip') as z, zipfile.ZipFile(folder/'native-candidate.zip') as c:
            before=z.read('checkMesh.log').decode(); after=c.read('checkMesh.log').decode()
        r=compare({}, {}, before,after)
        self.assertEqual((r['before_severe_faces'],r['after_severe_faces']),(6514,9018))
        self.assertTrue(r['same_discrete_volume']);self.assertFalse(r['no_additional_severe_faces'])
        with self.assertRaises(ValueError):nonortho('Mesh non-orthogonality Max: 86\nNon-orthogonality check OK.')

    def test_preserve_patch_orientation_and_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp);m=case/'constant/polyMesh';m.mkdir(parents=True)
            def write(n,data): (m/n).write_text(str(len(data))+'\n(\n'+'\n'.join(data)+'\n)\n')
            verts=['(0 0 0)','(1 0 0)','(0 1 0)','(0 0 1)'];faces=['3(0 1 2)','3(0 3 1)','3(1 3 2)','3(0 2 3)']
            (m/'boundary').write_text('inlet {type patch; nFaces 1; startFace 0;}\noutlet {type patch; nFaces 1; startFace 1;}\nvalve {type wall; nFaces 2; startFace 2;}')
            write('points',verts); write('faces',faces); original=envelope(case)
            write('faces',[faces[0],faces[1],faces[3],faces[2]]); self.assertEqual(original,envelope(case))
            write('faces',['3(0 2 1)',*faces[1:]]);self.assertNotEqual(original,envelope(case))
            write('faces',faces);write('points',[*verts[:-1],'(0 0 1.01)']); self.assertNotEqual(original,envelope(case))
