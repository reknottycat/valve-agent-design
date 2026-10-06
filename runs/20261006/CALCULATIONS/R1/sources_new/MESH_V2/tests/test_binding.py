import sys
sys.dont_write_bytecode=True
import json,os,re,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from binding import BindingError
from finalize_v2 import finalize

class FrozenBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT/'revalidation_manifest.json').exists(): raise RuntimeError('fresh revalidation seal required before integration tests')
        cls.digest=(ROOT/'manifest_sha256.txt').read_text().split()[0]
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='valve-v2-binding-test-')
        self.root=Path(self.tmp.name)/'copy'
        shutil.copytree(ROOT,self.root,copy_function=os.link,ignore=shutil.ignore_patterns('__pycache__','*.tar.gz'))
        self.output=Path(self.tmp.name)/'acceptance.json'
        self.output.write_text('{"status":"PASS","old":true}')
    def tearDown(self): self.tmp.cleanup()
    def replace(self,relative,data):
        p=self.root/relative; new=p.with_name(p.name+'.mutation');new.write_bytes(data);os.replace(new,p)
    def reject(self):
        with self.assertRaises((BindingError,FileNotFoundError)):
            finalize(self.root/'revalidation_manifest.json',self.digest,self.output)
        self.assertEqual(json.loads(self.output.read_text())['status'],'FAIL')
        self.assertTrue(list((self.output.parent/'superseded_reports').glob('*.json')))
    def test_fresh_seal_accepts(self):
        self.assertEqual(finalize(self.root/'revalidation_manifest.json',self.digest,self.output)['status'],'PASS')
    def test_owner_out_of_range_rejected(self):
        path='data/final_candidate/constant/polyMesh/owner';b=(self.root/path).read_text()
        changed=re.sub(r'(\n\(\n)\d+',r'\g<1>999999',b,count=1)
        self.assertNotEqual(changed,b);self.replace(path,changed.encode());self.reject()
    def test_faces_replacement_rejected(self):
        path='data/final_candidate/constant/polyMesh/faces';b=(self.root/path).read_text()
        changed=re.sub(r'3\((\d+) (\d+) (\d+)\)',r'3(\3 \2 \1)',b,count=1)
        self.assertNotEqual(changed,b);self.replace(path,changed.encode());self.reject()
    def test_old_native_log_rejected(self):
        self.replace('stage_evidence/native_final.log',(self.root/'data/baseline/log.checkMesh').read_bytes());self.reject()
    def test_report_replacement_rejected(self):
        self.replace('stage_evidence/agglomeration.json',b'{"status":"PASS","result":"substituted stale report"}\n');self.reject()
    def test_missing_mesh_input_rejected(self):
        (self.root/'data/final_candidate/constant/polyMesh/neighbour').unlink();self.reject()
    def test_diagnostic_set_mutation_rejected(self):
        path='data/final_candidate/constant/polyMesh/sets/nonOrthoFaces'
        self.replace(path,(self.root/path).read_bytes()+b'\n');self.reject()
    def test_audit_code_mutation_rejected(self):
        path='scripts/audit_agglomeration.py';self.replace(path,(self.root/path).read_bytes()+b'\n# substituted\n');self.reject()
    def test_resealed_manifest_rejected_by_external_digest(self):
        path='revalidation_manifest.json';self.replace(path,(self.root/path).read_bytes()+b'\n');self.reject()

class AuditOutputInvalidationTests(unittest.TestCase):
    def run_bad_cli(self,script,args):
        with tempfile.TemporaryDirectory(prefix='valve-v2-audit-output-test-') as td:
            out=Path(td)/'audit.json';out.write_text('{"status":"PASS","old":true}')
            result=subprocess.run([sys.executable,*(['-O'] if sys.flags.optimize else []),str(ROOT/'scripts'/script),*args,'--output',str(out)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
            self.assertNotEqual(result.returncode,0)
            report=json.loads(out.read_text());self.assertEqual(report['status'],'FAIL');self.assertIn('missing input',report['error'])
            self.assertTrue(list((Path(td)/'superseded_reports').glob('*.json')))
    def test_agglomeration_cli_invalidates_old_pass(self):
        self.run_bad_cli('audit_agglomeration.py',['--baseline','/tmp/nonexistent-valve-baseline-v2','--candidate','/tmp/nonexistent-valve-candidate-v2'])
    def test_merge_cli_invalidates_old_pass(self):
        self.run_bad_cli('repair_mesh.py',['audit-merge','--before','/tmp/nonexistent-valve-before-v2','--after','/tmp/nonexistent-valve-after-v2'])
if __name__=='__main__':unittest.main(verbosity=2)
