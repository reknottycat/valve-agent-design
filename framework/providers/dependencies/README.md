# CAD 依赖引用与 SOLIDWORKS MCP 延后接入

核查时间：2026-10-23 UTC。仅研究/依赖清单；未安装、未启动商业软件、未运行上游代码。用户最新说明电脑没有 SOLIDWORKS，本项搁置，不阻塞现有开源阀门工作。

## 结论

- 保留现有 CadQuery → STEP 审核/回读 → Gmsh → 开源求解主链。MCP 是接口，不是 CAD 或 CFD 内核，不能因引入接口重复开发内核。
- 社区项目 hjbaard/SolidWorks-MCP 的 GitHub 最新正式发行版实查为 **v0.16.1，2026-10-15**。其固定提交 `95bcd56306e63a8a44e18afa487469dcccc71774` 的 server.py 定义了 86 个对外异步工具。不是 Dassault 官方 MCP，也不是“所有 SOLIDWORKS MCP 中唯一/最新”的断言。
- 工具覆盖零件、装配、检查、CAD 导入导出。`slice_mesh` 和 `compare_with_mesh` 是 STL/3MF 截面和几何比对，**不是流体网格管理、流动求解或压降计算**。在核查的工具定义中未发现 Flow Simulation 工况/边界/求解/结果工具，不能承诺这个版本可做流量模拟。
- README 的绘图工具与旧限制段落有不一致；能力应以固定代码及将来的实机探测为准，不能照抄宣传列表即判验收。
- 包为 MIT，但 SOLIDWORKS 主机是独立商业软件。需要 Windows、Python 3.11+、已许可且运行的 SOLIDWORKS、Y-up 零件模板。维护者宣称测试过 2026 版本，不等于我们完成实测。Flow Simulation 产品/许可证和自动化接口另行核验。
- 可选 FreeCAD 社区适配器 neka-nat/freecad-mcp：固定提交 `78bf0230a03324b56c9a0b7f55150fb5be2a0d42`，包元数据 0.1.27；MIT 适配器，FreeCAD 主机另有许可证。插件和外部服务器须同版本。Python 执行和 FEM 辅助工具不等于已具备 CFD。

## 后续最小计划

1. 现在继续开源路径，商业路线仅记录网格处理经验，不安装购买、不改现有通过工况。
2. 将来有主机与许可证后，先查版本、能力清单和接口，再以可丢弃零件验证建模、测量、STEP 导出回读。
3. Flow Simulation 若无可核验 MCP 工具，再考虑窄适配器或受监督流程；不把 CAD API 当流体 API。
4. 只用一个同几何、同边界的小工况对照质量守恒、流量、压降、收敛和网格敏感性，再决定是否纳入常用依赖。

## 清单与验证

`dependency-references.json` 记录源地址、提交、版本、许可证分层、运行条件、能力、产物契约。仅在将来实际启用时从固定上游获取并记录下载校验值，不复制商业库。当前未下载包，所以没有编造包 SHA256。

`solidworks-tool-names.json` 是固定 server.py 的 86 个对外异步函数名（排除内部 `_call`）。本次本地检查通过：清单 JSON、40 位提交、许可证分层、未实测标志、86 个唯一工具，以及切片/比对/导出名称存在。它只是静态证据，不证明实机可用、工程正确或所有其它社区适配器也不支持 CFD。

## 一手来源

- 最新正式发行：[GitHub v0.16.1](https://github.com/hjbaard/SolidWorks-MCP/releases/tag/v0.16.1)
- 固定工具定义：[server.py](https://github.com/hjbaard/SolidWorks-MCP/blob/95bcd56306e63a8a44e18afa487469dcccc71774/src/solidworks_mcp/server.py)
- 运行条件：[README](https://github.com/hjbaard/SolidWorks-MCP/blob/95bcd56306e63a8a44e18afa487469dcccc71774/README.md)
- 包与许可：[pyproject.toml](https://github.com/hjbaard/SolidWorks-MCP/blob/95bcd56306e63a8a44e18afa487469dcccc71774/pyproject.toml)、[MIT](https://github.com/hjbaard/SolidWorks-MCP/blob/95bcd56306e63a8a44e18afa487469dcccc71774/LICENSE)
- FreeCAD 候选：[README](https://github.com/neka-nat/freecad-mcp/blob/78bf0230a03324b56c9a0b7f55150fb5be2a0d42/README.md)、[版本元数据](https://github.com/neka-nat/freecad-mcp/blob/78bf0230a03324b56c9a0b7f55150fb5be2a0d42/addon/FreeCADMCP/package.xml)、[包依赖](https://github.com/neka-nat/freecad-mcp/blob/78bf0230a03324b56c9a0b7f55150fb5be2a0d42/pyproject.toml)
