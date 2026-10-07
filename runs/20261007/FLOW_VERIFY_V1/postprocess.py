#!/usr/bin/env python3
"""Fail-closed scalar/residual checks for the fixed Re10 diagnostic.

This gate does not replace the runner's input binding, zero-exit-code, native
field-bounds, valve-domain PDE, or mesh gates. It is not engineering acceptance.
Only Python's standard library is required.
"""
import argparse
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import tempfile


WINDOW = 100
LIMITS = {
    "minimum_common_samples": WINDOW,
    "tail_samples": WINDOW,
    "p_initial_residual_max": 1e-7,
    "U_component_initial_residual_max": 1e-8,
    "flow_relative_range_max": 1e-3,
    "pressure_drop_relative_range_max": 1e-3,
    "mass_imbalance_max": 1e-6,
    "wall_net_leakage_relative_max": 1e-10,
}
FUNCTIONS = ("qIn", "qOut", "qWall", "pIn", "pOut")
FIELDS = ("Ux", "Uy", "Uz", "p")
COLUMNS = (
    "time", "qin_m3_s", "qout_m3_s", "qwall_net_m3_s",
    "pin_kinematic_m2_s2", "pout_kinematic_m2_s2",
    "dp_kinematic_m2_s2", "dp_static_Pa", "reference_velocity_m_s",
    "zeta_port_static", "mass_imbalance", "wall_net_leakage_relative",
    "Ux_initial_residual", "Uy_initial_residual", "Uz_initial_residual",
    "p_initial_residual",
)
TIME_RE = re.compile(r"^Time\s*=\s*(\S+)\s*$")
RESIDUAL_RE = re.compile(
    r"Solving for (Ux|Uy|Uz|p),\s*Initial residual = ([^,\s]+),"
    r"\s*Final residual = ([^,\s]+),\s*No Iterations ([^,\s]+)"
)


class EvidenceError(ValueError):
    pass


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite(value, label):
    if isinstance(value, bool):
        raise EvidenceError(f"{label}: booleans are not measurements")
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise EvidenceError(f"{label}: invalid number {value!r}") from exc
    if not math.isfinite(number):
        raise EvidenceError(f"{label}: nonfinite value")
    return number


def time_value(value, label):
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise EvidenceError(f"{label}: invalid time") from exc
    if not result.is_finite() or result < 0:
        raise EvidenceError(f"{label}: invalid/nonfinite/negative time")
    return result


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=path.name + ".", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(text)
    os.replace(temporary, path)


def write_json(path, value):
    atomic_text(path, json.dumps(value, indent=2, allow_nan=False) + "\n")


def read_scalar_history(directory, name):
    candidates = list((directory / name).glob("*/surfaceFieldValue.dat"))
    if not candidates:
        raise EvidenceError(f"Missing {name} surfaceFieldValue.dat")
    # The runner creates a fresh case. Multiple start-time folders would conceal
    # restart/stale data, so merging them is deliberately unsupported.
    if len(candidates) != 1:
        raise EvidenceError(f"{name}: multiple history files/restarts are not allowed")
    source = candidates[0]
    samples = {}
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        label = f"{source}:{line_number}"
        if len(parts) != 2:
            raise EvidenceError(f"{label}: expected exactly time and one scalar")
        time = time_value(parts[0], label)
        if samples and time <= next(reversed(samples)):
            raise EvidenceError(f"{label}: duplicate or unordered time")
        samples[time] = finite(parts[1], label)
    if not samples:
        raise EvidenceError(f"{source}: empty history")
    return samples, source, digest


def read_residual_history(path):
    text = path.read_text()
    if re.search(r"FOAM\s+FATAL|Floating point exception", text, re.IGNORECASE):
        raise EvidenceError("Fatal solver diagnostic in log.simpleFoam")
    residuals = {}
    current = None
    ended = False
    for line in text.splitlines():
        stripped = line.strip()
        match = TIME_RE.match(stripped)
        if match:
            if ended:
                raise EvidenceError("Solver Time appears after End; appended/stale log")
            current = time_value(match.group(1), "solver log")
            if residuals and current <= next(reversed(residuals)):
                raise EvidenceError("Duplicate or unordered solver Time")
            residuals[current] = {field: [] for field in FIELDS}
            continue
        match = RESIDUAL_RE.search(line)
        if match:
            if current is None or ended:
                raise EvidenceError("Residual outside a live solver Time block")
            field, initial_text, final_text, iterations_text = match.groups()
            initial = finite(initial_text, f"{field} initial residual")
            final = finite(final_text, f"{field} final residual")
            iterations = finite(iterations_text, f"{field} iterations")
            if initial < 0 or final < 0 or iterations < 0 or not iterations.is_integer():
                raise EvidenceError("Invalid negative residual or iteration count")
            residuals[current][field].append(initial)
        if stripped == "End":
            if ended:
                raise EvidenceError("Repeated End marker in solver log")
            ended = True
    if not ended or not residuals:
        raise EvidenceError("Solver log has no completed Time history and terminal End")
    for time, values in residuals.items():
        missing = [field for field in FIELDS if not values[field]]
        if missing:
            raise EvidenceError(f"Time {time}: missing residuals for {missing}")
        # Include every pressure/nonorthogonal corrector, not just the final
        # almost-zero solve, to avoid masking an unconverged outer iteration.
        residuals[time] = {field: max(values[field]) for field in FIELDS}
    return residuals


