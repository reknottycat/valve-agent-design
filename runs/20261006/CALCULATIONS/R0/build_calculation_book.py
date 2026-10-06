#!/usr/bin/env python3
"""Data-driven calculation-book generator; read-only engineering evidence inputs.
No CAD, solver, network or repository writes. Python-docx with native editable OMML.
"""
from pathlib import Path
import argparse, json, math, hashlib, shutil, datetime, re
from copy import deepcopy
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--repo',type=Path,default=Path('/workspace/shared/valve-cloud-20261006'))
parser.add_argument('--refresh-sources',action='store_true')
parser.add_argument('--output',type=Path,default=ROOT/'output')
args=parser.parse_args(); OUT=args.output; OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/'sources'; SRC.mkdir(exist_ok=True)
source_specs=[
('S01','C2/T06/variant_input_matrix.json','原图变型及技术要求'),
('S02','C2/T06/evidence_matrix.md','原图与规范证据评审'),
('S03','C2/T11/parameters.json','C2几何参数及性质'),
('S04','C2/T15/calc_results.json','几何和归一化算术'),
('S05','C2/T22/out/geometry_check.json','几何和接触检查'),
('S06','C2/T22/out/asset_roundtrip_report.json','27项STEP回读与单位'),
('S07','C2/T22/out/negative_contact_control.json','阀瓣碰体负对照'),
('S08','C2/T23/out/mesh_report.json','C2流域网格'),
('S09','C2/T40/out/BOM_study.json','七主件研究明细'),
('S10','C3/T11/interface_candidates.json','未选定接口候选'),
('S11','C3/T22/interface_check.json','尺寸和包络检查'),
('S12','C3/T22/surface_support.json','密封与垫圈支承面'),
('S13','C3/T22/assembly_access.json','离散抽出路径'),
('S14','C3/manufacturing_work_breakdown.json','制造工作M01至M15'),
('S15','C4/T06/research_basis.json','已选研究载荷及假设'),
('S16','C4/T06/seawater_study_cases.json','海水九点数据'),
('S17','C4/T06/seawater_study.py','海水关联式独立实现'),
('S18','C4/T19/pressure_areas.json','CAD压力投影面积'),
('S19','C4/T15/load_study.json','载荷驱动和盖接头结果'),
('S20','C4/T15/calculate_loads.py','载荷算术实现'),
('S21','C4/T19/extract_pressure_faces.py','受压面提取实现'),
('S22','C4/T06/research_sources/external_sources.json','未打包第三方来源索引'),
('S23','C5/T05/material_cards.json','材料来源和供货状态'),
('S24','C5/T03/solver_benchmark_results.json','独立标准求解算例'),
('S25','C5/cases/c2_mesh_preflight/log.checkMesh.complete','真实阀网格严格预检查'),
('S26','C5/cases/c2_dual_preflight/log.checkMesh','双对偶转换网格预检查'),
('S27','C2/T40/out/GA_C2.png','C2研究总图'),
('S28','C4/T40/out/C4_load_study.png','C4载荷研究图'),
('S29','C2/T06/source_manifest.json','原始图像校验和'),
('S30','C4/tests.log','C4普通模式测试记录'),
('S31','C4/tests-optimized.log','C4优化模式测试记录'),
('S32','C4/README.zh-CN.md','C4证据边界说明'),
]
manifest=[]
for sid,rel,desc in source_specs:
 src=args.repo/'runs/20261006'/rel; dest=SRC/rel
 if args.refresh_sources or not dest.exists():
  if not src.exists(): raise FileNotFoundError(src)
  dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dest)
 manifest.append({'id':sid,'relative_path':rel,'description':desc,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size})
(ROOT/'source_manifest.json').write_text(json.dumps({'snapshot_date_utc':'2026-10-06','commits':{'C2':'2566bdee5b52024036e0bbac559dd78f8a903a34','C3':'31662e66f0a14e426ab60b53c870f958a60f4ce1','C4':'79887e8e6fbfaf074262facb5cd9d8ed1b863d27','C5':'WORKING_EVIDENCE_SNAPSHOT_NOT_FROZEN_COMMIT'},'files':manifest},ensure_ascii=False,indent=2)+'\n')
def load(rel): return json.loads((SRC/rel).read_text())
P=load('C2/T11/parameters.json'); p={k:v['value'] for k,v in P['values'].items()}
K=load('C2/T15/calc_results.json'); GEO=load('C2/T22/out/geometry_check.json')
BASE=load('C4/T06/research_basis.json'); SEA=load('C4/T06/seawater_study_cases.json')
AREA=load('C4/T19/pressure_areas.json'); LOAD=load('C4/T15/load_study.json')
INT=load('C3/T11/interface_candidates.json'); FIT=load('C3/T22/interface_check.json')
SUP=load('C3/T22/surface_support.json'); ACCESS=load('C3/T22/assembly_access.json')
MAT=load('C5/T05/material_cards.json'); BENCH=load('C5/T03/solver_benchmark_results.json')
MESH=load('C2/T23/out/mesh_report.json'); WBS=load('C3/manufacturing_work_breakdown.json')
UPDATE=json.loads((ROOT/'c5_update.json').read_text()) if (ROOT/'c5_update.json').exists() else None

# Independent arithmetic audit. These checks do not execute engineering scripts.
checks=[]
def check(label,a,b,rel=1e-10,ab=1e-9):
 if not math.isclose(a,b,rel_tol=rel,abs_tol=ab): raise ValueError((label,a,b))
 checks.append({'check':label,'computed':a,'source':b,'passed':True})
pi=math.pi; disk=lambda d:pi*d*d/4
check('bore area',disk(p['bore']),K['kinematics']['bore_area_mm2'])
check('curtain area',pi*p['bore']*p['disc_max_lift'],K['kinematics']['ideal_curtain_area_mm2'])
check('reference turns',p['stem_travel']/p['thread_lead'],K['kinematics']['screw_revolutions_for_reference_travel'])
check('catalog pressure',6.3*.0980665,BASE['pressure_unit_conversion']['catalog_converted_MPa'])
for r in LOAD['cases']:
 for name,key in [('disc_guide','disc_pressure_force_z_N'),('stem','stem_pressure_force_z_N')]:
  aa=AREA['poses'][r['pose']]['parts'][name]
  check(r['case']+'/'+name,sum(aa[s]['axial_force_coefficient_N_per_MPa']*r[f'{s}_pressure_MPa_g'] for s in ['inlet','outlet']),r[key])
 if r['actual_contact_reaction_N'] is not None or r['actual_drive_force_N'] is not None: raise ValueError('Unexpected actual reaction assertion')
F=LOAD['drive_sensitivity']['hydraulic_force_component_N']; th=BASE['thread_study']; d2=th['pitch_diameter_mm']; lead=th['lead_mm']; lam=math.atan(lead/(pi*d2)); alpha=math.atan(math.tan(math.radians(th['axial_half_flank_angle_deg_assumed']))*math.cos(lam))
for i,r in enumerate(LOAD['drive_sensitivity']['rows']):
 m=r['thread_mu_assumed']/math.cos(alpha); T=F*d2/2000*(math.tan(lam)+m)/(1-m*math.tan(lam)); Tc=F*r['collar_mu_assumed']*.024
 check(f'drive{i}/thread torque',T,r['thread_torque_Nm']); check(f'drive{i}/collar torque',Tc,r['collar_torque_Nm']); check(f'drive{i}/rim force',(T+Tc)/.16,r['handwheel_rim_force_N'])
check('nominal root axial component',F/disk(29),LOAD['drive_sensitivity']['nominal_root_axial_component_MPa'])
for r in LOAD['joint_pressure_diameter_sensitivity']: check(r['candidate']+'/'+r['effective_diameter_scenario'],.63*disk(r['assumed_effective_pressure_diameter_mm']),r['pressure_separation_component_N'])
for r in SEA['rows']:
 t=r['temperature_C']; s=r['reference_composition_salinity_g_kg']/1000
 rho=999.9+.02034*t-.006162*t*t+2.261e-5*t**3-4.657e-8*t**4+802*s-2.001*s*t+.01677*s*t*t-3.060e-5*s*t**3-1.613e-5*s*s*t*t
 mu=(4.2844e-5+1/(.157*(t+64.993)**2-91.296))*(1+(1.541+.01998*t-9.52e-5*t*t)*s+(7.974-.07561*t+.0004724*t*t)*s*s)
 check(f'sea{t},{s}/rho',rho,r['density_kg_m3']); check(f'sea{t},{s}/mu',mu,r['dynamic_viscosity_Pa_s'],ab=1e-15); check(f'sea{t},{s}/nu',mu/rho,r['kinematic_viscosity_m2_s'],ab=1e-18)
(ROOT/'arithmetic_verification.json').write_text(json.dumps({'status':'PASS','checks':checks,'count':len(checks),'scope':'Independent arithmetic only; not CFD FEA strength or release'},ensure_ascii=False,indent=2)+'\n')

# Editable Word equation primitives. Structural fractions, powers and subscripts.
def node(tag,*children):
 el=OxmlElement('m:'+tag)
 for c in children:
  if isinstance(c,str): el.append(mr(c))
  elif isinstance(c,list):
   for cc in c: el.append(mr(cc) if isinstance(cc,str) else cc)
  else:el.append(c)
 return el

def mr(t):
 el=OxmlElement('m:r')
 # Prevent LibreOffice from reparsing named units/subscripts as StarMath operators.
 if re.search(r'[A-Za-z]{2,}',str(t)):
  mp=OxmlElement('m:rPr');nor=OxmlElement('m:nor');nor.set(qn('m:val'),'1');mp.append(nor);el.append(mp)
 rp=OxmlElement('w:rPr'); ft=OxmlElement('w:rFonts'); ft.set(qn('w:ascii'),'Cambria Math'); ft.set(qn('w:hAnsi'),'Cambria Math'); rp.append(ft); el.append(rp)
 tx=OxmlElement('m:t');tx.set(qn('xml:space'),'preserve');tx.text=str(t);el.append(tx);return el

