# Valve Agent Framework — private research foundation

Status: tested foundation, not a completed CAD/CFD agent or manufacturing release.

## Start here
- [DN200 product-specific build plan and evidence status](../../CURRENT_PLAN.md)
- [Recovered methods, evidence matrix and ten lessons](../../research/reusable-framework-20261022/README.md)
- [Ontology and three-layer architecture](../../research/reusable-framework-20261022/framework/ARCHITECTURE.md)
- [Open-source-first tool and interchange matrix](tool-matrix.md)
- [REA and Google source attribution](sources.md)
- [Actual P08 mesh investigation](../evidence/mesh-breakthrough-review.md)

## Implemented and checked
- `framework/tools/valve_readiness.py`: scoped inspection; catches local budget promoted to full-valve constraint, unverified boundary input, design-pressure/pressure-drop confusion, missing incompressible case files and repeated completed milestone without a new objective.
- `framework/tools/valve_candidate.py`: separate explicit refinement proposal; does not modify original geometry, generate a mesh or launch a solver.
- `research/reusable-framework-20261022/framework/evidence_contract.py`: basic claim/scope/verification contract.
- Original pressure/drive calculator bytes preserved with provenance. Only pure screw arithmetic was replayed against 12 saved scenarios, not the entire original load-study executable.

The active [57 mm research runner](../../verification/valve-3d-cfd-57mm/valve_3d_cfd.py) calls the Foundation 11 evidence gates before starting the solver. The gate replay tests use archived runs v18–v21; a passing preflight is not evidence of product compliance.

[Official ball-valve baseline and one-parameter sensitivity](../evidence/official-ball-valve/result.json): both transient runs reached 1 s. The archived example exercises parameter-to-flow automation, not the 57 mm product acceptance test.

## Reproduce bounded checks
Run from repository root with Python 3:

```sh
python -m unittest discover -s framework/tests -v
python -m unittest discover -s research/reusable-framework-20261022/tests -v
```

2026-10-22 cloud run: 22 + 11 test methods passed. The 11 include 8 synthetic evidence-contract methods and 3 original-calculator methods; one loops over 12 historical rows. These are not new CAD, finite-element, mesh-generation or CFD runs. Main agent independently repeated both suites before publishing.

## Existing achievements to reuse
NSC1 representative domain was continued from 680 to 960 on 2026-10-19. Its three 40-step pressure-change windows passed the scoped <0.1% milestone; this does not imply all initial residuals <1e-7, grid independence or full-valve validation. Do not rerun this milestone as if it were missing.

## Product integration
Follow the [current DN200 plan](../../CURRENT_PLAN.md). The fixed-input runner is not yet an assembly-to-flow builder.

## Preservation and release
The existing R1 snapshot is unchanged. This branch is private; no publication license has been assigned to recovered project material. Framework code, licensed handbook knowledge and customer/project data must stay separate. Commercial interoperability requires geometric and metadata round-trip checks; STEP is not a guarantee of native feature-tree preservation. A future public release needs explicit selection of publishable assets and license review, not publication of this entire research archive.
