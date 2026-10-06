#!/usr/bin/env python3
"""Fresh 2026-10-06 rebuild. N-mm-MPa. No restored numerical result is accepted.
Linear C3D4 / straight-sided C3D10 pressure-only, bilateral rigid seat reference.
Every acceptance gate is an explicit exception, including under Python -O.
"""
import argparse,csv,datetime,hashlib,json,math,os,pathlib,subprocess,time
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE_ROOT=pathlib.Path('/workspace/shared/valve-cloud-recovered-20261006')
STEP=SOURCE_ROOT/'runs/20261006/C2/T12/out/check_closed/disc_guide.step'
STEP_SHA='176d0f389e188b339132d7ec05e9e59cdd8861c5138e0839900ba653d0e85ee9'
R0=SOURCE_ROOT/'runs/20261006/CALCULATIONS/R0'
MATERIAL=R0/'sources/C5/T05/material_cards.json'
MATERIAL_SHA='7cfbbca2adb2698ad623278fcfe53704f11d4eaf89f3395ef386487860216c09'
SOLVER_ROOT=pathlib.Path('/workspace/shared/valve-solvers-rebuilt-20261006')
SOLVER_ENV=SOLVER_ROOT/'env.sh'
E=114000.;NU=.32;P=.63
EDGES=((0,1),(1,2),(2,0),(0,3),(1,3),(2,3))
def need(ok,message):
    if not ok:raise RuntimeError(message)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def write_json(p,obj):pathlib.Path(p).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def source_checks(patch=False):
    baseline=json.loads((SOLVER_ROOT/'evidence/fresh-baseline-results.json').read_text())
    need(baseline.get('old_logs_restored') is False,'Solver evidence must be a fresh run')
    need(len(baseline.get('ccx',[]))==4 and all(c.get('passed') is True for c in baseline['ccx']),'Fresh native CCX baseline required')
    sources={'solver_env':{'path':str(SOLVER_ENV),'sha256':sha(SOLVER_ENV)},'solver_baseline':{'path':str(SOLVER_ROOT/'evidence/fresh-baseline-results.json'),'sha256':sha(SOLVER_ROOT/'evidence/fresh-baseline-results.json')}}
    if not patch:
        need(STEP.is_file() and sha(STEP)==STEP_SHA,'Recovered source STEP missing or hash mismatch')
        need(MATERIAL.is_file() and sha(MATERIAL)==MATERIAL_SHA,'Recovered R0 material card hash mismatch')
        binding=json.loads((R0/'source_manifest.json').read_text());entries=[r for r in binding['files'] if r['relative_path']=='C5/T05/material_cards.json'];need(len(entries)==1 and entries[0]['sha256']==MATERIAL_SHA,'R0 material manifest binding mismatch')
        card=json.loads(MATERIAL.read_text());selected=[c for c in card['cards'] if c['id']=='ALT_C95800_CONTINUOUS_CAST'];need(len(selected)==1,'Explicit alternative material card missing')
        values=selected[0]['adopted_study_inputs'];need(values['young_modulus_MPa']==E and values['poisson_ratio']==NU and values['density_kg_m3']==7640,'Recovered reference card differs from task scope')
        need(values.get('allowable_stress_MPa') is None,'No allowable stress may be adopted')
        sources.update(source_step={'path':str(STEP),'sha256':sha(STEP)},material_card={'path':str(MATERIAL),'sha256':sha(MATERIAL)},R0_source_manifest={'path':str(R0/'source_manifest.json'),'sha256':sha(R0/'source_manifest.json')})
    return sources

def exterior_faces(tets):
    allfaces={}
    for e,t in enumerate(tets[:,:4]):
        for opposite in range(4):
            key=tuple(sorted(int(t[j]) for j in range(4) if j!=opposite))
            if key in allfaces:allfaces[key][2]+=1
            else:allfaces[key]=[e,int(t[opposite]),1]
    need(all(v[2] in (1,2) for v in allfaces.values()),'Nonmanifold volume mesh')
    return {k:v for k,v in allfaces.items() if v[2]==1}

