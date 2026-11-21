# Proposed local geometry-approximation repair — NOT EXECUTED

## Research budget (not a standard or flow-accuracy criterion)
Measured local CAD radial spacing g=1 mm. Allocate epsilon=0.2*g=0.2 mm maximum inward geometric approximation error per cylindrical surface. A conservative two-surface error allowance leaves g-2*epsilon=0.6 mm separation. This is a deliberately chosen diagnostic guard, not a regulatory criterion or certified CFD resolution.
For circular chord length c, sag e=R-sqrt(R²-c²/4), so c_max=2*sqrt(2*R*epsilon-epsilon²). At radii31/32 mm c_max=7.03136/7.14423 mm. Propose target mesh size6mm, with actual geometry error <=0.2mm verified after generation. A target size is not a guaranteed maximum edge length.

## Strict two-face remesh is insufficient with frozen boundary curves
Readback shows existing coarse boundary chords independently exceed0.2mm: curves161,165 on face64;253,254,258,264 on face108. Holding those edges fixed preserves the defect even if face interiors are refined. Therefore do NOT claim a safe face64/108-only repair.
Minimal conforming closure proposal: target face interiors64/108; refine exactly curves{161,165,253,254,258,264}; remesh adjacent faces{61,66,106,115} to accommodate changed shared nodes. Total affected surfaces{61,64,66,106,108,115}. Other curves and all other surfaces remain frozen. This bounded closure must be approved by parent before generation.

## Local Gmsh controls and proof obligations
Official API gmsh.model.mesh.setSizeCallback receives dim/tag/x/y/z/lc; returning lc is a no-op. Use min(lc,6.0) ONLY for (dim=2,tag in{64,108}) OR (dim=1,tag in the six affected curves); return lc for all others. No global MeshSizeMax or curvature change. Retain MeshSizeExtendFromBoundary=0.
Import unchanged CAD and actual failed-current.msh, assert hashes/mapping. Clear meshes on the six affected surfaces FIRST, then the six selected curves (no volume elements exist). Use Mesh.MeshOnlyEmpty=1 so populated unaffected entities are not remeshed. Generate2D only. This use of API and option is documented, but this exact selective workflow has NOT yet been runtime-validated.
Pre/post canonical per-entity fingerprints of coordinates/connectivity (not unstable element numbering) must be identical on all unaffected surfaces/curves. Callback counters must show modifications only for selected tags. Capture logs; any unexpected changed entity or propagation fails locality gate.
Sources: https://gmsh.info/doc/texinfo/gmsh.html#index-gmsh_002fmodel_002fmesh_002fsetSizeCallback ; https://gmsh.info/doc/texinfo/gmsh.html#index-Mesh_002eMeshOnlyEmpty ; installed official4.15.2 gmsh.py lines4193ff.

## Surface gate before any3D attempt
Check source CAD hash unchanged; no missing physical boundaries; no repeated/degenerate triangles; positive area; edge incidence and orientation. For both cylinders compute inward deviation over every triangle, not just vertices (vertices lie on CAD): project triangle to xy, find closest point of its projected triangle to axis(300,0), radial_min, error=R-radial_min. For linear triangles, min radius is a convex quadratic minimization on triangle, including interior/edges, so this bounds inward radial error. Also compare max radius/node projections and CAD finite parameter bounds. Require each cylinder error<=0.2mm and run local segment/facet intersection checks on repaired pair/closure. Retained original failing edge location must no longer conflict. Local pass does NOT prove globally intersection-free surfaces.

## Resource bounds and stopping
Same180s wall,2GiB RSS,4GiB address limits. No new packages. After surface generation cap total triangles200000 and affected six-surface triangles10000 as COST controls, not engineering requirements. If crossed, stop and report; do not silently raise cap. Parent reviews surface proof before any new3D generation. Do not launch flow solver or regenerate unaffected baseline computations.

## Domain semantics
Existing unchanged CAD volume1 has oriented boundaries+64,-108. On the failure ray, r31.25,31.5,31.75 are inside that volume; r30.5,32.5 are outside. Thus under the source asset's existing fluid_proxy labeling this1mm layer belongs to the modeled fluid volume, rather than excluded material wall. This classifies the proxy at this location only; it does not validate design intent, manufacturing clearance, or actual device flow.
