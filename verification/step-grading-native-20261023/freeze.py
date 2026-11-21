from pathlib import Path
import json,re,shutil,hashlib,zipfile
r=Path(__file__).parent;b=Path('/workspace/shared/valve-cone-grading-native-20261023');s=(r/'evidence/checkMesh.log').read_text();assert s.rstrip().endswith('End')
base=json.loads((b/'evidence/comparison.json').read_text())['new']
new={k:int(re.search(r'^\s*'+re.escape(k)+r':\s+(\d+)',s,re.M)[1]) for k in ['cells','faces','internal faces']}
for key,pat in {'skew':r', (\d+) highly skew faces','nonortho':r'faces: (\d+)\.', 'det':r'number of cells: (\d+)','weight':r'interpolation weight \(< 0.05\) found, number of faces: (\d+)','ratio':r'volume ratio \(< 0.01\) found, number of faces: (\d+)','failed':r'Failed (\d+) mesh checks'}.items():
 m=re.search(pat,s);new[key]=int(m[1]) if m else 0
for key,pat in {'max_skew':r'Max skewness = ([0-9.eE+-]+)','max_nonortho':r'non-orthogonality Max: ([0-9.eE+-]+)'}.items():new[key]=float(re.search(pat,s)[1])
new['fractions']={k:new[k]/new['cells' if k=='det' else 'faces'] for k in ['skew','nonortho','det','weight','ratio']}
out={'baseline':base,'new':new,'fraction_denominators':'det/all cells; face counts/all faces, not necessarily native tested subset','engineering_release':False,'R1_fullcheck_PASS':new['failed']==0}
(r/'evidence/comparison.json').write_text(json.dumps(out,indent=2));shutil.copy2(b/'evidence/tool-packages.json',r/'evidence/tool-packages.json')
rows='\n'.join(f'| {k} | {base[k]} ({100*base["fractions"][k]:.6f}%) | {new[k]} ({100*new["fractions"][k]:.6f}%) |' for k in ['skew','nonortho','det','weight','ratio'])
log=json.loads((r/'evidence/checkMesh.json').read_text());verify=json.loads((r/'evidence/conversion-verification.json').read_text())
(r/'README.md').write_text(f'''# Step-local grading: native quality evidence

Official Debian OpenFOAM1912.200626-3+b1, serial dummy Pstream. One new conversion/scale/check; no solver or threshold edits. Source SHA {verify['source_sha256']} immutable. Export dimension3 physical1→1001, MSH2.2; nodes and triangle/tetra connectivity identical, all132 surface roles/counts preserved. mm→m scaled exactly once, coordinate-set bijection verified before nativecheck. Explicit absolute cwd/env/argv and180s/2GiB perprocess guard in run.py/preflight.json; no oldcase writes or sourced wrappers.

Native Failed {new['failed']} versus baseline Failed {base['failed']}. Exit0 is not PASS. No engineering release. R1 prerequisite is not amended.

| Metric | 688424 baseline | 759760 step candidate |
|---|---:|---:|
{rows}

Maxskew {base['max_skew']}→{new['max_skew']}; maxnonorthogonality {base['max_nonortho']}→{new['max_nonortho']}. Fractions use allcells or allfaces as stated, not native tested subset. Native walltime{log['seconds']:.3f}s, peakRSS{log['peak_rss']}B. Totalvolume 0.0637018963656401→0.0637073024273604m³ (+0.00849%); bbox unchanged. This source surface refinement changes the faceted geometry: source/export identity does not prove geometry equivalence to prior cone. Positive cell volumes, facepyramids and facetets pass. Lowdet absolute count AND fraction worsen; average nonorthogonality25.47149→25.57188 also worsens. See full raw log for every deterioration, all geometry/topology results and volume extrema. All source/copy scripts,case,badsets,logs preserved; installed runtime binaries/packages excluded.
''')
manifest={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob('*') if p.is_file() and p.name not in ['manifest.json','step-grading-native-quality.zip']};(r/'manifest.json').write_text(json.dumps(manifest,indent=2))
z=r/'step-grading-native-quality.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as f:
 for p in sorted(r.rglob('*')):
  if p.is_file() and p!=z:f.write(p,p.relative_to(r))
with zipfile.ZipFile(z) as f:assert all(hashlib.sha256(f.read(k)).hexdigest()==v for k,v in manifest.items())
assert hashlib.sha256(Path('/workspace/shared/valve-step-grading-volume-20261023/fresh-local-surface.msh').read_bytes()).hexdigest()==verify['source_sha256']
print(json.dumps(out,indent=2));print(z,z.stat().st_size,hashlib.sha256(z.read_bytes()).hexdigest(), 'archive and source verified')