def oriented_load(coords,triangles,owners,pressure):
    f=np.zeros_like(coords);data=[]
    for row in triangles:
        tri=np.asarray(row,dtype=int);key=tuple(sorted(map(int,tri)));need(key in owners,'Load triangle has no exterior tetra owner')
        p=coords[tri];av=.5*np.cross(p[1]-p[0],p[2]-p[0])
        if np.dot(av,coords[owners[key][1]]-p.mean(axis=0))>0:av=-av
        ff=-pressure*av;f[tri]+=ff/3;data.append([*tri,*av,*ff])
    return f,np.array(data)

def mesh_linear(case,h,patch):
    need((ROOT/'evidence/CAD_READY.json').is_file(),'Parent CAD readiness confirmation required before meshing')
    sources=source_checks(patch)
    import gmsh
    gmsh.initialize();gmsh.logger.start()
    try:
        for key,val in {'General.NumThreads':1,'Mesh.MaxNumThreads1D':1,'Mesh.MaxNumThreads2D':1,'Mesh.MaxNumThreads3D':1,'Mesh.RandomSeed':20261006,'Mesh.ElementOrder':1,'Mesh.Algorithm3D':1,'Mesh.MeshSizeMin':h,'Mesh.MeshSizeMax':h,'Mesh.MeshSizeFromCurvature':0,'Mesh.Optimize':1,'Mesh.OptimizeThreshold':.3}.items():gmsh.option.setNumber(key,val)
        if patch:
            gmsh.model.occ.addBox(0,0,0,10,10,10);gmsh.model.occ.synchronize();before=after=1000.
        else:
            gmsh.model.occ.importShapes(str(STEP));gmsh.model.occ.synchronize();vols=gmsh.model.getEntities(3);need(len(vols)==1,'Source must be one solid');before=gmsh.model.occ.getMass(*vols[0])
            disks=[(2,gmsh.model.occ.addDisk(300,0,22,r,r)) for r in (100,114)];gmsh.model.occ.fragment(vols,disks);gmsh.model.occ.synchronize();vols=gmsh.model.getEntities(3);need(len(vols)==1,'Partition changed solid count');after=gmsh.model.occ.getMass(*vols[0]);need(abs(after/before-1)<1e-10,'Partition changed CAD volume')
            surfaces=[t for d,t in gmsh.model.getEntities(2) if abs(gmsh.model.occ.getMass(d,t)-math.pi*100**2)<1e-5];need(len(surfaces)==1,'Central face not identified');pt=gmsh.model.occ.addPoint(300,0,22);gmsh.model.occ.synchronize();gmsh.model.mesh.embed(0,[pt],2,surfaces[0])
        groups={'wet':[],'seat':[],'dry':[]};surface_info=[]
        for d,t in gmsh.model.getBoundary(gmsh.model.getEntities(3),combined=True,oriented=False):
            bb=gmsh.model.getBoundingBox(d,t);area=gmsh.model.occ.getMass(d,t);z=0 if patch else 22;bottom=abs(bb[2]-z)<1e-5 and abs(bb[5]-z)<1e-5
            if patch:kind='seat' if bottom else ('wet' if abs(bb[2]-10)<1e-5 and abs(bb[5]-10)<1e-5 else 'dry')
            elif not bottom:kind='wet'
            elif abs(area-math.pi*100**2)<1e-5:kind='dry'
            elif abs(area-math.pi*(114**2-100**2))<1e-5:kind='seat'
            elif abs(area-math.pi*(120**2-114**2))<1e-5:kind='wet'
            else:raise RuntimeError('Unclassified bottom surface')
            groups[kind].append(t);surface_info.append(dict(tag=t,kind=kind,area_mm2=area,bbox=list(bb)))
        for name,tags in groups.items():pid=gmsh.model.addPhysicalGroup(2,tags);gmsh.model.setPhysicalName(2,pid,name)
        gmsh.model.addPhysicalGroup(3,[t for d,t in gmsh.model.getEntities(3)])
        gmsh.model.mesh.generate(3);gmsh.write(str(case/'mesh.msh'))
        nt,xyz,_=gmsh.model.mesh.getNodes();o=np.argsort(nt);nt=np.asarray(nt)[o];coords=np.asarray(xyz).reshape(-1,3)[o];lookup={int(n):i for i,n in enumerate(nt)}
        types,et,conn=gmsh.model.mesh.getElements(3);need(len(types)==1 and int(types[0])==4,'Linear tetra mesh required');eo=np.argsort(et[0]);tets=np.array([[lookup[int(n)] for n in row] for row in np.asarray(conn[0]).reshape(-1,4)],int)[eo]
        det=np.linalg.det(coords[tets[:,1:]]-coords[tets[:,0,None]]);negative=det<0;tets[negative,1],tets[negative,2]=tets[negative,2].copy(),tets[negative,1].copy();det=np.linalg.det(coords[tets[:,1:]]-coords[tets[:,0,None]])
        need(det.min()>1e-12,'Nonpositive tetrahedron volume');need(len(coords)<150000 and len(tets)<800000,'Mesh size budget exceeded');vol=det/6
        quality=np.asarray(gmsh.model.mesh.getElementQualities(np.asarray(et[0])[eo].tolist(),'minSICN'));need(quality.min()>.01,'Degenerate tetra quality')
        tris={}
        for name,tags in groups.items():
            parts=[]
            for tag in tags:
                ty,_,cn=gmsh.model.mesh.getElements(2,tag);need(len(ty)==1 and int(ty[0])==2,'Only linear triangular faces supported');parts.extend([[lookup[int(n)] for n in row] for row in np.asarray(cn[0]).reshape(-1,3)])
            tris[name]=np.array(parts,int)
        owners=exterior_faces(tets);keys=[tuple(sorted(map(int,tr))) for group in tris.values() for tr in group];need(len(keys)==len(set(keys))==len(owners) and set(keys)==set(owners),'Exterior grouping coverage/topology failed')
        F,face_data=oriented_load(coords,tris['wet'],owners,P);seat=np.unique(tris['seat']);ta=np.array([0,0,0]) if patch else np.array([300,0,22]);tb=np.array([10,0,0]) if patch else np.array([400,0,22]);a=int(np.linalg.norm(coords-ta,axis=1).argmin());b=int(np.linalg.norm(coords-tb,axis=1).argmin());need(np.linalg.norm(coords[a]-ta)<1e-7 and np.linalg.norm(coords[b]-tb)<1e-7,'Required minimal anchor absent');bc=np.array([(int(n),2) for n in seat]+[(a,0),(a,1),(b,1)])
        origin=np.array([5,5,0]) if patch else ta;analytic=-P*(100 if patch else math.pi*114**2);forceerr=abs(F[:,2].sum()/analytic-1);moment=np.cross(coords-origin,F).sum(axis=0)
        need(forceerr<(1e-12 if patch else .002),'Pressure resultant area check failed');need(np.linalg.norm(F.sum(axis=0)[:2])<1e-8,'Unexpected transverse load');need(np.linalg.norm(moment)/abs(analytic)/(10 if patch else 114)<1e-4,'Applied pressure moment invalid')
        model=dict(schema='fresh_disc_structural/1',case=case.name,fresh_created_utc=now(),patch=patch,order='C3D4',target_h_mm=h,nodes=len(coords),elements=len(tets),sources=sources,gmsh_version=gmsh.__version__,cad_volume_before_mm3=before,cad_volume_after_mm3=after,mesh_volume_mm3=float(vol.sum()),mesh_volume_relative_error=float(vol.sum()/before-1),quality_minSICN_min=float(quality.min()),quality_minSICN_median=float(np.median(quality)),surfaces=surface_info,E_MPa=E,nu=NU,pressure_MPa=P,analytic_Fz_N=analytic,force_resultant_N=F.sum(axis=0).tolist(),force_area_relative_error=float(forceerr),load_moment_Nmm=moment.tolist(),origin_mm=origin.tolist(),material_for_manufacturing=False,allowable_stress_MPa=None,contact='Bilateral rigid frictionless seat; not unilateral contact',temperature_qualification=False)
        np.savez_compressed(case/'mesh.npz',coords=coords,tets=tets,volumes=vol,forces=F,bc=bc,seat_nodes=seat,seat_triangles=tris['seat'],wet_triangles=tris['wet'],pressure_faces=face_data,quality=quality)
        write_json(case/'model.json',model);write_input(case)
    finally:
        (case/'log.gmsh').write_text('\n'.join(gmsh.logger.get()));gmsh.logger.stop();gmsh.finalize()

