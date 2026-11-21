# Read-only quality localization of the frozen volume mesh

The input mesh SHA-256 remains `904ef11aff65088f83cafb8f4dcd28f4c44c68ad72ce164ca47d3de5c9e31df8`. No optimization, remeshing, CFD calculation, or cell deletion was performed. This report is a diagnostic localization exercise, not an independent full engineering verification or an engineering acceptance decision.

## Logged warning versus diagnostic scan

The Gmsh log reports **172 ill-shaped cells**, but does not list their IDs. This report does **not** claim to identify those 172 cells. A separate `minSICN` diagnostic scan gives these counts:

| Descriptive quality bin | Cell count |
| --- | ---: |
| q < 0.005 | 108 |
| q < 0.01 | 200 |
| q < 0.02 | 1,123 |
| q < 0.05 | 22,136 |
| q < 0.1 | 108,379 |

These are descriptive bins, not acceptance criteria.

## Worst cell and boundary localization

The worst cell in the `minSICN` scan is **324416**:

- Quality q: 0.002528429.
- Centroid: (407.726527, 30.044706, 78.998256) mm.
- Signed volume: 0.000655881 mm³.
- Longest edge: 6.647996 mm; shortest edge: 0.027713498 mm.
- Minimum altitude: 0.006637037 mm.
- Defined diagnostic aspect ratio (longest edge / minimum altitude): 1001.651. This is our explicitly defined diagnostic ratio, not the standard OpenFOAM aspect-ratio metric.
- Direct boundary adjacency: source CAD face **118**, in the `generic` family.

The next-worst cells, **344722** and **327092**, also touch face 118 near z = 79 mm.

For the worst 100 cells, direct boundary-face counts are nonexclusive: face 36 = 55; faces 37, 41, 43, and 47 = 9 each; face 45 = 8; face 39 = 7; face 118 = 6; face 102 = 3; face 104 = 2. These results indicate a broader low-quality tail involving `wallStep`, `generic`, and retainer interfaces, rather than only the two repaired PLC intersection locations.

## Lowest one percent and geometric windows

The lowest one percent comprises **2,306 cells**. Direct boundary-family counts are nonexclusive: `generic` = 1,828; `wallStep` = 60; `retainer` = 150; `keySide` = 20. A further 278 cells touch no surface face.

The following are geometric centroid windows, **not full trim-aware feature classifications**:

- Guide window, r = 31–32 mm and z = 96–197 mm: 8,781 cells, minimum q = 0.284879, and no cells in the lowest one percent.
- Retainer window, r = 23.9–24 mm and z = 104–106 mm: 2,232 cells, minimum q = 0.022063, and seven cells in the lowest one percent.

The worst-quality tail is therefore not concentrated in the repaired guide gap. This observation does not establish quality acceptance.

## CAD localization: evidence hierarchy and limitations

Direct tetrahedral-face → surface-triangle → CAD physical-ID adjacency is authoritative wherever it is listed. For the worst 100 cells, the report also records analytic CAD projection candidates filtered by bounding box and parameter-domain checks.

These candidates are **not certified nearest finite trimmed CAD faces**. Projections can fall outside trims; Gmsh inside tests can exclude valid candidates near edges; and the true closest point can lie on a boundary edge. Do not use candidate ordering as a design conclusion. Centroids and direct adjacency remain reproducible evidence for focusing further investigation.

## Files and remaining work

- `lowest-one-percent.json` records all 2,306 lowest-one-percent cells, including IDs, quality, volume, edge and altitude metrics, centroids, and boundary adjacency.
- `summary.json` retains the worst 100 records and aggregate results.
- `localize.py` reproduces the scan.

No acceptance cutoff was introduced. The original warning about 172 cells remains unresolved without its internal metric and cell IDs. Native `checkMesh` evaluation has been delegated separately.

The proposed next read-only investigation is to inspect the thin-transition or sliver geometry around face 118 at z = 79 mm and the `wallStep` region at faces 36–47, then compare against native quality metrics before choosing a repair. Do not discard cells or apply global refinement solely because of the minimum q value.
