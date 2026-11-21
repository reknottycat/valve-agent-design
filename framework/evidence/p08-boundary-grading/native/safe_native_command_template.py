# Future invocation template, NOT executed in this comparison.
from pathlib import Path
import os,subprocess
NEW=Path('/workspace/shared/valve-boundary-grading-native-quality-20261023').resolve()
OLD=Path('/workspace/shared/valve-openfoam-quality-20261023').resolve()
TOOL=OLD/'root/usr'
case=(NEW/'case').resolve(); output=(NEW/'evidence').resolve()
assert case.is_relative_to(NEW) and output.is_relative_to(NEW)
assert not case.is_relative_to(OLD) and not output.is_relative_to(OLD)
env=os.environ.copy();env.update(WM_PROJECT_DIR=str(TOOL/'share/openfoam'),FOAM_ETC=str(TOOL/'share/openfoam/etc'),LD_LIBRARY_PATH=f'{TOOL}/lib/dummy:{TOOL}/lib',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
commands=[
 [str(TOOL/'bin/gmshToFoam'),'-case',str(case),str(NEW/'source-copy-ascii22-mm.msh')],
 [str(TOOL/'bin/transformPoints'),'-case',str(case),'-scale','0.001'],
 [str(TOOL/'bin/checkMesh'),'-case',str(case),'-constant','-allGeometry','-allTopology']]
# DO NOT automatically rerun or rescale the completed case.
if __name__=='__main__':
 for c in commands: print(c)
