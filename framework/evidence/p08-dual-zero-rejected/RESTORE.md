# Rejected candidate evidence

This polyDualMesh 0-degree trial is rejected: native checkMesh Failed 10, including 55 zero/negative-volume cells. Do not use it for flow simulation. The source tetrahedral cases remain unchanged.

The complete 50,865,181-byte diagnostic ZIP is preserved in seven ordered binary parts under archives/. Concatenate part01 through part07 and verify SHA256 f7f1fdee1b14ad3d6eb5cad9b28b63695502b03f96381069c4a9623d9bc9256a before extracting. Individual hashes are in parts.json. No data was dropped; splitting only respects the transport limit.

Input/output cases, native failures, empty cellZone defect, geometry-check limitations, and the cwd-output diagnostic are intentionally retained. Exit code 0 is not an acceptance result.
