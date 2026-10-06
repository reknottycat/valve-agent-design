#!/usr/bin/env python3
import copy, hashlib, importlib.util, io, json, os, pathlib, sys, tempfile, unittest, zlib
from unittest.mock import patch
sys.dont_write_bytecode = True
QA = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location('transport_under_test', QA.parent / 'transport.py')
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
tempfile.tempdir = str(QA)
P = 'runs/20261006/assets/a.bin'
Q = 'runs/20261006/assets/b.bin'

class Review(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=QA)
        self.root = pathlib.Path(self.tmp.name)
        self.src = self.root/'src'; self.src.mkdir()
        self.bundle = self.root/'bundle'; self.bundle.mkdir()
        self.dest = self.root/'dest'; self.dest.mkdir()
    def tearDown(self): self.tmp.cleanup()
    def write(self, root, path, data):
        f = root/path; f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(data); return f
    def pack(self, vals=None, compression='raw'):
        vals = vals or [(P,b'first'),(Q,b'second')]
        for p, b in vals: self.write(self.src,p,b)
        return t.split(self.src,self.bundle,[p for p,b in vals],compression)
    def manifest(self): return json.loads((self.bundle/'artifact_storage/manifest.json').read_text())
    def save_manifest(self,m): (self.bundle/'artifact_storage/manifest.json').write_text(json.dumps(m))
    def refused(self,fn):
        with self.assertRaises((t.TransportError,OSError,zlib.error)): fn()
    def empty_dest(self): self.assertEqual(list(self.dest.rglob('*')),[])

    def test_roundtrip_modes_and_chunk_boundaries(self):
        for mode in ['raw','zlib','auto']:
            for n, raw in enumerate([b'',b'x',bytes(range(256)),b'a'*(t.CHUNK_BYTES*3+7),os.urandom(t.CHUNK_BYTES*2+31)]):
                with self.subTest(mode=mode,length=len(raw)):
                    out=self.root/f'bundle-{mode}-{n}'; out.mkdir()
                    dst=self.root/f'dest-{mode}-{n}'; dst.mkdir()
                    t.write_bundle(out,[t.make_entry(P,raw,mode)])
                    self.assertTrue(all(0<f.stat().st_size<=t.CHUNK_BYTES for f in out.rglob('*.bin')))
                    r=t.restore(out,dst)
                    self.assertEqual((dst/P).read_bytes(),raw)
                    self.assertEqual(r['created_files'],1)
                    self.assertEqual(t.restore(out,dst)['created_files'],0)
    def test_large_zlib_decode_buffers(self):
        for i,raw in enumerate([b'x'*(t.IO_BYTES*5+1), bytes(range(256))*(t.IO_BYTES//256*5+1)]):
            with self.subTest(i=i):
                out=self.root/f'z{i}'; out.mkdir(); dst=self.root/f'd{i}'; dst.mkdir()
                t.write_bundle(out,[t.make_entry(P,raw,'zlib')]); t.restore(out,dst)
                self.assertEqual((dst/P).read_bytes(),raw)
    def test_bad_original_paths(self):
        bad=['/runs/20261006/assets/x','../runs/20261006/assets/x','runs/20261006/assets/../x',
             'runs\\20261006\\assets\\x','C:/runs/20261006/assets/x','runs/20261006/.git/x',
             'runs/20261006/.GiT/x','runs/202610060/assets/x','runs/20261007/assets/x',
             'runs/20261006//x','runs/20261006/./x','runs/20261006/assets/x\x00',
             'runs/20261006/assets/x.','runs/20261006/assets/x ', 'runs/20261006/assets/x:y']
        for p in bad:
            with self.subTest(path=p): self.refused(lambda:t.make_entry(p,b'x'))
    def test_duplicate_casefold_and_prefix_conflicts(self):
        for other in [P,'runs/20261006/assets/A.bin','runs/20261006/Assets/b.bin',P+'/child']:
            with self.subTest(other=other): self.refused(lambda:t.create_manifest([t.make_entry(P,b'a')[0],t.make_entry(other,b'b')[0]]))
    def test_invalid_integer_fields(self):
        m=self.pack()
        for field in ['bytes','encoded_bytes']:
            for v in [True,False,-1,1.0,float('nan'),float('inf'),'1',None,2**70]:
                with self.subTest(field=field,value=v):
                    x=copy.deepcopy(m); x['files'][0][field]=v; self.refused(lambda:t.validate_manifest(x))
        for v in [True,False,-1,1.0,float('nan'),float('inf'),'1',None,0,t.CHUNK_BYTES+1]:
            with self.subTest(chunk_bytes=v):
                x=copy.deepcopy(m); x['files'][0]['chunks'][0]['bytes']=v; self.refused(lambda:t.validate_manifest(x))
        for v in [True,False,-1,1.0,float('nan'),float('inf'),'1',None,0,t.CHUNK_BYTES+1]:
            with self.subTest(manifest_chunk_bytes=v):
                x=copy.deepcopy(m); x['chunk_bytes']=v; self.refused(lambda:t.validate_manifest(x))
    def test_unsupported_codec(self):
        m=self.pack()
        for v in ['gzip','zlib64','RAW',None,True,{},[]]:
            with self.subTest(codec=v):
                x=copy.deepcopy(m); x['files'][0]['encoding']=v; self.refused(lambda:t.validate_manifest(x))
    def test_missing_later_chunk_publishes_nothing(self):
        m=self.pack(); (self.bundle/m['files'][1]['chunks'][0]['path']).unlink()
        self.refused(lambda:t.restore(self.bundle,self.dest)); self.empty_dest()
    def test_altered_later_chunk_publishes_nothing(self):
        m=self.pack(); (self.bundle/m['files'][1]['chunks'][0]['path']).write_bytes(b'change')
        self.refused(lambda:t.restore(self.bundle,self.dest)); self.empty_dest()
    def test_wrong_raw_hash_publishes_nothing(self):
        m=self.pack(compression='zlib'); e=m['files'][1]; e['sha256']='0'*64
        oldcid=e['content_id']; e['content_id']=t.content_id(e)
        (self.bundle/'artifact_storage/chunks'/oldcid).rename(self.bundle/'artifact_storage/chunks'/e['content_id'])
        for ch in e['chunks']: ch['path']=ch['path'].replace(oldcid,e['content_id'])
        self.save_manifest(m); self.refused(lambda:t.restore(self.bundle,self.dest)); self.empty_dest()
    def test_wrong_git_hash_publishes_nothing(self):
        m=self.pack(); m['files'][1]['git_blob_sha1']='0'*40; self.save_manifest(m)
        self.refused(lambda:t.restore(self.bundle,self.dest)); self.empty_dest()
    def test_overexpansion_publishes_nothing(self):
        m=self.pack([(P,b'first'),(Q,b'x'*(3*t.IO_BYTES))],compression='zlib'); m['files'][1]['bytes']=1; self.save_manifest(m)
        self.refused(lambda:t.restore(self.bundle,self.dest)); self.empty_dest()
    def test_zlib_bad_streams(self):
        raw=b'hello'*30
        for i,encoded in enumerate([zlib.compress(raw)[:-1],zlib.compress(raw)+b'junk',zlib.compress(raw)+zlib.compress(b'extra')]):
            with self.subTest(case=i):
                out=self.root/f'badz{i}'; out.mkdir(); e,_=t.make_entry(P,raw,'zlib')
                e['encoded_bytes']=len(encoded); e['encoded_sha256']=hashlib.sha256(encoded).hexdigest(); e['content_id']=t.content_id(e)
                ch={'path':f"artifact_storage/chunks/{e['content_id']}/000000.bin",'bytes':len(encoded),'sha256':hashlib.sha256(encoded).hexdigest()}; e['chunks']=[ch]
                self.write(out,ch['path'],encoded); self.write(out,'artifact_storage/manifest.json',json.dumps(t.create_manifest([e])).encode()); self.refused(lambda:t.restore(out,self.dest)); self.empty_dest()
    def test_conflicting_later_destination_publishes_nothing(self):
        self.pack(); self.write(self.dest,Q,b'edited')
        self.refused(lambda:t.restore(self.bundle,self.dest)); self.assertFalse((self.dest/P).exists()); self.assertEqual((self.dest/Q).read_bytes(),b'edited')
    def test_verify_only_has_no_publication(self):
        self.pack(); r=t.restore(self.bundle,self.dest,verify_only=True); self.empty_dest(); self.assertEqual(r['verified_files'],2)
    def test_split_later_invalid_source_publishes_nothing(self):
        self.write(self.src,P,b'a'); self.refused(lambda:t.split(self.src,self.bundle,[P,Q])); self.assertEqual(list(self.bundle.rglob('*')),[])
    def test_symlink_source_leaf(self):
        external=self.write(self.root,'outside.bin',b'outside'); f=self.src/P; f.parent.mkdir(parents=True); f.symlink_to(external)
        self.refused(lambda:t.split(self.src,self.bundle,[P])); self.assertEqual(list(self.bundle.rglob('*')),[])
    def test_symlink_source_ancestor(self):
        external=self.root/'outside'; external.mkdir(); self.write(external,'a.bin',b'outside')
        f=self.src/'runs/20261006/assets'; f.parent.mkdir(parents=True); f.symlink_to(external,target_is_directory=True)
        self.refused(lambda:t.split(self.src,self.bundle,[P])); self.assertEqual(list(self.bundle.rglob('*')),[])
    def test_symlink_source_root(self):
        self.write(self.src,P,b'x'); root=self.root/'linked'; root.symlink_to(self.src,target_is_directory=True)
        self.refused(lambda:t.split(root,self.bundle,[P])); self.assertEqual(list(self.bundle.rglob('*')),[])
    def test_symlink_manifest(self):
        self.pack(); f=self.bundle/'artifact_storage/manifest.json'; external=self.root/'manifest.json'; f.rename(external); f.symlink_to(external)
        self.refused(lambda:t.restore(self.bundle,self.dest)); self.empty_dest()
    def test_symlink_chunk_leaf(self):
        m=self.pack(); f=self.bundle/m['files'][1]['chunks'][0]['path']; external=self.root/'chunk.bin'; f.rename(external); f.symlink_to(external)
        self.refused(lambda:t.restore(self.bundle,self.dest)); self.empty_dest()
    def test_symlink_chunk_ancestor(self):
        self.pack(); f=self.bundle/'artifact_storage/chunks'; external=self.root/'chunks'; f.rename(external); f.symlink_to(external,target_is_directory=True)
        self.refused(lambda:t.restore(self.bundle,self.dest)); self.empty_dest()
    def test_symlink_bundle_root_ancestor(self):
        self.pack(); link=self.root/'link'; link.symlink_to(self.root,target_is_directory=True)
        self.refused(lambda:t.restore(link/'bundle',self.dest)); self.empty_dest()
    def test_symlink_destination_leaf(self):
        self.pack(); external=self.write(self.root,'outside.bin',b'first'); f=self.dest/P; f.parent.mkdir(parents=True); f.symlink_to(external)
        self.refused(lambda:t.restore(self.bundle,self.dest)); self.assertEqual(external.read_bytes(),b'first'); self.assertFalse((self.dest/Q).exists())
    def test_symlink_destination_ancestor(self):
        self.pack(); external=self.root/'outside'; external.mkdir(); (self.dest/'runs').symlink_to(external,target_is_directory=True)
        self.refused(lambda:t.restore(self.bundle,self.dest)); self.assertEqual(list(external.rglob('*')),[])
    def test_symlink_destination_root(self):
        self.pack(); link=self.root/'linked'; link.symlink_to(self.dest,target_is_directory=True)
        self.refused(lambda:t.restore(self.bundle,link)); self.empty_dest()
    def test_destination_file_as_ancestor(self):
        self.pack(); (self.dest/'runs').write_bytes(b'keep'); self.refused(lambda:t.restore(self.bundle,self.dest)); self.assertEqual((self.dest/'runs').read_bytes(),b'keep')
    def test_source_fifo_is_rejected_without_blocking(self):
        p=self.src/P; p.parent.mkdir(parents=True); os.mkfifo(p)
        self.refused(lambda:t.split(self.src,self.bundle,[P])); self.assertEqual(list(self.bundle.rglob('*')),[])
    def test_destination_fifo_is_rejected_without_blocking(self):
        self.pack(); p=self.dest/P; p.parent.mkdir(parents=True); os.mkfifo(p)
        self.refused(lambda:t.restore(self.bundle,self.dest)); self.assertFalse((self.dest/Q).exists())
    def test_no_overwrite_when_leaf_appears_at_publish(self):
        self.pack([(P,b'first')]); original=os.link; raced=[]
        def create_first(src,dst,*a,**kw):
            self.write(self.dest,P,b'user-edit'); raced.append(True); return original(src,dst,*a,**kw)
        with patch.object(t.os,'link',side_effect=create_first): self.refused(lambda:t.restore(self.bundle,self.dest))
        self.assertTrue(raced); self.assertEqual((self.dest/P).read_bytes(),b'user-edit'); self.assertFalse(list(self.dest.rglob('.valve-transport-*')))
    def test_duplicate_json_keys_are_rejected(self):
        self.pack(); f=self.bundle/'artifact_storage/manifest.json'; s=f.read_text(); f.write_text(s.replace('"format":','"format":"duplicate", "format":',1))
        self.refused(lambda:t.restore(self.bundle,self.dest)); self.empty_dest()
    def test_nonfinite_json_numbers_are_rejected(self):
        self.pack(); m=self.manifest(); m['files'][0]['bytes']=float('nan'); self.save_manifest(m)
        self.refused(lambda:t.restore(self.bundle,self.dest)); self.empty_dest()

if __name__=='__main__': unittest.main(verbosity=2)
