#!/usr/bin/env bash
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../../../.." && pwd)"
venv="${VALVE_VENV:-$root/.venv-cloud}"
python="${PYTHON:-python3.12}"
"$python" -m venv "$venv"
"$venv/bin/python" -m pip install --require-hashes -r "$here/requirements.lock"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$venv/cache}"
mkdir -p "$XDG_CACHE_HOME"
"$venv/bin/python" "$here/probe.py" --output "$here/evidence"
# Product audit intentionally exits 2 on HOLD; inspect its report before proceeding.
printf '\nNext: %s %s/audit_c0.py --repo %s\n' "$venv/bin/python" "$here" "$root"
