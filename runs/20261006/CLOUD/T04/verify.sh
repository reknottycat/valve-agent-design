#!/usr/bin/env bash
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../../../.." && pwd)"
python="${VALVE_PYTHON:-$root/.venv-cloud/bin/python}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$root/.venv-cloud/cache}"
mkdir -p "$here/evidence" "$XDG_CACHE_HOME"
"$python" -m unittest discover -s "$here" -p 'test_*.py' -v > "$here/evidence/tests.log" 2>&1
(cd "$root/valve_agent_bundle"; "$python" validate_manifest.py) > "$here/evidence/manifest.log" 2>&1
"$python" "$here/probe.py" --output "$here/evidence" > "$here/evidence/probe.log" 2>&1
set +e
"$python" "$here/audit_c0.py" --repo "$root" > "$here/evidence/audit.log" 2>&1
audit_exit=$?
set -e
printf 'Observed C0 audit exit: %s (expected 2: HOLD)\n' "$audit_exit" | tee "$here/evidence/observed-red.txt"
if [ "$audit_exit" -ne 2 ]; then
  printf 'Unexpected C0 result; inspect audit.log. No product solver permitted.\n' >&2
  exit 1
fi
"$python" "$here/verify_evidence.py" >> "$here/evidence/observed-red.txt"
"$python" "$here/propose_flow_geometry.py" --repo "$root" > "$here/evidence/proposal.log" 2>&1
printf 'Cloud tool tests passed; original C0 was correctly rejected. Product status remains HOLD.\n'