def sub(a,b): return node('sSub',node('e',a),node('sub',b))
def sup(a,b): return node('sSup',node('e',a),node('sup',b))
def frac(a,b): return node('f',node('num',a),node('den',b))
def sqrt(a):
 pr=node('radPr'); hide=OxmlElement('m:degHide');hide.set(qn('m:val'),'1');pr.append(hide)
 return node('rad',pr,node('deg'),node('e',a))
def group(*a): return list(a)

D=Document(); sec=D.sections[0]; sec.page_width=Inches(8.5);sec.page_height=Inches(11);sec.top_margin=Inches(.72);sec.bottom_margin=Inches(.65);sec.left_margin=Inches(.75);sec.right_margin=Inches(.75)
sec.header_distance=Inches(.27);sec.footer_distance=Inches(.3)
styles=D.styles
for nm in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3','Caption']:
 st=styles[nm];st.font.name='Noto Serif CJK SC';st.font.color.rgb=RGBColor(0,0,0)
 st._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Noto Serif CJK SC')
 st.paragraph_format.space_after=Pt(6)
styles['Normal'].font.size=Pt(10.5);styles['Normal'].paragraph_format.line_spacing=1.16
styles['Title'].font.size=Pt(25);styles['Title'].font.bold=True
styles['Subtitle'].font.size=Pt(13);styles['Subtitle'].font.italic=False
# Remove built-in template title border residue and direct decorative borders.
for st in styles:
 for border in list(st._element.xpath('.//w:pBdr')):
  border.getparent().remove(border)
for nm,sz in [('Heading 1',15),('Heading 2',12),('Heading 3',11)]:
 styles[nm].font.size=Pt(sz);styles[nm].font.bold=True;styles[nm].paragraph_format.space_before=Pt(13);styles[nm].paragraph_format.space_after=Pt(6);styles[nm].paragraph_format.keep_with_next=True
styles['Caption'].font.size=Pt(9);styles['Caption'].font.italic=False;styles['Caption'].paragraph_format.space_before=Pt(5)
for st in styles:
 if st.type==1:
  try: st.paragraph_format.widow_control=True
  except:pass
D.core_properties.title='522 35 4179 阀门工程计算书';D.core_properties.subject='轴向升降式截止止回阀研究计算工作稿';D.core_properties.author='工程计算研究';D.core_properties.keywords='522-35.4179,C2,C3,C4,C5,研究计算,未制造放行'
header=sec.header.paragraphs[0];header.text='522-35.4179  阀门工程计算书  |  工作稿 R0';header.style=styles['Caption']
foot=sec.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.RIGHT
rr=foot.add_run('研究计算  ·  ');rr.font.size=Pt(9)
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');foot._p.append(fld)

def para(t='',style=None,boldlead=None):
 z=D.add_paragraph(style=style)
 if boldlead and t.startswith(boldlead):z.add_run(boldlead).bold=True;z.add_run(t[len(boldlead):])
 else:z.add_run(t)
 return z

def h(t,l=1):D.add_heading(t,l)
def eq(number,*items):
 z=D.add_paragraph();z.paragraph_format.space_before=Pt(5);z.paragraph_format.space_after=Pt(6)
 om=OxmlElement('m:oMath')
 for x in items:
  if isinstance(x,list):
   for y in x:om.append(mr(y) if isinstance(y,str) else y)
  else:om.append(mr(x) if isinstance(x,str) else x)
 z._p.append(om);z.add_run('    ('+number+')').font.size=Pt(9)
 return z

def table(headers,rows,widths=None,small=9.1,aligncols=None):
 t=D.add_table(rows=1,cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
 if widths is None: widths=[7/len(headers)]*len(headers)
 for c,w in zip(t.columns,widths):c.width=Inches(w)
 pr=t._tbl.tblPr; borders=OxmlElement('w:tblBorders')
 for ed in ['top','left','bottom','right','insideH','insideV']:
  ee=OxmlElement('w:'+ed);ee.set(qn('w:val'),'single');ee.set(qn('w:sz'),'4');ee.set(qn('w:color'),'D9D9D9');borders.append(ee)
 pr.append(borders)
 for rowidx,vals in enumerate([headers]+list(rows)):
  cells=t.rows[0].cells if rowidx==0 else t.add_row().cells
  row=cells[0]._tc.getparent();trPr=row.get_or_add_trPr();cant=OxmlElement('w:cantSplit');trPr.append(cant)
  if rowidx==0:
   repeat=OxmlElement('w:tblHeader');trPr.append(repeat)
  for j,(c,val) in enumerate(zip(cells,vals)):
   c.width=Inches(widths[j]);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   cp=c._tc.get_or_add_tcPr();marg=OxmlElement('w:tcMar')
   for ed,amount in [('top',65),('bottom',65),('left',85),('right',85)]:
    e=OxmlElement('w:'+ed);e.set(qn('w:w'),str(amount));e.set(qn('w:type'),'dxa');marg.append(e)
   cp.append(marg)
   sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'DCE6EC' if rowidx==0 else ('F4F6F7' if rowidx%2==0 else 'FFFFFF'));cp.append(sh)
   z=c.paragraphs[0];z.paragraph_format.space_after=Pt(0);z.paragraph_format.line_spacing=1.08
   if aligncols and j in aligncols:z.alignment=WD_ALIGN_PARAGRAPH.CENTER
   run=z.add_run(str(val));run.font.size=Pt(small);run.bold=(rowidx==0)
  # keep table header with first row, without gluing entire dataset together
  if rowidx==0:
   for c in cells:c.paragraphs[0].paragraph_format.keep_with_next=True
 para().paragraph_format.space_after=Pt(1)
 return t

def caption(t):z=para(t,'Caption');z.paragraph_format.keep_with_next=True;return z

def f(v,d=3):return f'{v:,.{d}f}'
def pending(what):return [what,'NOT YET COMPUTED','待输入和计算闭合']

# Front matter
para('522 35 4179\n阀门工程计算书','Title')
para('基础无后缀型号  轴向升降式截止止回研究模型','Subtitle')
para('工作稿 R0  |  证据截止 2026年10月6日  |  非制造放行文件')
para('本计算书把原图、研究假设、公式代入、计算数据与未完成项连成可复算的工程记录。当前已完成几何运动学、限定域海水物性、真实CAD受压面积、双侧压力载荷，以及丝杆和盖接头敏感性计算。尚无可用于验收的本阀流阻、强度、泄漏或实物试验结论。')
para('研究载荷取0.63 MPa表压，介质海水，原图工作温度范围为−2至50°C。0.63 MPa为本项目类比选定的计算输入；原制造厂额定值、现场工况和物理试验压力仍未确定。')
caption('文件组成和读法')
table(['组成','内容'],[['第1至2章','完成矩阵、输入登记、源图与研究假设边界'],['第3至8章','有真实结果的几何、物性、压力、驱动与接口计算'],['第9至12章','材料、CFD/FEA和规范验收；缺项显式保留'],['第13至14章及附录','制造闭环、复算方法、全工况表与来源索引']],[1.5,5.5],10)
para('关键结论：液压力分量不能直接作为最终执行器推力；平均牙根应力不能直接作为强度合格结论；网格拓扑检查或标准求解算例通过不能替代本阀收敛和网格不确定度。')
para('文档状态  WORKING DRAFT\n制造放行  HOLD\n工程审签  未执行\n实际整阀CFD与FEA  NOT YET COMPUTED')
D.add_page_break()

h('1 计算范围和完成矩阵')
para('计算对象为用户选定的522-35.4179基础无后缀型号。采用C2轴向升降研究几何、C3未选定接口候选和C4研究工况；C5只接入已形成的材料卡及独立求解器基准。后续结果须保留各自几何、工况和证据版本。')
table(['章节','已完成且可复算','仍需闭合'],[
['2 输入','基础型号、原图介质范围、0.63 MPa研究选择','原厂额定、现场载荷、外压和水锤'],['3 几何','9.5转、通道面积、离散运动和STEP交换','全行程、防脱、真实最小壁厚、公差'],['4 物性','0/20/50°C与30/35/40 g/kg九点','−2°C相态、压力修正、现场盐度'],['5 载荷','两姿态CAD投影、4压力级×5模式','座面渗压、接触反力和实际驱动力'],['6 驱动','12摩擦情景、名义根径和牙面代理','预紧、填料、弯扭屈曲、保持机构'],['7 接头','3候选×3有效边界、支承面检查','选型、预紧散差、法兰刚度、泄漏'],['8 装拆','离散抽出路线和碰撞负对照','连续路径、实际保持与吊装空间'],['9 材料','6份材料证据卡及状态边界','原牌号完整性质、供货证书、许用值'],['10 CFD','C2网格和严格预检查、方腔标准算例','本阀流场、压降、ζ、Kv/Cv、网格收敛'],['11 FEA','拉伸标准算例和单位一致性','本阀应力、变形、接触、预紧、强度裕量'],['12 验收','原图要求与规范候选索引','适用条款、物理耐压、泄漏、耐久试验'],['13 制造','工作分解及研究图/BOM索引','完整制造图、检验计划、工程审签']], [.75,3.0,3.25])
para('本书“通过”仅用于明确列出的算术、几何或软件检查，范围写在同一节。“NOT YET COMPUTED”表示没有计算输出；“未评定”表示即使存在数值，也尚未建立可用的验收依据。两者均不填成零或合格。')
h('1 1 版本和旧记录的解释',2)
para('C2和C3是冻结历史基线，内含当时未选压力、未定型号或暂停求解的字段。当前型号和研究压力由C4选定；后续工具操作许可属于独立活动。不能把历史状态当成当前授权，也不能回改冻结来源来掩盖阶段差异。C5为本书制作时的工作证据快照，未声称具有冻结提交。')
table(['阶段','版本标识','本书用途'],[['原始资料','4222b3d4df24','源图检视基线'],['C2','2566bdee5b52','轴向升降几何与归一化算术'],['C3','31662e66','候选接口和制造分解'],['C4','79887e8e6fbf','研究载荷和全部C4结果']],[.65,2.5,3.85],8.5)

