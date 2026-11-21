from pathlib import Path
import json,re,shutil,hashlib,zipfile
r=Path(__file__).parent;b=Path('/workspace/shared/valve-local-volume-grading-native-20261023')
s=(r/'evidence/checkMesh.log').read_text()
base=json.loads((b/'evidence/comparison.json').read_text())['new']
new={k:int(re.search(r'^\s*'+re.escape(k)+r':\s+(\d+)',s,re.M)[1]) for k in ['cells','faces','internal faces']}
new.update(skew=0,nonortho=4235,det=2799,weight=229,ratio=112,max_skew=3.66000889652733,max_nonortho=89.7807095209027,failed=3)
new['fractions']={k:new[k]/new['cells' if k=='det' else 'faces'] for k in ['skew','nonortho','det','weight','ratio']}
out={'baseline':base,'new':new,'fraction_denominators':'det/all cells; all face counts/all faces, not necessarily the native tested subset','engineering_release':False,'R1_fullcheck_PASS':False}
(r/'evidence/comparison.json').write_text(json.dumps(out,indent=2))
shutil.copy2(b/'evidence/tool-packages.json',r/'evidence/tool-packages.json')
rows='\n'.join(f'| {k} | {base[k]} ({100*base["fractions"][k]:.6f}%) | {new[k]} ({100*new["fractions"][k]:.6f}%) |' for k in ['skew','nonortho','det','weight','ratio'])
(r/'README.md').write_text('''# Cone-local grading: native OpenFOAM quality evidence

Official Debian OpenFOAM 1912.200626-3+b1, serial dummy Pstream. ONE new conversion/scale/check; no solver, no threshold edits. Source mm mesh SHA ec42b02e7f907abd5297bfdeeb74afa1917730ed986541eb7113fdfd95d1c3ef remains immutable. Export MSH2.2 changes only dimension-3 physical 1→1001; nodes and triangle/tetra connectivity matched, 132 surface roles/counts preserved. transformPoints scale0.001 once, point-set bijection verified before checkMesh.

## Result
Native **Failed 3**, improved from prior Failed 4. Native exit0 is not PASS. Frozen R1 fullcheckPASS prerequisite remains unmet; no engineering release.

| Check | 614334 baseline | 688424 cone candidate |
|---|---:|---:|
'''+rows+'''

Fractions use all cells for determinant, all faces for face counts; not a claim of exact tested-face subset fractions. Max skew 10.1340537→3.6600089; max nonorthogonality89.7807095 unchanged. Positive volumes, face pyramids, face tets and topology checks pass. Total volume0.0637018963656401m³ (prior0.0637018962272279m³); same bounding box. This surface-refined candidate is intentionally not identical to prior boundary triangulation, but its exported copy is identical to its own source.

Native check elapsed11.539s, peak691142656B; all native processes below180s/2GiB guard. Exact absoluteargv/cwd/environment in evidence/preflight.json and per-step JSON. Oldcases untouched; no environment scripts sourced. Initial source-path string replacement pointed to older2D mesh; SHA assertion stopped preflight before any export/native action. Corrected to authorized cone-grading-volume source; only validated chain executed.

All source/export/readback evidence, logs, native badsets, scripts and case retained. Archive excludes installed libraries/packages/binaries.
''')
manifest={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob('*') if p.is_file() and p.name not in ['manifest.json','cone-grading-native-quality.zip']}
(r/'manifest.json').write_text(json.dumps(manifest,indent=2))
z=r/'cone-grading-native-quality.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as f:
 for p in sorted(r.rglob('*')):
  if p.is_file() and p!=z:f.write(p,p.relative_to(r))
print(json.dumps(out,indent=2));print(z,z.stat().st_size,hashlib.sha256(z.read_bytes()).hexdigest())
