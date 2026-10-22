"""Synthetic arithmetic smoke tests only; NOT validated engineering implementations.

Run: python -m unittest discover -s /workspace/shared/valve-research -p test_mechanical_arithmetic.py -v
No external packages, network, standards, real material constants or customer files.
"""
import unittest


class SyntheticArithmeticTests(unittest.TestCase):
    def test_uniform_pressure_force(self):
        self.assertAlmostEqual(2e6 * 1e-3, 2000.0, places=9)

    def test_ideal_square_thread_raise_torque(self):
        load_N, mean_diameter_m, tan_lead, synthetic_mu = 1000, 0.02, 0.1, 0.2
        torque = load_N * mean_diameter_m / 2 * (tan_lead + synthetic_mu) / (1 - synthetic_mu * tan_lead)
        self.assertAlmostEqual(torque, 3.061224489795918, places=12)

    def test_free_linear_expansion(self):
        synthetic_alpha_per_K, length_m, temperature_change_K = 1e-5, 0.1, 100
        self.assertAlmostEqual(synthetic_alpha_per_K * length_m * temperature_change_K, 1e-4, places=12)

    def test_thin_cylinder_membrane_stresses(self):
        pressure_Pa, radius_m, thickness_m = 1e6, 0.1, 0.001
        self.assertAlmostEqual(pressure_Pa * radius_m / thickness_m, 100e6, places=6)
        self.assertAlmostEqual(pressure_Pa * radius_m / (2 * thickness_m), 50e6, places=6)


if __name__ == '__main__':
    unittest.main(verbosity=2)
