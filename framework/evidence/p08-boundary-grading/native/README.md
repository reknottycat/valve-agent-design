# New boundary-grading native comparison (2026-10-23)

**Both candidates Failed 4 native mesh checks; no CFD solver or engineering release.**

| Metric | Previous | New |
|---|---:|---:|
| Tetrahedra |230553|266705|
| Boundary triangles |165428|196926|
| nonorthogonality >70deg faces |9613|8904|
| max nonorthogonality deg |89.7807095|89.7807095|
| highly skew faces |954|1442|
| max skewness |6.7150993|6.0515495|
| determinant<.001 cells |152134|177637|
| interpolation weight<.05 faces |31814|26883|
| volume ratio<.01 faces |789|582|
| Total volume m3 |.0637024898164436|.0637018962272274|

Mixed effect, not a successful native quality gate. Cell counts differ; do not interpret raw counts alone as improvement. New run7.020s,356626432BpeakRSS. Conversion1.806s; scaling.201s. Exit0 is NOT pass. Native logs and badsets included.

Source immutable SHA29877cecc2d7d3868ab877867240b0089a3c7e5d2c958f2a96a681f57787f295. All101802nodes and triangle/tetconnectivity verified;132surfacegroup names/counts retained. Volumephysicaltag3:1→3:1001 avoids convertercollision; namefluid_proxy. Single mm→m scaling verified by coordinate-set bijection. Source-copy MSH2.2 ASCII preserves relevant mesh, omits lowerdimension nonphysical elements. See conversion-verification.json.

Official Debian1912 binaries reused from old isolated prefix, never systeminstalled. Commands/versions/packagehashes retained. Fresh minimalfvSchemes is only a required checkMesh input, no fieldsolve.

## Execution incident, transparent record
Initial sourced env.sh assigned generic B to old toolroot and caused an unintended old-case conversion/scale/check rerun. Original sourceMSH and frozenZIP were untouched; failed4 unchanged. Mistaken-run logs retained in evidence/env-collision-incident. Before restoration frozenZIP SHAa88263ec63a98e2585f08931da6506b7e7fd7e3dbe32ba3ab34cf2b469af89a3 verified; after restoration every old manifest-listed bytehash matched. New env uses OF_ROOT, nativecommandJSONs prove all new case/output paths. Parent stop arrived after new check completed; no further run occurred. safe_native_command_template.py is an unexecuted explicit-env/absolute-path preflight replacement, not a request to rerun.

No old-artifact publishing from mistaken execution. No CFD or optimization run. New native quality remains unsatisfactory.
