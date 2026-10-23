# Short-step scale and boundary audit (read only)

No mesh was generated. Original CAD and existing positive baseline remain unchanged.

## Proven geometry and scale

Faces 37/39/41/43/45/47 are six finite cylindrical sectors of radius 112.5 mm, axial height 0.05 mm (z = 21.95 to 22.00 mm). Their complete boundary consists of 24 curves: 12 circular arcs and 12 axial lines. Each arc has CAD length about 115.809698 mm. Each current sector has only ten triangles, with circumferential chord about 23.121 mm and axial edge 0.05 mm, yielding aspect about 462.42. This is a discretization aspect issue on a genuine short CAD step, not an inference from a curved bounding box.

At the midpoint azimuth of all six sectors, finite domain probes below z=21.95 are outside, at z=21.975 the radially inner side is inside and outer side outside, and just above z=22 both sampled radial sides are inside. These observations support a local step in the fluid proxy boundary. They do NOT establish a 0.05-mm fluid passage or a manufacturing requirement. Geometry simplification is not authorized by this result.

The old torus volume law is inert here: measured distance is about 57 mm, beyond its 31.086-mm cutoff. Existing explicit guide, retainer, plane and cone callback entity sets do not include these step faces or their 24 curves. Global curvature and size rules therefore leave the long circumferential edges coarse.

## Boundary-complete scope

The six steps have 25 immediate conformal faces including themselves, face 36, twelve small side planes and six upper planes. Their full uncombined boundary union contains 97 curves, recorded in proposed-boundary-union.json. Refining just one selected circle would recreate the previous discontinuity problem. Applying a law on all these parent faces requires evaluating that same law on all 97 curves, preserving stricter existing controls, and auditing any newly affected second-ring adjacent faces. No hidden global size extension should be enabled.

## Smallest justified next action, not authorization to run

First compare the parent's manufactured numerical test. If this tail still warrants repair, prepare one 2D-only local size-law comparison on the six step sectors and their necessary planar transition closure. A research starting scale h0=0.25 mm would reduce a one-row short-step circumferential/axial ratio from about 462 to about 5; it is not a quality acceptance cutoff. A candidate transition h=min(existing, 0.25+0.8*d) should use exact distance to the finite cylindrical sectors, with angle and axial clipping, not full-circle or sparse-point distance. Preserve geometry and all previously validated controls.

Order-of-magnitude surface cost: the six step areas total about 34.743 mm²; a single-row strip with 0.25-mm circumferential spacing gives roughly 5,560 triangles versus 60 now. A two-sided graded-strip approximation over the total arc length 694.858 mm yields about 15,900 transition triangles (integrating 4/sqrt(3) * length / h(d)^2). This suggests roughly +21,400 triangles, but is NOT a hard prediction: narrow side planes, corners, curve closure, curvature and actual mesher behavior alter it. About 253k total surface triangles is a planning estimate; a 270k cost review screen could be proposed, not silently adopted. A 2D-only resource envelope of 180 seconds / 2 GiB would be ample relative to the 231k surface baseline, but no run is approved here.

Do not carry this candidate into 3D automatically. Interior step grading and any finite-volume effects need a separate reviewed proposal after surface results. Do not chase the 471 double-boundary determinant flags indiscriminately or refine the already repaired cones again.
