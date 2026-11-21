"""Real saved study arithmetic regression, NOT a whole-valve validation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'original/R1/C4/T15/calculate_loads.py'
spec=importlib.util.spec_from_file_location('original_calculator',P)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
d=json.loads((P.parent/'load_study.json').read_text())

class OriginalArithmetic(unittest.TestCase):
    def test_original_calculator_byte_identity(self):
        self.assertEqual(hashlib.sha256(P.read_bytes()).hexdigest(), d['calculator_sha256'])
    def test_all_saved_screw_scenarios(self):
        for row in d['drive_sensitivity']['rows']:
            with self.subTest(mu=row['thread_mu_assumed'],collar=row['collar_mu_assumed']):
                actual=m.screw_model(row['load_used_N'],33,6,15,row['thread_mu_assumed'])
                for key in ('thread_torque_Nm','ideal_frictionless_torque_Nm','thread_efficiency','self_lock_mu_threshold'):
                    self.assertAlmostEqual(actual[key],row[key],places=10)
                self.assertEqual(actual['static_self_lock_model'],row['static_self_lock_model'])
    def test_reject_nonfinite_pressure(self):
        with self.assertRaises(ValueError):m.pressure_force({'inlet':1,'outlet':-1},float('nan'),0)

if __name__=='__main__':unittest.main()
