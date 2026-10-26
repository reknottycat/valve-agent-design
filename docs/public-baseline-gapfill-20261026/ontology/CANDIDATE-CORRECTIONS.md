# 可补齐的部分：隔离候选，不是上游修复或工程放行

固定来源 `reknottycat/standards-kb@2937b5901b26d02456b95545ab2c1a059676e82a`。原对象、原E1/UNVERIFIED_CLAUSE、文件blob与规范化记录SHA256全部保存在 `source-records.json`。本包不是标准全文核验，也不改93条原始状态。

## 已确认的内部冲突及最小候选

| ID | 可直接确认的差异 | 候选补法 | 仍未解决 |
|---|---|---|---|
| F-STR-002 | canonical与第一条rearranged不等价；p=1 MPa,a=100 mm,b=112 mm时分别8.861635与4.930818 MPa，原sample记1.1299 MPa | **保持canonical为比较基准**，第一rearranged候选改 `p*(1+2*a^2/(b^2-a^2))`；同一输入的sample候选改8.861635 MPa；a、b单位一致，输出随p | 此改动仅修代数/样例一致性，不核准Lamé边界条件、不核准UG-27(b)条款归属，不认可其他rearranged、范围限值、实体阀体适用性 |
| F-FLW-001 | 原canonical末尾/1000；按原D200 mm、ζ6、ρ1000 kg/m³，结果0.652968而sample写653 m³/h | 对**该水参考算例**：D先转m；A=πD²/4 m²；速度sqrt(2*1e5/(ζρ)) m/s；乘3600得652.967771 m³/h，不再/1000 | 这只是给定压差1e5 Pa及ρ1000下流量量纲/样例一致性；若将常ζ平方律用于物理预测，须另证实充分湍流、非阻塞、非汽蚀、无闪蒸，且ζ的取压位置和参考面积一致，**不可用于Re≈10诊断工况**；本次算术未验证这些条件；IEC Kv定义、参考密度、其他流体密度归一、ζ参考面积/取压位置以及反解公式仍需独立核实，不发布通用修正版Kv函数 |
| F-DRV-002 | solved_for=F_hand，variables.F_hand=Q:DRIVE:HAND_FORCE，但result_quantity=Q:DRIVE:LEVER_RATIO | 如果维持当前canonical和solved_for，result_quantity候选指向已有 `Q:DRIVE:HAND_FORCE`；不新建qid | 条目也含lever_ratio的变形式，需作者确认主输出意图；不对样例操作力作新的工程结论 |
| F-FLW-002 | solved_for=Cv_US，variables.Cv_US=Q:FLOW:FLOW_COEFFICIENT_CV，但result_quantity是KV | 如果维持当前canonical和solved_for，候选改为已有 `Q:FLOW:FLOW_COEFFICIENT_CV` | 不由此核准1.156、IEC引用或上游F-FLW-001 |

## 已发现但不擅自代改

- F-SEAL-002：表达式有w_seal，variables/映射为w_seat。可登记显式别名候选，但必须核对物理定义、实际实现及样例，不能因名字接近静默合并。
- F-DRV-001：现有条目与本地M02方牙模型不同；外径/工作中径、螺距/导程、牙型角、mm到m和deg/rad转换均需要来源/实现复核。不把方牙教材公式覆盖梯形螺纹条目。
- M01已有机器结构、无执行实现；M03/M04/M06为文字草案。仍需物理语义、合法全文定位、实际工况与标准约束；可以先研究，不可以冒充已执行。

## 使用影响：只说已追到的证据

原记录 `project_usage` 声称：F-STR-002用于T24 FEA解析基准；F-FLW-001用于T08流量估算；F-DRV-002用于T17操作力。这是**条目自身声明**，不是本次运行日志或计算脚本的独立证据。本包没有取得这些运行的实际输入/脚本/结果hash，也没有证明历史求解器执行了有冲突的字符串。因此不能推出T24、T08、T17结果或R1基线错误；应只阻止未经复核的新执行，并向已有消费链查证。

## 检索与执行分开

建议调用方保留原record供研究检索，附加独立侧车决策 `execution_review_status=BLOCKED_PENDING_REVIEW` 与原因，不回写原 `evidence.status`，不隐藏记录。这里只提供决策清单，**未部署或修改适配器**。旧适配器本来不执行公式，且固定旧commit，不受本包自动替换。

## 可重跑验证

在包根目录执行：`python -B -m unittest discover -s ontology -p 'test_*.py' -v`

8项通过：固定commit与记录指纹、原状态保留、Lamé代数和单位尺度、给定水样例流量量纲、两个结果绑定冲突、密封符号差异。测试使用明确写出的受控算术，不对上游字符串做eval。这些通过意味着**成功复现缺陷且候选局部自洽**，不是所有原公式通过，更不是规范/产品通过。