def elevate(source,case):
    x=np.load(source/'mesh.npz');co=x['coords'];allco=co.tolist();edge_index={};new=[]
    for tet in x['tets']:
        mids=[]
        for a,b in EDGES:
            edge=tuple(sorted((int(tet[a]),int(tet[b]))))
            if edge not in edge_index:edge_index[edge]=len(allco);allco.append(((co[edge[0]]+co[edge[1]])/2).tolist())
            mids.append(edge_index[edge])
        new.append([*tet,*mids])
    co=np.array(allco);need(len(co)<100000,'Quadratic node budget exceeded');tets=np.array(new,int);F=np.zeros_like(co)
    for row in x['pressure_faces']:
        tri=row[:3].astype(int);mids=[edge_index[tuple(sorted((int(tri[k]),int(tri[(k+1)%3]))))] for k in range(3)];F[mids]+=row[6:9]/3
    seat=set(map(int,x['seat_nodes']))
    for tri in x['seat_triangles']:
        for k in range(3):seat.add(edge_index[tuple(sorted((int(tri[k]),int(tri[(k+1)%3]))))])
    bc=np.array([(n,2) for n in sorted(seat)]+[(int(n),int(d)) for n,d in x['bc'] if d!=2]);need(np.allclose(F.sum(axis=0),x['forces'].sum(axis=0),atol=1e-7,rtol=1e-12),'Quadratic consistent load changed resultant')
    m=json.loads((source/'model.json').read_text());m.update(case=case.name,order='C3D10',nodes=len(co),fresh_created_utc=now(),source_linear_mesh_sha256=sha(source/'mesh.npz'),geometry='Straight-sided edge midpoints; same faceted volume as C3D4')
    np.savez_compressed(case/'mesh.npz',coords=co,tets=tets,volumes=x['volumes'],forces=F,bc=bc,seat_nodes=np.array(sorted(seat)),seat_triangles=x['seat_triangles'],wet_triangles=x['wet_triangles'],pressure_faces=x['pressure_faces'],quality=x['quality']);write_json(case/'model.json',m);write_input(case)

