"""Small adversarial tests of measurements, units, and failure output handling."""
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("flow_postprocess", Path(__file__).with_name("postprocess.py"))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PostprocessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.manifest = self.root / "manifest.json"
        self.rho = 1024.9109328963
        self.diameter = 0.2
        self.q = 1.650060221652016e-6
        self.dp_kinematic = 1.0e-7
        self.manifest.write_text(json.dumps({"selected": {
            "density_kg_m3": self.rho, "nominal_diameter_m": self.diameter}}))
        self.make_fixture()

    def tearDown(self):
        self.temporary.cleanup()

    def make_fixture(self, count=110):
        case = self.root / "case"
        case.mkdir(exist_ok=True)
        log = []
        for time in range(1, count + 1):
            log.append(f"Time = {time}")
            for field in MODULE.FIELDS:
                residual = 1e-9 if field == "p" else 1e-10
                log.append(f"smoothSolver: Solving for {field}, Initial residual = {residual}, "
                           "Final residual = 1e-12, No Iterations 2")
        log.append("End")
        (case / "log.simpleFoam").write_text("\n".join(log) + "\n")
        self.values = {"qIn": -self.q, "qOut": self.q, "qWall": 0,
                       "pIn": self.dp_kinematic, "pOut": 0}
        for name, value in self.values.items():
            target = self.history(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# Time scalar\n" + "".join(
                f"{time} {value:.17g}\n" for time in range(1, count + 1)))

    def history(self, name):
        return self.root / "case" / "postProcessing" / name / "0" / "surfaceFieldValue.dat"

    def run_gate(self):
        return MODULE.process(self.root, self.manifest)

    def assert_failed(self, result):
        self.assertEqual(result["status"], "FAIL")
        for key in ("actual_mesh_flux_m3_s", "computed_pressure_drop_Pa", "computed_loss_coefficient"):
            self.assertIsNone(result[key])

    def test_pass_converts_kinematic_pressure_and_uses_actual_outlet_flow(self):
        result = self.run_gate()
        self.assertEqual(result["status"], "DIAGNOSTIC_PASS")
        self.assertEqual(result["actual_mesh_flux_m3_s"], self.q)
        self.assertAlmostEqual(result["computed_pressure_drop_Pa"], self.rho * self.dp_kinematic)
        area = math.pi * self.diameter ** 2 / 4
        expected = 2 * self.dp_kinematic / (self.q / area) ** 2
        self.assertAlmostEqual(result["computed_loss_coefficient"], expected)
        self.assertFalse(result["engineering_acceptance"])

    def test_density_scaling_changes_pa_but_not_dimensionless_coefficient(self):
        original = self.run_gate()
        self.manifest.write_text(json.dumps({"selected": {
            "density_kg_m3": self.rho * 2, "nominal_diameter_m": self.diameter}}))
        changed = self.run_gate()
        self.assertEqual(changed["status"], "DIAGNOSTIC_PASS")
        self.assertAlmostEqual(changed["computed_pressure_drop_Pa"], 2 * original["computed_pressure_drop_Pa"])
        self.assertAlmostEqual(changed["computed_loss_coefficient"], original["computed_loss_coefficient"])

    def test_missing_history_replaces_previous_pass_and_clears_csv(self):
        self.assertEqual(self.run_gate()["status"], "DIAGNOSTIC_PASS")
        self.history("pOut").unlink()
        self.assert_failed(self.run_gate())
        self.assertEqual(len((self.root / "history.csv").read_text().splitlines()), 1)
        self.assertEqual(json.loads((self.root / "results.json").read_text())["status"], "FAIL")

    def test_stale_history_tail_is_rejected(self):
        path = self.history("qOut")
        path.write_text("\n".join(path.read_text().splitlines()[:-1]) + "\n")
        self.assert_failed(self.run_gate())

    def test_nonfinite_history_and_residuals_are_rejected(self):
        with self.subTest("history"):
            path = self.history("pIn")
            path.write_text(path.read_text().replace("110 9.9999999999999995e-08", "110 nan"))
            self.assert_failed(self.run_gate())
        self.make_fixture()
        with self.subTest("residual"):
            path = self.root / "case" / "log.simpleFoam"
            path.write_text(path.read_text().replace("Initial residual = 1e-09", "Initial residual = nan"))
            self.assert_failed(self.run_gate())

    def test_wrong_signs_keep_observations_but_withhold_actual_results(self):
        for name in ("qIn", "qOut"):
            value = -self.values[name]
            self.history(name).write_text("# Time scalar\n" + "".join(
                f"{time} {value:.17g}\n" for time in range(1, 111)))
        result = self.run_gate()
        self.assert_failed(result)
        self.assertIsNotNone(result["observed"])
        self.assertFalse(result["checks"]["inlet_outlet_signs"])

    def test_pressure_oscillation_and_wall_leakage_fail_independent_gates(self):
        self.history("pIn").write_text("# Time scalar\n" + "".join(
            f"{time} {self.dp_kinematic * (1.01 if time % 2 else 1):.17g}\n" for time in range(1, 111)))
        self.history("qWall").write_text("# Time scalar\n" + "".join(
            f"{time} {self.q * 1e-8:.17g}\n" for time in range(1, 111)))
        result = self.run_gate()
        self.assert_failed(result)
        self.assertFalse(result["checks"]["pressure_stabilization"])
        self.assertFalse(result["checks"]["wall_net_leakage"])

    def test_incomplete_log_and_too_few_samples_fail(self):
        self.make_fixture(count=99)
        self.assert_failed(self.run_gate())
        self.make_fixture()
        log = self.root / "case" / "log.simpleFoam"
        log.write_text(log.read_text().removesuffix("End\n"))
        self.assert_failed(self.run_gate())

    def test_pressure_corrector_cannot_hide_high_outer_residual(self):
        log = self.root / "case" / "log.simpleFoam"
        text = log.read_text().replace("Time = 110\n", "Time = 110\n"
            "GAMG: Solving for p, Initial residual = 1e-4, Final residual = 1e-12, No Iterations 4\n")
        log.write_text(text)
        result = self.run_gate()
        self.assert_failed(result)
        self.assertFalse(result["checks"]["p_residual"])

    def test_mass_imbalance_cannot_be_hidden_by_stable_flow(self):
        self.history("qIn").write_text("# Time scalar\n" + "".join(
            f"{time} {-self.q * 1.001:.17g}\n" for time in range(1, 111)))
        result = self.run_gate()
        self.assert_failed(result)
        self.assertFalse(result["checks"]["mass_balance"])


if __name__ == "__main__":
    unittest.main()
