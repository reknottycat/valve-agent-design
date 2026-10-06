import ast
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

import yaml

import probe
from geometry_gate import step_length_unit


HERE = Path(__file__).resolve().parent


class SafetyRegressionTests(unittest.TestCase):
    def test_probe_checks_cannot_be_disabled_with_python_optimize(self):
        r = subprocess.run([sys.executable, "-O", "-c",
                            "from probe import require; require(False, 'EXPECTED_NEGATIVE_CONTROL')"],
                           cwd=HERE, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("EXPECTED_NEGATIVE_CONTROL", r.stderr)

    def assert_geometry_only(self):
        tree = ast.parse((HERE / "proposals/cfd_boolean_only.py").read_text())
        functions = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        self.assertEqual(functions, {"build_geometry"})
        imports = {n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)}
        self.assertEqual(imports, {"os", "cadquery"})
        self.assertFalse(any(isinstance(n, ast.Name) and n.id in
                             {"subprocess", "run_point", "gen_mesh", "sh", "eval", "exec"}
                             for n in ast.walk(tree)))
        for node in tree.body:
            self.assertIsInstance(node, (ast.Expr, ast.Import, ast.Assign, ast.FunctionDef, ast.If))
            if isinstance(node, ast.Expr):
                self.assertIsInstance(node.value, ast.Constant)
            if isinstance(node, ast.If):
                self.assertEqual(len(node.body), 1)
                self.assertIsInstance(node.body[0], ast.Raise)
                self.assertFalse(node.orelse)

    def test_geometry_only_proposal_contains_no_solver_routes(self):
        self.assert_geometry_only()

    def test_direct_proposal_execution_cannot_launch_solver(self):
        # Check in THIS test before executing: unittest continues after failures in other tests.
        self.assert_geometry_only()
        r = subprocess.run([sys.executable, str(HERE / "proposals/cfd_boolean_only.py")],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("product solvers are disabled", r.stderr)

    def test_syntax_proposal_does_not_freeze_unknown_parameters(self):
        value = yaml.safe_load((HERE / "proposals/design_contract.syntax-only.yaml").read_text())
        self.assertIs(value["t07_freeze_decision"]["can_freeze"], False)
        self.assertIsNone(value["product"]["design_pressure"]["value"])
        self.assertIn("% 0", next(x["threshold"] for x in value["requirements"] if x["id"] == "REQ-ACT-01"))

    def test_step_metadata_must_be_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'unit.step'
            for content, expected in [('SI_UNIT(.MILLI.,.METRE.)', 'mm'),
                                      ('SI_UNIT($,.METRE.)', 'm'), ('', None),
                                      ('SI_UNIT(.MILLI.,.METRE.) SI_UNIT($,.METRE.)', None)]:
                p.write_text(content)
                self.assertEqual(step_length_unit(p)['unit'], expected)


if __name__ == "__main__":
    unittest.main()
