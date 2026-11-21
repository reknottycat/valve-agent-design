# Native OpenFOAM quality gate — 2026-10-23

## Result: NOT accepted for CFD
Official Debian trixie OpenFOAM 1912 patch200626 native checkMesh ran on the saved 230553-tetrahedron mesh. Exit code was zero **but output says Failed 4 mesh checks**. No solver was run. One connected region, valid topology/positive volumes are not sufficient for CFD readiness.

Failure evidence: max skewness6.7150993 /954 faces; small determinant<0.001 in152134 cells; interpolation weight<0.05 in31814 faces; volume ratio<0.01 in789 faces. Additionally9613 faces exceed70deg nonorthogonality (max89.7807095deg). Native thresholds are software checks, not engineering acceptance criteria.

## Reproducibility
Official package downloads and SHA256 hashes: evidence/packages.json and saved official download pages. Download69558048 bytes; isolated extract only, no dpkg install/no system settings. Scripts use private LD_LIBRARY_PATH plus package-provided dummy Pstream for serial-only operation; initial MPI VFS socket attempt was denied, no security setting changed. Three utilities' -help output confirms1912 patch200626. No additional runtime packages necessary.

Frozen original source SHA256904ef11aff65088f83cafb8f4dcd28f4c44c68ad72ce164ca47d3de5c9e31df8 remains unchanged. export_copy.py writes only a new MSH2.2 ASCII copy, no mesh generation/optimization. Important converter issue: dimension-specific physical tags3:1 and2:1 collide in1912 converter. Volume tag remapped3:1→3:1001 in copy, retaining fluid_proxy;132 surface tags/names/counts unchanged. Initial wrong-name converter log is retained. Export omits28466 lower-dimensional point/line elements that are not physical boundary/volume groups; all165428triangle and230553tet connectivity and85918points checked unchanged to ASCII precision. Tags for elements may be renumbered by format export. verify_conversion.py performs proof, including all132OpenFOAM patches and exact single mm→m scaling tolerance.

Commands recorded per step in evidence/{convert,scale,checkMesh}.json. bounded.py enforces180s wall time and2GiB observedRSS and aborts on limit. Actualnativecheck5.316s/300613632bytespeakRSS. Initial check lacked fvSchemes and stopped; log retained. Added minimum fvSchemes/fvSolution (no field solvers), reran check only. Converted case unitsm, volume0.0637024898164436m³. Allpatch types remain genericpatch at this quality stage; physicalwall/inlet/outletnames preserved, no physicalCFDfields/boundaryconditions configured.

Run: `. ./env.sh`; inspectcommandJSONs. Do not rerun transformPoints: already scaled once.

Official sources:
- https://packages.debian.org/trixie/amd64/openfoam/download
- https://packages.debian.org/trixie/amd64/libopenfoam/download
- https://manpages.debian.org/trixie/openfoam/gmshToFoam.1.en.html
- https://manpages.debian.org/trixie/openfoam/transformPoints.1.en.html
