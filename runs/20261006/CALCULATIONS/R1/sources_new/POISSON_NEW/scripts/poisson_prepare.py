from pathlib import Path
import re,subprocess,json
root=Path(__file__).resolve().parents[1]
def need(ok,msg):
 if not ok:raise RuntimeError(msg)
def clean(p):return re.sub(r'/\*.*?\*/|//[^\n]*','',p.read_text(),flags=re.S)
def body(p):
 s=clean(p);s=s[s.index('}')+1:];m=re.search(r'(\d+)\s*\(',s);need(bool(m),'bad list header');return int(m[1]),s[m.end():]
for n,su in [(5,-6),(10,-6),(5,6)]:
 case=root/'poisson-newrun'/f'n{n}_{"right" if su<0 else "wrong_sign"}'
 for d in ['system','constant','0']:(case/d).mkdir(parents=True,exist_ok=True)
 def dictfile(path,name,txt):path.write_text('FoamFile {version 2.0; format ascii; class dictionary; object '+name+';}\n'+txt)
 dictfile(case/'system/controlDict','controlDict','application laplacianFoam; startFrom startTime; startTime 0; stopAt endTime; endTime 10; deltaT 1; writeControl timeStep; writeInterval 1; writeFormat ascii; writePrecision 17; runTimeModifiable false;\n')
 dictfile(case/'system/blockMeshDict','blockMeshDict',f'''scale 1;
vertices ((0 0 0) (1 0 0) (1 1 0) (0 1 0) (0 0 1) (1 0 1) (1 1 1) (0 1 1));
blocks (hex (0 1 2 3 4 5 6 7) ({n} {n} {n}) simpleGrading (1 1 1)); edges ();
boundary (
x0 {{type wall; faces ((0 4 7 3));}}
x1 {{type wall; faces ((1 2 6 5));}}
y0 {{type wall; faces ((0 1 5 4));}}
y1 {{type wall; faces ((3 7 6 2));}}
z0 {{type wall; faces ((0 3 2 1));}}
z1 {{type wall; faces ((4 5 6 7));}}
); mergePatchPairs ();
''')
 dictfile(case/'system/fvSchemes','fvSchemes','ddtSchemes {default steadyState;} gradSchemes {default Gauss linear;} divSchemes {default none;} laplacianSchemes {default Gauss linear corrected;} interpolationSchemes {default linear;} snGradSchemes {default corrected;}\n')
 dictfile(case/'system/fvSolution','fvSolution','solvers {T {solver PCG; preconditioner DIC; tolerance 1e-12; relTol 0; maxIter 10000;}} SIMPLE {nNonOrthogonalCorrectors 2; residualControl {T 1e-11;}}\n')
 dictfile(case/'constant/transportProperties','transportProperties','DT [0 2 -1 0 0 0 0] 1;\n')
 dictfile(case/'constant/fvOptions','fvOptions','analyticalSource {type scalarSemiImplicitSource; active yes; scalarSemiImplicitSourceCoeffs {selectionMode all; volumeMode specific; injectionRateSuSp {T ('+str(su)+' 0);}}}\n')
 for exe,args in [('blockMesh',[]),('checkMesh',['-allTopology','-allGeometry'])]:
  r=subprocess.run([exe,'-case',str(case)]+args,text=True,capture_output=True,timeout=90);(case/f'log.{exe}').write_text(r.stdout+r.stderr);need(r.returncode==0 and 'FOAM FATAL' not in r.stdout+r.stderr,exe+' failed')
  if exe=='checkMesh':need('Mesh OK.' in r.stdout and 'Failed ' not in r.stdout,'checkMesh quality failed')
 mesh=case/'constant/polyMesh';np,ptxt=body(mesh/'points');points=[tuple(map(float,s.split())) for s in re.findall(r'\(([^()]+)\)',ptxt)];need(len(points)==np,'point count')
 nf,ftxt=body(mesh/'faces');faces=[list(map(int,s.split())) for k,s in re.findall(r'(\d+)\s*\(([^()]*)\)',ftxt)];need(len(faces)==nf and all(len(f)==4 for f in faces),'face format')
 no,otxt=body(mesh/'owner');owners=list(map(int,re.findall(r'-?\d+',otxt)))[:no]
 nn,ntxt=body(mesh/'neighbour');nei=list(map(int,re.findall(r'-?\d+',ntxt)))[:nn]
 cellpts=[set() for _ in range(n**3)]
 for fi,vv in enumerate(faces):
  cellpts[owners[fi]].update(vv)
  if fi<nn:cellpts[nei[fi]].update(vv)
 need(all(len(v)==8 for v in cellpts),'expected regular hexes')
 C=[tuple(sum(points[i][j] for i in v)/len(v) for j in range(3)) for v in cellpts]
 b=clean(mesh/'boundary');b=b[b.index('}')+1:];patches=[]
 for name,txt in re.findall(r'(\w+)\s*\{([^{}]+)\}',b):
  start=int(re.search(r'startFace\s+(\d+)',txt)[1]);count=int(re.search(r'nFaces\s+(\d+)',txt)[1]);patches.append((name,start,count))
 need(len(patches)==6,'six patches required')
 T='FoamFile {version 2.0; format ascii; class volScalarField; object T;}\ndimensions [0 0 0 1 0 0 0];\ninternalField uniform 0;\nboundaryField {\n'
 faceRecords=[]
 for name,start,count in patches:
  vals=[]
  for fi in range(start,start+count):
   cf=tuple(sum(points[i][j] for i in faces[fi])/4 for j in range(3));value=sum(x*x for x in cf);vals.append(value);faceRecords.append({'face':fi,'patch':name,'owner':owners[fi],'Cf':cf,'T_boundary':value,'area':1/n**2,'normal_distance':.5/n})
  T+=name+' {type fixedValue; value nonuniform List<scalar> '+str(count)+' (\n'+'\n'.join(f'{v:.17g}' for v in vals)+'\n);}\n'
 T+='}\n';(case/'0/T').write_text(T)
 (case/'reference.json').write_text(json.dumps({'n':n,'cell_count':n**3,'h':1/n,'V':1/n**3,'C':C,'boundary_faces':faceRecords,'analytic_source_laplacian':6,'fvOptions_Su':su,'initial_internal_T':0,'source_provenance':'Constant analytic Delta(T)=6, never computed from a discrete exact field','units':{'T':'K','DT':'m^2/s','analytic_laplacian':'K/m^2','fvOptions_Su':'K/s'}},indent=2)+'\n')
 print('Prepared',case,flush=True)
