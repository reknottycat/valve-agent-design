# Boundary grading comparison

Surface transition improved, but the resulting 266,705-cell native case still Failed 4 mesh checks. No flow solver was run and this is not engineering approval. Keep the previous 230,553-cell candidate for an honest comparison. Detailed findings and an execution-incident audit are in native/README.md.

The archives directory preserves the actual 2D surface, 3D mesh and complete native case/evidence. Native ZIP parts must be concatenated in numeric order. Verify sizes and SHA256 against archives.json before extracting. Splitting only addresses a transport request limit; no case data was omitted. Do not scale the native case twice; it is already in metres.
