# C2研究阶段文件包

先读 `../T40/out/C2_design_review.pdf`（五页中文报告），再看
`../T40/out/GA_C2.pdf`（A3关闭/开启剖视图）。

可打开的设计文件：

- `../T40/out/C2_closed.FCStd`、`C2_open.FCStd`：FreeCAD中性几何快照
- `../T12/out/closed/assembly.step`、`open/assembly.step`：通用CAD装配
- `../T40/out/GA_C2.svg`、`GA_C2_section.dxf`：矢量研究图
- `../T40/out/BOM_study.csv`、`BOM_study.json`：七个主要简化部件的研究BOM
- `../T11/parameters.json`、`../T12/build_lift_model.py`：可修改并重建的参数化主数据
- `../T23/out/fluid_open_si.msh`：来自同一主模型的米制网格
- `../T15/calc_results.json`：不预先选择设计压力的归一化计算

本包包含兄弟目录 `CLOUD/T04`，供C2验证脚本导入共同守卫。
完整复跑入口为 `runs/20261006/C2/verify_available.sh`；依赖与命令见仓库README。
脚本不会调用CFD/FEA求解器，也不会推送GitHub。

这是一份已验证几何阶段的研究包，不是最终制造设计。
设计目标仍在推进，尚欠受控工况和材料、阀盖连接与紧固密封、完整阀杆/螺母/导向细节、
公差、标准全文、求解器基准、本阀计算及工程/实物验收。
同步和求解器执行因工具审批取消而暂停；本包没有把这些写为完成。
