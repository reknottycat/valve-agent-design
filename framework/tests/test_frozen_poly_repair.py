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

    def test_reject_claimed_merges_with_no_reduction(self):
        import json
        from frozen_poly_repair import confirm_pair_reduction
        p=ROOT/'verification/valve-3d-cfd-57mm/opus-repair/rejected-first-report.json'
        result=json.loads(p.read_bytes());s=result['statistics'];self.assertEqual(result['status'],'success')
        with self.assertRaisesRegex(ValueError,'real shared'):
            confirm_pair_reduction(s['input_cells'],s['output_cells'],s['input_internal_faces'],s['output_internal_faces'],s['cells_merged'],[])
        self.assertEqual(confirm_pair_reduction(4,3,3,2,1,[0]),1)
        with self.assertRaises(ValueError):confirm_pair_reduction(4,2,3,1,2,[0,0])

    def test_actual_native_pair_aggregation(self):
        import re,json
        from frozen_poly_repair import confirm_pair_reduction
        folder=ROOT/'verification/valve-3d-cfd-57mm/opus-repair'
        with zipfile.ZipFile(folder/'native-record.zip') as z:
            def counts(name):
                t=z.read(name).decode();return [int(re.search(r'^\s*'+k+r':\s*(\d+)\s*$',t,re.M)[1]) for k in ('cells','internal faces')]
            ac,af=counts('baseline.log');bc,bf=counts('candidate.log');m=json.loads(z.read('merge.json'));ids=list(map(int,z.read('removed_native_face_ids.txt').split()));r=json.loads(z.read('result.json'))
            self.assertEqual(confirm_pair_reduction(ac,bc,af,bf,m['merged_pairs'],ids),m['removed_shared_internal_faces']);self.assertEqual(bc,m['expected_cells'])
            self.assertEqual(r['candidate_envelope'],r['baseline_envelope']);self.assertTrue(r['mesh_checks']['connected_fluid_points']);
            if not r['mesh_checks']['native_quality']:self.assertFalse(r['solver_started']);self.assertEqual(r['study_assessment'],'not_evaluated')
