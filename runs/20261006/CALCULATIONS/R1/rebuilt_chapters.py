"""Fresh R1 chapters. Inputs are new source snapshots, never lost-workspace values."""
import math

def helpers(g):return [g[k] for k in ['h','para','eq','table','caption','f','sub','sup','frac','sqrt','group']]

def poisson_chapter(g,d):
 h,para,eq,table,caption,f,sub,sup,frac,sqrt,group=helpers(g)
 h('10 6 新执行的原生Poisson解析基准',2)
 para('本节采用当前重建环境重新执行的原生laplacianFoam结果，运行记录时间为'+d['fresh_run_utc']+'。在独立单位立方体上，从内部零初值实际求解PDE；不是把解析场直接送入离散算子，也不是恢复旧日志。两张正交网格和一个错源符号负例均有新的输入、求解后T场、残差日志和散列。 [N06至N09]')
 table(['证据层级','本版有证据的内容','不能外推的内容'],[
 ['R0归档软件基准','历史拉伸与方腔记录','重建环境的所有功能均已验证'],
 ['新Poisson基准','原生PDE求解、两级误差阶、错源负例','非正交阀域、真实阀流场'],
 ['新阀瓣结构','六个重新运行的弹性参考算例','真实单边接触或整阀强度通过'],
 ['实际阀域','新网格v2已复核；阀域PDE未计算','失盘前MeshOK和算子记录不可沿用']], [1.4,2.8,2.8],9.0)
 h('10 7 解析方程符号单位和离散输入',2)
 para('取0≤x,y,z≤L，L=1 m，T_ref=1 K，标量温度解析场如下。T只是制造解的变量，不表示本阀的实际热工载荷；本节未求材料温度场或热应力。')
 eq('10-10',sub('T','exact'),' = ',sub('T','ref'),frac(group(sup('x','2'),' + ',sup('y','2'),' + ',sup('z','2')),sup('L','2')))
 eq('10-11',sup('∇','2'),'T = ',frac(group('6',sub('T','ref')),sup('L','2')),' = 6 K/m²')
 eq('10-12','−∇·(',sub('D','T'),'∇T) = ',sub('S','u'),' ;  ',sub('D','T'),' = 1 m²/s ;  ',sub('S','u'),' = −6 K/s')
 para('原生v1912代码的稳态符号为−div(DT grad T)=Su，因此Su必须取−6 K/s，才能得到目标ΔT=+6 K/m²。source独立来自连续解析式，没有用离散解析场的Laplacian倒算一个恰好匹配的源。 [N07至N09]')
 table(['设置','实际取值'],[['内部初值','统一0 K；不是解析解初始化'],['边界','六面fixedValue；各面中心代入解析温度'],['扩散与时间项','DT=1 m²/s；ddtSchemes=steadyState'],['Laplacian离散','Gauss linear corrected'],['线性求解','PCG/DIC；tolerance 10⁻¹²；relTol=0'],['外循环设置','nNonOrthogonalCorrectors=2；残差停止值10⁻¹¹'],['实际网格','5³与10³规则正交单元；非正交角0°']],[1.65,5.35],9.1)
 para('结果目录标记的latest_time=2属于该稳态求解的输出索引，不据此声称进行了2 s物理瞬态分析。独立通量复核只适用于本节正交规则立方体的面值、owner值、半单元法向距离和面积。')
 h('10 8 实际误差与两级观测阶',2)
 good=[r for r in d['records'] if r['matches_positive_analytic_target']]
 table(['网格','单元数','温度E₂ K','温度E∞ K','PCG累计迭代','外向梯度通量 K·m³/s'],[[str(r['n'])+'³',r['cells'],f"{r['l2_temperature_error_K']:.12g}",f"{r['linf_temperature_error_K']:.12g}",r['linear_iterations_total'],f"{r['numerical_outward_diffusive_gradient_flux_K_m3_per_s']:.13g}"] for r in good],[.65,.75,1.3,1.3,1.15,1.85],8.7)
 eq('10-13',sub('E','2,V'),' = ',sqrt(frac(group('Σ ',sub('V','i'),sup('eᵢ','2')),group('Σ ',sub('V','i')))),' ;  ',sub('E','∞'),' = max |',sub('e','i'),'|')
 eq('10-14',sub('p','obs'),' = ',frac(group('ln(',sub('E','5'),'/',sub('E','10'),')'),'ln 2'),' = ',frac('ln(0.0100/0.0025)','ln 2'),' ≈ 2.000000')
 para(f'两级L2误差比为{d["refinement_error_ratio"]:.12f}，观测阶为{d["observed_two_level_order"]:.12f}，与本规则网格上的二阶趋势一致。只有两级网格，不据此构造完整三网格GCI、渐近区证明或本阀误差界。误差是离散解与解析单元中心值的差，不是线性残差。')
 eq('10-15',sub('Q','grad'),' = ∮ ',sub('D','T'),'∇T·n dA = −∫ ',sub('S','u'),' dV = 6 K·m³/s')
 para('Q_grad定义为+DT∇T的域外面积积分，单位K·m³/s；它不是采用负号定义的物理导热通量，也不是以W计的热流、m³/s海水流量或kg/s质量流率。两个正确算例的通量与目标体积源之差约为+2.35×10⁻¹²和−7.90×10⁻¹³ K·m³/s。')
 h('10 9 错误源符号负例',2)
 wrong=next(r for r in d['records'] if not r['matches_positive_analytic_target'])
 table(['负例指标','实际结果'],[['源设置','Su=+6 K/s；求解的ΔT为−6 K/m²'],['L2 / L∞温度误差',f(wrong['l2_temperature_error_K'],9)+' / '+f(wrong['linf_temperature_error_K'],9)+' K'],['外向梯度通量',f(wrong['numerical_outward_diffusive_gradient_flux_K_m3_per_s'],12)+' K·m³/s'],['相对其实际方程的通量平衡差',f"{wrong['balance_error']:.5e} K·m³/s"],['末次线性残差',f"{wrong['linear_solver_calls'][-1]['final']:.5e}"],['对目标ΔT=+6的结论','按预期拒绝；不是目标问题通过']],[2.45,4.55],9.0)
 para('负例同样把线性残差降到约10⁻¹²，并与它实际求解的错误符号源保持代数平衡，但温度场和通量不符合目标解析问题。这一结果把“求解器收敛”“离散守恒”和“正确目标方程”三项分开验证。')
 from current_flow_chapter import add
 add(g,g['FRESH_FLOW_PLAN'],g['FRESH_MESH_ACCEPTANCE'])

