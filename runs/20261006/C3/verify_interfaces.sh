#!/usr/bin/env bash
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../../.." && pwd)"
python="${VALVE_PYTHON:-$root/.venv-cloud/bin/python}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$root/.venv-cloud/cache}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$root/.venv-cloud/mpl-cache}"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$XDG_CACHE_HOME" "$MPLCONFIGDIR"
"$python" "$here/T22/check_sources_and_registers.py"
"$python" -m unittest discover -s "$here" -p 'test_*.py' -v
"$python" "$here/T11/check_interfaces.py" > "$here/T22/interface-check.log"
"$python" "$here/T12/build_interface_previews.py" > "$here/T12/build.log" 2>&1
"$python" "$here/T22/check_surface_support.py" > "$here/T22/surface-support.log" 2>&1
"$python" "$here/T22/check_assembly_access.py" > "$here/T22/assembly-access.log" 2>&1
"${VALVE_DRAWING_PYTHON:-python}" "$here/T40/draw_candidate_interfaces.py" > "$here/T40/drawing.log" 2>&1
printf 'Interface research completed; candidates remain unselected and manufacturing remains blocked.\n'
