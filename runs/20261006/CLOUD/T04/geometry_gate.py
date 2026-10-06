"""Numerical geometry gates only; these never establish engineering acceptance."""
from __future__ import annotations

import math
from pathlib import Path
import re


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def check_geometry(measurement, *, expected_solids=1, expected_span=None, rtol=1e-6):
    if type(expected_solids) is not int or expected_solids < 1:
        raise ValueError("Expected solid count must be a positive integer")
    if not finite_number(rtol) or rtol < 0:
        raise ValueError("Tolerance must be finite and nonnegative")
    if expected_span is not None and (not finite_number(expected_span) or expected_span <= 0):
        raise ValueError("Expected span must be finite and positive")
    failures = []
    if measurement.get("valid") is not True:
        failures.append("INVALID_OR_UNKNOWN_BREP")
    count = measurement.get("solid_count")
    if type(count) is not int or count != expected_solids:
        failures.append("UNEXPECTED_SOLID_COUNT")
    volume = measurement.get("volume")
    if not finite_number(volume) or volume <= 0:
        failures.append("INVALID_OR_UNKNOWN_VOLUME")
    if expected_span is not None:
        span = measurement.get("x_span")
        if (not finite_number(span)
                or not math.isclose(span, expected_span, rel_tol=rtol, abs_tol=1e-7)):
            failures.append("UNITS_OR_EXTENT_MISMATCH")
    return {"status": "PASS" if not failures else "FAIL", "failures": failures}


def check_exchange(before, after, *, relative_volume_tolerance=1e-6):
    if not finite_number(relative_volume_tolerance) or relative_volume_tolerance < 0:
        raise ValueError("STEP exchange tolerance must be finite and nonnegative")
    failures = []
    for name, item in (("before", before), ("after", after)):
        result = check_geometry(item, expected_solids=before.get("solid_count", 1))
        failures.extend(f"{name}:{x}" for x in result["failures"])
    error = None
    if not failures:
        error = abs(before["volume"] - after["volume"]) / before["volume"]
        if error > relative_volume_tolerance:
            failures.append("STEP_VOLUME_DRIFT")
        for axis in ("x_span", "y_span", "z_span"):
            a, b = before.get(axis), after.get(axis)
            if not finite_number(a) or not finite_number(b) or a <= 0 or b <= 0:
                failures.append("STEP_UNKNOWN_EXTENT:" + axis)
            elif not math.isclose(a, b, rel_tol=relative_volume_tolerance, abs_tol=1e-7):
                failures.append("STEP_EXTENT_DRIFT:" + axis)
    return {"status": "PASS" if not failures else "FAIL", "failures": failures,
            "relative_volume_error": error, "relative_volume_tolerance": relative_volume_tolerance}


def step_length_unit(path):
    """Recognize SI metre-based units; reject unknown/mixed encodings, never infer from a filename."""
    content = Path(path).read_text()
    prefixes = set(re.findall(r"SI_UNIT\s*\(\s*(\$|\.[A-Z]+\.)\s*,\s*\.METRE\.\s*\)", content))
    factors = {".MILLI.": ("mm", .001), "$": ("m", 1.0), ".CENTI.": ("cm", .01),
               ".MICRO.": ("um", .000001)}
    if len(prefixes) != 1 or not prefixes <= factors.keys() or "CONVERSION_BASED_UNIT" in content:
        return {"status": "UNKNOWN", "unit": None, "metres_per_unit": None}
    name, factor = factors[next(iter(prefixes))]
    return {"status": "VERIFIED_METADATA", "unit": name, "metres_per_unit": factor}


def product_decision(geometry_results, *, basis_frozen, interfaces_frozen):
    reasons = []
    if basis_frozen is not True:
        reasons.append("T07_BASIS_NOT_FROZEN")
    if interfaces_frozen is not True:
        reasons.append("I1_INTERFACES_NOT_FROZEN")
    if not geometry_results or any(item.get("status") != "PASS" for item in geometry_results):
        reasons.append("GEOMETRY_NOT_VERIFIED")
    # This module is not authorized to freeze a product even when numerical gates pass.
    return {"decision": "HOLD" if reasons else "REVIEW_REQUIRED",
            "reasons": reasons, "manufacturing_release": False,
            "geometry_prerequisites_met": not reasons,
            "product_solver_authorized": False, "evidence_ceiling": "E1"}


def measure(shape):
    b = shape.BoundingBox()
    solids = shape.Solids()
    return {"valid": shape.isValid(), "solid_count": len(solids),
            "volume": shape.Volume(), "x_span": b.xlen, "y_span": b.ylen, "z_span": b.zlen,
            "bbox": {"xmin": b.xmin, "xmax": b.xmax, "ymin": b.ymin,
                     "ymax": b.ymax, "zmin": b.zmin, "zmax": b.zmax},
            "components": [{"volume": s.Volume(), "xmin": s.BoundingBox().xmin,
                            "xmax": s.BoundingBox().xmax} for s in solids]}