h('2 输入来源和假设登记')
para('登记类别：R为原图参考；A为研究假设；C为目录/标准类比；D为由输入推导；U为尚未控制。来源编号Sxx对应附录的文件索引。原图带星尺寸保留参考性质，不因进入CAD就成为制造公差。')
inputs=[
['I01','型号','522-35.4179','R/已选','S01、S15'],['I02','介质和温度','海水 −2至50°C','R','原图注4；S01'],['I03','研究内压','0.63 MPa(g)','A','S15'],['I04','研究关闭压差','0.63 MPa','A','全压差情景；S15'],['I05','参考外压','0.101325 MPa(abs)','A','非现场气压；S15'],['I06','盐度','35 g/kg；30/40扫描','A','非实测；S15'],['I07','通径D','200 mm','R','S03'],['I08','结构长度','600 mm','R','原图600*；S03'],['I09','管端法兰','Ø295 / Ø264 / Ø247 mm','R','外径/孔圆/密封面；S03'],['I10','孔与厚度','12×Ø15；15 mm','R','S03'],['I11','手轮外径','320 mm','R','S03'],['I12','上部参考高度','515 mm','R','S03'],['I13','丝杆参考行程','57 mm','R','S03'],['I14','阀瓣最大自由升程','57 mm','A','不等同原图已给升程；S03'],['I15','丝杆包络外径','36 mm','A','光杆替代Tr36×6；S03'],['I16','螺纹导程和头数','6 mm；单头','A','S15'],['I17','名义螺纹尺寸','d₂33；d₃29；D₁30；D₄37 mm','C','DIN103类比；S15'],['I18','牙型半角','轴向截面15°','A/C','法向换算后使用；S15'],['I19','阀座/阀瓣外径','228 / 240 mm','A','S03'],['I20','阀座/阀瓣厚度','10 / 14 mm','A','S03'],['I21','阀体名义壁偏置','20 mm','A','非全局最小承压壁；S03'],['I22','阀座凸出量','2 mm','A','几何隔离阀瓣与阀体；S03'],['I23','螺纹摩擦','0.03/0.08/0.15/0.25','A','敏感性，不是实测；S15'],['I24','支承环','内径36；外径60 mm','A','均匀磨损代理；S15'],['I25','支承环摩擦','0/0.05/0.10','A','S15'],['I26','名义啮合长度','40/54/70 mm','A/C','候选包络，不是已选啮合；S10'],['I27','材料许用应力','未确定','U','S23'],['I28','物理试验压力','未确定','U','S15'],['I29','密封预紧和填料摩擦','未确定','U','未知不得作为最终设计的零值'],['I30','安装姿态','管轴水平 丝杆+Z竖直','A','与图相符；S15']]
table(['编号','量或条件','数值','性质','依据'],inputs,[.48,1.35,2.0,.58,2.59],8.8)
h('2 1 压力单位和压力层级',2)
eq('2-1', '1 kgf/cm² = ',frac('9.80665 N','0.0001 m²'),' = 0.0980665 MPa')
eq('2-2', 'p = 6.3 × 0.0980665 = 0.61781895 MPa')
eq('2-3',frac('0.63 − 0.61781895','0.61781895'),' × 100% = 1.972%')
para('类比LPA目录PN栏的6.3单位为kgf/cm²。原图字面“Ру6”保留原文；将6解释为kgf/cm²时只得到0.588399 MPa的条件换算。0.63 MPa是选定研究值，1.0 MPa仅用于额外数值超载敏感性。它们均未建立物理试验压力。 [S02、S15]')
eq('2-4',sub('p','abs'),' = ',sub('p','g'),' + ',sub('p','ref'),' = 0.63 + 0.101325 = 0.731325 MPa(abs)')
para('上述绝压转换用于区分压力基准。C4机械载荷只算相对共同参考外压的表压增量，未求参考大气压下的接触预应力。物性表仅在0.101325 MPa(abs)建立，不能未经说明用于0.731325 MPa(abs)。')
h('2 2 型号和机制的适用边界',2)
para('基础型号适用海水工况；−02后缀的28%氯化钙溶液、−40°C工况不能移入本书。基础型号原表质量119 kg为原产品参考，当前七主件研究模型没有完整材料和零件，不能以其几何体积宣称达到119 kg。原图19条给9.5转参考，20条给辅助扳手45 kgf限值，24条给流阻系数不大于6；各自的测量位置与试验定义仍需闭合。')
para('原剖面是竖直丝杆与轴向升降阀瓣。当前研究为丝杆可退开的截止止回解释，未采用摆动铰链、45°阀瓣倾斜或加重杠杆公式。自由升降连接、导向、防转和防脱细节尚未还原。 [S01至S03]')

h('3 几何运动学和过流面积计算')
h('3 1 丝杆行程和阀瓣升程',2)
eq('3-1','n = ',frac('s','l'),' = ',frac('57 mm','6 mm/转'),' = 9.5 转')
para('s为丝杆参考行程，l为单头解释下的导程，n为手轮转数。结果与原图9.5转参考一致，属于一致性检查。阀瓣假定最大自由升程h=57 mm与s数值相同，但源图没有独立确认两者必然相等。 [S03、S04]')
h('3 2 通道截面和理想帘幕面积',2)
eq('3-2',sub('A','b'),' = ',frac(group('π',sup('D','2')),'4'),' = ',frac('π × 200²','4'),' = 31 415.927 mm²')
eq('3-3',sub('A','c'),' = πDh = π × 200 × 57 = 35 814.156 mm²')
eq('3-4',frac(sub('A','c'),sub('A','b')),' = ',frac('4h','D'),' = 1.140')
eq('3-5',sub('h','equal'),' = ',frac('D','4'),' = 50.0 mm')
para('A_b为DN200圆截面面积；A_c为周长乘升程的理想帘幕面积。57 mm时比值为1.14，说明这个理想开口尺度大于管口面积。阀体弯折通道、导向、局部缩流及流动分离尚未计入，因此不能由该比值推出ζ≤6、流量达标或无空化。')
h('3 3 阀座环面积和接触的几何条件',2)
eq('3-6',sub('A','seat'),' = ',frac(group('π(',sup(sub('D','s'),'2'),' − ',sup('D','2'),')'),'4'),' = ',frac('π(228² − 200²)','4'),' = 9 412.212 mm²')
para('D_s为当前研究座圈外径228 mm。此面积与闭位平面求交接触面积吻合；它不是由密封压缩试验取得的有效接触面积。几何检测使用相对共面平面的布尔求交，曲面接触未评定。 [S05]')
table(['研究状态','阀座接触 mm²','丝杆端接触 mm²','几何含义'],[['阀瓣0 丝杆0','9 412.212','1 017.876','两处接触；反力不能仅凭静力合力唯一分配'],['阀瓣0 丝杆退57','9 412.212','0','止回落座，丝杆不抵住'],['阀瓣升57 丝杆退57','0','1 017.876','达到研究丝杆端止挡']], [1.7,1.1,1.25,2.95],9)
para(f'共检查{len(GEO["motion"])}个丝杆/阀瓣离散组合，记录中没有体积干涉；流域在阀瓣闭位为两个实体，在1、5、10、20、35、57 mm升程为一个实体。离散检查不证明所有连续位置均安全，也不证明运动受载下不咬死。')
para('负对照取消阀座2 mm凸出后，阀瓣与阀体形成3 928.427 mm²意外平面接触，检测按预期报警。由此验证接触检查会发现这一特定错误；并非结构和密封性能已经验证。 [S07]')
h('3 4 几何交换和体积',2)
table(['零件','CAD体积 cm³','实体数','交换检查'],[[{'body':'阀体','seat_ring':'阀座','bonnet':'阀盖','packing':'填料包络','disc_guide':'阀瓣与导向','stem':'丝杆包络','handwheel':'手轮'}[name],f(row['native_mm']['volume']/1000,3),row['native_mm']['solid_count'],'回读通过'] for name,row in GEO['parts'].items()],[2.1,1.7,1,2.2],9.3,aligncols={1,2,3})
para('27个STEP导出文件通过回读、单位与体积检查。模型长度单位为mm，CFD流域转换为m时仅乘0.001一次；体积应乘10⁻⁹。通过STEP交换不意味着制造尺寸、公差和CAD特征历史完整。 [S06]')

