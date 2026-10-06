# 522-35.4179 R1 工程计算书工作稿

本版完成文档归档，工程状态仍为 WORKING DRAFT / HOLD，不是制造放行计算书。

## 交付内容

- output 内为39页 PDF 和可编辑 DOCX，含78个原生公式、48张表
- build_calculation_book.py、rebuilt_chapters.py、current_flow_chapter.py 为数据驱动生成器
- sources 保留32个R0来源原字节；sources_new含116个重建后来源/派生摘要
- source_manifest.json 与 new_source_manifest.json 登记全部文件来源及 SHA256
- verification 保存197项文稿算术检查的生成一致性、来源防误改检查、独立原始数据复核及逐页QA记录
- freeze_record.json 和 artifact_manifest.json 固定本版文档与包载荷身份

## 本版有结果的范围

保留R0几何、物性、双侧压力和驱动/接头敏感性计算；加入新执行的六例阀瓣弹性参考解、两压力块和三个原生Poisson立方体基准。当前网格v2的原生检查与固定来源绑定已独立复核，54个大于70°的非正交面警告保留。

阀瓣采用C95800弹性研究替代、刚性无摩擦双边约束；单边接触解释为HOLD，原始应力峰未收敛，无强度许用比较。立方体PDE不能替代阀域PDE或真实流场；流动规划的实际通量、压降和阻力系数仍为空。整阀结构、物理耐压、泄漏和制造验收仍未完成。

## 复算方法

在已有 python-docx / Pillow 依赖的环境运行 python build_calculation_book.py。此步骤只重算文稿算术并生成DOCX，不运行CAD、CFD或FEA。PDF用原文档渲染器或等效Word渲染后逐页核查。

verification/test_source_guards.py 在临时副本测试普通和−O模式的来源字节篡改与禁止刷新；verification/test_rebuilt_generation.py 比较两模式文稿XML和算术记录。文档内容不依赖当前外部工作目录，只读取随包快照。

snapshot_new_sources.py、add_current_flow_sources.py 和 add_mesh_v2_sources.py 是来源登记工具，依赖所记实际工程目录；不能将来源刷新等同于旧结果重新验收。integrate_rebuilt.py 是一次性重建准备脚本，不要在本版再次执行。

完整原始求解器网格、DAT和工程运行包由各工程包单独保存，本轻量文稿包不重复全部大型二进制。固定网格v2包：Library libfile_d1fe3abe4124819191187761705c99c6；归档SHA256 aa2410a92d6aa64dc6e9f0a6253f4a82e1a5cceb9814557b3a84b4190d2f667e。网格固定清单SHA256 98976d5277a5592284cd20c9dbce095d7c7b845e036417ade65c90e5aff0bd05。

R0从固定提交恢复并逐项核字节，本版没有改动R0。失盘前R1结果和旧QA没有用作现有证据。后续阀域PDE、接触和接头结果另行补编，不回改本版研究边界。