def structural_chapter(g,s,cases,patches):
 h,para,eq,table,caption,f,sub,sup,frac,sqrt,group=helpers(g)
 rows=s['rows'];by={(r['order'],r['target_h_mm']):r for r in rows}
 h('11 3 当前执行盘重新计算的真实阀瓣',2)
 para('本节六例均来自当前执行盘的新运行，汇总生成时间为'+s['fresh_assembled_utc']+'。先逐个核对冻结清单、原始INP/DAT、运行脚本快照、模型和上游材料/STEP散列，再使用重新解析DAT的报告。数值恰与历史线索相符时，也以本次实际文件为依据，不使用失盘稿的“通过”状态。 [N01至N05、N10]')
 para('导入C2 check_closed阀瓣与导向的同一STEP实体，来源SHA256为176d0f389e188b339132d7ec05e9e59cdd8861c5138e0839900ba653d0e85ee9。阀瓣中心(300,0) mm，底面/顶面z=22/36 mm，外半径120 mm；导向内/外半径20/26 mm，延伸到z=116 mm。仅把底面在r=100和114 mm处分区，分割前后体积保持约702711.444755 mm³。')
 h('11 4 材料约束和压力载荷代入',2)
 m=cases[0]['model'];E=m['E_MPa'];nu=m['nu'];p=m['pressure_MPa'];G=E/(2*(1+nu));la=E*nu/((1+nu)*(1-2*nu))
 eq('11-1',sub('F','z,CAD'),' = −pπ',sup(sub('R','seal'),'2'),' = −0.63π × 114² = −25 721.727019 N')
 para('采用N-mm-MPa一致单位，+Z向上。入口0、出口0.63 MPa表压；底面r≤114 mm为无出口压力区，其余外表面为出口湿面，包括阀瓣外缘、导向外壁/顶面、孔壁和孔底。实际施加牵引t=−pn，包括合力近零的径向载荷。式11-1用于核对面载荷积分，未再叠加同值集中力。')
 table(['输入','本次值和边界'],[['参考材料','C95800连续铸造替代；E=114000 MPa，ν=0.32；无许用值'],['支承','底面100≤r≤114 mm全部节点Uz=0；刚性无摩擦双边约束'],['平面内约束','中心底点Ux=Uy=0；内座环+X接缝点Uy=0；只消除三个刚体模态'],['未建模','真实座柔度/预紧/摩擦、杆和导向接触、重力、流体惯性、温度依赖'],['制造材料与强度状态','未选定制造材料；不是原俄牌号；无强度通过']],[1.45,5.55],9.1)
 eq('11-2','K u = F ;  σ = 2Gε + ',sub('λ','e'),' tr(ε) I')
 eq('11-3','G = ',frac('E','2(1+ν)'),f' = {G:.6f} MPa ;  ',sub('λ','e'),' = ',frac('Eν','(1+ν)(1−2ν)'),f' = {la:.6f} MPa')
 para('G和λ_e是由本参考E、ν得到的各向同性弹性常数，ε为小应变，I为单位张量。它们不增加材料供货状态、强度或全温区资格。')
 h('11 5 离散载荷与新压力块基准',2)
 eq('11-4','A n = ',frac('1','2'),' [(',sub('x','2'),'−',sub('x','1'),')×(',sub('x','3'),'−',sub('x','1'),')] ;  ',sub('f','i'),' = ∫ ',sub('N','i'),' (−pn) dA')
 para('面外法向与相邻四面体的对顶节点方向核对。线性三节点面每角节点分得均匀总面力1/3。直边二次六节点面采用角点N_i=L_i(2L_i−1)及中边N_ij=4L_iL_j，积分权重为[0,0,0,1/3,1/3,1/3]，不能将总面力平均分给六个节点。C3D10中边节点是同一分片网格的共享边中点，未投影回曲面CAD。')
 eq('11-5','a = ',frac(group('5+3',sqrt('5')),'20'),' ;  b = ',frac(group('5−',sqrt('5')),'20'))
 para('C3D10四个积分点为(a,b,b,b)的重心坐标排列，节点顺序为顶点1/2/3/4，再接边12/23/31/14/24/34的中点。当前后处理从节点位移重新构造应变/应力，避免仅相信缓存场或节点排列假定。')
 para('两个新压力块算例为10 mm立方体、0.63 MPa压应力，解析Szz=−0.63 MPa、顶部Uz=−pL/E=−0.0000552631579 mm、弹性能0.001740789474 N·mm。最大节点位移模还含横向泊松变形，不等同Uz。')
 table(['新压力块','单元数','位移相对误差','应力相对误差','力平衡相对误差'],[[r['order'],r['elements'],f"{r['patch_validation']['displacement_relative_error']:.4e}",f"{r['patch_validation']['stress_relative_error']:.4e}",f"{r['force_equilibrium_relative_error']:.4e}"] for r in patches],[1.3,.9,1.6,1.6,1.6],8.9)
 h('11 6 几何离散误差与压力合力',2)
 linear=[r for r in rows if r['order']=='C3D4']
 table(['目标h mm','四面体数','C3D4/C3D10节点','最大角点边 mm','最小minSICN','体积相对差 %'],[[r['target_h_mm'],f(r['elements'],0),f"{r['nodes']:,}/{by[('C3D10',r['target_h_mm'])]['nodes']:,}",f(r['max_corner_edge_mm'],4),f(r['minSICN'],4),f(100*r['mesh_volume_relative_error'],5)] for r in linear],[.7,1.0,1.8,1.15,1.1,1.25],8.7)
 table(['目标h mm','面载荷Fz N','解析Fz N','合力相对误差绝对值 %'],[[r['target_h_mm'],f(r['load_Fz_N'],6),f(m['analytic_Fz_N'],6),f(100*r['load_area_relative_error'],6)] for r in linear],[.9,2.0,2.0,2.1],9.0)
 para('h是Gmsh尺寸场参数，不是实际最大四面体边长。两阶次在同一h下采用相同分片几何体积；均按实际面片积分压力，没有为匹配解析合力而缩放载荷。相对面积误差随细化下降，不能把该误差当成应力误差界。')
 h('11 7 最大节点位移能量与应力敏感性',2)
 eq('11-6',sub('u','node,max'),' = ',sub('max','i'),sqrt(group(sup(sub('u','ix'),'2'),'+',sup(sub('u','iy'),'2'),'+',sup(sub('u','iz'),'2'))))
 table(['阶次','h mm','最大节点位移 mm','弹性能 N·mm','原始von Mises峰 MPa'],[[r['order'],r['target_h_mm'],f(r['maximum_nodal_displacement_mm'],7),f(r['strain_energy_Nmm'],5),f(r['raw_vm_peak_MPa'],5)] for r in rows],[1.0,.7,1.9,1.6,1.8],9.0)
 para('最大值严格限定在网格节点，不宣称完成二次插值场内部极值搜索。C3D4应力为单元值，C3D10应力为积分点值；表中原始峰未进行节点外推或光顺。')
 table(['h6到h4变化','C3D4 %','C3D10 %'],[[label,f(by[('C3D4',4)][k+'_last_refinement_change_percent'],5),f(by[('C3D10',4)][k+'_last_refinement_change_percent'],5)] for label,k in [('最大节点位移','maximum_nodal_displacement_mm'),('弹性能','strain_energy_Nmm'),('原始应力峰','raw_vm_peak_MPa')]],[3.0,2.0,2.0],9.1)
 para('C3D4位移和能量最后一步分别改变约24.39%和23.48%，尚未收敛；C3D10分别约1.83%和2.15%，仅显示全局响应趋稳。C3D10原始峰仍增加约25.63%，不得用32.1953 MPa给强度裕量。三张不规则网格不构成已验证渐近序列，没有形式化误差上界。')
 table(['C3D10 h mm','内部区域体积均值 MPa','内部区域体积95分位 MPa'],[[r['target_h_mm'],f(r['interior_vm_volume_mean_MPa'],6),f(r['interior_vm_volume_p95_MPa'],6)] for r in rows if r['order']=='C3D10'],[1.4,2.8,2.8],9.1)
 para('固定内部诊断区为阀瓣厚度内30≤r≤85 mm。内部应力统计变化较小，不代表座支承边缘或导向尖锐交界峰值收敛，也不能替代规范应力分类、许用值和疲劳数据。')
 h('11 8 反力力矩与能量核算',2)
 eq('11-7','R = RF − ',sub('F','applied'),'  at constrained DOFs')
 eq('11-8','Σ(F+R)=0 ;  Σ[(x−',sub('x','0'),')×(F+R)]=0')
 eq('11-9',sub('U','elastic'),' = ',frac('1','2'),'∫ σ:ε dV = ',frac('1','2'),'Σ(F·u)')
 para('当前CalculiX RF字段包含施加的节点力与支反力；在约束自由度取RF−F_applied才是所声明支承模型的反力。另核对自由自由度残差、关于(300,0,22) mm的力矩，以及从原始DAT重建的应变、应力和能量。')
 table(['阶次/h','施加Fz N','支承Rz N','力平衡相对差','能量与功相对差'],[[c['result']['order']+'/'+str(c['result']['target_h_mm']),f(c['result']['applied_force_N'][2],6),f(c['result']['reaction_force_N'][2],6),f"{c['result']['force_equilibrium_relative_error']:.4e}",f"{c['result']['energy_relative_error']:.4e}"] for c in cases],[1.0,1.7,1.7,1.3,1.3],8.7)
 fine=next(c['result'] for c in cases if c['result']['order']=='C3D10' and c['result']['target_h_mm']==4)
 para(f'最细C3D10：弹性能{fine["strain_energy_Nmm"]:.9f} N·mm，外力半功{fine["half_external_work_Nmm"]:.9f} N·mm，相对差{fine["energy_relative_error"]:.4e}。这些是计算完整性检查，不证明双边支承可解释真实密封接触。')
 h('11 9 单边接触解释仍为HOLD',2)
 lin=next(c['result'] for c in cases if c['result']['order']=='C3D4' and c['result']['target_h_mm']==4)
 table(['最细网格诊断','C3D4','C3D10'],[
 ['支承节点数',lin['seat_node_count'],fine['seat_node_count']],
 ['显著负反力节点数',lin['negative_seat_nodes'],fine['negative_seat_nodes']],
 ['向下负节点反力合计 N',f(lin['negative_seat_force_N'],6),f(fine['negative_seat_force_N'],6)],
 ['向上正节点反力合计 N',f(lin['positive_seat_force_N'],6),f(fine['positive_seat_force_N'],6)],
 ['二次中边显著负节点数','不适用',fine['negative_seat_midside_nodes']],
 ['二次中边负反力合计 N','不适用',f(fine['negative_seat_midside_force_N'],6)]],[3.0,2.0,2.0],9.0)
 para('全环Uz=0是能“拉住”阀瓣的双边约束。线性面形函数非负，显著负法向一致节点反力不能由处处非负压缩牵引产生，因此C3D4序列不能当作只承压的落座解。二次角点形函数可变号，单看角点负值不够；本次还识别出1216个负中边节点，合计约−28665.19 N。中边形函数4L_iL_j非负，这进一步支持当前约束的单边接触HOLD。')
 para('这里没有恢复可信的连续接触压力分布，也没有完成真实座柔度、间隙、预紧和杆/导向相互作用。负节点反力完整保留，未剪裁为零；HOLD不等于证明实物泄漏或强度失效。本节理想双边反力不能回填第5章的实际接触反力未知项。')
 h('11 10 新证据门控与剩余整阀工作',2)
 para('当前结构代码用显式异常进行验收，普通与优化模式分别检查；冻结清单创建和只读验收分开，禁止原地重建基准。已做原始DAT篡改、应力翻倍、缓存更改、假通过标记与清单绑定负例。每份结果绑定本次INP、DAT、模型、网格、运行记录和脚本身份，不把历史运行归于修改后的脚本。 [N03至N05、N10]')
 table(['对象','当前状态','仍缺内容'],[
 ['阀瓣及导向','六个新弹性参考解已计算','单边接触及相关应力指标收敛'],
 ['阀体与阀盖','NOT YET COMPUTED','完整承压映射、外载、材料和网格'],
 ['螺栓与垫片','NOT YET COMPUTED','预紧、刚度、松弛和残余夹紧'],
 ['丝杆组合强度/屈曲','NOT YET COMPUTED','实际根径、弯扭和支承长度'],
 ['实际密封接触与泄漏','HOLD 未完成可信评定','单边接触、装配和实物试验'],
 ['许用比较和制造放行','未评定 / HOLD','控制材料、规范条款与工程审签']],[2.15,2.05,2.8],9.0)