h('4 海水物性关联式和有效域')
para('采用Sharqawy等2010公开论文的数学关系独立计算密度和黏度，用MIT原始表的九个温盐点核对。没有把纯水物性直接当成海水，也没有复制第三方程序源码。本实现限定0至50°C、30至40 g/kg、0.101325 MPa(abs)。 [S16、S17、S22]')
h('4 1 符号和关系',2)
para('t为摄氏温度的数值，S为盐度g/kg，s=S/1000为质量分数数值。关联式的系数与摄氏温标及下列输出单位绑定，不可直接将t替换为开尔文温度。ρ单位kg/m³，μ单位Pa·s，ν单位m²/s。')
eq('4-1','ρ = ',sub('ρ','w'),' + ',sub('ρ','salt'))
eq('4-2',sub('ρ','w'),' = 999.9 + 0.02034t − 0.006162',sup('t','2'),' + 2.261×',sup('10','−5'),sup('t','3'),' − 4.657×',sup('10','−8'),sup('t','4'))
eq('4-3',sub('ρ','salt'),' = 802s − 2.001st + 0.01677s',sup('t','2'),' − 3.060×',sup('10','−5'),'s',sup('t','3'),' − 1.613×',sup('10','−5'),sup('s','2'),sup('t','2'))
eq('4-4',sub('μ','w'),' = 4.2844×',sup('10','−5'),' + ',frac('1',group('0.157',sup('(t + 64.993)','2'),' − 91.296')))
eq('4-5','μ = ',sub('μ','w'),' (1 + As + B',sup('s','2'),')')
eq('4-6','A = 1.541 + 0.01998t − 9.52×',sup('10','−5'),sup('t','2'))
eq('4-7','B = 7.974 − 0.07561t + 0.0004724',sup('t','2'))
eq('4-8','ν = ',frac('μ','ρ'))
h('4 2 20°C参考点代入',2)
# Intermediate values derived independently for the transparent worked example.
t=20;s=.035;rw=999.9+.02034*t-.006162*t*t+2.261e-5*t**3-4.657e-8*t**4; rs=802*s-2.001*s*t+.01677*s*t*t-3.060e-5*s*t**3-1.613e-5*s*s*t*t; mw=4.2844e-5+1/(.157*(t+64.993)**2-91.296);aa=1.541+.01998*t-9.52e-5*t*t;bb=7.974-.07561*t+.0004724*t*t
para(f't=20，S=35 g/kg，s=0.035；按式4-2和4-3分别得到ρ_w={rw:.7f} kg/m³、ρ_salt={rs:.7f} kg/m³。A={aa:.7f}，B={bb:.7f}，μ_w={mw:.9f} Pa·s。')
eq('4-9',f'ρ = {rw:.7f} + {rs:.7f} = {rw+rs:.7f} kg/m³')
eq('4-10','μ = ',f'{mw:.10f}',' × (1 + ',f'{aa:.5f}',' × 0.035 + ',f'{bb:.5f}',' × 0.035²)')
para('得到μ=0.001076628925 Pa·s，ν=1.050460963×10⁻⁶ m²/s。计算书生成时再次用独立算术与冻结数据核对。')
caption('九个物性研究点  参考绝压均为0.101325 MPa')
table(['t °C','S g/kg','ρ kg/m³','μ mPa·s','ν ×10⁻⁶ m²/s'],[[r['temperature_C'],r['reference_composition_salinity_g_kg'],f(r['density_kg_m3'],4),f(r['dynamic_viscosity_Pa_s']*1000,7),f(r['kinematic_viscosity_m2_s']*1e6,7)] for r in SEA['rows']],[.75,.85,1.75,1.8,1.85],9.2,aligncols={0,1,2,3,4})
para('九点与已舍入原始表比较，密度差小于0.1 kg/m³、动力黏度差小于10⁻⁶ Pa·s。表列密度0.14%、黏度1.5%的关联式精度标记不包含盐度不确定性、压力修正、网格误差或整阀预测误差。')
h('4 3 未覆盖的温压条件',2)
para('−2°C输入由实现明确拒绝。低温海水是否保持单相液态取决于盐度、组成和压力；尚未通过TEOS-10冻结点分析闭合。不得用0°C结果替代−2°C并给出通过。到0.731325 MPa(abs)的压力依赖也未实现；现有机械压力合力计算不等于完成热膨胀或温度强度分析。')
table(['目标','状态','所需证据'],[['−2°C相态与物性','NOT YET COMPUTED','组成、盐度、压力下的冻结点和适用物性'],['研究压力下ρ和μ修正','NOT YET COMPUTED','在目标绝压下有效的关联式或误差界'],['蒸气压和空化判定','NOT YET COMPUTED','目标温盐压力与最低绝压结果']],[1.6,1.65,3.75],9.1)

h('5 CAD受压面和双侧压力载荷')
h('5 1 几何映射和符号约定',2)
para('正Z方向表示阀瓣上升或丝杆退开。closed为丝杆抵住阀瓣的闭位；check_closed为丝杆退开的止回闭位。两者各有入口、出口两个独立流体实体。对CAD零件外法向n，压力对零件的方向为−n。 [S18]')
eq('5-1',sub('C','i,z'),' = −', '∫',sub('n','z'),' dA')
eq('5-2',sub('F','z'),' = ',sub('p','in'),sub('C','in,z'),' + ',sub('p','out'),sub('C','out,z'))
para('C为带符号的轴向投影面积，单位mm²；p取MPa(g)。因为1 MPa=1 N/mm²，式5-2直接得到N。先核对轴向再将平行Z轴的圆柱侧面计为零轴向投影。接触面按干接触处理，未施加座面渗入压力。')
caption('由逐面CAD积分和独立圆投影公式交叉核对的系数')
table(['姿态','零件','入口系数 mm²','出口系数 mm²'],[[pose,'阀瓣与导向' if part=='disc_guide' else '丝杆',f(AREA['poses'][pose]['parts'][part]['inlet']['axial_force_coefficient_N_per_MPa']),f(AREA['poses'][pose]['parts'][part]['outlet']['axial_force_coefficient_N_per_MPa'])] for pose in ['closed','check_closed'] for part in ['disc_guide','stem']],[1.25,1.25,2.25,2.25],9.1)
eq('5-3',sub('C','disc,out,closed'),' = −',frac('π × 228²','4'),' + ',frac('π × 36²','4'),' = −39 810.262 mm²')
eq('5-4',sub('C','disc,out,check'),' = −',frac('π × 228²','4'),' = −40 828.138 mm²')
eq('5-5',sub('C','stem,out,check'),' = ',frac('π × 36²','4'),' = 1 017.876 mm²')
para('阀瓣与丝杆合计的出口投影系数在两姿态均为−39 810.262 mm²，表明干接触区域打开后，投影载荷在两零件之间转移而合计守恒。入口合计始终为31 415.927 mm²。受压面积逐面编号、法向、z坐标和六个STEP散列保存在S18。')
h('5 2 主研究压力代入',2)
eq('5-6',sub('F','disc,forward'),' = 0.63 × 31 415.926536 + 0 × (−39 810.262106) = 19 792.034 N')
eq('5-7',sub('F','disc,reverse'),' = 0 × 31 415.926536 + 0.63 × (−40 828.138126) = −25 721.727 N')
eq('5-8',sub('F','stem,reverse'),' = 0.63 × 1 017.876020 = 641.262 N')
para('反向止回的阀瓣压力分量绝对值为简单DN200面积法的1.2996倍，约增大29.96%。原因是当前座圈Ø228与干接触边界；这尚不是已确认的真实密封有效直径。')
main=[r for r in LOAD['cases'] if r['sample_kind']=='STUDY_ASSUMPTION']
mode_names={'forward-held':'正向关闭 丝杆抵住','reverse-check':'反向止回 丝杆退开','common-held':'两侧均压 丝杆抵住','common-check':'两侧均压 丝杆退开','forward-free-diagnostic':'正向自由落座诊断'}
table(['工况','入口/出口 MPa(g)','阀瓣Fz kN','丝杆Fz kN'],[[mode_names[r['case'].split('/')[1]],f"{r['inlet_pressure_MPa_g']:.2f} / {r['outlet_pressure_MPa_g']:.2f}",f(r['disc_pressure_force_z_N']/1000),f(r['stem_pressure_force_z_N']/1000)] for r in main],[2.2,1.7,1.55,1.55],9.2)
eq('5-9',sub('F','disc,common-held'),' = 0.63 × (31 415.926536 − 39 810.262106) = −5 288.431 N')
para('两侧等压并不必然给出零合力：模型仍有干接触面和外部参考压力边界。不能把所有工况压缩成一个Δp×DN面积公式。附录A保留4个压力级×5个模式的20组结果，包括每一压力级的正向自由落座负对照。')
h('5 3 静力平衡与不能由合力确定的量',2)
eq('5-10',sub('F','p,z'),' + ',sub('R','seat'),' − ',sub('R','screw'),' − W + ',sub('F','other,z'),' = 0')
para('R_seat和R_screw为单边接触反力的非负幅值；W为重量向下，F_other,z为摩擦、预紧、惯性等项的有符号总量。closed有两处未知接触反力，仅一个合力方程不能唯一求解，必须加入接触刚度、约束和预紧等关系。')
para('check_closed的简化压力单项诊断取R_seat=−F_disc。反向止回得到+25 721.727 N，符合非负单边反力条件，但不是实际反力。正向自由落座得到−19 792.034 N，要求阀座承受拉力，因此该简化状态不能维持静态落座。应让阀瓣运动或完善重量/预紧/摩擦条件，不能将该负数隐藏为通过。')
para('所有20组结果的actual_contact_reaction_N和actual_drive_force_N均保持null。未计算泄漏、接触渗压、弹性开启、静水头分布和瞬态惯性。机械压力分量跨温度不变的表述只说明本算术不含温度项，不能据此确认−2至50°C的强度。')

