#!/usr/bin/env python3
"""Calculate a conditional liquid-flow Kv estimate, not a release value."""

import argparse
import json
import math


def positive_finite(value):
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a number") from None
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be finite and greater than zero")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flow-m3-s", type=positive_finite, required=True,
                        help="positive volumetric flow magnitude in m³/s")
    parser.add_argument("--pressure-drop-pa", type=positive_finite, required=True,
                        help="positive inlet-minus-outlet pressure difference in Pa")
    parser.add_argument("--density-kg-m3", type=positive_finite, required=True,
                        help="assumed liquid density in kg/m³")
    parser.add_argument("--flow-regime", choices=("laminar", "turbulent", "unknown"),
                        default="unknown")
    parser.add_argument("--convergence", choices=("converged", "unconverged", "unknown"),
                        default="unknown")
    args = parser.parse_args()

    try:
        kv = math.exp(math.log(args.flow_m3_s) + math.log(3600)
                      + 0.5 * (math.log(args.density_kg_m3) - math.log(1000)
                               - (math.log(args.pressure_drop_pa) - math.log(100000))))
    except (OverflowError, ValueError):
        parser.error("inputs produce an unrepresentable Kv")
    if not math.isfinite(kv) or kv == 0:
        parser.error("inputs produce an unrepresentable Kv")

    result = {
        "kv_m3_h": kv,
        "uncertainty": {"flag": "±30%", "validated": False},
        "status": "WARNING",
        "engineering_release": False,
        "capacity_status": "HOLD",
        "assumptions": [
            "Conditional liquid estimate: Kv = Q(m³/h) * sqrt((density/1000 kg/m³)/(pressure drop/bar)).",
            "Density and pressure drop are caller-provided assumptions, not authenticated measurements.",
            "The ±30% flag is indicative only; it is not a validated uncertainty bound.",
            "This estimate does not establish steady, turbulent, nonchoked flow or applicable product test conditions.",
            "Not a validated product capacity, acceptance result, or engineering release.",
        ],
        "flow_regime": args.flow_regime,
        "convergence": args.convergence,
        "warnings": [
            "WARNING: Conditional research estimate only; product capacity remains HOLD.",
        ],
    }
    if args.flow_regime != "turbulent":
        result["warnings"].append("WARNING: Flow regime is " + args.flow_regime + "; turbulent applicability is not established.")
    if args.convergence != "converged":
        result["warnings"].append("WARNING: Convergence is " + args.convergence + "; steady flow is not established.")
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
