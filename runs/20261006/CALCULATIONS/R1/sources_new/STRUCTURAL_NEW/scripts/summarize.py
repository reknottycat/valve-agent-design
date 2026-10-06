#!/usr/bin/env python3
"""Read frozen cases, reparse DAT, and build clearly labeled derived outputs."""
import csv,json,pathlib
import numpy as np
import structural as s
import freeze
ROOT=s.ROOT
rows=[];reports=[]
for order in ('C3D4','C3D10'):
    previous=None
    for h in (8,6,4):
        case=ROOT/'cases'/f'disc_h{h}_{order}';receipt=json.loads((ROOT/'evidence'/f'disc_h{h}_{order}_freeze.json').read_text());verified=freeze.verify(case,case/'FROZEN_MANIFEST.json',receipt['manifest_sha256']);r=verified['fresh_checks'];m=json.loads((case/'model.json').read_text());x=np.load(case/'mesh.npz');z=np.load(case/'solution.npz');co=x['coords'];t=x['tets'];vm=z['von_mises'];vol=x['volumes'];nq=vm.shape[1]
        if nq==1:xyz=co[t[:,:4]].mean(axis=1)[:,None,:]
        else:
            aa=(5+3*np.sqrt(5))/20;bb=(5-np.sqrt(5))/20;bary=np.full((4,4),bb);np.fill_diagonal(bary,aa);xyz=np.einsum('qi,eia->eqa',bary,co[t[:,:4]])
        rad=np.linalg.norm(xyz[:,:,:2]-[300,0],axis=2);sel=(rad>=30)&(rad<=85)&(xyz[:,:,2]<=36.0001);weights=np.broadcast_to(vol[:,None]/nq,vm.shape)[sel];values=vm[sel];sort=np.argsort(values);cum=np.cumsum(weights[sort])/weights.sum();mean=float(np.dot(values,weights)/weights.sum());p95=float(np.interp(.95,cum,values[sort]));edges=np.concatenate([np.linalg.norm(co[t[:,i]]-co[t[:,j]],axis=1) for i,j in s.EDGES])
        row=dict(order=order,target_h_mm=h,nodes=r['nodes'],elements=r['elements'],max_corner_edge_mm=float(edges.max()),minSICN=m['quality_minSICN_min'],mesh_volume_relative_error=m['mesh_volume_relative_error'],load_Fz_N=r['applied_force_N'][2],load_area_relative_error=m['force_area_relative_error'],maximum_nodal_displacement_mm=r['maximum_nodal_displacement_mm'],strain_energy_Nmm=r['strain_energy_Nmm'],raw_vm_peak_MPa=r['raw_von_mises_peak_MPa'],interior_vm_volume_mean_MPa=mean,interior_vm_volume_p95_MPa=p95,negative_seat_nodes=r['negative_seat_nodes'],negative_seat_force_N=r['negative_seat_force_N'],negative_midside_nodes=r.get('negative_seat_midside_nodes'),negative_midside_force_N=r.get('negative_seat_midside_force_N'),force_equilibrium_relative_error=r['force_equilibrium_relative_error'],energy_relative_error=r['energy_relative_error'],manifest_sha256=receipt['manifest_sha256'])
        for key in ('maximum_nodal_displacement_mm','strain_energy_Nmm','raw_vm_peak_MPa'):
            row[key+'_last_refinement_change_percent']=None if previous is None else (row[key]/previous[key]-1)*100
        rows.append(row);reports.append(verified);previous=row
s.write_json(ROOT/'summary.json',dict(schema='fresh_disc_summary/1',fresh_assembled_utc=s.now(),old_solver_data_restored=False,rows=rows,verification='Every case immutable manifest checked and raw DAT reparsed',status='BILATERAL_REFERENCE_COMPLETE_CONTACT_HOLD_NO_STRENGTH_PASS',material_for_manufacturing=False,case_reports=reports))
with (ROOT/'summary.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps(rows,indent=2))