h('6 丝杆根部与驱动摩擦敏感性')
h('6 1 模型载荷和螺纹几何',2)
para('本章取F=19 792.034 N，即0.63 MPa正向关闭液压力分量，研究驱动克服该反向载荷时的扭矩大小。实际执行器需要的推力还含密封预紧、填料、起动、重量以及真实接触分配，尚未确定。螺纹旋向未确认，因此本章只计算大小。')
eq('6-1','λ = arctan',frac('l','πd₂'),' = arctan',frac('6','π × 33'),' = 3.312271°')
eq('6-2',sub('α','n'),' = arctan(tan',sub('α','x'),' cosλ) = 14.976069°')
eq('6-3',sub('μ','e'),' = ',frac('μ',group('cos',sub('α','n'))))
para('λ为导程角；α_x=15°为轴向截面半牙角，α_n为法向截面半牙角。不能直接把轴向角与法向效率关系混用。d₂=33 mm、d₃=29 mm来自Tr36×6的DIN103厂商名义表，公差等级及实际最小根径未控制。 [S15、S19、S20]')
h('6 2 螺纹扭矩和功一致性',2)
eq('6-4',sub('T','thread'),' = ',frac('Fd₂','2000'),frac(group('tanλ + ',sub('μ','e')),group('1 − ',sub('μ','e'),'tanλ')))
para('F单位N，d₂单位mm，2000包含半径除2和mm转m；输出T为N·m。该式为库仑准静态关系。')
eq('6-5',sub('T','ideal'),' = ',frac('Fl','2000π'),' = ',frac('19 792.033718 × 6','2000π'),' = 18.900 N·m')
eq('6-6','η = ',frac(group('tanλ(cos',sub('α','n'),' − μtanλ)'),group('cos',sub('α','n'),'tanλ + μ')),' ;  η',sub('T','thread'),' = ',sub('T','ideal'))
para(f'μ=0.15时，μ_e={.15/math.cos(alpha):.8f}，代入式6-4得T_thread=70.238822 N·m，η=0.26908196。C4对每个摩擦情景用独立效率/每转功恒等式交叉检查。η是此简化螺纹模型的效率，不能当作已测整机效率。')
h('6 3 支承环和手轮轮缘力',2)
eq('6-7',sub('r','c'),' = ',frac(group(sub('D','c,o'),' + ',sub('D','c,i')),'4'),' = ',frac('60 + 36','4'),' = 24 mm')
eq('6-8',sub('T','c'),' = ',frac(group('F',sub('μ','c'),sub('r','c')),'1000'),' = ',frac('19 792.033718 × 0.10 × 24','1000'),' = 47.500881 N·m')
eq('6-9',sub('T','sum'),' = ',sub('T','thread'),' + ',sub('T','c'),' = 117.739702 N·m')
eq('6-10',sub('F','rim'),' = ',frac(sub('T','sum'),sub('R','wheel')),' = ',frac('117.739702','0.160'),' = 735.873 N')
para('支承环采用均匀磨损有效半径，仅作为反力支承的敏感性代理，尚未选定实际轴承。μ_c=0表示本模型不加入支承环摩擦项，不代表真实支承无摩擦。')
caption('12组摩擦情景  F固定为19 792.034 N')
table(['μ螺纹','μ支承','T螺纹 N·m','T合计 N·m','轮缘力 N','螺纹静态自锁'],[[f(r['thread_mu_assumed'],2),f(r['collar_mu_assumed'],2),f(r['thread_torque_Nm'],3),f(r['combined_model_torque_Nm'],3),f(r['handwheel_rim_force_N'],2),'模型满足' if r['static_self_lock_model'] else '模型不满足'] for r in LOAD['drive_sensitivity']['rows']],[.7,.7,1.4,1.4,1.2,1.6],8.9,aligncols={0,1,2,3,4,5})
h('6 4 自锁条件和名义牙根平均应力',2)
eq('6-11','μ > cos',sub('α','n'),' tanλ = 0.05590875')
para('μ=0.03情景不满足该静态自锁条件。静态条件成立也不能证明振动环境下不倒转，防松、保持、反力路径仍需专门设计。原图45 kgf限值作用于辅助扳手，未获得扳手长度和施力方向，故未与Ø320手轮轮缘力直接比较。')
eq('6-12',sub('A','root'),' = ',frac('πd₃²','4'),' = ',frac('π × 29²','4'),' = 660.520 mm²')
eq('6-13',sub('σ','axial'),' = ',frac('F',sub('A','root')),' = ',frac('19 792.033718','660.519855'),' = 29.964328 MPa')
para('这是仅该液压力分量在29 mm名义根径上的平均正应力。实际最小根径、牙根应力集中、弯曲、扭转、屈曲、疲劳和腐蚀均未计入，也没有材料许用应力。因此没有强度裕量或通过判定。')
h('6 5 啮合长度的均匀牙面代理',2)
eq('6-14',sub('A','flank'),' = ',frac('πd₂Lₑ','2'),' ;  ',sub('q','flank'),' = ',frac('F',sub('A','flank')))
table(['Lₑ情景 mm','投影面积 mm²','平均压力代理 MPa'],[[r['engagement_scenario_mm'],f(r['uniform_projected_flank_area_mm2']),f(r['uniform_mean_projected_flank_pressure_MPa'],5)] for r in LOAD['drive_sensitivity']['uniform_thread_flank_proxy']],[1.8,2.6,2.6],9.5,aligncols={0,1,2})
para('例如Lₑ=54 mm时，A_flank=π×33×54/2=2 799.159 mm²，q_flank=7.070707 MPa。此代理忽略首牙载荷集中、剪切、磨损、有效牙数及端部效应。40/54/70 mm来源是螺母包络候选，不能直接视为真实有效啮合长度。')

h('7 盖接头与密封支承敏感性')
h('7 1 未选定的三套几何候选',2)
table(['候选','数量×名义径 mm','盖法兰外径 mm','螺栓圆 mm','垫片内/外径 mm'],[[r['id'],f"{r['bolt_count']} × {r['values']['bolt_nominal_d']['value']}",r['values']['flange_od']['value'],r['values']['bolt_circle_d']['value'],f"{r['values']['gasket_id']['value']} / {r['values']['gasket_od']['value']}"] for r in INT['bonnet_joint_candidates']],[1,1.65,1.45,1.25,1.65],9.0)
para('J8-16、J12-16和J8-20均为研究候选，没有自动选中。孔边距和支承面满足几何条件，不等同规范最小边距、螺栓强度或垫片密封要求。C3候选为接口试件，尚未整合进冻结C2承压结构。 [S10至S12]')
h('7 2 垫片有效边界对分离载荷的影响',2)
eq('7-1',sub('F','sep'),' = p',frac(group('π',sup(sub('D','eff'),'2')),'4'))
eq('7-2',sub('F','count'),' = ',frac(sub('F','sep'),'N'))
para('D_eff为未知的有效压力直径，分别以垫片内缘、中径、外缘进行扫描；N为紧固件数量。F_count只是总分离压力分量的数量等分尺度，不是单个螺栓实际载荷。')
eq('7-3',sub('F','sep,J8-16,mid'),' = 0.63 × ',frac('π × 310²','4'),' = 47 550.361 N')
eq('7-4',sub('F','count,J8-16,mid'),' = ',frac('47 550.361','8'),' = 5 943.795 N')
table(['候选','边界','D有效 mm','分离分量 kN','数量等分 kN'],[[r['candidate'],{'inner-edge':'内缘','mid-annulus':'中径','outer-edge':'外缘'}[r['effective_diameter_scenario']],r['assumed_effective_pressure_diameter_mm'],f(r['pressure_separation_component_N']/1000),f(r['equal_count_division_N']/1000)] for r in LOAD['joint_pressure_diameter_sensitivity']],[1.15,.9,1.3,1.8,1.85],9.2,aligncols={1,2,3,4})
para('在0.63 MPa下，J8-16/J12-16分离分量随有效直径从42.189增至53.233 kN；更宽的J8-20外缘情景到58.553 kN。改为12个螺栓只降低数量等分尺度，并不自动保证每个螺栓等载或接头更可靠。需建立法兰/螺栓/垫片刚度、预紧散差、嵌入损失、松弛和外载模型。')
h('7 3 真实平面支承面积',2)
eq('7-5',sub('A','g,J8-16'),' = ',frac('π(328² − 292²)','4'),' = 17 530.087 mm²')
table(['候选','垫片面积 mm²','垫圈单面最小支承 mm²','检查面数','结论'],[[r['id'],f(r['gasket_face_area_mm2']),f(r['washer_min_contact_mm2']),r['washer_faces_checked'],'几何全面支承'] for r in SUP['joint_support']],[1.05,1.65,2.1,.75,1.45],8.9)
para('CAD求交显示三候选垫片在阀体侧和盖侧均有全平面几何支承，垫圈对应支承面也完整。没有由此推定接触压力均匀、残余夹紧足够或垫片不泄漏。J8-20的法兰外径已在候选阶段从420增至440 mm，使45 mm垫圈完全落在试件表面。')
h('7 4 填料端部支承与挤出边界',2)
eq('7-6',sub('A','packing'),' = ',frac('π(44² − 36²)','4'),' = 502.655 mm²')
table(['表面','几何接触面积 mm²','覆盖率','状态'],[['底部壳体',f(SUP['packing_end_support']['bottom_housing_contact_mm2']),f(SUP['packing_end_support']['bottom_contact_fraction']*100,3)+'%','局部未支承'],['顶部压套',f(SUP['packing_end_support']['top_follower_contact_mm2']),f(SUP['packing_end_support']['top_contact_fraction']*100,3)+'%','局部未支承']],[1.4,2.2,1.25,2.15],9.2)
para('四圈填料总包络高20 mm，压套外径43.8 mm、内径36.4 mm；相对填料腔/杆的径向几何间隙分别0.1和0.2 mm。材料、压缩比例、挤出容许间隙和泄漏等级未定，因此92.731%/95.475%的端部覆盖率只揭示支承缺口，不给密封通过。 [S10至S12]')

h('8 装拆空间和机构闭合')
h('8 1 驱动螺母包络',2)
para('C3取拟议驱动支承底面z=388 mm，C2闭位手轮轮毂下表面z=438 mm，净轴向空间50 mm。3 mm仅为拟议可视几何余量，不是标准安全间距。')
eq('8-1','g = 438 − (388 + L) = 50 − L')
table(['候选','长度 mm','手轮间隙 mm','达到3 mm余量还需 mm','包络判断'],[[r['id'],INT['drive_nut_candidates'][i]['length'],r['handwheel_hub_gap_mm'],r['additional_axial_space_required_mm'],'几何通过' if r['packaging_gate']=='PASS' else '几何冲突'] for i,r in enumerate(FIT['drive_candidates'])],[1.85,.85,1.3,1.8,1.2],9.0)
para('D40仍未验证防转、轴向保持、螺纹承载、支承反力和完整装配；D54/D70的长度敏感性不能作为可直接采购并装入的产品结论。D70供应商外包络的法兰等特征也没有完整纳入支承模型。')
h('8 2 抽出路径检查',2)
para('在阀盖与丝杆组已移除的研究几何中，阀瓣沿轴向抽出0、25、50、100、150、200、250 mm时，与阀体和阀座的体积干涉均为零。保留阀盖时抬升200 mm产生468 518.279 mm³干涉；保持丝杆固定时抬升25 mm产生14 250.264 mm³干涉，作为预期负对照。 [S13]')
para('这只证明列出的离散CAD状态。尚未检查完整螺栓、保持件、导向、防脱、工具操作、吊装和连续扫掠路径，也没有抽出力计算；不得将此节用于指导现场带压设备拆卸。')
h('8 3 下阶段机构输出',2)
para('需形成明确的自由度和启闭顺序：丝杆强制关闭、退开后的自由止回、最大升程止挡、阀瓣防脱、导向长度与间隙、螺母防转和轴向反力支承。每个状态均应重新求几何接触、流域连通、受压面和装配路径，避免只修改外观而沿用旧载荷面积。')

