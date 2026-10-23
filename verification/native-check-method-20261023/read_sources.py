from pathlib import Path
import urllib.request
r=Path(__file__).parent
for p in ['src/OpenFOAM/meshes/primitiveMesh/primitiveMeshCheck/primitiveMeshTools.C','src/OpenFOAM/meshes/polyMesh/polyMeshCheck/polyMeshCheck.C','applications/utilities/mesh/manipulation/checkMesh/checkGeometry.C']:
 s=urllib.request.urlopen('https://sources.debian.org/data/main/o/openfoam/1912.200626-3/'+p,timeout=20).read().decode();(r/Path(p).name).write_text(s)
 lines=s.splitlines()
 for i,l in enumerate(lines):
  if any(x in l for x in ['Foam::polyMesh::checkCellDeterminant','Foam::primitiveMeshTools::cellDeterminant','Foam::primitiveMeshTools::faceWeights','Foam::primitiveMeshTools::volRatio']):print('FILE',p,'\n'+'\n'.join(f'{j+1}: {lines[j]}' for j in range(i,min(i+140,len(lines)))))
