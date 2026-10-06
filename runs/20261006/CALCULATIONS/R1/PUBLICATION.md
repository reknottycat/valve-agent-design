# R1 publication and recovery

This directory preserves the frozen 39-page R1 WORKING DRAFT. Manufacturing release remains HOLD. The 183 ZIP member files and their scientific manifest are unchanged.

## Ordinary ZIP and Windows

The ordinary ZIP is named `522-35.4179_R1_计算书重建检查点.zip`: 3,322,031 bytes, SHA256 `7de84ba1c6f7654aa79948c5c39cbc76d6e10a0a0fd1f13480c6c60577e4d5fe`. Its already delivered Library identity is `libfile_8ebda1ebc58081919dd72e9f32294da2`, version 10. This identity is not a public download URL. Windows users can download that ordinary ZIP from the existing attachment/Library item and use Windows “Extract All”; no chunk restorer is needed for that ZIP.

## Git checkout

Git stores the two large output documents and the exact ordinary ZIP as lossless chunks. They are not directly present at their original paths until restored. The 181 smaller frozen files remain at their ordinary paths. Existing C2/C3/R0 transport is unchanged; its default manifest does not include R1.

From the repository root on Linux with Python 3.9+ and /proc/self/fd:

```sh
python3 -B artifact_storage/restore_artifacts.py --storage-root . --manifest artifact_storage/manifests/R1.json --verify-only
python3 -B artifact_storage/restore_artifacts.py --storage-root . --manifest artifact_storage/manifests/R1.json --restore --destination .
```

Git chunk restoration requires Linux. Windows is unsupported and macOS restoration has not been verified. The restorer checks all bytes and refuses different existing files rather than overwriting them. See the existing artifact_storage/README.md for the safety limits.

## Scope

R1 includes six elastic disc reference cases, mesh v2 evidence and independent cube Poisson benchmarks. The later actual-valve PDE failure, unilateral-contact patch, and joint studies are not in this frozen edition. Neither successful solver benchmarks nor document QA establish completed actual-valve CFD/FEA, permitted strength, physical testing, or manufacturing acceptance.