def write_input(case):
    m=json.loads((case/'model.json').read_text());x=np.load(case/'mesh.npz')
    with (case/'disc.inp').open('w') as f:
        f.write('*HEADING\nFresh source-C2 reference only; N-mm-MPa; no strength pass\n*NODE,NSET=NALL\n')
        for n,co in enumerate(x['coords'],1):f.write(f'{n},'+','.join(f'{v:.12e}' for v in co)+'\n')
        f.write(f"*ELEMENT,TYPE={m['order']},ELSET=EALL\n")
        for n,t in enumerate(x['tets'],1):f.write(f'{n},'+','.join(str(int(v)+1) for v in t)+'\n')
        f.write('*MATERIAL,NAME=C95800_ELASTIC_REFERENCE_ONLY\n*ELASTIC\n114000,0.32\n*SOLID SECTION,ELSET=EALL,MATERIAL=C95800_ELASTIC_REFERENCE_ONLY\n*BOUNDARY\n')
        for n,d in x['bc']:f.write(f'{n+1},{d+1},{d+1}\n')
        f.write('*STEP\n*STATIC\n*CLOAD\n')
        for n,row in enumerate(x['forces'],1):
            for d,v in enumerate(row,1):
                if abs(v)>1e-15:f.write(f'{n},{d},{v:.12e}\n')
        f.write('*NODE PRINT,NSET=NALL\nU,RF\n*EL PRINT,ELSET=EALL\nS\n*NODE FILE\nU\n*EL FILE\nS\n*END STEP\n')
    for line in (case/'disc.inp').read_text().splitlines():
        if line and line[0].isdigit():need(all(len(v)<=20 for v in line.split(',')),'Numeric input field exceeds CalculiX width')

def parse_dat(path,nn,ne,nq):
    u=np.full((nn,3),np.nan);rf=u.copy();s=np.full((ne,nq,6),np.nan);mode=None
    for line in pathlib.Path(path).read_text().splitlines():
        t=line.strip();p=t.split()
        if t.startswith('displacements ('):mode='U';continue
        if t.startswith('forces ('):mode='RF';continue
        if t.startswith('stresses ('):mode='S';continue
        if not p or not p[0].isdigit():continue
        if mode in ('U','RF') and len(p)==4:(u if mode=='U' else rf)[int(p[0])-1]=list(map(float,p[1:]))
        elif mode=='S' and len(p)==8:
            e,q=int(p[0])-1,int(p[1])-1;need(0<=e<ne and 0<=q<nq,'Unexpected stress integration point');s[e,q]=list(map(float,p[2:]))
    need(np.isfinite(u).all() and np.isfinite(rf).all() and np.isfinite(s).all(),'Raw DAT missing/nonfinite required fields')
    return u,rf,s

