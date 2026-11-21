# Read-only native tail localization: step759760

The frozen native case and actual source MSH were only read. All native-manifest hashes were verified after analysis; no mesh, solver, optimizer, threshold or source changes were made. Native indices are mapped through coordinate matching (maximum error 5.46e-12 mm) and exact unordered tetrahedral connectivity, not assumed identical to Gmsh indices. Coordinates were converted from metres to millimetres once.

## Low determinant is a mixed regression, not all harmless

The 6,988 flagged cells split into 3,518 with two actual boundary triangle faces, 3,074 with one, and396 with none. Every two-boundary cell in this mesh is flagged, consistent with the native implementation's structural rank argument: only internal/coupled face-area outer products contribute, so a tetrahedron with two ordinary boundary faces supplies at most two vectors to a3x3 matrix. This is not its signed volume or the full PDE matrix with boundary conditions.

Compared with cone688424 (471 /1,831 /497 for two/one/zero boundary faces), the total rise is4,189. Of this,3,047 comes from the expanded two-boundary population, but the non-double population also rises from2,328 to3,470 (+1,142). Do not dismiss the entire regression. Of4,175 low-det cells touching plane36 or the six short cylinders,2,779 are double-boundary and1,396 are not. These are unique-cell counts, not sums of overlapping CAD-role histograms.

## Remaining low-weight and low-volume-ratio faces

All57 low-weight faces are internal, with114 unique incident cells. Twenty-two faces have an incident cell touching the repaired step group; residual problems have not vanished there. One face (1386799) is associated with retainer role102. Full coordinates, owners/neighbors, boundary roles and source tetrahedron IDs for all57 are retained in report.json.

The single remaining low-ratio face is native1340298, centroid[292.856052,20.298018,106.033333] mm. Owner696150 (Gmsh955153) touches retainer face128; neighbour755586 (Gmsh1014589) has no boundary face. Their centroids are at z106.025 and107.761739 mm. This defect is no longer at the z21.975-mm step. Owner minSICN is0.00768833, neighbour0.319574. No unmeasured pressure-loss significance is inferred.

The overall worst minSICN cell is native755036 / Gmsh1014039, centroid[282.701230,15.606663,103.925] mm, touching retainer face102. Its minSICN is0.00417649. It belongs to the remaining low-det and non-orthogonal tails, not the lone low-ratio pair. Role102 has110 low-det incident cells and159 non-orthogonal incident cells. The worst cell's existence is not proof that it alone caused any prior solver failure.

## CAD preservation versus discrete volume

A separate saved-MSH determinant-sum calculation independently reproduces:

- cone688424:63,701,896.365642 mm³,0.686799% below CAD.
- step759760:63,707,302.427356 mm³,0.678371% below CAD.
- increase5,406.061714 mm³, or0.00848650%.

The original STEP remains unchanged, but the discretized surface approximation and enclosed mesh volume changed between cone and step candidates. “CAD unchanged” does NOT mean “discrete geometry/volume identical.” Each actual3D surface matched its own approved2D reference. Neither volume difference is asserted to satisfy an engineering tolerance.

## Interpretation and next decision

Native result is still Failed3. Reduced low-weight/ratio/skew counts and better step aspect are useful, but do not certify numerical convergence or valve performance. Wait for the separately authorized controlled numerical comparison before further meshing. There is no basis to refine the cones again, erase geometry, relax thresholds or chase every structurally rank-deficient boundary cell to zero. If another geometric investigation becomes justified, the remaining single ratio pair and role102 belong to the retainer area, while1,396 non-double step-associated low-det cells remain a separate stencil/anisotropy question.

Parser note: the one-entry native faceSet was serialized as `1(1340298)` instead of a multiline list. The first read-only parser attempt stopped on this formatting difference; its log is retained. The parser was corrected to support both formats, then analysis completed. No native rerun was required.
