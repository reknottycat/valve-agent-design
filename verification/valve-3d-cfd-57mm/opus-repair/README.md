# 57 mm：内部共面单元合并的实跑核验

原始网格为固定 v22，原始零件、研究流道、工况均未修改。第一版脚本声称合并 40 对但单元和内部面均未减少，被拒绝；`rejected-first-report.json` 为当时回执。实际提交的实现从原生邻接关系选择共用面的单元，对体积、边界、六点连通、严重非正交面与原生完整质量标准分别复核。

真实移除 3783 个共用内部面和 3783 个单元；严重非正交面 6514 → 6247。原生检查原文：

- ***Cells with small determinant (< 0.001) found, number of cells: 818
- ***Concave cells (using face planes) found, number of cells: 3313
- ***Faces with small interpolation weight (< 0.05) found, number of faces: 15
- Failed 3 mesh checks.

以 result.json 中 solver_started、study_assessment 为准；单项改善不关闭任务。原始记录、执行脚本和合并面的原生编号在 native-record.zip。

## 拒绝近共面单元后的同标准对照

本候选从同一冻结 v22 起步，不是沿用有 3313 个凹单元的网格。匹配原生面对面夹角判据后，仅合并 677 对；原生单元与内部面均减少 677。凹单元检查通过，严重非正交面 6514 → 6357，低行列式单元 4657 → 3960，低权重面 16 → 15。体积、边界、六点连通核对通过；整网格仍有两类失败，没有运行压力求解。两项合并对照均未消除环边的离散问题，不再把调整合并容差当作下一轮修复。[原始检查、移除面清单与实际脚本](native-strict-face-plane.zip)。
