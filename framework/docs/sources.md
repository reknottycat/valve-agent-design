# 架构借鉴来源（官方，一次性核实 2026-10-22）

| ID | 来源 | 核实用途 / 不应外推 |
|---|---|---|
| REA-01 | https://github.com/morluto/rea | Reverse Engineer Anything 官方仓库；CLI/MCP/工作流指引将 Agent 接到专业分析工具，IDA 是可选引擎而非 REA 别名。不是阀门工具。 |
| REA-02 | https://github.com/morluto/rea/blob/main/docs/mcp-contracts.md | 原始与规范化结果、evidence_id、coverage/unknown/limitations、未知项账本、保留证据及分页/引用、不可信目标内容。借其契约，不照搬领域操作。 |
| GC-01 | https://cloud.google.com/blog/topics/healthcare-life-sciences/architecting-scalable-agentic-biotech-workloads/ | 正文题名 Architecting autonomy: A design pattern for high-compute, governed agents in biotech；Schneider Larbi / Chelsie Czop，2026-10-16。认知编排/计算执行/企业治理三层，原文是参考架构不是具名客户生产案例。大型文件传引用、长任务阶段进度、按风险审批。药研动态风险阈值不可外推成阀门强制标准可被模型放宽。 |
| GC-02 | https://cloud.google.com/blog/topics/developers-practitioners/four-eval-engineering-lessons/ | Four evaluation engineering lessons learned from building agent plugins；Casey West，2026-10-16。对象 Google Cloud Developer plugin，与 GC-01 不同文章。评执行轨迹、保留异步轮次、live/plan-only 对照、黄金样例回归。 |

工程工具接口/格式/许可一手链接见同目录 tool-matrix.md；未安装或运行这些工具。网页与 latest 分支会变化，实际接入须固定 release/commit、保存许可及兼容性验收记录。