h('9 材料卡与供货状态边界')
para('本章记录原型号类比候选和独立替代材料，不能将材料家族、相近牌号或不同供货状态的数值混用。抗拉强度、屈服/规定延伸强度和设计许用应力是不同量。当前所有材料卡的设计许用应力均为null。 [S23]')
table(['材料卡','产品状态','可用数据','当前用途'],[
['БрО8Ц4','锡青铜铸件；金属模/砂模参考','抗拉参考196 MPa；延伸10%；E/ν/ρ空缺','原目录阀体候选'],['БрАЖНМц9-4-4-1','变形加工体系；本阀料态未知','有化学成分；力学和弹性输入空缺','盖/阀瓣原目录候选'],['Сплав 3М','海工α Ti-Al家族；具体料态未明','牌号摘要491/442 MPa；不采作阀输入','座/杆身份研究'],['C95800','连续铸造；铸态或回火退火','E114 GPa；ν0.32；ρ7640 kg/m³','单列替代弹性研究'],['C90300','连续铸造','E96.527 GPa；ρ8800；ν空缺','部分替代性质'],['C63000','热挤压或拉制/去应力棒材','未选具体尺寸与状态性质行','替代采购路线筛选']],[1.4,1.6,2.5,1.5],8.9)
h('9 1 原目录材料候选',2)
para('БрО8Ц4依据ГОСТ613-79：Sn 7至9%、Zn 4至6%、Cu余量；承压铸件Al+Si组合限制不可按非承压件放宽。附录参考力学数据为未热处理材料，抗拉196 MPa、延伸10%；它们不能代替本产品技术文件规定的验收。没有采用E、ν、ρ、屈服或许用应力。')
para('БрАЖНМц9-4-4-1依据ГОСТ18175-78化学成分：Al 8.8至10%、Fe 4至5%、Ni 4至5%、Mn 0.5至1.2%。厂商有挤压圆棒16至160 mm供货线索，但尚未取得对应力学要求。不能用同名料系替代铸造牌号БрА9Ж4Н4Мц1，也未采纳无一级供货状态证据的650 MPa/15%网络值。2027-02-01才生效的修订3未提前采用。')
para('Сплав 3М有较强证据指向海工α型Ti-Al合金；目标目录该页未指定准确产品标准。开发者牌号摘要列抗拉491 MPa、Rp0.2=442 MPa等，但缺具体供货形态、截面、热处理与基准试温，所以本阀采用输入仍为空。350°C的牌号数据点不扩展本阀工作温度。')
h('9 2 连续铸造替代材料与冲突',2)
para('C95800是独立镍铝青铜替代研究候选，不声明与任何俄牌号等同。厂商连续铸造数据可支持E=114000 MPa、ν=0.32、ρ=7640 kg/m³的常数弹性/质量敏感性；ρ明确20°C，E/ν表内未重复温度。不得把连续铸造最小强度移用于砂型阀体，也不得把0.5%受载延伸屈服定义改写为Rp0.2。')
para('C95800厂商Mn下限0.08%与CDA的0.8%冲突；热膨胀9×10⁻⁶/°F与15.5×10⁻⁶/°C并不精确互换。C90300的P上限网页0.05%与PDF1.50%冲突，热膨胀单位对也不一致。因此完整化学成分及热膨胀均未冻结；C90300还缺ν，不能用其卡直接补齐三维各向同性弹性模型。')
para('材料正式冻结需逐零件确认：供货标准及版本、成形路线、截面尺寸、热处理、温度性质、腐蚀/冲蚀余量、铸造质量要求和证书。即使后续以C95800算出弹性位移，也只能命名为该替代候选的结果，不能作为原俄牌号阀体强度验收。')

h('10 流动计算定义与真实CFD状态')
h('10 1 流量压降和阻力系数',2)
para('本阀尚无可用的CFD压降或流量结果。为保证后续可比较，预先固定符号与单位，并在每一结果行登记实际开度、流向、温盐条件、压力取样面和参考截面。下列是定义与后处理方法，不是本阀已经得到的性能。')
eq('10-1',sub('U','ref'),' = ',frac('Q',sub('A','ref')),' ;  Re = ',frac(group('ρ',sub('U','ref'),sub('D','h')),'μ'))
eq('10-2','Δp = ',sub('p','up'),' − ',sub('p','down'),' ;  ζ = ',frac('Δp',group(frac('1','2'),'ρ',sup(sub('U','ref'),'2'))))
para('Q采用m³/s，U_ref采用m/s，ρ采用kg/m³，Δp采用Pa，D_h采用m，Re和ζ无量纲。参考速度若采用DN200截面，则A_ref=0.0314159265 m²。压差必须说明静压或总压、面积或流量加权平均及测压截面；需明确直管损失是否扣除。对不同定义，ζ不能直接比较。')
para('采用运动压力的不可压求解器时，字段p的量纲为m²/s²；同一常密度模型中压差Pa=ρ×字段差。需检查实际求解器和输出量纲，不能仅凭字段名为p就当Pa。')
h('10 2 Kv和Cv的单位约定',2)
eq('10-3',sub('K','v'),' = Q [m³/h] ',sqrt(frac('SG','Δp [bar]')))
eq('10-4',sub('C','v'),' = Q [US gal/min] ',sqrt(frac('SG','Δp [psi]')))
eq('10-5',sub('K','v'),' ≈ 0.8650 ',sub('C','v'),' ;  ',sub('C','v'),' ≈ 1.1561 ',sub('K','v'))
para('SG为相对于明确参考水密度的比重。Kv按参考液体1 bar压差的m³/h容量约定，Cv按1 psi压差的US gal/min容量约定；两者不是无量纲ζ。式10-3至10-5适用于所声明的非阻塞单相不可压平方律解释，不能不加修正地用于空化、闪蒸或其他流态。若报告标准化产品Kv/Cv，必须进一步选定标准及参考水温/密度。')
para('单纯SI换算：1 US gal=0.003785411784 m³，1 psi≈6894.757293 Pa，1 bar=100000 Pa。由同一SG和同一压差定义得到Kv/Cv≈0.865；不得将Pa数值直接代入bar或psi位置。')
h('10 3 当前网格证据和预检查失败',2)
table(['项目','实测值','说明'],[['长度单位','m','STEP mm仅转换一次'],['节点/四面体',f"{MESH['nodes']:,} / {MESH['tetrahedra']:,}",'C2全开研究流域'],['面连通分量/非流形面','1 / 0','拓扑检查'],['CAD体积 m³',f(MESH['cad_volume_m3'],9),'研究流域'],['网格体积 m³',f(MESH['mesh_volume_m3'],9),'线性四面体'],['相对体积差',f(MESH['relative_volume_error']*100,5)+'%','几何离散差；非CFD误差'],['入口/出口/壁三角面','212 / 212 / 12984','边界覆盖完整']],[2,2.15,2.85],9.2)
para('C2几何/拓扑网格检查与OpenFOAM严格几何检查评估不同性质。现有C2四面体网格导入后，严格checkMesh报告3类失败：2个高偏斜面（最大5.65834）、326个小行列式单元、10个低插值权重面。另有44个大于70°的非正交面，最大80.8156°。双对偶转换方案也未通过，共7项失败。该失败被保留，不以原有拓扑通过覆盖。 [S08、S25、S26]')
if UPDATE:
 para('C5后续补充：'+UPDATE.get('summary','已接入更新快照，详见独立证据。'))
para('截至本版没有把上述失败网格的流动结果列为性能。真实阀网格正在修复；更新必须含修复几何/网格散列、严格预检、求解设置、日志与监测曲线，不能只替换图片。')
h('10 4 标准方腔算例与阀性能分开登记',2)
foam=BENCH['openfoam']
table(['标准算例项目','记录'],[['算例','Re=10方腔；非本阀'],['步数/最终时间',f"{foam['timesteps']} / {foam['final_time']} s"],['最终Ux/Uy/p线性残差','2.30910×10⁻⁷ / 5.06840×10⁻⁷ / 9.59103×10⁻⁷'],['最大Courant数',str(foam['max_courant'])],['累计连续性误差','1.21735×10⁻¹⁷'],['已证明范围','串行执行、日志/单位/守恒冒烟检查'],['未证明范围','本阀ζ、壁面湍流、空化和网格独立性']],[2.1,4.9],9.3)
para('方腔线性残差低和连续性良好是软件执行证据。该算例没有建立本阀解的误差界，也没有以独立实验值完成阀性能验证。 [S24]')
h('10 5 真实CFD结果和收敛矩阵',2)
table(['输出','当前结果','必须同时报告'],[pending('本阀Q Δp ζ Kv Cv'),pending('本阀速度压力和壁面分辨率'),pending('本阀稳态残差与流量守恒'),pending('网格加密趋势与GCI'),pending('−2°C相态与空化边界')],[2.2,1.7,3.1],9.1)
para('完成标准：在选定开度和流量下，至少记录残差、入口/出口质量流率、Δp与力监测的稳定性；改变网格分辨率时保持几何、边界、物性和后处理一致。仅有残差降低不足以建立物理收敛；不稳定流动可能需要瞬态统计及时间步敏感性。')
eq('10-6',sub('ε','mass'),' = ',frac(group('|',sub('ṁ','in'),' + ',sub('ṁ','out'),'|'),group('max(|',sub('ṁ','in'),'|, |',sub('ṁ','out'),'|)')))
para('ṁ_in、ṁ_out均以计算域外法向为正，因此正常入口为负、出口为正；零流量时式10-6的归一化指标不适用。')
para('对于确实处于渐近区、细化比相同的三网格序列，令1细、2中、3粗，h₁<h₂<h₃，r=h₂/h₁=h₃/h₂，φ为同一定义输出，可使用下列观察阶与误差估计；非单调或振荡收敛时不能强套。')
eq('10-7',sub('p','obs'),' = ',frac(group('ln|',frac('φ₃ − φ₂','φ₂ − φ₁'),'|'),'ln r'))
eq('10-8',sub('φ','ext'),' = φ₁ + ',frac('φ₁ − φ₂',group(sup('r',sub('p','obs')),' − 1')))
eq('10-9',sub('GCI','fine'),' = ',sub('F','s'),frac('|φ₁ − φ₂| / |φ₁|',group(sup('r',sub('p','obs')),' − 1')))
para('p_obs、φ_ext、Fs和GCI均未赋本阀数值。安全系数Fs、输出接近零时的归一化和非等比网格处理须在选定验证方法中说明。网格不确定度、迭代误差、物性误差、模型误差与实验偏差应分开报告。')

