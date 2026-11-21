# Remaining-feature evidence review and minimal verification plan

Read-only synthesis of existing132-face surface statistics, frozen geometry metadata, prior retainer domain probes and native-tail mapping. One saved surface MSH was read to count selected boundary edges. No CAD reimport, new meshing, numerical solve or design modification was performed.

## Systematic priorities, not a new single-point patch

1. Retainer end transitions102/104: maximum surface aspect25.07, median10.44. The associated outer curve246/247 has151 edges about0.99858 mm, while inner curve245/249 has only12 edges about11.90568 mm. This is a measured boundary-scale mismatch across an R23–24 planar ring, not merely a speculative bad cell.
2. Retainer end faces128/130: outer trimmed curve296/298 has147 edges about0.99424 mm, inner curve302/306 has12 edges about10.54760 mm; the two side lines are2.91163 mm each. Maximum aspect7.16. The sole native low-volume-ratio face is adjacent to128. A future proposal must include all end-face boundaries and transitions, not only the already-refined R24/R23.9 cylindrical walls.
3. Face93: highest current surface aspect197.46,12 triangles on a planar region at z93. It has two six-edge loops with edge lengths19.74538 and19.62991 mm. This is evidence of a narrow planar mesh feature; it is not proof of a flow gap, material thickness, or a new0.05-mm boundary height. Its numerical influence must be assessed rather than ignored because the latest worst cell is elsewhere.
4. Face122 and107/109/111/112 retain other elevated surface aspect tails. All132 faces are ranked in review.json so the review is not limited to whichever point failed last. Ranking alone is not a refinement command or engineering criterion.

## Relationship to the proven0.1-mm proxy gap

Existing CAD orientation/domain samples established that between R23.9 and24 at the sampled retainer location, the0.1-mm radial layer belongs to fluid_proxy. Faces102/104 connect to the R24 cylinder103; faces128/130 connect to the R23.9 cylinder127. Therefore the residual102/128 problems are in the end-transition neighborhood of that known modeled radial gap.

The planar z positions103.9/104.0 and106.0/106.1 differ by0.1 mm. Existing evidence does NOT independently prove every overlap of these finite trimmed faces is an axial through-flow channel. That requires finite overlap and local domain/orientation verification, not subtracting bounding boxes. Cell-centre offsets0.025 or0.05 mm are not new geometric layer thicknesses. The separately audited six short cylinders at z21.95–22 really have0.05-mm axial height, but that is a boundary step height, not a proved0.05-mm fluid passage. No evidence here warrants deleting either geometry.

## Minimal decision sequence after the pending mathematical comparison

A. First compare final controlled manufactured-solution outcomes on the old/new meshes with identical scheme, stopping rule and error definitions. Separate iteration plateau, field error, balance and geometry metrics. A quality-count improvement is not numerical convergence.
B. If the residual field-error/stencil evidence points to retainer ends, inspect the complete local reconstruction stencil and physical-boundary contributions at the worst102 cell and the lone128 ratio pair, alongside representative good cells. Include3518 structurally double-boundary cells separately; do not try to remove their diagnostic rank flag by brute-force refinement.
C. Only if needed, do a bounded read-only finite-face overlap/domain check at the retainer end planes and a complete curve/adjacency audit for102/104/128/130. Keep the proven radial-gap research guards. Determine a continuous surface AND volume transition law; do not repeat face-only or selected-edge refinement.
D. Keep face93 as a separate narrow-planar-feature question: establish its finite geometry and association with actual numerical error before allocating mesh cost. Avoid treating the highest aspect value alone as a mandate.

No next mesh size, global resolution or new acceptance cutoff is imposed by this report. The immediate next result needed is the already-running final mathematical comparison. No engineering release follows from this synthesis.
