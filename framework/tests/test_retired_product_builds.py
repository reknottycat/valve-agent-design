"""Retired DN200 entry paths must stop before importing a historical builder."""
import ast
import hashlib
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / 'verification/valve-3d-cfd-57mm'
ARCHIVED = {
    'v19/valve_cfd_release.py': 'ac012a58ed30c18b18327ea0d385d82ef9c068c9',
    'v20/valve_cfd_release.py': 'f47bf1234cf22db319387dc41d1853665609830b',
    'v21/valve_cfd_release.py': '02aa85ae013611d97079bbf9ebb6c3137a344879',
    'v21/geometry/mesh_trial.py': '2010e1f0418ad94c531ccf91e4e34ac5be869091',
    'v22/geometry/mesh_trial.py': '045267f74ec926669e7eff5ede877b77b914479a',
}


class ArchivedBuilds(unittest.TestCase):
    def test_history_is_byte_preserved_and_not_an_alternate_launcher(self):
        self.assertTrue((CASE / 'valve_3d_cfd.py').is_file())
        self.assertEqual({p.relative_to(CASE).as_posix() for p in CASE.glob('v[0-9]*/**/*.py')}, set(ARCHIVED),
                         'Store historical sources as .py.txt, not runnable builds.')
        for relative, expected in ARCHIVED.items():
            with self.subTest(relative=relative):
                entry = CASE / relative
                data = entry.with_suffix('.py.txt').read_bytes()
                self.assertEqual(hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(), expected)
                # Inspect before executing: a restored historical job may install software or submit work.
                code = ast.parse(entry.read_bytes()); self.assertEqual(len(code.body), 1)
                self.assertIsInstance(code.body[0], ast.Raise)
                call = code.body[0].exc; self.assertIsInstance(call, ast.Call)
                self.assertIsInstance(call.func, ast.Name); self.assertEqual(call.func.id, 'SystemExit')
                self.assertEqual(len(call.args), 1); self.assertIsInstance(call.args[0], ast.Constant)
                self.assertIsInstance(call.args[0].value, str); self.assertFalse(call.keywords)
                self.assertIsNone(code.body[0].cause)
                result = subprocess.run([sys.executable, '-I', str(entry)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0); self.assertIn('CURRENT_PLAN.md', result.stderr)
