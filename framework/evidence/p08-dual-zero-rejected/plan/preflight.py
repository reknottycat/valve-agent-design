import pathlib,hashlib,os,json,shutil
SRC=pathlib.Path('/workspace/shared/valve-boundary-grading-native-quality-20261023/case').resolve()
OUT=pathlib.Path('/workspace/shared/valve-dual-zero-trial-20261023').resolve()
TOOL=pathlib.Path('/workspace/shared/valve-openfoam-quality-20261023/root/usr').resolve()
OLD=pathlib.Path('/workspace/shared/valve-openfoam-quality-20261023/case').resolve()
assert not OUT.exists(), 'Refuse reuse: proposed output must not exist'
assert OUT!=SRC and OUT!=OLD and not OUT.is_relative_to(SRC) and not SRC.is_relative_to(OUT)
required=['points','faces','owner','neighbour','boundary','cellZones','faceZones','pointZones']
files=[SRC/'constant/polyMesh'/n for n in required if (SRC/'constant/polyMesh'/n).is_file()]
assert all((SRC/'constant/polyMesh'/n).is_file() for n in required[:5])
files += [SRC/'system'/n for n in ['controlDict','fvSchemes','fvSolution']]
assert all(p.is_file() and not p.is_symlink() for p in files)
assert all('sets' not in p.relative_to(SRC).parts for p in files)
manifest={str(p.relative_to(SRC)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
# Programmatic environment: no sourced shell, no assignment to caller variables.
env=os.environ.copy();env.update(WM_PROJECT_DIR=str(TOOL/'share/openfoam'),FOAM_ETC=str(TOOL/'share/openfoam/etc'),LD_LIBRARY_PATH=str(TOOL/'lib/dummy')+':'+str(TOOL/'lib'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
case=OUT/'case';assert case.is_relative_to(OUT) and not case.is_relative_to(SRC)
argv=[str(TOOL/'bin/polyDualMesh'),'-case',str(case),'-noFunctionObjects','0']
# Source controlDict inspected: startTime 0, deltaT 1, hence default nonoverwrite output expected 1.
text=(SRC/'system/controlDict').read_text();assert 'startTime 0;' in text and 'deltaT 1;' in text and 'startFrom startTime;' in text
check=[str(TOOL/'bin/checkMesh'),'-case',str(case),'-time','1','-allGeometry','-allTopology','-noFunctionObjects']
assert '-overwrite' not in argv and '-scale' not in argv
assert str(SRC) not in argv and str(OLD) not in argv
proof={'source':str(SRC),'new_root':str(OUT),'copy_whitelist':list(manifest),'source_hashes':manifest,'environment_overrides':{k:env[k] for k in ['WM_PROJECT_DIR','FOAM_ETC','LD_LIBRARY_PATH','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']},'conversion_argv':argv,'postvalidation_check_argv':check,'time_gate':'require exactly new 1/polyMesh with points faces owner neighbour boundary; check log must say time=1; never fallback constant','bounds':{'wall_seconds_per_native_process':180,'rss_bytes':2147483648},'no_conversion_executed':True}
print(json.dumps(proof,indent=2))