def relative_range(values):
    mean = math.fsum(values) / len(values)
    denominator = abs(mean)
    if not math.isfinite(mean) or denominator == 0:
        raise EvidenceError("Cannot normalize a zero/nonfinite stabilization mean")
    return (max(values) - min(values)) / denominator


def make_rows(histories, residuals, rho, diameter):
    solver_times = list(residuals)
    if len(solver_times) < WINDOW:
        raise EvidenceError(f"Need at least {WINDOW} completed common times")
    for name, history in histories.items():
        # An optional pre-solve t=0 function-object write is allowed; no interior
        # gaps, tail omission, or history beyond the solver log may be hidden.
        measurement_times = list(history)
        if measurement_times and measurement_times[0] == 0 and solver_times[0] > 0:
            measurement_times = measurement_times[1:]
        if measurement_times != solver_times:
            raise EvidenceError(f"{name}: stale, missing, or extra times relative to solver log")
    area = math.pi * diameter * diameter / 4
    rows = []
    for time in solver_times:
        qin, qout, wall, pin, pout = [histories[name][time] for name in FUNCTIONS]
        denominator = max(abs(qin), abs(qout))
        if denominator == 0:
            raise EvidenceError(f"Time {time}: zero flow denominator")
        velocity = qout / area
        dynamic_pressure = 0.5 * rho * velocity * velocity
        if dynamic_pressure == 0 or not math.isfinite(dynamic_pressure):
            raise EvidenceError(f"Time {time}: invalid dynamic-pressure denominator")
        dp_kinematic = pin - pout
        dp = rho * dp_kinematic
        row = {
            "time": str(time), "qin_m3_s": qin, "qout_m3_s": qout,
            "qwall_net_m3_s": wall, "pin_kinematic_m2_s2": pin,
            "pout_kinematic_m2_s2": pout, "dp_kinematic_m2_s2": dp_kinematic,
            "dp_static_Pa": dp, "reference_velocity_m_s": velocity,
            "zeta_port_static": dp / dynamic_pressure,
            "mass_imbalance": abs(qin + qout) / denominator,
            "wall_net_leakage_relative": abs(wall) / abs(qout),
        }
        row.update({f"{field}_initial_residual": residuals[time][field] for field in FIELDS})
        for key, value in row.items():
            if key != "time":
                finite(value, f"Time {time}: {key}")
        rows.append(row)
    return rows


def check_tail(rows):
    tail = rows[-WINDOW:]
    maximum_residuals = {
        field: max(row[f"{field}_initial_residual"] for row in tail) for field in FIELDS
    }
    flow_range = relative_range([row["qout_m3_s"] for row in tail])
    pressure_range = relative_range([row["dp_static_Pa"] for row in tail])
    maximum_imbalance = max(row["mass_imbalance"] for row in tail)
    maximum_leakage = max(row["wall_net_leakage_relative"] for row in tail)
    checks = {
        "inlet_outlet_signs": all(row["qin_m3_s"] < 0 < row["qout_m3_s"] for row in tail),
        "positive_static_pressure_drop": all(row["dp_static_Pa"] > 0 for row in tail),
        "p_residual": maximum_residuals["p"] <= LIMITS["p_initial_residual_max"],
        "U_residuals": all(maximum_residuals[field] <= LIMITS["U_component_initial_residual_max"]
                           for field in ("Ux", "Uy", "Uz")),
        "flow_stabilization": flow_range <= LIMITS["flow_relative_range_max"],
        "pressure_stabilization": pressure_range <= LIMITS["pressure_drop_relative_range_max"],
        "mass_balance": maximum_imbalance <= LIMITS["mass_imbalance_max"],
        "wall_net_leakage": maximum_leakage <= LIMITS["wall_net_leakage_relative_max"],
    }
    return checks, {
        "tail_first_time": tail[0]["time"], "tail_last_time": tail[-1]["time"],
        "maximum_initial_residuals": maximum_residuals,
        "flow_relative_range": flow_range, "pressure_drop_relative_range": pressure_range,
        "maximum_mass_imbalance": maximum_imbalance,
        "maximum_wall_net_leakage_relative": maximum_leakage,
    }


