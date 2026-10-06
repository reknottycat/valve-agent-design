#!/usr/bin/env python3
"""Generate readable study drawings and reports from the actual rebuilt STEP parts."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import cadquery as cq
import ezdxf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image

HERE=Path(__file__).resolve().parent;BASE=HERE.parent
NAMES={'body':'Body','seat_ring':'Seat ring','disc_guide':'Disc + guide','bonnet':'Bonnet + support',
       'packing':'Packing study','stem':'Spindle envelope','handwheel':'Handwheel'}
COLORS={'body':'#334155','seat_ring':'#b8860b','disc_guide':'#16836b','bonnet':'#3b6484',
        'packing':'#9b4a73','stem':'#555555','handwheel':'#7549a6'}


def load_parts(state):
    return {name:cq.importers.importStep(str(BASE/'T12/out'/state/(name+'.step'))).val() for name in NAMES}


def section_lines(shape):
    wire=cq.Workplane('XZ',origin=(300,0,150)).rect(1800,1800).val()
    section=shape.intersect(cq.Face.makeFromWires(wire))
    if not section.isValid():raise RuntimeError('Invalid drawing section')
    lines=[]
    for edge in section.Edges():
        pts,_=edge.sample(48 if edge.geomType()!='LINE' else 2)
        lines.append([(p.x,p.z) for p in pts])
    return lines


def draw_state(ax,state,title):
    for name,shape in load_parts(state).items():
        for line in section_lines(shape):
            ax.plot([p[0] for p in line],[p[1] for p in line],color=COLORS[name],lw=.9)
    ax.axhline(0,color='#999',lw=.6,linestyle='-.');ax.axvline(300,color='#aaa',lw=.5,linestyle='-.')
    ax.set_aspect('equal');ax.set_xlim(-75,695);ax.set_ylim(-250,570)
    ax.set_title(title,fontsize=12,pad=10);ax.set_xlabel('X / mm');ax.set_ylabel('Z / mm')
    ax.grid(alpha=.12)
    ax.annotate('',xy=(600,-215),xytext=(0,-215),arrowprops={'arrowstyle':'<->','lw':.8})
    ax.text(300,-202,'600* REF',ha='center',fontsize=9)
    ax.annotate('',xy=(650,515),xytext=(650,0),arrowprops={'arrowstyle':'<->','lw':.8})
    ax.text(660,257.5,'515* REF',rotation=90,va='center',fontsize=9)


def drawing(out):
    fig,axes=plt.subplots(1,2,figsize=(16.54,11.69))
    draw_state(axes[0],'closed','A-A longitudinal section | forced closed')
    draw_state(axes[1],'open','A-A longitudinal section | proposed full lift')
    fig.suptitle('522-35.4179 | C2 AXIAL-LIFT STUDY',fontsize=19,y=.965)
    fig.text(.5,.927,'RESEARCH GEOMETRY - NOT FOR MANUFACTURE - dimensions in mm',ha='center',fontsize=11,color='#a22')
    handles=[Line2D([0],[0],color=COLORS[n],lw=2,label=NAMES[n]) for n in NAMES]
    fig.legend(handles=handles,ncol=4,loc='lower center',bbox_to_anchor=(.5,.063),frameon=False)
    fig.text(.5,.035,'* Drawing reference dimensions only. All unreferenced internal sizes are proposed study values. No manufacturing tolerances or pressure rating assigned.',ha='center',fontsize=8)
    fig.subplots_adjust(left=.06,right=.95,top=.89,bottom=.13,wspace=.24)
    fig.savefig(out/'GA_C2.pdf');fig.savefig(out/'GA_C2.svg');fig.savefig(out/'GA_C2.png',dpi=135);plt.close(fig)
    doc=ezdxf.new('R2010');doc.header['$INSUNITS']=4;msp=doc.modelspace()
    for i,(name,shape) in enumerate(load_parts('closed').items(),1):
        layer='PART_'+name;doc.layers.new(layer,dxfattribs={'color':i})
        for line in section_lines(shape):msp.add_lwpolyline(line,dxfattribs={'layer':layer})
    msp.add_text('C2 STUDY - NOT FOR MANUFACTURE',dxfattribs={'height':12,'insert':(0,560)})
    msp.add_text('mm | * reference dimensions | internal sizes proposed',dxfattribs={'height':8,'insert':(0,540)})
    msp.add_linear_dim(base=(0,-215),p1=(0,-165),p2=(600,-165),text='600* REF',dimstyle='EZDXF').render()
    doc.saveas(out/'GA_C2_section.dxf')
    check=ezdxf.readfile(out/'GA_C2_section.dxf')
    if check.header['$INSUNITS']!=4 or len(check.modelspace())<10:raise RuntimeError('DXF re-read failed')
    return len(check.modelspace())


def bill_of_materials(out):
    rows=[]
    for i,(name,shape) in enumerate(load_parts('closed').items(),1):
        rows.append({'item':i,'name':NAMES[name],'file':name+'.step','quantity':1,
                     'volume_cm3':round(shape.Volume(1e-9)/1000,3),
                     'material':'UNSELECTED','status':'PROPOSED_SIMPLIFIED_COMPONENT'})
    with (out/'BOM_study.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');writer.writeheader();writer.writerows(rows)
    (out/'BOM_study.json').write_text(json.dumps({'items':rows,'scope':'Seven main simplified components, not original full40-position BOM',
        'missing':['Bonnet fasteners and gasket','Detailed stem nut/thread','Locking parts','Complete packing/gland detail','Original part-number material traceability'],
        'manufacturing_authorized':False},indent=2))
    return rows


def report(out,rows):
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    styles=getSampleStyleSheet()
    for name in ('Normal','Title','Heading1','Heading2','BodyText'):
        styles[name].fontName='STSong-Light';styles[name].leading=16
    styles['Normal'].fontSize=10;styles['Title'].fontSize=22;styles['Title'].leading=28
    styles['Heading1'].fontSize=15;styles['Heading1'].leading=21
    elements=[]
    def para(text,style='Normal'):
        elements.append(Paragraph(text,styles[style]));elements.append(Spacer(1,8))
    def heading(text):para(text,'Heading1')
    def table(data,widths):
        wrapped=[[Paragraph(str(c),styles['Normal']) for c in row] for row in data]
        t=Table(wrapped,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf1f4')),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#d9d9d9')),
                              ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
                              ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
        elements.append(t);elements.append(Spacer(1,12))
    para('522 35 4179 阀门 C2 研究设计','Title')
    para('2026年10月6日 | 轴向升降止回与截止候选 | 阶段性设计文件包')
    para('本候选已从错误的摆盘模型改为与总装剖面相符的竖直阀杆和水平阀瓣构型。CAD、行程取样、STEP交换和SI网格已经实际生成和检查。设计压力、材料许用值及制造细节尚未确定，本文件不得用于制造放行。')
    elements.append(Image(str(out/'GA_C2.png'),width=480,height=339))
    para('图为本次真实CAD的纵剖面，左侧强制关闭，右侧按研究假设全升程。彩色仅区分零件；不是原图尺寸的精确复制。')
    elements.append(PageBreak())
    heading('原图证据和纠正')
    table([['项目','当前解释'],['600*','原图明确给出的面到面参考长度；C0的300mm无源假设撤回'],['机构','原图为竖直阀杆及水平阀瓣；没有支持底部铰轴、45度摆盘或配重杠杆的证据'],['320*','手轮直径，不是杠杆跨度'],['57*','阀杆及手轮参考行程；将最大自由阀瓣升程取57mm是另列的研究假设'],['介质','基本型适用海水-2至50摄氏度；氯化钙低温条款只列于-02变型'],['注30','防松措施，不是IP55或IP54等级'],['标准','GOST356-80为压力系列标准，不是石棉垫片标准']],[90,390])
    para('原图几何图像SHA256已重新计算为9401cc66f20f95fbf7dcc6dbbd820f64a848e98dd4a0ebcfa4f80471ebbaa25b，原C0登记的摘要不一致。变型与条款矩阵、原图和裁片见T06目录。尺寸星号按注31保留；局部螺钉细节另有公差，不能概括为整张图均无受控尺寸。')
    para('官方标准公开目录可确认名称和状态，但关键全文页面要求授权登录。没有绕过访问限制，也没有据目录元数据给出许用应力或试验压力。厂家相似产品材料仅作候选线索。')
    elements.append(PageBreak())
    heading('研究装配清单')
    table([['项','部件','几何体积 cm3','材料状态']]+[[r['item'],r['name'],r['volume_cm3'],'未选定'] for r in rows],[28,210,130,112])
    para('本表为七个主要简化部件，不等于原总装图全部件号的明细表。阀盖紧固件、垫片、螺母/螺纹、锁紧零件、填料压盖与配合公差尚需补齐。不得根据中性STEP文件直接下达加工。')
    para('设计主数据为T11/parameters.json及T12/build_lift_model.py。STEP供交换；FCStd为可检查的几何快照，不含完整CadQuery参数特征历史。全部内部尺寸按研究设计选择标注，不从图像比例量取。')
    para('总几何体积约 %.2f L。材料未选择，因此没有把密度假设换算成正式质量，也没有宣称达到原图119kg参考质量。'%(sum(r['volume_cm3'] for r in rows)/1000))
    elements.append(PageBreak())
    heading('行程和归一化计算')
    calc=json.loads((BASE/'T15/calc_results.json').read_text());kin=calc['kinematics'];n=calc['normalized_static_relations']
    table([['量','研究结果'],['阀杆参考转数','%.2f圈（57mm / 6mm）'%kin['screw_revolutions_for_reference_travel']],
           ['最大自由阀瓣升程','57mm，研究假设'],['理想环形帘面积 / 通径面积','%.3f'%kin['curtain_to_bore_area']],
           ['不利压差单位关闭力','%.1f N/MPa'%n['adverse_pressure_closing_force_N_per_MPa']],
           ['阀杆光杆平均轴向应力','%.3f MPa/MPa'%n['gross_stem_axial_stress_MPa_per_MPa']],
           ['平面座平均接触压强','%.3f MPa/MPa'%n['uniform_flat_seat_mean_contact_pressure_MPa_per_MPa']]],[235,245])
    para('以上按单位压差表达，没有选定本阀设计压力。接触压强采用平面环带平均模型，不采用C0的45度放大。环形帘面积不等于流量系数或阻力验收；光杆应力不含螺纹根部、弯曲、扭转、失稳及疲劳。')
    para('丝杆计算仅给出摩擦系数0.10、0.15、0.20下的螺纹力矩分量，导程及中径解释仍需标准核对。未计填料、支承、启动摩擦和密封预紧。45kgf限制作用于辅助扳手，不能直接与手轮边缘力相比较。完整公式及数值见T15。')
    elements.append(PageBreak())
    heading('已验证和未完成的边界')
    geom=json.loads((BASE/'T22/out/geometry_check.json').read_text());mesh=json.loads((BASE/'T23/out/mesh_report.json').read_text())
    table([['项目','本阶段结果'],['几何','七零件有效且单实体；STEP单位与回读检查通过'],['运动取样','%d组阀杆/阀瓣位置，无超过阈值的实体干涉'%len(geom['motion'])],['流体区域','关闭为两隔离区域；开启为一个连通区域，七升程样本检查'],['实际网格','%d节点，%d四面体；体积相对CAD误差%.3f%%'%(mesh['nodes'],mesh['tetrahedra'],100*mesh['relative_volume_error'])],['CFD和FEA','未运行本阀求解；安装/执行审批取消后保持暂停'],['制造放行','未授权，未冻结']],[130,350])
    para('行程检查为离散取样，不是所有连续位置的数学证明。网格正体积和物理标签正确，不代表湍流模型、壁面分辨率、收敛性或流量性能达标。CAD几何接触不代表密封和承载成立。')
    para('后续优先完成：产品变型与受控基准确认；真实压力温度矩阵；材料、工艺、许用应力和腐蚀余量；自由升降导向及约束细节；阀盖连接、紧固及密封；标准全文及泄漏/冲击/振动验收；求解器独立基准和本阀数值算例。')
    para('主要来源：用户仓库原始总装图；Rosstandart官方标准登记页；Lenpromarmatura厂家目录相似产品。逐项URL、版本和证据限制见T06/evidence_matrix.md。')
    SimpleDocTemplate(str(out/'C2_design_review.pdf'),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=42).build(elements)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=HERE/'out');args=parser.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    params=hashlib.sha256((BASE/'T11/parameters.json').read_bytes()).hexdigest()
    for path in (BASE/'T12/out/build_report.json',BASE/'T22/out/geometry_check.json',BASE/'T23/out/mesh_report.json',BASE/'T15/calc_results.json'):
        if json.loads(path.read_text())['parameters_sha256']!=params:raise RuntimeError('Stale input: '+str(path))
    if json.loads((BASE/'T22/out/geometry_check.json').read_text())['geometry_gate']!='PASS':raise RuntimeError('Geometry not verified')
    dxf_count=drawing(out);rows=bill_of_materials(out);report(out,rows)
    (out/'drawing_report.json').write_text(json.dumps({'status':'STUDY_NOT_FOR_MANUFACTURE','parameters_sha256':params,
          'dxf_entities_read_back':dxf_count,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='drawing_report.json'}},indent=2))
    print('Generated study PDF, SVG, DXF, PNG and BOM; visual QA still required')


if __name__=='__main__':main()
