# Agent Work Error Log

每次 agent 工作中出现的失误，按时间倒序记录在这里。
目的：让下一个 agent 看到，不重蹈覆辙。

| 文件 | 时间 | 任务 |
|------|------|------|
| [cfd-validation-2026-11.md](cfd-validation-2026-11.md) | 2026-11 | Kaggle CFD 3D 验证 |

## 规则表（每条规则 → 执行它的机制）

| 规则 | 执行机制 |
|------|---------|
| 求解器只能在单位、几何覆盖、原生质量、指定点连通和边界字典检查通过后启动 | `framework/tools/foam11_gates.py` 与 `valve_readiness.audit`；真实失败回放见 `framework/tests/test_foam11_gates.py` |
| 进程正常结束不能代替压力与流量质量判定 | `foam11_gates.assess`；未收敛或字段不全时不判定阻力系数达标 |
| 历史版本按原条件留档，不作为当前求解入口 | 暂停的固定输入入口为 `verification/valve-3d-cfd-57mm/valve_3d_cfd.py`；v18–v22 的记录供复查；`framework/tests/test_retired_product_builds.py` 核对历史原件并验证旧入口拒绝启动 |
| 同类工程失败不因改版本重置；暂停时不运行 | `study_retry.require_fixed_study_run`；`framework/tests/test_study_retry.py` 回放四份真实失败工件。 |
