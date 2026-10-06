import unittest

from geometry_gate import check_exchange, check_geometry, product_decision


class GeometryGateTests(unittest.TestCase):
    def valid(self, **overrides):
        return dict(valid=True, solid_count=1, volume=10.0, x_span=1500.0, y_span=200., z_span=200., **overrides)

    def test_connected_domain_passes_numeric_gate(self):
        self.assertEqual(check_geometry(self.valid(), expected_span=1500)["status"], "PASS")

    def test_disconnected_domain_rejected(self):
        m = self.valid(); m["solid_count"] = 2
        self.assertIn("UNEXPECTED_SOLID_COUNT", check_geometry(m)["failures"])

    def test_mixed_millimetres_metres_rejected(self):
        m = self.valid(); m["x_span"] = 301.2
        self.assertIn("UNITS_OR_EXTENT_MISMATCH", check_geometry(m, expected_span=1500)["failures"])

    def test_invalid_brep_rejected(self):
        m = self.valid(); m["valid"] = False
        self.assertEqual(check_geometry(m)["status"], "FAIL")

    def test_missing_or_nonfinite_measurements_rejected(self):
        for item in ({}, {"valid": True, "solid_count": 1, "volume": float("nan")},
                     {"valid": True, "solid_count": True, "volume": 10}):
            self.assertEqual(check_geometry(item)["status"], "FAIL")

    def test_all_six_parts_require_roundtrip(self):
        a = self.valid(); b = self.valid(); b["volume"] = 10.001
        self.assertEqual(check_exchange(a, b)["status"], "FAIL")

    def test_roundtrip_preserves_multiple_solids_but_does_not_approve_them(self):
        a = self.valid(); a["solid_count"] = 2
        self.assertEqual(check_exchange(a, a)["status"], "PASS")
        self.assertEqual(check_geometry(a)["status"], "FAIL")

    def test_baseline_unknown_or_unfrozen_blocks_solver(self):
        for value in (False, None, "true"):
            d = product_decision([{"status": "PASS"}], basis_frozen=value, interfaces_frozen=True)
            self.assertEqual(d["decision"], "HOLD"); self.assertFalse(d["geometry_prerequisites_met"])

    def test_missing_checks_block_solver(self):
        d = product_decision([], basis_frozen=True, interfaces_frozen=True)
        self.assertEqual(d["decision"], "HOLD")

    def test_unknown_check_blocks_solver(self):
        d = product_decision([{}], basis_frozen=True, interfaces_frozen=True)
        self.assertEqual(d["decision"], "HOLD")

    def test_numeric_success_is_not_manufacturing_release(self):
        d = product_decision([{"status": "PASS"}], basis_frozen=True, interfaces_frozen=True)
        self.assertEqual(d["decision"], "REVIEW_REQUIRED"); self.assertFalse(d["manufacturing_release"])
        self.assertFalse(d["product_solver_authorized"])

    def test_boolean_volume_rejected(self):
        a = self.valid(); a["volume"] = True
        self.assertEqual(check_geometry(a)["status"], "FAIL")

    def test_empty_shape_exchange_rejected(self):
        a = self.valid(); a["solid_count"] = 0
        with self.assertRaises(ValueError):
            check_exchange(a, a)

    def test_invalid_tolerance_rejected(self):
        for tol in (float('nan'), float('inf'), -1, True):
            with self.assertRaises(ValueError):
                check_exchange(self.valid(), self.valid(), relative_volume_tolerance=tol)

    def test_volume_preserving_extent_drift_rejected(self):
        a = self.valid(); b = self.valid(); b['x_span'] = 15000.
        self.assertIn('STEP_EXTENT_DRIFT:x_span', check_exchange(a, b)['failures'])


if __name__ == "__main__":
    unittest.main()