def calculate(case):
    """Read raw DAT every time. This function writes no result or manifest."""
    m=json.loads((case/'model.json').read_text());x=np.load(case/'mesh.npz');co=x['coords'];t=x['tets'];F=x['forces'];bc=x['bc'];vol=x['volumes'];nq=1 if m['order']=='C3D4' else 4;u,rf,s=parse_dat(case/'disc.dat',len(co),len(t),nq)
    mask=np.zeros_like(u,bool);mask[bc[:,0],bc[:,1]]=True;R=np.where(mask,rf-F,0);scale=np.linalg.norm(F.sum(axis=0));balance=np.linalg.norm((F+R).sum(axis=0))/scale;free=np.linalg.norm((rf-F)[~mask])/scale;need(balance<2e-5 and free<2e-5,'Reaction or free-DOF force equilibrium failed')
    need(abs(u[mask]).max()<1e-12,'Prescribed zero displacement violated')
    grad=np.linalg.inv(np.concatenate([np.ones((len(t),4,1)),co[t[:,:4]]],axis=2))[:,1:,:].transpose(0,2,1)
    aa=(5+3*np.sqrt(5))/20;bb=(5-np.sqrt(5))/20;barys=np.full((4,4),bb);np.fill_diagonal(barys,aa)
    reconstructed=[]
    for q in range(nq):
        if nq==1:g=grad
        else:
            b=barys[q];g=np.zeros((len(t),10,3));g[:,:4]=(4*b-1)[None,:,None]*grad
            for k,(i,j) in enumerate(EDGES):g[:,k+4]=4*(b[i]*grad[:,j]+b[j]*grad[:,i])
        gu=np.einsum('eia,eib->eab',u[t],g);eps=(gu+gu.transpose(0,2,1))/2;mu=E/(2*(1+NU));lam=E*NU/((1+NU)*(1-2*NU));sig=2*mu*eps+lam*np.trace(eps,axis1=1,axis2=2)[:,None,None]*np.eye(3);reconstructed.append(np.stack([sig[:,0,0],sig[:,1,1],sig[:,2,2],sig[:,0,1],sig[:,0,2],sig[:,1,2]],axis=1))
    sr=np.stack(reconstructed,axis=1);serr=float(abs(sr-s).max()/max(1,abs(s).max()));need(serr<.003,'Raw stress disagrees with displacement kinematics')
    normal_eps=(s[:,:,:3]-NU*(s[:,:,:3].sum(axis=2)[:,:,None]-s[:,:,:3]))/E;ed=.5*(normal_eps*s[:,:,:3]).sum(axis=2)+(1+NU)/E*(s[:,:,3:]**2).sum(axis=2);energy=float((vol[:,None]*ed/nq).sum());work=float(.5*(F*u).sum());need(energy>0 and work>0,'Nonpositive strain energy/work');eerr=abs(energy/work-1);need(eerr<2e-5,'Strain energy/external half-work consistency failed')
    vm=np.sqrt(.5*((s[:,:,0]-s[:,:,1])**2+(s[:,:,1]-s[:,:,2])**2+(s[:,:,2]-s[:,:,0])**2)+3*(s[:,:,3:]**2).sum(axis=2));node_mag=np.linalg.norm(u,axis=1);seat=x['seat_nodes'];rz=R[seat,2];tol=scale*1e-8;moment=np.cross(co-np.array(m['origin_mm']),F+R).sum(axis=0);need(np.linalg.norm(moment)/(scale*(10 if m['patch'] else 114))<2e-5,'Moment equilibrium failed')
    result=dict(case=case.name,fresh_evaluated_utc=now(),passed_integrity=True,order=m['order'],target_h_mm=m['target_h_mm'],nodes=len(co),elements=len(t),maximum_nodal_displacement_mm=float(node_mag.max()),maximum_nodal_displacement_xyz_mm=co[int(node_mag.argmax())].tolist(),strain_energy_Nmm=energy,half_external_work_Nmm=work,energy_relative_error=float(eerr),stress_kinematics_relative_error=serr,force_equilibrium_relative_error=float(balance),free_dof_force_residual_relative=float(free),applied_force_N=F.sum(axis=0).tolist(),reaction_force_N=R.sum(axis=0).tolist(),moment_residual_Nmm=moment.tolist(),raw_von_mises_peak_MPa=float(vm.max()),seat_node_count=len(seat),negative_seat_nodes=int((rz<-tol).sum()),negative_seat_force_N=float(rz[rz<0].sum()),positive_seat_force_N=float(rz[rz>0].sum()),material_for_manufacturing=False,strength_pass=False,physical_contact='BILATERAL_REFERENCE_ONLY; negative linear/midside forces require unilateral-contact HOLD',nodal_metric_warning='Only mesh-node maxima, not rigorous quadratic interpolation extrema')
    if nq==4:
        mids=np.intersect1d(seat,np.unique(t[:,4:]));vals=R[mids,2];result['negative_seat_midside_nodes']=int((vals<-tol).sum());result['negative_seat_midside_force_N']=float(vals[vals<-tol].sum())
    if m['patch']:
        exact=np.column_stack([NU*P/E*co[:,0],NU*P/E*co[:,1],-P/E*co[:,2]]);exs=np.zeros_like(s);exs[:,:,2]=-P;du=float(abs(u-exact).max()/(P/E*10));ds=float(abs(s-exs).max()/P);need(du<2e-6 and ds<2e-6 and balance<2e-6,'Independent pressure patch failed');result['patch_validation']=dict(passed=True,displacement_relative_error=du,stress_relative_error=ds,analytic_energy_Nmm=P**2/(2*E)*1000)
    bound={name:sha(case/name) for name in ('disc.inp','disc.dat','mesh.npz','model.json','run.json')};result['raw_input_output_binding']=bound;result['checker_sha256']=sha(pathlib.Path(__file__))
    return result,dict(u=u,reactions=R,stress=s,von_mises=vm,energy_density=ed)