def write_history(path, rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_text(path, output.getvalue())


def process(run_root, manifest_path, output_dir=None):
    run_root, manifest_path = Path(run_root).resolve(), Path(manifest_path).resolve()
    output_dir = Path(output_dir).resolve() if output_dir else run_root
    result_path, history_path = output_dir / "results.json", output_dir / "history.csv"
    result = {
        "schema": "valve.flow-diagnostic-postprocess/1.0",
        "status": "RUNNING",
        "scope": "NUMERICAL_DIAGNOSTIC_POSTPROCESS_ONLY",
        "manufacturing_authorized": False,
        "engineering_acceptance": False,
        "actual_mesh_flux_m3_s": None,
        "computed_pressure_drop_Pa": None,
        "computed_loss_coefficient": None,
        "coefficient_kind": "STATIC_PRESSURE_PORT_TO_PORT_INCLUDING_EXTENSIONS",
        "isolated_valve_coefficient": None,
        "drawing_note24_limit_assessment": "UNASSESSED",
        "observed": None,
        "limits": LIMITS,
        "limits_kind": "NEW_NUMERICAL_DIAGNOSTIC_GATES_NOT_ENGINEERING_REQUIREMENTS",
        "required_runner_gates": [
            "input_and_source_binding", "solver_returncode_zero", "mesh_v2_and_fresh_checkMesh",
            "native_face_field_probe", "nonzero_source_valve_PDE_and_sensitivity", "native_field_bounds",
        ],
        "notes": [
            "Actual values are final-time samples, released only when these postprocessing gates pass.",
            "Qactual is outward outlet surface flux; p is kinematic and is multiplied by density.",
            "Net wall leakage alone cannot rule out cancelling local leakage; native noSlip/bounds gate is separate.",
            "Contact, joints, pressure/load reconstruction, and manufacturing remain outside this gate.",
        ],
        "errors": [],
    }
    write_json(result_path, result)
    # Clear any previous CSV before reading evidence: a failed rerun cannot leave
    # an old apparently-current successful history beside its new failure record.
    write_history(history_path, [])
    try:
        manifest_hash = sha256(manifest_path)
        manifest = json.loads(manifest_path.read_text())
        selected = manifest["selected"]
        rho = finite(selected["density_kg_m3"], "density_kg_m3")
        diameter = finite(selected["nominal_diameter_m"], "nominal_diameter_m")
        if rho <= 0 or diameter <= 0:
            raise EvidenceError("Density and diameter must be positive")
        result["selected"] = {"density_kg_m3": rho, "nominal_diameter_m": diameter}
        log = run_root / "case" / "log.simpleFoam"
        sources = {str(manifest_path): manifest_hash, str(log): sha256(log),
                   str(Path(__file__).resolve()): sha256(__file__)}
        residuals = read_residual_history(log)
        histories = {}
        for name in FUNCTIONS:
            history, source, digest = read_scalar_history(run_root / "case" / "postProcessing", name)
            histories[name] = history
            sources[str(source)] = digest
        rows = make_rows(histories, residuals, rho, diameter)
        checks, metrics = check_tail(rows)
        result["checks"] = checks
        result["metrics"] = metrics
        result["common_samples"] = len(rows)
        result["observed"] = rows[-1]
        for path, expected in sources.items():
            if sha256(path) != expected:
                raise EvidenceError(f"Input changed during postprocessing: {path}")
        result["input_sha256"] = sources
        write_history(history_path, rows)
        if all(checks.values()):
            result["status"] = "DIAGNOSTIC_PASS"
            result["actual_mesh_flux_m3_s"] = rows[-1]["qout_m3_s"]
            result["computed_pressure_drop_Pa"] = rows[-1]["dp_static_Pa"]
            result["computed_loss_coefficient"] = rows[-1]["zeta_port_static"]
        else:
            result["status"] = "FAIL"
            result["errors"] = [f"Gate failed: {name}" for name, passed in checks.items() if not passed]
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        result["status"] = "FAIL"
        result["errors"].append(f"{type(exc).__name__}: {exc}")
    result["history_sha256"] = sha256(history_path)
    write_json(result_path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    result = process(args.run_root, args.manifest, args.output_dir)
    print(json.dumps({"status": result["status"], "errors": result["errors"]}, allow_nan=False))
    return 0 if result["status"] == "DIAGNOSTIC_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
