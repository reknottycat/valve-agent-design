#!/usr/bin/env python3
"""Technical study views from actual STEP coupons/envelopes; not manufacturing drawings."""
import hashlib
import json
from pathlib import Path
import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE=Path(__file__).resolve().parents[1]


def lines(shape,cx=0):
    plane=cq.Face.makeFromWires(cq.Workplane('XZ',origin=(cx,0,250)).rect(1800,1800).val())
    section=shape.intersect(plane)
    if not section.isValid():raise RuntimeError('Unknown drawing section')
    result=[]
    for e in section.Edges():
        pts,_=e.sample(2 if e.geomType()=='LINE' else 40)
        result.append([(v.x-cx,v.z) for v in pts])
    return result


def plot(ax,shape,color,cx=0,width=.8):
    for row in lines(shape,cx):ax.plot([x[0] for x in row],[x[1] for x in row],color=color,lw=width)


def main():
    current=hashlib.sha256((BASE/'T11/interface_candidates.json').read_bytes()).hexdigest()
    report=json.loads((BASE/'T12/out/preview_report.json').read_text())
    if report['interfaces_sha256']!=current:raise RuntimeError('Stale candidate geometry')
    fig,axes=plt.subplots(2,3,figsize=(16,9))
    for ax,name in zip(axes[0],report['joint_candidates']):
        folder=BASE/'T12/out'/name
        for part,color in [('body_flange_coupon','#475569'),('cover_coupon','#475569'),('gasket_uncompressed','#d59015')]:
            plot(ax,cq.importers.importStep(str(folder/(part+'.step'))).val(),color)
        for name2 in report['joint_candidates'][name]['parts']:
            if not name2.startswith(('stud_','washer_','nut_proxy_')):continue
            plot(ax,cq.importers.importStep(str(folder/(name2+'.step'))).val(),'#256f9a')
        ax.set_title(name+' | unselected joint coupon');ax.set_xlim(-235,235);ax.set_ylim(-32,90)
        ax.set_aspect('equal');ax.set_xlabel('X / mm');ax.set_ylabel('Z / mm');ax.grid(alpha=.15)
    wheel=cq.importers.importStep(str(BASE.parent/'C2/T12/out/closed/handwheel.step')).val()
    for ax,row in zip(axes[1],report['drive_candidates']):
        nut=cq.importers.importStep(str(BASE/'T12/out'/row['id']/'nut_cylindrical_envelope.step')).val()
        plot(ax,wheel,'#475569',300);plot(ax,nut,'#216e55',300)
        if row['measured_collision']:
            common=nut.intersect(wheel)
            plot(ax,common,'#c72828',300,1.8)
        fit='COLLISION' if row['measured_collision'] else 'Envelope clear only'
        ax.set_title(row['id']+' | '+fit)
        ax.set_xlim(-55,55);ax.set_ylim(360,478);ax.set_aspect('equal')
        ax.set_xlabel('X from spindle / mm');ax.set_ylabel('Z / mm');ax.grid(alpha=.15)
        ax.text(0,366,'Overlap %.1f mm3'%row['measured_overlap_with_C2_handwheel_mm3'],ha='center',fontsize=8)
    fig.suptitle('C3 interface candidates | NO SELECTION - NO LOAD APPROVAL',fontsize=17)
    fig.text(.5,.014,'Smooth thread envelopes only. No material, grade, preload, torque or gasket/packing performance approved. Frozen C2 remains unchanged.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.95))
    out=BASE/'T40/out';out.mkdir(exist_ok=True)
    fig.savefig(out/'C3_interface_studies.svg');fig.savefig(out/'C3_interface_studies.png',dpi=140)
    plt.close(fig)
    (out/'drawing_report.json').write_text(json.dumps({'status':'STUDY_NOT_FOR_MANUFACTURE','interfaces_sha256':current,
       'source_preview_report_sha256':hashlib.sha256((BASE/'T12/out/preview_report.json').read_bytes()).hexdigest(),
       'output_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.name!='drawing_report.json'}},indent=2))


if __name__=='__main__':main()