h('11 结构计算和真实FEA状态')
h('11 1 可用载荷与未闭合边界',2)
para('C4已给压力增量在阀瓣/丝杆上的轴向分量；尚未给壳体全部面载荷的受控映射、阀盖连接刚度、端法兰安装约束、管系外载、座面渗压、螺栓预紧和实际接触。不可直接将19.792 kN作为所有结构件的唯一载荷。')
para('C2壳体20 mm为构形偏置，尚未建立全局最小有效壁厚。承压设计需包括开孔、过渡圆角、法兰、铸造质量、腐蚀余量和温度许用值；用理想薄圆筒公式套当前复杂阀体并给安全系数不成立。')
h('11 2 已运行的均匀拉伸标准算例',2)
table(['单位体系','单元数','端位移','平均轴向应力','合反力'],[[r['units'],r['elements'],str(r['mean_end_displacement'])+(' mm' if r['units']=='N-mm-MPa' else ' m'),str(r['mean_axial_stress'])+(' MPa' if r['units']=='N-mm-MPa' else ' Pa'),f(r['reaction_x'],1)+' N'] for r in BENCH['ccx']],[1.55,.8,1.6,1.65,1.4],9.2)
para('CalculiX均匀应变拉伸检查在1、8、64单元及SI重算下均得到相同物理位移、应力和反力；记录的理论位移/应力/力平衡相对误差为零（输出精度范围），伪应力相对误差约10⁻¹⁵至10⁻¹⁴量级（无量纲）。它验证线弹性均匀应变和单位链，不是本阀应力收敛，也未验证非线性接触、螺纹和预紧。 [S24]')
h('11 3 待计算结构结果',2)
table(['结果','当前值','缺少的关键条件'],[
['阀体/阀盖最大应力','NOT YET COMPUTED','承压边界、材料和网格'],['阀体/阀盖变形','NOT YET COMPUTED','相同条件及边界刚度'],['阀座接触压力与开启','NOT YET COMPUTED','接触/渗压/预紧/材料'],['螺栓真实载荷与剩余夹紧','NOT YET COMPUTED','刚度、预紧和散差'],['丝杆组合应力及屈曲','NOT YET COMPUTED','最小根径、弯扭、支承长度'],['结构网格不确定度','NOT YET COMPUTED','同工况多网格结果'],['规范利用率或安全系数','NOT YET COMPUTED','上述应力及有效许用值']],[2.4,1.65,2.95],9.0)
para('后续结果至少应记录全局力/力矩平衡、位移与应力的网格趋势、接触穿透/开闭状态和求解收敛。奇异约束或尖角处的最大节点应力不能直接作为尺寸优化或验收指标；需要与选定规范的应力分类和局部评定方法一致。')
h('11 4 材料与数值解的命名',2)
para('如果优先使用C95800连续铸造替代常数做线弹性研究，报告必须写明“C95800连续铸造参考性质弹性敏感性”，并保持屈服/许用为空。没有非线性材料曲线，不能将线弹性高应力直接解释成塑性极限载荷；没有疲劳曲线和循环谱，不能给寿命。')

h('12 规范适用性和未满足验收要求')
para('原图引用标准与现代候选标准分开登记。公开登记状态或厂商节录可以证明文献身份，不能单凭它们确定合同适用性、船级、版本和条款合格。以下是2026-10-06研究证据的摘要；不是已获批准的规范计算基准。 [S02、S23]')
table(['标准或文件','关联内容','当前边界'],[
['ГОСТ356-80','原图注3压力系列','需材料/温度行及2024更正的受控全文'],['ГОСТ1536-76','原图注10船用法兰连接/密封面','几何匹配不确定整阀额定或试压'],['ГОСТ613-79','锡铸造青铜','材料候选；附录参考值非许用'],['ГОСТ18175-78','压力加工无锡青铜的化学成分','只冻结已读成分范围；产品状态未定'],['ГОСТ33260-2015','现代阀门材料选用候选','非原图引用；需批准适用性'],['ГОСТ33257-2015','现代控制和试验方法候选','尚无已执行的本阀试验'],['ГОСТ9544-2015','现代泄漏等级候选','等级、方向、方法未选'],['ГОСТ34437-2018','水力阻力/空化表征候选','2026修订需与全文对照；定义待闭合'],['ГОСТ15150-69','原图气候ОМ5与贮存条件','不能据此扩展承压工作温度'],['ГОСТ9.032-74 / 35094-2024','旧涂层要求与后续替代','替代状态不自动授权改旧图'],['ОСТВ5.4347-81','原图振动A组','需具体试验谱和验收'],['РД5.9307-79','原图机械锁紧','不是IP防护等级'],['Л-ПСП-4035-85','基础型号压温时间分布','文件尚缺；不能填造循环谱']],[1.85,2.05,3.1],8.8)
h('12 1 按原图要求逐项保留缺口',2)
table(['要求','来源或说明','当前验证'],[['耐压/物理试验','试验压力、时长、介质及方法未确定','NOT YET COMPUTED / 未试验'],['关闭泄漏','等级、方向、压差与温度未冻结','未试验'],['水力阻力系数≤6','原图注24；取压和参考速度待定义','本阀ζ NOT YET COMPUTED'],['辅助扳手力≤45 kgf','原图注20；扳手816-03.106几何未闭合','未验证'],['冲击2级','原图注22；具体方法待取得','未验证'],['振动A组','原图注23','未验证'],['噪声≤70 dB','原图注25；МКШС-71Е方法','未验证'],['可靠度0.97及5000 h连续','原图注27；寿命谱/方法未闭合','未验证'],['寿命和储存','原图注8/9及适用说明','未验证'],['制造图与检验','逐件材料/公差/工艺/验收','尚未冻结']],[1.85,3.1,2.05],9.0)
para('数值超载1.0 MPa没有被批准为实物试压。材料抗拉强度、均匀拉伸基准通过、网格几何通过、静态受力算术通过均不能补齐物理承压、泄漏、耐久、冲击振动或噪声验收。')

h('13 制造闭环和剩余计算顺序')
para('C3工作分解M01至M15继续保留，但本表反映已更新的研究进度：M01的基础型号和研究载荷已选，M13的工具许可/标准算例已推进；它们仍不等于正式工况和本阀专项验收完成。')
statusmap={'M01':'部分完成：基础型号与研究载荷已选','M02':'部分完成：材料证据卡；无许用值','M03':'部分完成：来源矩阵；适用全文待控','M04':'待计算：承压详细设计','M05':'研究完成：三候选未选','M06':'部分完成：压力边界敏感性','M07':'部分完成：几何支承；性能待算','M08':'部分完成：摩擦/根径敏感性','M09':'待完善：导向、防脱与全行程','M10':'部分完成：七主件与抽出样点','M11':'研究完成：图纸/尺寸索引','M12':'待冻结：制造与检验图','M13':'部分完成：标准基准；真阀待算','M14':'未完成：实际试验','M15':'HOLD：未工程审签'}
table(['编号','工作项','当前状态'],[[r['id'],r['title'],statusmap[r['id']]] for r in WBS['tasks']],[.65,2.9,3.45],9.0)
para('优先顺序：先修复真实阀网格并完成可追溯流动研究；并行闭合材料状态、驱动支承与保持、密封有效边界和制造几何。受力面积或机构改变后重算C4载荷，再进入结构接触与预紧。最后根据适用规范和实物试验证据审签，不把计算书排版完成当成设计完成。')

h('14 复算方法和证据可追溯性')
para('本书由build_calculation_book.py从sources快照中的JSON/日志生成。正文结果表使用相同源数据，不另录一份手工数值。生成器独立复核通道面积、转数、压力换算、全部双侧载荷、螺纹/支承扭矩、根部平均应力、接头分离力和九点海水算术。')
para(f'本版独立算术检查共{len(checks)}项，均与冻结数据一致；详见arithmetic_verification.json。该状态不包括CAD重建、求解器运行或工程验收。每个引用文件的完整SHA256、字节数和来源路径见source_manifest.json。')
para('在已有文档依赖环境中运行：python build_calculation_book.py。需要刷新来源时使用--repo指定仓库副本并显式加--refresh-sources。刷新只复制来源到计算书目录，生成器不改模型、运行目录、冻结清单或求解文件，也不安装软件或访问网络。')
para('工程复算脚本索引：C2/T15/study_calculations.py为早期归一化算术；C4/T06/seawater_study.py为物性；C4/T19/extract_pressure_faces.py为CAD受压面；C4/T15/calculate_loads.py为载荷和敏感性。C4/verify_study.sh会重写该阶段结果/日志，冻结包复跑须在新副本执行以免破坏散列。')
para('C4普通及Python优化模式记录各47项测试通过，连同独立评审和归档字节散列检查形成C4证据链。测试范围是C4输入、算术、拒绝越界及证据完整性；并未测试真实阀CFD或FEA。 [S30至S32]')
para('文档更新规则：新章节只有在结果文件、输入版本、网格/材料/边界、日志与独立检查一致时才替换NOT YET COMPUTED。数值解与工程合格分开设栏；旧结果保留版本，不以新图覆盖历史失败。')

