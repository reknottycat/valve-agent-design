# P08 exact original proxy-fluid CAD readback, 2026-10-22

Source: https://drive.google.com/file/d/1RPoinCN3rwLSOgo-lbgH0jTPBiHVRQDL/view
`AGR1_open_seal_omitted_proxy_main_mm.step`, 507,364 bytes, SHA256 `a9aeb45996a388a3d894f69605205c70c25edd154adc6d3c71658329a730e787`. Located in existing PRODUCT_INDEX and 20261012-P08-NATIVE source pins, fetched only this small original, not the 56.8 MB surface package. Raw STEP is retained as a cloud attachment, not proposed for GitHub.

**This is the seal-omitted proxy fluid domain**, not a complete validated physical-valve model. Actual CadQuery 2.7.0 / OCP 7.8.1.1 read-only import: 1 valid solid, 2 shells, 132 faces; declared STEP millimetres; bbox 1800 × 290 × 477 mm; volume approximately 64,142,426.1438 mm³. Kernel validity does not establish manufacturing, physics, grid or CFD acceptance. Neither two shells nor one solid is proof of every real flow path being correctly represented.

Actual planar end-face measurements:
- Imported face 79: x = -600 mm, area 31415.9265359 mm², oriented CAD normal -X.
- Imported face 34: x = +1200 mm, same area, oriented CAD normal +X.
- Both areas equal DN200 circular cross-section. At each face centre, a point 0.1 mm along the oriented normal is outside this solid and a point opposite is inside; this supports outward orientation **at those sampled CAD points**.
- These numbers and areas agree with historical P08 source records. This does not formally establish a face-ID bijection across every original CAD exporter/importer or map these faces to a retained final mesh patch. No final mesh normals were inspected.

Later source recovery corrected the evidence gap: ../p08-pose/ preserves the original FDG1 independent review of nominal +Z 57 mm translations with zero reported bidirectional geometry differences. This port readback itself did not measure pose; the historical review is reusable evidence, not merely an R1 plan. Actual-product disc/seat datum and loaded-assembly acceptance remain separate. No geometry modification/healing, boolean, mesh, CFD or field generation was performed. Original file hash unchanged. One nonfatal ezdxf cache warning occurred; no permission escalation was needed.

Reproduce real CAD check: `python3 check_ports.py /path/to/AGR1_open_seal_omitted_proxy_main_mm.step`. The tool refuses any other SHA256. `python3 -m unittest -v` runs 3 small tests (hash rejection and assertions on saved actual measurements); these tests are not a fresh CAD import. `p08_port_actual.json` is the separate actual import result.
