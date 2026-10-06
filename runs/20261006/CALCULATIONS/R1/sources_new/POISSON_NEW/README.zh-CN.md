# 新执行盘：原生laplacianFoam实际Poisson制造解

状态：在独立5³/10³单位立方体上完成**真正的PDE求解**与解析收敛检查。不是旧日志恢复，也不是本阀域验收。

## 可运行入口

先source当前基础环境：`source /workspace/shared/valve-solvers-rebuilt-20261006/env.sh`。

准备：`python3 scripts/poisson_prepare.py`

原生求解：`laplacianFoam -case poisson-newrun/n5_right`，再运行n10_right及n5_wrong_sign。

验证：`python3 scripts/poisson_verify.py`

脚本使用显式RuntimeError检查，不依赖可能被-O关闭的assert。首次字典层级错误的失败日志保留为log.initial-placement-error；最终配置已经原生实测成功。

## 解析问题、符号和单位

L=1m，T_ref=1K；T_exact=T_ref[(x/L)²+(y/L)²+(z/L)²]，故ΔT=6K/m²。

- 内部初值为0，未从解析场初始化
- 六个壁面全部fixedValue，取解析式在各面中心的值
- DT=1m²/s；ddtSchemes=steadyState；laplacianSchemes=Gauss linear corrected
- SIMPLE设置nNonOrthogonalCorrectors=2；本次实际网格正交，checkMesh非正交角0°
- PCG/DIC，tolerance=1e−12，relTol=0；SIMPLE残差停止值1e−11

原生v1912源码方程为：ddt(T)−div(DT grad T)=fvOptions(T)。因此本稳态问题必须使用Su=−6K/s，才得到ΔT=+6K/m²。

正确字典位于constant/fvOptions：analyticalSource的type为scalarSemiImplicitSource；其scalarSemiImplicitSourceCoeffs内部包含selectionMode all、volumeMode specific、injectionRateSuSp { T (-6 0); }。selectionMode放在外层会被此版本拒绝，不能照搬不同版本写法。

源始终是独立解析常数6。没有计算离散解析场的laplacian来制造“恰好通过”的源。

## 新执行结果

| 网格 | 单元数 | T误差L2(K) | T误差L∞(K) | 累计PCG迭代 | 数值边界通量 |
|---|---:|---:|---:|---:|---:|
| 5³ | 125 | 0.01000000000004 | 0.01000000000095 | 11 | +6.00000000000235 |
| 10³ | 1000 | 0.00249999999999 | 0.00250000000185 | 18 | +5.99999999999921 |

误差比4.000000000026，两个网格的观测阶2.000000000009。两个正例均SIMPLE外循环2次收敛，最终线性残差约8×10⁻¹³。离散通量与体积解析源的差分别约2.35e−12和−7.90e−13。

通量在此指+DT grad(T)的域外数值面积积分，单位K·m³/s，不是采用负号定义的物理导热通量。核算采用这个**正交规则立方体**的面值、owner求解值、半单元法向距离及面积，与其有限体积边界通量一致。它不是任意非正交网格的通用通量程序。

## 保留的符号负例

将Su改为+6，原生求解器仍收敛到约8×10⁻¹³残差，但求解的是ΔT=−6：数值域外通量≈−6，T误差L2≈0.322172、L∞≈0.682277。验证器明确拒绝它与目标ΔT=+6相符。这证明仅“残差收敛”不能作为目标方程通过证据。

## 来源与边界

原生二进制来自本次重新下载并验证签名索引/包SHA256的Debian OpenFOAM 1912.200626-3+b1。源码来自官方Debian源码包，固定SHA256为c75ca0f04cc4f49708296c1926cbde9d0138b3fef298fed54270dfe29e2df404，相关方程与source实现原样附于source-excerpts。

实际原始输入、输出T、残差日志、初次配置失败及负例均随包保存，机器可读摘要为results.json。没有修改原生库或主机安全设置。stock postProcess的sha1缺陷与UCX VFS诊断已经在新盘重现；本求解不使用失败的functionObjects路线。

当前只证明该版本原生Poisson路径在上述正交基准和解析源下可用。非正交阀域的PDE误差、网格收敛、边界一致性、v1–v4辅助工具重建与CELS补丁仍须各自重新建立证据，不能由本包外推。
