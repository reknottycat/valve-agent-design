#!/usr/bin/env python3
"""Synthetic regression fixtures only; these are NOT native valve-solver results.

The analytical tetrahedron checks Python geometry independently. Tiny CSV
fixtures check refusal paths and cannot count toward a native PASS report.
"""
from pathlib import Path
import tempfile
import unittest

import numpy as np

import native_gate as gate


class NativeGateTests(unittest.TestCase):
    def tetra(self):
        points = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        faces = [(1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1)]
        patches = [{"name": "inlet", "startFace": 0, "nFaces": 1},
                   {"name": "wall", "startFace": 1, "nFaces": 3}]
        mesh = (points, faces, np.zeros(4, dtype=int), np.array([], dtype=int), patches, 1)
        # Closed-form moments and outward vectors for the unit coordinate tetrahedron.
        expected = (np.array([[0.25, 0.25, 0.25]]),
                    np.array([[1/3, 1/3, 1/3], [0, 1/3, 1/3],
                              [1/3, 0, 1/3], [1/3, 1/3, 0]]),
                    np.array([[0.5, 0.5, 0.5], [-0.5, 0, 0],
                              [0, -0.5, 0], [0, 0, -0.5]]),
                    np.array([1/6]))
        return mesh, expected

    def test_unit_tetra_geometry_matches_closed_form(self):
        mesh, expected = self.tetra()
        actual = gate.independent_geometry(mesh)
        for name, calculated, analytical in zip(("C", "Cf", "Sf", "V"), actual, expected):
            with self.subTest(quantity=name):
                np.testing.assert_allclose(calculated, analytical, rtol=0, atol=1e-15)
        np.testing.assert_allclose(actual[2].sum(axis=0), 0, rtol=0, atol=1e-15)

    def test_geometry_probe_rejects_patch_and_normal_tampering(self):
        mesh, expected = self.tetra()
        c, cf, sf, volume = expected
        cells = np.column_stack((np.arange(1), c, volume))
        clean_faces = np.column_stack((np.arange(4), cf, sf, [0, 1, 1, 1]))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            np.savetxt(root / "native_cells.csv", cells, delimiter=",", header="id,x,y,z,volume", comments="")
            np.savetxt(root / "native_faces.csv", clean_faces, delimiter=",", header="id,x,y,z,sx,sy,sz,patch", comments="")
            self.assertEqual(gate.compare_geometry(root, mesh, expected)["boundary_mapping"], "PASS")
            for name, row, column, replacement, message in (
                ("patch", 0, 7, 1, "Native patch mapping mismatch"),
                ("normal", 0, 4, -0.5, "Native versus independent Sf mismatch"),
            ):
                with self.subTest(tampering=name):
                    modified = clean_faces.copy()
                    modified[row, column] = replacement
                    np.savetxt(root / "native_faces.csv", modified, delimiter=",", header="id,x,y,z,sx,sy,sz,patch", comments="")
                    with self.assertRaisesRegex(gate.GateError, message):
                        gate.compare_geometry(root, mesh, expected)

    def assert_bad_mms_rejected(self, solution):
        centres = np.array([[1., 0., 0.], [2., 0., 0.]])
        exact = np.array([1., 4.])
        volumes = np.ones(2)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "1").mkdir()
            (root / "1/T").write_text("Synthetic fixture marker; not a native field.\n")
            values = np.column_stack((np.arange(2), solution, exact, solution-exact))
            np.savetxt(root / "manufactured_field.csv", values, delimiter=",", header="id,T,T_exact,error", comments="")
            # Even perfect claimed residuals must not hide an incorrect manufactured solution.
            history = np.column_stack((np.arange(1, 4), np.zeros((3, 4))))
            np.savetxt(root / "iterations.csv", history, delimiter=",",
                       header="iteration,initial_residual,final_residual,linear_iterations,max_scaled_update", comments="")
            with self.assertRaisesRegex(gate.GateError, "MMS L2=.*exceeds diagnostic gate"):
                gate.inspect_mms(root, centres, volumes)

    def test_wrong_nonconstant_mms_rejected_despite_zero_residuals(self):
        self.assert_bad_mms_rejected(np.array([1.2, 4.0]))

    def test_zero_source_constant_result_cannot_pass_nonzero_source_mms(self):
        self.assert_bad_mms_rejected(np.array([2.5, 2.5]))


if __name__ == "__main__":
    unittest.main()
