from pathlib import Path
R=Path(__file__).resolve().parent;p=R/'build_calculation_book.py';s=p.read_text()
s=s.replace("default=Path('/workspace/shared/valve-cloud-20261006')", "default=Path('/workspace/shared/valve-cloud-recovered-20261006')")
s=s.replace("args=parser.parse_args(); OUT=args.output", "args=parser.parse_args()\nif args.refresh_sources:raise RuntimeError('Recovered R0 snapshot is frozen; register new R1 inputs separately')\nOUT=args.output")
s=s.replace("def load(rel): return json.loads((SRC/rel).read_text())", "def reject_nonfinite(v):raise ValueError('Non-finite input '+v)\ndef load(rel): return json.loads((SRC/rel).read_text(),parse_constant=reject_nonfinite)\ndef newload(rel):return json.loads((ROOT/'sources_new'/rel).read_text(),parse_constant=reject_nonfinite)")
s=s.replace("UPDATE=json.loads", """FRESH_STRUCT=newload('STRUCTURAL_NEW/summary.json');POISSON=newload('POISSON_NEW/results.json')
FRESH_CASES=[]
for rr in FRESH_STRUCT['rows']:
 name=f"disc_h{rr['target_h_mm']}_{rr['order']}"
 FRESH_CASES.append({key:newload('STRUCTURAL_NEW/cases/'+name+'/'+key+'.json') for key in ['model','run','results']})
for c in FRESH_CASES:c['result']=c.pop('results')
FRESH_PATCHES=[newload('STRUCTURAL_NEW/cases/pressure_patch_'+o+'/results.json') for o in ['C3D4','C3D10']]
from rebuilt_chapters import poisson_chapter, structural_chapter
UPDATE=json.loads""")
newchecks="""
# Fresh summary arithmetic only. Raw file binding is separately recorded in verification.
if FRESH_STRUCT['old_solver_data_restored'] is not False:raise ValueError('Lost structural results cannot be reused')
if len(FRESH_STRUCT['rows'])!=6 or len(POISSON['records'])!=3:raise ValueError('Fresh case counts')
prev={}
for row,c in zip(FRESH_STRUCT['rows'],FRESH_CASES):
 m=c['model'];rr=c['result'];label=rr['case']
 if rr['material_for_manufacturing'] is not False or rr['strength_pass'] is not False:raise ValueError('Structural release overclaim')
 check(label+'/analytic load',-.63*math.pi*114**2,m['analytic_Fz_N'])
 for a,b in [('maximum_nodal_displacement_mm','maximum_nodal_displacement_mm'),('strain_energy_Nmm','strain_energy_Nmm'),('raw_vm_peak_MPa','raw_von_mises_peak_MPa')]:check(label+'/'+a,row[a],rr[b])
 check(label+'/reaction sum',rr['positive_seat_force_N']+rr['negative_seat_force_N'],rr['reaction_force_N'][2],ab=1e-7)
 check(label+'/energy consistency',abs(rr['strain_energy_Nmm']-rr['half_external_work_Nmm'])/abs(rr['strain_energy_Nmm']),rr['energy_relative_error'],rel=2e-6,ab=1e-15)
 check(label+'/load relative error',abs(abs(row['load_Fz_N'])/abs(m['analytic_Fz_N'])-1),row['load_area_relative_error'])
 before=prev.get(row['order'])
 if before:
  for k in ['maximum_nodal_displacement_mm','strain_energy_Nmm','raw_vm_peak_MPa']:
   check(label+'/'+k+' change',100*(row[k]/before[k]-1),row[k+'_last_refinement_change_percent'])
 prev[row['order']]=row
E0=FRESH_CASES[0]['model']['E_MPa'];nu0=FRESH_CASES[0]['model']['nu'];G0=E0/(2*(1+nu0));la0=E0*nu0/((1+nu0)*(1-2*nu0))
check('Fresh elastic E identity',2*G0*(1+nu0),E0);check('Fresh elastic nu identity',la0/(2*(la0+G0)),nu0)
good=[r for r in POISSON['records'] if r['matches_positive_analytic_target']]
ratio=good[0]['l2_temperature_error_K']/good[1]['l2_temperature_error_K']
check('Poisson error ratio',ratio,POISSON['refinement_error_ratio']);check('Poisson two-level order',math.log(ratio)/math.log(2),POISSON['observed_two_level_order'])
for rr in POISSON['records']:
 check(rr['case']+'/cells',rr['n']**3,rr['cells'])
 check(rr['case']+'/flux balance',rr['numerical_outward_diffusive_gradient_flux_K_m3_per_s']-rr['volume_source_for_DeltaT_equation_K_m3_per_s'],rr['balance_error'],ab=1e-13)
 if rr['source_from_discrete_exact_field'] is not False:raise ValueError('Discrete manufactured source not accepted')
"""
s=s.replace("(ROOT/'arithmetic_verification.json').write_text",newchecks+"\n(ROOT/'arithmetic_verification.json').write_text")
s=s.replace('工作稿 R0','工作稿 R1 重建准备版').replace('_工作稿_R0.docx','_工作稿_R1_重建准备版.docx')
s=s.replace('证据截止 2026年10月6日','重建证据 2026年10月6日 21时后')
s=s.replace('当前已完成几何运动学、限定域海水物性、真实CAD受压面积、双侧压力载荷，以及丝杆和盖接头敏感性计算。','当前保留经重新核对的R0几何、物性、压力和驱动计算，并加入当前执行盘重新计算的六例阀瓣弹性参考解，以及真实原生Poisson立方体PDE基准。')
s=s.replace('实际整阀CFD与FEA  NOT YET COMPUTED','真实阀瓣弹性参考  新六例已算 接触HOLD\\n实际阀域流场及整阀装配FEA  NOT YET COMPUTED')
s=s.replace('C5只接入已形成的材料卡及独立求解器基准。','新增证据来自重建后的结构及Poisson新执行包；失盘R1的结果与审查状态均未继承。')
s=s.replace("['10 CFD','C2网格和严格预检查、方腔标准算例'", "['10 CFD','R0归档基准及新原生Poisson立方体PDE'")
s=s.replace("['11 FEA','拉伸标准算例和单位一致性','本阀应力、变形、接触、预紧、强度裕量']", "['11 FEA','六个新阀瓣弹性算例与力能量核算','单边接触、整阀、预紧和强度评定']")
s=s.replace('C5为本书制作时的工作证据快照，未声称具有冻结提交。','恢复后的R0文件逐项与其冻结散列核对；本版新结构和PDE来源重新绑定实际文件。原始网格字节相同不意味着失盘前修复、网格门、算子记录或逐页QA仍有效。R1保持准备状态，最终来源尚待对齐。')
a=s.index("table(['阶段','版本标识','本书用途']");b=s.index('\n',a)
s=s[:a]+"para('版本定位：原始资料4222b3d4df24；C2几何2566bdee5b52；C3接口31662e66；C4载荷79887e8e6fbf。完整来源散列见基线与新来源清单；重建后的新运行时间和脚本身份分别记录。')"+s[b:]
needle="table(['编号','量或条件','数值','性质','依据'],inputs"
s=s.replace(needle,"""inputs.extend([
['I31','新结构载荷','入口0 出口0.63 MPa(g)','A','反向工况；N01、N02'],
['I32','结构替代弹性','E114000 MPa ν0.32','C/A','C95800参考；S23、N02'],
['I33','阀座支承','r100至114 mm 底环Uz=0','A','刚性无摩擦双边；N02'],
['I34','结构尺寸场','h8/6/4 mm','A','非实际最大边长；N01'],
['I35','单元阶次','C3D4与直边C3D10','A','相同分片几何；N03'],
['I36','Poisson参考尺度','L=1 m T_ref=1 K','A','制造解；N06、N07'],
['I37','扩散率','DT=1 m²/s','A','原生稳态标量方程；N07'],
['I38','正确源项','Su=−6 K/s','D/A','目标ΔT=+6；N06'],
['I39','PDE基准网格','5³与10³正交立方体','A','不是实际阀域；N06'],
['I40','实际阀域新证据','网格/PDE待当前结果对齐','U','不继承失盘MeshOK'],
])
"""+needle)
s=s.replace('真实阀网格正在修复；更新必须含修复几何/网格散列、严格预检、求解设置、日志与监测曲线，不能只替换图片。','执行盘重建后，新的实际阀域网格/修复/PDE正在重新建立证据；本版不继承失盘前MeshOK。新独立Poisson基准见第10.6至10.9节，不能替代阀域验证。')
s=s.replace("h('10 4 标准方腔算例与阀性能分开登记',2)","h('10 4 R0归档方腔算例与阀性能分开登记',2)")
s=s.replace("h('11 结构计算和真实FEA状态')", "poisson_chapter(globals(), POISSON)\n\nh('11 结构计算与新阀瓣弹性研究')")
a=s.index("h('11 3 待计算结构结果'");b=s.index("h('12 规范适用性和未满足验收要求')",a)
s=s[:a]+"structural_chapter(globals(), FRESH_STRUCT, FRESH_CASES, FRESH_PATCHES)\n\n"+s[b:]
s=s.replace("'M13':'部分完成：标准基准；真阀待算'", "'M13':'部分完成：新结构及立方体PDE；阀流场待算'")
s=s.replace('M13的工具许可/标准算例已推进','M13新增结构六例与立方体Poisson基准已推进')
s=s.replace('本书由build_calculation_book.py从sources快照中的JSON/日志生成。','本书由build_calculation_book.py与rebuilt_chapters.py从R0来源及sources_new的新快照生成。失盘R1没有被恢复为计算证据；旧审查“通过”未复用。')
s=s.replace('本版独立算术检查共','本版R0和新来源摘要独立算术检查共')
s=s.replace('该状态不包括CAD重建、求解器运行或工程验收。','本生成器不运行CAD或求解器；第10章与第11章的真实新运行从单独结果包追溯，工程验收仍未成立。')
s=s.replace('需要刷新来源时使用--repo指定仓库副本并显式加--refresh-sources。刷新只复制来源到计算书目录，生成器不改模型、运行目录、冻结清单或求解文件，也不安装软件或访问网络。','本版R0基线禁止原地刷新；snapshot_new_sources.py只从指定新结果包读取并核对文件散列，再复制到sources_new。来源和代码修改后保存同一Library检查点的新版本；最终仍需重新渲染和逐页QA。生成器不改模型或求解输入，也不安装软件。')
newindex="""
h('附录C1 重建后新来源索引',2)
para('以下N编号引用当前新执行数据。相对路径以sources_new为根；六例和两压力块的model/run/results/冻结清单逐一保存。new_source_manifest.json记录全部新来源的原位置和SHA256，verification/fresh_source_hash_bindings.json记录本次只读绑定检查。')
table(['编号','实际文件或分组','依据'],[
['N01','STRUCTURAL_NEW/summary.json 与summary.csv','六例新运行数值汇总'],
['N02','STRUCTURAL_NEW/cases/各例model/run/results/ FROZEN_MANIFEST.json','各次模型、原始输出绑定、运行时间与冻结身份'],
['N03','STRUCTURAL_NEW/scripts/structural.py','新结构网格、载荷和后处理实现'],
['N04','STRUCTURAL_NEW/scripts/freeze.py','冻结创建与只读验收分离'],
['N05','STRUCTURAL_NEW/evidence/fresh_case_gate_tests.json 与extra_tampering_tests.json','普通/优化模式正负例'],
['N06','POISSON_NEW/results.json','三个新原生PDE结果及哈希'],
['N07','POISSON_NEW/README.zh-CN.md 与各例字典','符号、单位、求解设置'],
['N08','POISSON_NEW/scripts/poisson_prepare.py 与poisson_verify.py','准备和正交通量/误差核算'],
['N09','POISSON_NEW/source-excerpts/','原生方程与源实现的来源节录'],
['N10','verification/fresh_source_hash_bindings.json','本次实际文件重新绑定，非失盘状态复用'],
],[.6,4.4,2.0],8.8)
"""
s=s.replace("h('附录D 外部一级来源索引')",newindex+"\nh('附录D 外部一级来源索引')")
s=s.replace("'actual_valve_FEA':'NOT YET COMPUTED'", "'new_disc_FEA':'SIX_FRESH_BILATERAL_ELASTIC_CASES_CONTACT_HOLD','new_Poisson':'INDEPENDENT_ORTHOGONAL_CUBES_ONLY','whole_valve_FEA':'NOT YET COMPUTED','source_alignment':'PENDING'")
s=s.replace("'native_equations':len", "'revision':'R1_REBUILT_PREPARATION','native_equations':len")
p.write_text(s)
print('Integrated fresh chapters')
