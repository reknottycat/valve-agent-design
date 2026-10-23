# Step-local grading: native quality evidence

Official Debian OpenFOAM1912.200626-3+b1, serial dummy Pstream. One new conversion/scale/check; no solver or threshold edits. Source SHA 4e1b4168c9cfdd8d248a54dbbe2411c6fd7661305e479d77f53e3a0f07568a98 immutable. Export dimension3 physical1→1001, MSH2.2; nodes and triangle/tetra connectivity identical, all132 surface roles/counts preserved. mm→m scaled exactly once, coordinate-set bijection verified before nativecheck. Explicit absolute cwd/env/argv and180s/2GiB perprocess guard in run.py/preflight.json; no oldcase writes or sourced wrappers.

Native Failed 3 versus baseline Failed 3. Exit0 is not PASS. No engineering release. R1 prerequisite is not amended.

| Metric | 688424 baseline | 759760 step candidate |
|---|---:|---:|
| skew | 0 (0.000000%) | 0 (0.000000%) |
| nonortho | 4235 (0.283770%) | 4064 (0.246449%) |
| det | 2799 (0.406581%) | 6988 (0.919764%) |
| weight | 229 (0.015344%) | 57 (0.003457%) |
| ratio | 112 (0.007505%) | 1 (0.000061%) |

Maxskew 3.66000889652733→2.36008089639052; maxnonorthogonality 89.7807095209027→89.4180026389237. Fractions use allcells or allfaces as stated, not native tested subset. Native walltime14.063s, peakRSS759996416B. Totalvolume 0.0637018963656401→0.0637073024273604m³ (+0.00849%); bbox unchanged. This source surface refinement changes the faceted geometry: source/export identity does not prove geometry equivalence to prior cone. Positive cell volumes, facepyramids and facetets pass. Lowdet absolute count AND fraction worsen; average nonorthogonality25.47149→25.57188 also worsens. See full raw log for every deterioration, all geometry/topology results and volume extrema. All source/copy scripts,case,badsets,logs preserved; installed runtime binaries/packages excluded.
