# Independent technical review

Reviewed the DOCX and generator against the local frozen evidence snapshots on 2026-10-06. This is a read-only source, arithmetic and document-text review, not engineering approval, CAD recomputation, solver execution or external-source revalidation.

## Outcome

No remaining substantive arithmetic error or invented actual-valve CFD/FEA result was found after the author's correction of the two density intermediate terms and dynamic generation of effective thread friction. The current Word XML contains the corrected density example: 998.0154288 + 26.8955041 = 1024.9109329 kg/m³.

An independent audit passed 208 arithmetic comparisons covering geometric pressure coefficients derived from diameters, all 20 bilateral pressure cases, all 12 drive/friction scenarios including efficiencies and self-lock threshold, root stress, three flank-contact proxies, nine joint pressure-boundary cases, and all nine seawater density/viscosity/kinematic-viscosity points. All 32 source files match manifest byte counts and SHA256 values. The document contains 60 native OMML equations with unique equation labels. Fractions, roots, subscripts and superscripts were inspected structurally.

## Three minor text corrections sent to the author

1. Section 11.2: change “微小伪应力约10⁻¹⁵至10⁻¹⁴量级” to “伪应力相对误差约10⁻¹⁵至10⁻¹⁴量级（无量纲）”. Source S24 stores these values under relative_errors.spurious_stress; they are not dimensional stress values.
2. After equation 10-6: specify the outward-positive signed mass-flow convention, normally negative at the inlet and positive at the outlet. State the normalization is undefined at zero flow. The formula itself is valid under that convention.
3. Section 12 table, ГОСТ18175-78: replace “变形锡青铜以外合金成分” with “压力加工无锡青铜的化学成分” to match the wrought tin-free bronze source identity.

## Scope and evidence boundaries checked

- Gauge, absolute and differential pressures remain distinct; 0.63 MPa is a research assumption, 1.0 MPa is a numerical sensitivity, and neither is promoted to certified rating or physical proof pressure.
- Contact-force and actuator-force outputs remain null; unilateral contact diagnostics are not labeled actual reactions.
- Materials remain candidates with product state and source conflicts stated. No tensile strength becomes a design allowable; adopted Russian-alloy inputs remain missing and C95800 stays a separately named continuous-cast alternative.
- The 3-check and 7-check mesh failures match logs and remain failures. Standard cavity and uniform-tension solver tests are clearly separated from actual valve predictions.
- No numerical result fills missing leakage, flow coefficient, stress margin, buckling, fatigue, pressure-test or manufacturing-acceptance fields.
- Geometry checks remain limited to discrete poses, exchange consistency and specific negative controls.

Final render-4 visual review has now completed for pages 16–29; see review_report.md and review_report.json for the complete closed review record.
