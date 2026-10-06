#!/usr/bin/env python3
"""Plot calculated study evidence; no new CAD or solver results are implied."""
import hashlib
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

BASE=Path(__file__).resolve().parents[1]
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    loads=BASE/'T15/load_study.json';properties=BASE/'T06/seawater_study_cases.json'
    data=json.loads(loads.read_text());fluid=json.loads(properties.read_text())
    if data['calculator_sha256']!=sha(BASE/'T15/calculate_loads.py') or data['input_hashes']['basis']!=sha(BASE/'T06/research_basis.json'):
        raise ValueError('Stale load data')
    if fluid['script_sha256']!=sha(BASE/'T06/seawater_study.py') or len(fluid['rows'])!=9:raise ValueError('Stale fluid data')
    fig,ax=plt.subplots(2,2,figsize=(14,9.2),layout='constrained')
    fig.suptitle('C4 | Base-model pressure and interface study',fontsize=21,fontweight='bold',x=.04,ha='left')
    blue='#245c91';orange='#dc7f26';grey='#65717b'
    cases={r['case']:r for r in data['cases']};names=['forward-held','reverse-check','common-check']
    x=np.arange(3);width=.34
    a=ax[0,0]
    a.bar(x-width/2,[cases['selected-study/'+n]['disc_pressure_force_z_N']/1000 for n in names],width,label='Disc',color=blue)
    a.bar(x+width/2,[cases['selected-study/'+n]['stem_pressure_force_z_N']/1000 for n in names],width,label='Stem',color=orange)
    a.axhline(0,color=grey,lw=.9);a.set_xticks(x,['Forward, held','Reverse, free check','Common pressure'])
    a.set_ylabel('Axial pressure component (kN), +Z upward');a.set_ylim(-31,29)
    a.set_title('0.63 MPa(g): pressure components, not contact reactions',fontsize=12,loc='left')
    a.legend(frameon=False,ncol=2,loc='upper right');a.grid(axis='y',alpha=.15);a.set_axisbelow(True)
    for i,n in enumerate(names):
        value=cases['selected-study/'+n]['disc_pressure_force_z_N']/1000
        a.text(i-width/2,value+(1 if value>0 else -1.7),f'{value:+.2f}',ha='center',fontsize=10)
    a.text(.40,.77,'Dry contacts; no pressure penetration\nContact reactions and final drive\nthrust remain unresolved',transform=a.transAxes,fontsize=9,color=grey)
    a=ax[0,1]
    for mu,color in zip([0,.05,.10],[blue,orange,'#803e77']):
        rows=[r for r in data['drive_sensitivity']['rows'] if r['collar_mu_assumed']==mu]
        a.plot([r['thread_mu_assumed'] for r in rows],[r['combined_model_torque_Nm'] for r in rows],marker='o',label=f'Collar friction = {mu:.2f}',color=color)
    a.set_xlabel('Assumed thread friction coefficient');a.set_ylabel('Opposing-load screw-model torque (N m)')
    a.set_title('19.79 kN hydraulic component only; preload/packing absent',fontsize=12,loc='left')
    threshold=data['drive_sensitivity']['rows'][0]['self_lock_mu_threshold']
    a.axvspan(0,threshold,alpha=.08,color='red');a.axvline(threshold,color=grey,ls='--',lw=.8)
    a.text(.02,.96,'Low-friction region may backdrive\n(static screw model only)',ha='left',va='top',transform=a.transAxes,fontsize=9,color=grey)
    a.set_xlim(0,.27);a.set_ylim(0,170);a.legend(frameon=False,loc='lower right');a.grid(alpha=.15)
    a=ax[1,0]
    groups={}
    for row in data['joint_pressure_diameter_sensitivity']:groups.setdefault(row['candidate'],[]).append(row['pressure_separation_component_N']/1000)
    for i,(name,values) in enumerate(groups.items()):
        a.plot([min(values),max(values)],[i,i],lw=5,color=blue,solid_capstyle='round')
        a.scatter(values,[i]*3,c=[blue,orange,blue],s=40,zorder=3)
        a.text(max(values)+.6,i,f'{min(values):.1f}–{max(values):.1f} kN',va='center',fontsize=10)
    a.set_yticks(range(len(groups)),groups);a.set_ylim(-.6,2.8);a.set_xlim(38,69)
    a.set_xlabel('Assumed pressure separation component (kN)')
    a.set_title('Gasket ID / midpoint / OD pressure-boundary sensitivity',fontsize=12,loc='left')
    a.text(.02,.93,'No actual bolt load, preload or joint acceptance inferred',transform=a.transAxes,fontsize=9,color=grey)
    a.grid(axis='x',alpha=.15)
    a=ax[1,1]
    for sal,color in zip([30,35,40],[grey,blue,orange]):
        rows=[r for r in fluid['rows'] if r['reference_composition_salinity_g_kg']==sal]
        a.plot([r['temperature_C'] for r in rows],[r['kinematic_viscosity_m2_s']*1e6 for r in rows],marker='o',label=f'{sal} g/kg',color=color)
    a.axvspan(-2,0,color='red',alpha=.09,hatch='///');a.set_xlim(-3,52);a.set_ylim(.4,2.2)
    a.set_xlabel('Temperature (degC)');a.set_ylabel('Kinematic viscosity (10^-6 m^2/s)')
    a.set_title('Seawater reference properties at 0.101325 MPa(abs)',fontsize=12,loc='left')
    a.legend(frameon=False,loc='upper right');a.grid(alpha=.15)
    a.text(.38,.95,'-2 degC: property / phase gate HOLD\nNo pressure correction implemented',ha='left',va='top',transform=a.transAxes,fontsize=9,color=grey)
    for a in ax.flat:
        a.spines[['top','right']].set_visible(False);a.tick_params(labelsize=9)
    fig.supxlabel('RESEARCH ASSUMPTIONS | No physical proof test, strength approval or manufacturing release',fontsize=11,color='#8a3333')
    output=BASE/'T40/out';output.mkdir(parents=True,exist_ok=True)
    for suffix in ('png','svg'):
        fig.savefig(output/f'C4_load_study.{suffix}',dpi=170,facecolor='white')
    (output/'plot_sources.json').write_text(json.dumps({'load_study_sha256':sha(loads),'seawater_table_sha256':sha(properties),'plot_script_sha256':sha(Path(__file__)),'images':{p.name:sha(p) for p in output.glob('C4_load_study.*')}},indent=2))
    print('Generated C4_load_study.png and SVG from checked current data')


if __name__=='__main__':main()
