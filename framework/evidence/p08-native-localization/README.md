# Native OpenFOAM bad-set localization (read-only)

## Scope and provenance

No CAD change, meshing, optimization, cell deletion, or flow solve was performed. This is diagnostic localization, not engineering acceptance. The frozen Gmsh source SHA-256 is `904ef11aff65088f83cafb8f4dcd28f4c44c68ad72ce164ca47d3de5c9e31df8`.

OpenFOAM points are in metres; they were converted to millimetres for CAD comparisons. Native cell indices were mapped to Gmsh element IDs using a bijective coordinate match followed by exact unordered tetrahedral vertex connectivity. Cell ordering was not assumed. Native boundary patch names map to the existing source CAD face IDs. `report.json` retains the coordinate-match error, counts, distributions, and representative cells. Native failing sets came from the separate real `checkMesh -allGeometry -allTopology` run; its zero process exit did not mean quality acceptance.

## Unit correction and actual CAD features

**0.079351684 m means 79.351684 mm, not 79.000351684 mm.** There is no demonstrated submicrometre fluid layer here.

Faces 118 and 126 are planes at z = 79 mm, with different radial extents. Faces 119 and 125 are toroidal blends spanning z = 79 to 79.351684160769 mm. Their sampled minor principal radius is 0.25 mm. Faces 120 and 124 are cones extending to z = 82.093263356924 mm. Faces 121 and 123 are toroidal blends with sampled minor principal radius 1 mm, leading to planar face 122 at z = 83.5 mm.

The 0.351684 mm z range is the axial extent of a curved surface, **not a measurement of opposing-wall clearance**. A surface bounding box alone cannot establish fluid-layer thickness.

Bounded CAD volume-membership probes at x = 300 + r, y = 0 confirm a modeled annular fluid extension: at r = 106, 108, and 110 mm, sampled z values from 79.0001 through 83.4 mm are inside volume 1, while z = 83.6 mm is outside. At r = 100 and 115 mm, the sampled points above z = 79 mm are outside, while z = 78.9 mm is inside. Other samples at r = 105/111 change with height as expected for the curved/conical boundary. These are representative domain samples, not a global thickness certificate or validation of design intent. The source remains the seal-omitted fluid proxy.

## Where the native failures occur

- `underdeterminedCells`: 152,134 native cells. Direct boundary adjacency includes 47,926 cells touching face 119 and 45,242 touching face 125. Counts by face are nonexclusive. The median centroid z is 78.917793 mm.
- `skewFaces`: all 954 are boundary faces: face 125 = 749, face 119 = 173, face 126 = 29, face 118 = 2, face 124 = 1. None of this set is an internal face.
- `lowWeightFaces`: all 31,814 are internal faces, incident on 53,926 cells. These cells strongly concentrate around the same z = 79 mm transition.
- `lowVolRatioFaces`: all 789 are internal faces, incident on 1,415 cells. Other regions, including the earlier `wallStep` region, also occur.
- `nonOrthoFaces`: all 9,613 are internal faces, incident on 13,498 cells. This distribution also includes the retainer and other features; it is not confined to the toroidal blends.

Full direct-patch counts, incident-cell boundary counts, z distributions, and worst `minSICN` representatives within each native set are in `report.json`. Representatives are ranked by the available Gmsh `minSICN`, not by an invented native determinant/skewness value. The native set membership is exact; it is distinct from the earlier Gmsh warning about 172 ill-shaped cells, whose IDs remain unavailable.

## Separate surface quality, volume shape, and feature size

Faces 119 and 125 contain 48,156 and 45,539 surface triangles respectively: 93,695 in total, approximately 56.6% of all surface triangles. Their median edge lengths are approximately 0.131 mm. Their surface triangles are generally well shaped by the stated diagnostic ratio (longest edge / minimum triangle altitude): median about 1.23 and maximum below 2.82.

Adjacent plane 118 has a median triangle ratio of 37.77 and maximum 98.81; plane 126 has median 9.54 and maximum 106.36. These are our explicitly defined triangle ratios, not OpenFOAM's native metric. A good individual boundary triangle does not guarantee a good attached tetrahedron or acceptable boundary-face skewness.

The unchanged mesh configuration uses `Mesh.MeshSizeFromCurvature = 12`, `Mesh.MeshSizeExtendFromBoundary = 0`, and maximum size 25 mm. A circle of radius 0.25 mm divided into 12 segments has arc spacing approximately 0.1309 mm, consistent with the measured dense toroidal surface. The evidence therefore supports a **curvature-driven local size scale plus an inadequate transition to neighboring surface/volume scales** as a leading explanation. It does not prove a Gmsh defect or a wrong mechanical design. The exact contribution of the meshing settings requires a controlled comparison.

## Smallest justified next experiment (proposal only)

Start with a bounded **2D transition-quality experiment**, not another full 3D solve:

1. Preserve the CAD, the verified guide/retainer controls, and the curved-surface geometry error requirements.
2. Change only the size transition on the immediate neighbors of the densely discretized toroidal boundary, initially planar faces 118 and 126. Use a documented local distance/gradation control rather than a global refinement switch. Enumerate shared curves and conformal neighbors before execution.
3. Compare the actual triangle aspect distribution, edge-length transition, facet-to-CAD error, and surface count against this frozen baseline. A configured size field alone is not proof of improvement.
4. Estimate the added count before authorizing a full case. The existing 165,428-triangle baseline leaves only 34,572 triangles below the prior 200,000 cost ceiling. If a safe gradual transition does not fit, stop and report the budget conflict; do not silently enlarge the run or delete the 0.25 mm blend. A small representative annular transition submodel can test the method first, but cannot count as full-case acceptance.
5. Only after an improved surface/transition result is reviewed should a bounded 3D comparison be considered, followed by the same native checks. Surface improvements alone cannot resolve or certify the internal determinant, interpolation-weight, or volume-ratio checks.

A directional/anisotropic treatment of the small toroidal blend may eventually reduce unnecessary circumferential density, but requires separate supported-tool and geometry-error validation. It is not assumed solved here. No global refinement or geometric defeaturing is justified solely by these diagnostics.
