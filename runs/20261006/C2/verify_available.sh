#!/usr/bin/env bash
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../../.." && pwd)"
python="${VALVE_PYTHON:-$root/.venv-cloud/bin/python}"
drawing_python="${VALVE_DRAWING_PYTHON:-python}"
freecad_python="${FREECAD_PYTHON:-/usr/bin/python3}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$root/.venv-cloud/cache}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$root/.venv-cloud/mpl-cache}"
mkdir -p "$XDG_CACHE_HOME" "$MPLCONFIGDIR"
"$python" "$here/T06/validate_inputs.py"
"$python" -m unittest discover -s "$here/../CLOUD/T04" -p 'test_*.py' -v
"$python" -m unittest discover -s "$here" -p 'test_*.py' -v
"$python" "$here/T12/build_lift_model.py" > "$here/T12/build.log" 2>&1
"$python" "$here/T22/validate_lift_model.py" > "$here/T22/validation.log" 2>&1
"$python" "$here/T22/validate_exported_assets.py" > "$here/T22/asset-roundtrip.log" 2>&1
"$python" "$here/T22/negative_contact_control.py" > "$here/T22/negative-control.log" 2>&1
"$python" "$here/T23/mesh_open_domain.py" > "$here/T23/mesh.log" 2>&1
"$python" "$here/T15/study_calculations.py" > "$here/T15/calculation.log"
"$freecad_python" "$here/T40/export_freecad_snapshots.py" > "$here/T40/freecad.log" 2>&1
"$drawing_python" "$here/T40/export_review_files.py" > "$here/T40/drawings.log" 2>&1
printf 'Available study gates passed. Product design remains PARTIAL/HOLD. No CFD/FEA solver was launched.\n'