D.add_page_break()
h('附录A 四个压力级的完整载荷表')
para('所有压力为MPa(g)，轴向载荷为kN。符号+表示上升。表中的压力自由落座诊断只检验单边接触符号，不给实际反力。')
for level in BASE['pressure_sensitivity']:
 h({'literal6-conditional':'A1 原图6 kgf每平方厘米的条件解释','catalog6p3-converted':'A2 目录6点3 kgf每平方厘米换算','selected-study':'A3 选定研究压力','overload-sensitivity':'A4 数值超载敏感性'}[level['id']],2)
 rows=[r for r in LOAD['cases'] if r['case'].startswith(level['id']+'/')]
 table(['模式','p入口','p出口','F阀瓣','F丝杆','仅压力接触诊断'],[[mode_names[r['case'].split('/')[1]],f(r['inlet_pressure_MPa_g'],6),f(r['outlet_pressure_MPa_g'],6),f(r['disc_pressure_force_z_N']/1000),f(r['stem_pressure_force_z_N']/1000),{'TWO_CONTACT_REACTIONS_UNDETERMINED':'两反力未定','NONNEGATIVE_SEAT_REACTION':'符号可非负','WOULD_REQUIRE_TENSILE_SEAT_REACTION':'要求拉力 不成立'}[r['pressure_only_unilateral_contact']]] for r in rows],[1.9,.9,.9,.95,.95,1.4],8.6)
para('以上每行的实际接触反力、最终驱动力、工程通过值均未求得；源数据均为null或false，不将缺失值显示为0。 [S19]')

h('附录B 主要几何参数补充登记')
para('本表补充正文未逐列的CAD研究参数，单位mm。除另注明外均属设计假设，不能直接签发为制造尺寸。')
labels={'raised_face_height':'法兰凸面高度','chamber_radius':'阀腔半径','body_top':'阀体顶面z','bonnet_flange_radius':'阀盖法兰半径','bonnet_thickness':'阀盖厚','neck_radius':'颈部半径','neck_top':'颈部顶面z','stem_bore_radius':'杆孔半径','packing_bottom':'填料底面z','guide_od':'导向外径','guide_id':'导向内径','guide_height':'导向高','inlet_transition_end':'入口过渡终点x','lower_channel_z':'下通道中心z','lower_channel_y_radius':'下通道y半径','lower_channel_z_radius':'下通道z半径','outlet_transition_start':'出口过渡起点x','upper_channel_z':'上通道中心z','upper_channel_y_radius':'上通道y半径','upper_channel_z_radius':'上通道z半径','body_bottom':'阀体底面z','body_flange_thickness':'阀体法兰厚','packing_height':'填料高','handwheel_rim_radius':'轮缘圆截面半径','handwheel_hub_radius':'轮毂半径','handwheel_hub_height':'轮毂高','spoke_width':'辐条宽','spoke_thickness':'辐条厚','spoke_overlap':'辐条搭接','stem_square':'丝杆方头','square_drive_clearance':'方头间隙','chamber_floor_z':'阀腔底面z'}
table(['键','中文含义','值 mm','性质'],[[k,lab,p[k],'原图参考' if P['values'][k]['kind']=='DRAWING_REFERENCE' else '研究假设'] for k,lab in labels.items()],[2.65,2.2,.95,1.2],8.8)

h('附录C 证据文件索引')
para('路径相对于工程仓库runs/20261006。计算书随附sources保存被引用文件的逐字节副本；每个完整散列保存在source_manifest.json，表中仅列前12位用于人工定位。第三方标准和物性论文全文未在本书包中复制。')
table(['编号','文件路径','内容','SHA256前12位'],[[r['id'],r['relative_path'],r['description'],r['sha256'][:12]] for r in manifest],[.48,3.25,2.05,1.22],8.4)

h('附录D 外部一级来源索引')
para('外部链接用于追查当前证据，不自动构成已获批准的适用版本。读取日期为来源包所记2026-10-06；本计算书生成没有重新取代原证据审查。')
links=[
('D01 LPA船用阀目录 印刷第53页','https://lenpromarmatura.ru/downloads/LPA_catalog_sudarm.pdf#page=54','基础型号类比；压力栏kgf/cm²和材料候选'),
('D02 NIST单位换算','https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8','kgf/cm²与SI的换算依据'),
('D03 海水物性原作者论文','https://web.mit.edu/lienhard/www/papers/journal/Thermophysical_properties_of_seawater-DWT-16-354-2010.pdf','Sharqawy等2010 式8 22 23'),
('D04 MIT海水原始表','https://web.mit.edu/seawater/2017_MIT_Seawater_Property_Tables_r2b_2023c.pdf','九温盐点的舍入表值'),
('D05 TEOS 10冻结点说明','https://teos-10.org/pubs/gsw/html/gsw_t_freezing.html','低温相态需组成和压力'),
('D06 Bornemann梯形螺纹名义表','https://www.bornemann-gewindetechnik.de/en/products/trapezoidal-threads/data/','Tr36×6基本名义尺寸'),
('D07 Roton丝杆效率关系','https://www.roton.com/screw-university/formula-calculators/efficiency-power-screws-forward-drive/','法向半角效率恒等式交叉核对'),
('D08 ГОСТ613厂商托管副本','https://mzocm.com/613-79.pdf','БрО8Ц4成分与参考附录'),
('D09 ГОСТ18175厂商托管副本','https://mzocm.com/18175-78.pdf','БрАЖНМц9-4-4-1成分'),
('D10 Prometey海洋钛合金','https://www.crism-prometey.ru/science-and-education/research-and-development/titanovye-splavy/titanovye-splavy-dlya-sudostroeniya-i-morskoy-tekhniki/','3М牌号身份与开发者摘要'),
('D11 Concast C95800','https://www.concast.com/files/C95800.pdf','连续铸造替代材料参考数据'),
('D12 CDA C95800','https://alloys.copper.org/alloy/C95800','材料交叉对照和冲突登记'),
('D13 Concast C90300','https://www.concast.com/files/C90300.pdf','连续铸造替代材料参考数据'),
('D14 CDA C63000','https://alloys.copper.org/alloy/C63000','变形材尺寸/状态筛选'),
]
from docx.opc.constants import RELATIONSHIP_TYPE as RT
def hyperlink(par,text,url):
 rel=par.part.relate_to(url,RT.HYPERLINK,is_external=True);he=OxmlElement('w:hyperlink');he.set(qn('r:id'),rel);run=OxmlElement('w:r');pr=OxmlElement('w:rPr');col=OxmlElement('w:color');col.set(qn('w:val'),'1A4F72');pr.append(col);run.append(pr);tx=OxmlElement('w:t');tx.text=text;run.append(tx);he.append(run);par._p.append(he)
for title,url,desc in links:
 z=para();hyperlink(z,title,url);z.add_run('  '+desc)
para('规范的官方登记链接和其余材料来源见S02与S23。部分规范全文仍不可读或尚未完成修订对照，故本书没有据此给出条款级符合性、材料许用值或签核。')

h('附录E 研究图和源数据关系')
para('研究总图与载荷图用于阅读定位。图本身不增加未经计算的性能结论。可编辑几何源、STEP、SVG、DXF与原始数表在各阶段工程包中保留。')
# Narrow height cap keeps source drawings legible as separately scaled pages.
for rel,cap in [('C2/T40/out/GA_C2.png','图E1 C2研究总图  参考尺寸与研究假设需按第2章区分'),('C4/T40/out/C4_load_study.png','图E2 C4载荷与接口敏感性  精确值以第5至7章数表为准')]:
 from PIL import Image
 im=Image.open(SRC/rel);w,hh=im.size;maxw=7;maxh=3.65;scale=min(maxw/w,maxh/hh)
 caption(cap);D.add_picture(str(SRC/rel),width=Inches(w*scale),height=Inches(hh*scale))

# Accessibility: declare document language and mark source figure descriptions.
settings=D.settings.element
lang=OxmlElement('w:themeFontLang');lang.set(qn('w:val'),'zh-CN');lang.set(qn('w:eastAsia'),'zh-CN');settings.append(lang)
for i,inline in enumerate(D.inline_shapes):
 inline._inline.docPr.set('descr',['C2轴向升降研究总图，参考尺寸并非制造公差','C4压力及驱动、接头敏感性图，详见正文数表'][i])
# Prevent font/color theme overrides on headings.
for nm in ['Title','Subtitle','Heading 1','Heading 2','Heading 3']:
 rp=styles[nm]._element.get_or_add_rPr();col=rp.find(qn('w:color'))
 if col is not None:
  for attr in ['themeColor','themeTint','themeShade']:col.attrib.pop(qn('w:'+attr),None)

path=OUT/'522-35.4179_工程计算书_工作稿_R0.docx';D.save(path)
metadata={'docx':str(path),'native_equations':len(D._element.xpath('.//m:oMath')),'tables':len(D.tables),'arithmetic_checks':len(checks),'source_files':len(manifest),'actual_valve_CFD':'NOT YET COMPUTED','actual_valve_FEA':'NOT YET COMPUTED','manufacturing_release':'HOLD'}
(OUT/'build_summary.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n');print(json.dumps(metadata,ensure_ascii=False,indent=2))