def solve(case):
    m=json.loads((case/'model.json').read_text());source_checks(m['patch']);start=time.time();need(not (case/'run.json').exists(),'Existing run cannot be overwritten')
    (case/'solver_script_snapshot.py').write_bytes(pathlib.Path(__file__).read_bytes())
    with (case/'log.ccx').open('w') as log:p=subprocess.run(['bash','-c',f'source {SOLVER_ENV}; ccx disc'],cwd=case,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    text=(case/'log.ccx').read_text();need(p.returncode==0 and 'Job finished' in text and '*ERROR' not in text,'CCX failed; raw log retained')
    write_json(case/'run.json',dict(fresh_run_utc=now(),elapsed_seconds=time.time()-start,returncode=p.returncode,solver='CalculiX2.23 fresh rebuilt environment',solver_script_sha256=sha(pathlib.Path(__file__)),solver_env_sha256=sha(SOLVER_ENV),input_sha256=sha(case/'disc.inp'),threads=1))
    result,arrays=calculate(case);write_json(case/'results.json',result);np.savez_compressed(case/'solution.npz',**arrays)
    with (case/'seat_reactions.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['node','x_mm','y_mm','z_mm','Rz_N']);x=np.load(case/'mesh.npz');w.writerows([int(n)+1,*x['coords'][n],arrays['reactions'][n,2]] for n in x['seat_nodes'])
    print(json.dumps(result,indent=2))

def main():
    p=argparse.ArgumentParser();p.add_argument('--patch',action='store_true');p.add_argument('--h',type=int,default=8);p.add_argument('--order',choices=['C3D4','C3D10'],default='C3D4');p.add_argument('--check-only');a=p.parse_args()
    if a.check_only:print(json.dumps(calculate(pathlib.Path(a.check_only))[0],indent=2));return
    case=ROOT/'cases'/(('pressure_patch' if a.patch else f'disc_h{a.h}')+'_'+a.order);need(not case.exists(),'Fresh cases must use a new name; refusing overwrite');case.mkdir()
    if not a.patch:
        benchmark=ROOT/'cases'/('pressure_patch_'+a.order);result,_=calculate(benchmark);need(result['patch_validation']['passed'],'Same-order pressure benchmark required')
    if a.order=='C3D4':mesh_linear(case,2 if a.patch else a.h,a.patch)
    else:
        source=ROOT/'cases'/(('pressure_patch' if a.patch else f'disc_h{a.h}')+'_C3D4');elevate(source,case)
    solve(case)
if __name__=='__main__':main()
