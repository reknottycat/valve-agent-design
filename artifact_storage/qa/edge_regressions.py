#!/usr/bin/env python3
"""Independent regression checks for discovered public-API and publication edges."""
import hashlib, importlib.util, os, pathlib, sys, tempfile, unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
QA = pathlib.Path(__file__).parent
tempfile.tempdir = str(QA)
spec = importlib.util.spec_from_file_location('transport_under_test',QA.parent/'transport.py')
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
P='runs/20261006/assets/a.bin'

class EdgeRegressions(unittest.TestCase):
    def test_named_staging_replacement_does_not_publish_unverified_symlink(self):
        with tempfile.TemporaryDirectory(dir=QA) as d:
            root=pathlib.Path(d); bundle=root/'bundle'; bundle.mkdir(); dest=root/'dest'; dest.mkdir()
            external=root/'outside'; external.write_bytes(b'unverified')
            t.write_bundle(bundle,[t.make_entry(P,b'expected')])
            original=os.link
            def race(src,dst,*args,**kw):
                # Models a process that can write the destination's publication directory.
                staging = src if not str(src).startswith('/proc/self/fd/') else next(name for name in os.listdir(kw['src_dir_fd']) if name.startswith('.valve-transport-'))
                os.unlink(staging,dir_fd=kw['src_dir_fd'])
                os.symlink(str(external),staging,dir_fd=kw['src_dir_fd'])
                return original(src,dst,*args,**kw)
            try:
                with patch.object(t.os,'link',side_effect=race): t.restore(bundle,dest)
            except (t.TransportError,OSError): pass
            target=dest/P
            self.assertFalse(target.is_symlink(),'A substituted staging symlink became a successful restored target')
            if target.exists(): self.assertEqual(target.read_bytes(),b'expected')
    def test_renamed_staging_and_substitute_symlink_still_publish_verified_inode(self):
        with tempfile.TemporaryDirectory(dir=QA) as d:
            root=pathlib.Path(d); bundle=root/'bundle'; bundle.mkdir(); dest=root/'dest'; dest.mkdir()
            external=root/'outside'; external.write_bytes(b'unverified')
            t.write_bundle(bundle,[t.make_entry(P,b'expected')]); original=os.link
            def race(src,dst,*args,**kw):
                parent=kw['src_dir_fd']
                staging=next(name for name in os.listdir(parent) if name.startswith('.valve-transport-'))
                os.rename(staging,'retained-inode',src_dir_fd=parent,dst_dir_fd=parent)
                os.symlink(str(external),staging,dir_fd=parent)
                return original(src,dst,*args,**kw)
            with patch.object(t.os,'link',side_effect=race): result=t.restore(bundle,dest)
            self.assertEqual(result['created_files'],1)
            self.assertFalse((dest/P).is_symlink()); self.assertEqual((dest/P).read_bytes(),b'expected')
    def test_destination_symlink_race_is_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir=QA) as d:
            root=pathlib.Path(d); bundle=root/'bundle'; bundle.mkdir(); dest=root/'dest'; dest.mkdir()
            external=root/'outside'; external.write_bytes(b'unverified')
            t.write_bundle(bundle,[t.make_entry(P,b'expected')]); original=os.link
            def race(src,dst,*args,**kw):
                os.symlink(str(external),dst,dir_fd=kw['dst_dir_fd'])
                return original(src,dst,*args,**kw)
            with patch.object(t.os,'link',side_effect=race):
                with self.assertRaises((t.TransportError,OSError)): t.restore(bundle,dest)
            self.assertTrue((dest/P).is_symlink()); self.assertEqual(external.read_bytes(),b'unverified')
    def test_non_linux_publication_fails_closed_before_creating_paths(self):
        with tempfile.TemporaryDirectory(dir=QA) as d:
            root=pathlib.Path(d)
            with patch.object(t.sys,'platform','darwin'):
                with self.assertRaises(t.TransportError): t.write_bundle(root,[t.make_entry(P,b'expected')])
            self.assertEqual(list(root.rglob('*')),[])
    def test_writer_checks_blob_bytes_against_manifest_before_publication(self):
        with tempfile.TemporaryDirectory(dir=QA) as d:
            root=pathlib.Path(d); entry,blobs=t.make_entry(P,b'a','raw')
            blobs[0]=(blobs[0][0],b'b'*(t.CHUNK_BYTES+1))
            with self.assertRaises((t.TransportError,OSError)):
                t.write_bundle(root,[(entry,blobs)])
            self.assertEqual(list(root.rglob('*')),[])
    def test_direct_child_of_authorized_prefix_is_accepted(self):
        entry,_=t.make_entry('runs/20261006/direct.bin',b'x')
        self.assertEqual(entry['path'],'runs/20261006/direct.bin')

if __name__=='__main__': unittest.main(verbosity=2)
