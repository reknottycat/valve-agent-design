# Valve Agent Framework — private research foundation

Status: tested foundation, not a completed CAD/CFD agent or manufacturing release.

## Start here
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

## Reproduce bounded checks
Run from repository root with Python 3:

```sh
python -m unittest discover -s framework/tests -v
python -m unittest discover -s research/reusable-framework-20261022/tests -v
```

2026-10-22 cloud run: 22 + 11 test methods passed. The 11 include 8 synthetic evidence-contract methods and 3 original-calculator methods; one loops over 12 historical rows. These are not new CAD, finite-element, mesh-generation or CFD runs. Main agent independently repeated both suites before publishing.

## Existing achievements to reuse
NSC1 representative domain was continued from 680 to 960 on 2026-10-19. Its three 40-step pressure-change windows passed the scoped <0.1% milestone; this does not imply all initial residuals <1e-7, grid independence or full-valve validation. Do not rerun this milestone as if it were missing.

## Next executable integration, not a claimed completion
1. Select a specific engineering study and bind geometry revision, physical boundary inputs, materials and observables to sources. A drawing alone does not provide all operating conditions.
2. Restore the necessary full case only when its identity and study scope are known. P08's inspected small source package is a mesh-only case, not a ready flow solve; absence there does not establish absence in all archives.
3. Locate or provision an authorized professional runtime and validate its version. Current cloud PATH lacked simpleFoam/checkMesh/gmsh at inspection; no new software installation or solver run was performed.
4. Measure resource needs on a bounded meaningful increment. Historic 4096 metadata-test cap, 12M maximum and L6 are not universal engineering requirements. Do not blindly repeat previously applied coarsening.
5. Build tool adapters and one traceable drawing-to-calculation golden case before expanding to arbitrary drawings. The present repository does not yet provide a complete MCP service, CAD adapter or automatic manufacturing approval.

## Preservation and release
The existing R1 snapshot is unchanged. This branch is private; no publication license has been assigned to recovered project material. Framework code, licensed handbook knowledge and customer/project data must stay separate. Commercial interoperability requires geometric and metadata round-trip checks; STEP is not a guarantee of native feature-tree preservation. A future public release needs explicit selection of publishable assets and license review, not publication of this entire research archive.
