import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import verify_frozen_artifacts as gate


class CheckpointIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / 'frozen'
        self.base.mkdir()
        (self.base / 'part.txt').write_text('frozen evidence\n')
        self.rows = [{'path': 'part.txt', 'bytes': 16, 'sha256': gate.sha256(self.base / 'part.txt')}]
        self.checkpoint = {'frozen_directories': [{'path': 'frozen', 'file_count': 1}], 'archives': []}
        self.write_manifest()

    def write_manifest(self):
        manifest = self.base / 'artifact_manifest.json'
        manifest.write_text(json.dumps({'files': self.rows}))
        self.checkpoint['frozen_directories'][0]['manifest_sha256'] = gate.sha256(manifest)

    def test_valid_is_read_only_and_not_engineering_acceptance(self):
        before = {p.name: p.read_bytes() for p in self.base.iterdir()}
        result = gate.verify(self.root, self.checkpoint)
        self.assertEqual(result['status'], 'FROZEN_ARTIFACT_INTEGRITY_PASS')
        self.assertFalse(result['engineering_acceptance'])
        self.assertFalse(result['manufacturing_authorized'])
        self.assertFalse(result['archives_requested'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.base.iterdir()})

    def test_changed_file_rejected(self):
        (self.base / 'part.txt').write_text('altered evidence')
        with self.assertRaises(ValueError):
            gate.verify(self.root, self.checkpoint)

    def test_missing_file_rejected(self):
        (self.base / 'part.txt').unlink()
        with self.assertRaises(ValueError):
            gate.verify(self.root, self.checkpoint)

    def test_changed_manifest_rejected(self):
        (self.base / 'artifact_manifest.json').write_text('{}')
        with self.assertRaises(ValueError):
            gate.verify(self.root, self.checkpoint)

    def test_duplicate_record_rejected(self):
        self.rows.append(copy.deepcopy(self.rows[0]))
        self.checkpoint['frozen_directories'][0]['file_count'] = 2
        self.write_manifest()
        with self.assertRaises(ValueError):
            gate.verify(self.root, self.checkpoint)

    def test_unsafe_path_rejected(self):
        self.rows[0]['path'] = '../part.txt'
        self.write_manifest()
        with self.assertRaises(ValueError):
            gate.verify(self.root, self.checkpoint)

    def test_symlink_rejected(self):
        (self.root / 'external.txt').write_text('frozen evidence\n')
        (self.base / 'part.txt').unlink()
        (self.base / 'part.txt').symlink_to(self.root / 'external.txt')
        with self.assertRaises(ValueError):
            gate.verify(self.root, self.checkpoint)

    def test_bad_size_type_rejected(self):
        self.rows[0]['bytes'] = True
        self.write_manifest()
        with self.assertRaises(ValueError):
            gate.verify(self.root, self.checkpoint)

    def test_requested_missing_archive_rejected(self):
        self.checkpoint['archives'] = [{'filename': 'missing.zip', 'sha256': '0' * 64}]
        with self.assertRaises(ValueError):
            gate.verify(self.root, self.checkpoint, self.root)

    def test_archive_hash_mismatch_rejected(self):
        (self.root / 'archive.zip').write_bytes(b'not a valid zip')
        self.checkpoint['archives'] = [{'filename': 'archive.zip', 'sha256': '0' * 64}]
        with self.assertRaises(ValueError):
            gate.verify(self.root, self.checkpoint, self.root)


if __name__ == '__main__':
    unittest.main()
