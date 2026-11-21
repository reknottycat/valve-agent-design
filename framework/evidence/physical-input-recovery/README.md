# Existing physical-input recovery, 2026-10-22

## Positive finding
A full-valve **research operating plan already exists** in frozen R1; it is not necessary to ask the user to invent new diagnostic inputs. The plan is `PLANNED_NOT_RUN`, not a completed CFD case. Source: https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/CALCULATIONS/R1/sources_new/FLOW_PLAN_NEW/flow_study_plan.json

R1 fixed-held-open diagnostic: lift 57 mm, DN200, reference seawater state 20°C / 35 g/kg, density 1024.9109328963 kg/m³, kinematic viscosity 1.0504609627009073e-6 m²/s. Re10 inlet face speed 5.252304813504536e-5 m/s; outlet kinematic p=0, absolute reference 101325 Pa. This is a numerical diagnostic, not a prediction of spontaneous valve opening. The 0.5/1/2 m/s sensitivity cases are also research assumptions and require turbulent/near-wall treatment, not ready laminar cases.

## Source geometry compatibility actually checked
P08 rules have inlet finite face 79 at x=-600 mm, outlet face 34 at x=1200 mm; both CAD areas 31415.926535897932 mm², consistent with R1's DN200 and port positions. Packing cutoff face80 is named packing_research_z332. These are source CAD-rule checks, not verification of final mesh patch normals or actual retained connectivity. P08 currently lacks a qualified retained mesh and populated flow dictionaries.

## Unknowns are precisely separated
Research adaptation still needs final mesh boundary identity/normals, proof P08 pose matches held-open 57 mm, full wall/packing boundary assignment, version-valid schemes/solvers and qualified retained mesh. These are engineering work, not additional user authorization.

Actual product duty remains unsourced in reviewed files: operating flow/curve, actual fluid temperature/composition, absolute pressure, opening/equilibrium condition, coefficient reference area and pressure-tap/test standard. These are needed for product-performance claims, not to prohibit the source-backed diagnostic.

**0.63 MPa(g) is a separate structural research load in this source, NOT an original product rating and NOT imposed CFD pressure drop.** NSC1 local 0.01 m/s and artificial crop-slip boundaries must not be copied across.

`p08_physical_input_template.json` preserves known original assumptions and explicitly nulls unverified adaptation/product fields. It is deliberately non-executable, with no U/p generated and no solver launched. `flow_study_plan_R1_original.json` retains fetched original source text. Three simple assertions passed: expected three non-true-wall patches, product absolute pressure remains null, and archived case retains STUDY_ASSUMPTION_NOT_RUN status.
