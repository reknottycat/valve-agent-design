import math

def add(g,plan,mesh):
 h,para,eq,table,caption,f,sub,sup,frac,sqrt,group=[g[k] for k in ['h','para','eq','table','caption','f','sub','sup','frac','sqrt','group']]
 h('10 10 当前网格修复与已复核绑定',2)
 para('本节采用新执行的v2网格复核，固定清单SHA256为98976d5277a55922开头，完整值见N12。旧验收可误接收已改拓扑和旧日志的漏洞已修复；新验收与独立复核通过，原网格数据保持不变。原始HXT网格经原生转换后，有界合并7对凸相邻四面体，再合并2组同单元精确共面壁面。 [N12]')
 table(['当前新测量','结果','解释'],[
 ['单元 / 点 / 面',f"{mesh['cells']:,} / {mesh['points']:,} / {mesh['faces']:,}",'本版已绑定网格'],
 ['原生网格体积 m³',f(mesh['native_total_volume_m3'],12),'修复前后原生体积文本一致'],
 ['最大非正交角 / >70°面',f(mesh['maximum_nonorthogonality_degrees'],6)+'° / '+str(mesh['faces_over_70_degrees']),'54项警告保留'],
 ['最大偏斜度',f(mesh['maximum_skewness'],8),'检查量不是流动误差'],
 ['最小单元行列式',f(mesh['min_cell_determinant'],10),'本次原生日志记录'],
 ['普通 / 优化模式测试',str(mesh['normal_and_optimized_tests'])+'项','20项几何加11项绑定/失败输出测试'],
 ['新原生检查与绑定','Mesh OK','固定清单、日志及独立复核一致']], [2.1,2.5,2.4],9.0)
 conv=mesh['source_native_conversion_note']
 para(f'Gmsh到原生格式的坐标并非位级完全相等：{conv["conversion_differing_scalars"]}个标量发生不超过{conv["conversion_max_absolute_difference_m"]:.5e} m的差异，最大{conv["conversion_max_ulp"]:.0f} ULP；点索引对应和物理边界身份已核对。之后的单元合并与共面壁面合并保持点坐标不变。不能把后两步的严格保持表述扩大成全部转换链字节一致。')
 para('7对单元合并只移除内部公共面，外边界三角面的取向、顺序和patch归属核对保持；共面合并另核对86092个未动边界面、两组四边形外缘、0平面偏差及内部连接不变。完整日志仍保留时间选择告警和非致命UCX VFS诊断。v2在normal及−O下各31项通过；本书再核107项包载荷字节。网格与来源绑定通过不代表PDE精度、流动收敛或工程合格。')
 h('10 11 已复算的研究输入仍未求解',2)
 state=plan['selected_study_property_state'];nu=state['kinematic_viscosity_m2_s'];rho=state['density_kg_m3'];D=plan['nominal_diameter_m'];A=plan['nominal_circle_area_m2']
 para('当前流动计划状态为PLANNED_NOT_RUN。物性重新核对在20°C、盐度35 g/kg、0.101325 MPa(abs)：ρ=1024.9109328963 kg/m³，μ=0.001076628925253 Pa·s，ν=1.050460962701×10⁻⁶ m²/s。没有设计压力修正，−2°C相态/物性仍未闭合。以下数值是研究输入和名义算术，不是已得到的CFD输出。 [N11]')
 eq('10-16','Re = ',frac('U D','ν'),' ;  ',sub('Q','nom'),' = U',frac('πD²','4'),' ;  ',sub('q','dyn'),' = ',frac('ρU²','2'))
 eq('10-17',sub('U','Re10'),' = ',frac('10ν','D'),f' = {10*nu/D:.10g} m/s')
 eq('10-18',sub('Q','nom,U1'),' = 1 × ',frac('π × 0.2²','4'),' = 0.03141592654 m³/s = 113.0973355 m³/h')
 table(['计划情景','入口面速 m/s','名义Re','名义圆口Q m³/h','动压尺度 Pa'],[[r['id'].replace('laminar_diagnostic_','').replace('speed_sensitivity_','U='),f"{r['inlet_fixed_face_speed_m_s']:.8g}",f(r['nominal_D_Reynolds_from_face_speed'],3),f"{r['nominal_circle_flow_m3_h']:.10g}",f"{r['dynamic_pressure_from_face_speed_Pa']:.9g}"] for r in plan['cases']],[1.35,1.25,1.35,1.7,1.35],8.8)
 para('Re10固定全开算例用于低Re数值诊断。0.5/1/2 m/s为自主研究敏感性，不是已知额定流量或现场运行速度；对应的高Re工况还需湍流及近壁模型验证。输入采用入口固定面速，名义Q按理想DN200圆口计算；实际网格通量必须另积分，不能把名义Q改名为已测求解通量。')
 h('10 12 开度压力与阻力系数的边界',2)
 para('几何固定为阀瓣升程57 mm、丝杆退开57 mm，并在研究中视为受约束保持全开。这不预测自然升程、运动平衡或关闭过程；不能因低Re数值结果存在就推断真实阀瓣在该流速下会自行打开。')
 para('入口/出口分别在x≈−0.6/1.2 m，两侧数值直管各约3D。端口到端口压差包含延长直管和发展/受扰流动损失，不自动等于单独阀本体ζ。需要声明静压或总压、测压截面、实际参考速度及直管修正，才能与原图注24的≤6要求建立可比性；当前该要求仍未评定。')
 para('0.63 MPa(g)是独立结构研究载荷，不是施加的流动压降。拟议不可压simpleFoam的p单位为m²/s²，转Pa需乘ρ；出口轴线上绝压参考101325 Pa与归一化p=0分开记录。恒密度流动方程不显式含重力，后续竖向压力力积分仍需明确静水头重构和接触面的干湿边界，不能直接冒充第5章静力载荷。')
 table(['真实流动输出','当前数据'],[['四个情景的实际网格通量','null / NOT_RUN'],['压降','null / NOT_RUN'],['ζ、Kv、Cv','NOT YET COMPUTED'],['阀域PDE误差和受控网格敏感性','等待本次新执行证据'],['自由阀瓣运动、水锤、空化、泄漏','未计算']],[3.65,3.35],9.1)
 para('启动实际流场前还需当前网格散列与严格检查、新原生场/面探针、非零源阀域Poisson及相关敏感性，以及实际输入/软件指纹。启动后分别检查残差、流量压降稳定性、守恒、有界性和模型近壁要求。规划表不构成已求解记录。')
