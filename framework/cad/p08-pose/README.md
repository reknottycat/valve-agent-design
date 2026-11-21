# P08 source-to-pose evidence recovery

**Correction:** 57 mm is not supported only by the R1 planned input. The original FDG1 validation summary contains a historical independent read-only source/export geometry review establishing nominal +Z translation 57 mm for disc, stem, shoe and retainer. Both directional shape-set differences (expected minus export, export minus expected) are recorded as 0 mm³ for all four. Disc volume delta is approximately 1.0838e-7 mm³; other three are zero. Zero reported differences are numerical CAD results, not proof of infinite exactness. The recovered JSON does not state the boolean/classifier tolerance for those operations; do not invent one.

The same historical report pins closed/source component hashes, open57 exported component hashes, the source manifest, C2/GA1 parameter files, build_fluid_domain.py and exact original fluid STEP SHA a9aeb45996a388a3d894f69605205c70c25edd154adc6d3c71658329a730e787. It records unchanged reviewed files, no candidate-builder execution, and NOMINAL_METAL_GEOMETRY_PROXY_VERIFIED_WITH_EXPLICIT_HOLDS. This is a stronger historical evidence chain than a filename or plan alone.

This run fetched only two small original FDG1 JSON files (1,707 and 32,548 bytes), checked both hashes against existing PRODUCT_INDEX, and extracted the chain. Original files are included unchanged, exact URLs/hashes in pose_chain.json. A separate prior run imported the hash-matching fluid STEP and checked ports. **This run did not reexecute the historical translation/boolean checks.** Do not describe those historical checks as never done. Conversely, the same face numbers do not establish a full cross-exporter face-ID bijection.

Remaining distinctions:
- Historical nominal translation verification is available and can be reused; new component-level measurement needs the exact pinned source/open component bytes or verified datum correspondence. Those byte files were not in the recovered A02 subset, not asserted absent from all archives.
- Engineering meaning of physical lift still needs the identified disc/seat reference surfaces plus toleranced/loaded assembly conditions if actual-product acceptance is claimed. Do not block nominal proxy research merely because actual-product datum qualification is a separate future criterion.
- Rubber omitted, J16 uncompressed 2 mm gasket, packing cap z332 parameter-derived not cover ledge, and other original model holds remain. Original report's complete holds are preserved.
- Final retained volume-mesh patch mapping and solver acceptance remain separate; the historical pose report does not establish them.

Stopped after recovering source-to-pose chain; no geometry reconstruction, new mesh or CFD. Reproduce extraction using included FDG1 JSONs and existing PRODUCT_INDEX.json: `python3 extract_pose_chain.py FDG1_验证摘要.json FDG1_模型范围与单位.json /path/to/PRODUCT_INDEX.json`.
