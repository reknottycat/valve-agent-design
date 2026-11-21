# Read-only localization of the remaining native quality tail

Source is the frozen 688,424-cell cone-grading mesh and its native OpenFOAM case. No mesh generation, optimization, solver or quality-threshold change was performed. Native point coordinates were converted from metres to millimetres once, matched to source nodes, then tetrahedra were matched by unordered vertex connectivity. Native cell IDs are not assumed equal to Gmsh IDs.

## Results

Native results remain Failed 3: 2,799 low-determinant cells, 229 low-weight faces, 112 low-volume-ratio faces; 4,235 non-orthogonal faces above 70 degrees. Skew failures are zero.

Of 2,799 low-determinant cells, 471 have exactly two actual boundary triangle faces, 1,831 have one, and 497 are wholly internal. The two-boundary group has minSICN median 0.692804 and maximum 0.970097: its determinant flag is not interchangeable with poor tetrahedron shape. This is a structural classification, not permission to ignore the criterion. The other 2,328 cannot be dismissed by the double-boundary explanation. Separate source-code interpretation of the native determinant belongs to the native-checking report.

All 229 low-weight and 112 low-ratio faces are internal. Their incident-cell counts are 361 and 193 respectively. Neither set has an incident cell touching the repaired cones 120/124 or tori 119/125. Boundary-role counts are nonexclusive. The low-ratio incident cells include 49 touching face 36; the six short cylindrical steps 37/39/41/43/45/47 are also prominent. The worst minSICN cell is native 589273 / Gmsh 820394 at [366.405964, -90.041877, 21.975] mm, touching face 47.

The remaining non-orthogonality is concentrated instead around retainer roles 103/127 and adjacent roles; it is not evidence to refine the now-repaired cones again. Some flagged cells have no boundary face and are explicitly reported as interior, not assigned an invented CAD role.

## Smallest justified next action

Read-only audit the full boundary and actual scale transition at plane 36 and six 0.05-mm-high cylindrical step faces before proposing a local surface/volume law. The actual short-cylinder triangles have aspect about 462.42 because their circumferential edge is about 23.121 mm while the axial edge is 0.05 mm. Plane 36 has a high-aspect tail about 243.49. This is a real discretization-scale mismatch; the 0.05-mm axial feature height does not by itself establish a fluid-gap thickness or authorize CAD simplification. Repeating cone refinement, deleting steps, or trying to clear every determinant flag indiscriminately is not justified.

`report.json` retains representative worst cells, all native-set role distributions, exact boundary-face counts, CAD adjacency and input hashes. `feature-scales.json` contains additional read-only source-mesh measurements. Numerical verification and any further mesh experiment require separate review.
