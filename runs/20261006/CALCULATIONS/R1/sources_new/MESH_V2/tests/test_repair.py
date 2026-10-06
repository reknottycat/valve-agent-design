import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import repair_mesh as r

def tet_mesh(points,tets):
    incidences={}
    for c,tet in enumerate(tets):
        for face in __import__('itertools').combinations(tet,3):
            face=tuple(int(x) for x in face); q=points[list(face)]
            if np.dot(np.cross(q[1]-q[0],q[2]-q[0]),q.mean(axis=0)-points[tet].mean(axis=0))<0: face=tuple(reversed(face))
            incidences.setdefault(tuple(sorted(face)),[]).append((c,face))
    internal=[]; boundary=[]
    for v in incidences.values():
        v.sort()
        if len(v)==2: internal.append((v[0][0],v[1][0],v[0][1]))
        else: boundary.append((v[0][0],v[0][1]))
    internal.sort(); boundary.sort()
    return dict(points=points.copy(),faces=[x[2] for x in internal]+[x[1] for x in boundary],owner=np.array([x[0] for x in internal]+[x[0] for x in boundary]),neighbour=np.array([x[1] for x in internal],dtype=np.int64),patches=[dict(name='wall',type='wall',startFace=len(internal),nFaces=len(boundary))])

class RepairTests(unittest.TestCase):
    def setUp(self):
        self.p=np.array([[-1.,-1,0],[1,-1,0],[0,1,0],[0,0,1],[0,0,-1]])
        self.t=np.array([[0,1,2,3],[0,2,1,4]])
        self.m=tet_mesh(self.p,self.t)
    def test_exact_source_identity(self):
        self.assertEqual(r.source_identity(self.m,self.p,self.t)['cells'],2)
    def test_bad_source_cell_identity_rejected(self):
        with self.assertRaisesRegex(r.GateError,'cell identity'): r.source_identity(self.m,self.p,self.t[::-1])
    def test_moved_vertex_rejected(self):
        m=copy.deepcopy(self.m); m['points'][0,0]+=1e-12
        with self.assertRaisesRegex(r.GateError,'point'): r.source_identity(m,self.p,self.t)
    def test_reversed_boundary_rejected(self):
        m=copy.deepcopy(self.m); m['faces'][-1]=tuple(reversed(m['faces'][-1]))
        with self.assertRaisesRegex(r.GateError,'orientation'): r.source_identity(m,self.p,self.t)
    def test_convex_union(self):
        cf,adj=r.topology(self.m,2); vol,worst=r.validate_convex_shell(self.p,r.shell(self.m,(0,1),cf))
        self.assertAlmostEqual(vol,4/3); self.assertLessEqual(worst,1e-11)
    def test_concave_union_rejected(self):
        p=self.p.copy(); p[4,0]=5; m=tet_mesh(p,self.t); cf,_=r.topology(m,2)
        with self.assertRaisesRegex(r.GateError,'nonconvex'): r.validate_convex_shell(p,r.shell(m,(0,1),cf))
    def test_rank_deficient_determinant(self):
        self.assertEqual(r.determinant([[1,0,0],[0,1,0],[-1,-1,0]]),0)
        self.assertEqual(r.determinant([]),0)
        self.assertAlmostEqual(r.determinant([[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]]),1)
    def test_boundary_faces_excluded_from_determinant(self):
        cf,adj=r.topology(self.m,2); areas=r.triangle_areas(self.p,self.m['faces'])
        self.assertEqual(r.determinant(areas[[i for i in cf[0] if i<len(self.m['neighbour'])]]),0)
        self.assertGreater(r.determinant(areas[cf[0]]),0)
    def merge_fixture(self):
        before=dict(points=np.array([[0.,0,0],[1,0,0],[1,1,0],[0,1,0]]),faces=[(0,1,2),(0,2,3)],owner=np.array([0,0]),neighbour=np.array([],dtype=int),patches=[dict(name='wall',type='wall',startFace=0,nFaces=2)])
        after=copy.deepcopy(before); after['faces']=[(0,1,2,3)]; after['owner']=np.array([0]); after['patches'][0]['nFaces']=1
        return before,after
    def test_merge_identity(self):
        before,after=self.merge_fixture(); self.assertEqual(r.verify_patch_merge(before,after)['merged_quad_count'],1)
    def test_merge_moved_point_rejected(self):
        before,after=self.merge_fixture(); after['points'][0,0]=1e-12
        with self.assertRaisesRegex(r.GateError,'points'): r.verify_patch_merge(before,after)
    def test_merge_reversed_boundary_rejected(self):
        before,after=self.merge_fixture(); after['faces']=[(0,3,2,1)]
        with self.assertRaisesRegex(r.GateError,'oriented boundary-edge'): r.verify_patch_merge(before,after)
    def test_merge_nonplanar_rejected(self):
        before,after=self.merge_fixture(); before['points'][3,2]=after['points'][3,2]=1e-4
        with self.assertRaisesRegex(r.GateError,'coplanar'): r.verify_patch_merge(before,after)
    def test_merge_wrong_cell_rejected(self):
        before,after=self.merge_fixture(); after['owner'][0]=1
        with self.assertRaisesRegex(r.GateError,'same-cell'): r.verify_patch_merge(before,after)
    def test_one_ulp_source_conversion_recorded(self):
        m=copy.deepcopy(self.m); m['points'][0,0]=np.nextafter(m['points'][0,0],-np.inf)
        result=r.source_identity(m,self.p,self.t)
        self.assertFalse(result['point_coordinates_bitwise_equal'])
        self.assertEqual(result['conversion_max_ulp'],1)
    def test_two_ulp_source_discrepancy_rejected(self):
        m=copy.deepcopy(self.m); m['points'][0,0]=np.nextafter(np.nextafter(m['points'][0,0],-np.inf),-np.inf)
        with self.assertRaisesRegex(r.GateError,'conversion ULP'): r.source_identity(m,self.p,self.t)
    def test_flagged_bound_rejected(self):
        with self.assertRaisesRegex(r.GateError,'1..100'): r.select_groups(self.m,self.t,set(range(101)))
    def test_empty_flagged_rejected(self):
        with self.assertRaisesRegex(r.GateError,'1..100'): r.select_groups(self.m,self.t,set())
    def test_nonmanifold_union_rejected(self):
        cf,_=r.topology(self.m,2); shell=r.shell(self.m,(0,1),cf); shell.append(shell[0])
        with self.assertRaisesRegex(r.GateError,'nonmanifold'): r.validate_convex_shell(self.p,shell)
    def test_merge_internal_mutation_rejected(self):
        before,after=self.merge_fixture()
        for m in (before,after):
            m['faces'].insert(0,(0,1,2)); m['owner']=np.r_[0,m['owner']]; m['neighbour']=np.array([1]); m['patches'][0]['startFace']=1
        after['faces'][0]=(2,1,0)
        with self.assertRaisesRegex(r.GateError,'internal faces'): r.verify_patch_merge(before,after)
    def test_gate_survives_optimization(self):
        with self.assertRaises(r.GateError): r.gate(False,'hard gate')

if __name__=='__main__': unittest.main(verbosity=2)
