# Fresh disc structural rebuild

This package contains re-created reproducible code after execution-workspace loss. Previous conversational numerical values are comparison clues only, not evidence. New solver results are accepted only after fresh execution and raw-DAT checks.

Scope: hash-identified C2 check_closed disc/guide, reverse pressure 0.63 MPa gauge, zero inlet, constant C95800 alternative elastic reference, bilateral rigid frictionless seat support. No actual contact, strength pass, material certification, thermal qualification or manufacturing release.

All engineering gates are explicit exceptions under normal Python and -O. Each result binds raw INP, DAT, mesh, model and run hashes. A frozen verifier checks an externally retained immutable manifest SHA, then reparses raw DAT and independently reconstructs stresses and strain energy. It never creates or updates a manifest. Creation is a separate refusal-to-overwrite action.

Runtime: /workspace/shared/valve-cad-rebuilt-20261006/venv/bin/python. Solver: source /workspace/shared/valve-solvers-rebuilt-20261006/env.sh. Source paths and exact hashes are checked before meshing/solving. Parent confirmed CAD readiness on 2026-10-06 at 20:59:10 UTC.

New runs, sequentially:
- scripts/structural.py --patch --order C3D4
- scripts/structural.py --patch --order C3D10
- For h=8,6,4: scripts/structural.py --h H --order C3D4, then --order C3D10

Existing cases cannot be overwritten. Each order requires its freshly checked independent pressure patch. Freeze only completed raw results with scripts/freeze.py create CASE; preserve the printed manifest SHA externally. Verify read-only with scripts/freeze.py verify CASE --expected-sha256 SHA.

Maximum displacement means maximum nodal displacement magnitude only. Quadratic field extrema are not rigorously searched. Raw stress peaks and bilateral tensile seat reactions require explicit mesh/contact HOLD interpretations.
