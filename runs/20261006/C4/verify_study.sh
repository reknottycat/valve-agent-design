#!/usr/bin/env bash
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../../.." && pwd)"
python="${VALVE_PYTHON:-$root/.venv-cloud/bin/python}"
export PYTHONDONTWRITEBYTECODE=1
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp/valve-cache}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/valve-mpl}"
# This script writes only C4 outputs and temporary library caches. It never installs,
# calls OpenFOAM/CalculiX, changes GitHub or edits the frozen C2/C3 artifacts.
"$python" "$root/docs/checkpoint/verify_frozen_artifacts.py"
"$python" "$here/T06/basis_gate.py"
"$python" "$here/T06/seawater_study.py" > "$here/T06/fluid-properties.log"
"$python" "$here/T19/extract_pressure_faces.py" > "$here/T19/pressure-faces.log" 2>&1
"$python" "$here/T15/calculate_loads.py" > "$here/T15/calculations.log"
"$python" -m unittest discover -s "$here" -p 'test_*.py' -v > "$here/tests.log" 2>&1
"$python" -O -m unittest discover -s "$here" -p 'test_*.py' -v > "$here/tests-optimized.log" 2>&1
"${VALVE_DRAWING_PYTHON:-python}" "$here/T40/draw_load_study.py" > "$here/T40/drawing.log"
"$python" "$here/T22/check_current_evidence.py"
printf 'C4 study checks passed; engineering/manufacturing release remains HOLD. No solver or network write.\n'
