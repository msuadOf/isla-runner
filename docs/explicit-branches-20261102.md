# 恢复显式语义分支（2026-11-02）

NaN、正负零等特殊值选择不同语义行为，按控制流分界保留显式分支。mask活动性、合法性与异常状态同理；纯谓词和普通数值计算内部的ITE不机械展开。本轮只恢复完整Clause消融中预算内自然完成的项，单项完成不代替组合性能验证。

## 已提交模型范围

基线为9c339044，`7f3f50d`恢复FD特殊值选择，`fd71c9a`恢复V分类、合法性和活动元素；五个模型文件均已由独立GPT-6.1 Sol按上述语义原则审阅，无源码阻断项。

- min/max保留双NaN、单NaN、异号零和大小关系的原优先序；minm/maxm仍先计算flags再选NaN结果。
- f32共享算术出口对NaN返回规范NaN，对非NaN返回原位表示。
- 向量十分类区分sNaN/qNaN、正负无穷、普通数、次正规数、零；分类位序不变。
- FVVTYPE和RFVVTYPE只在活动lane计算、写结果和累计flags；归约次序不变。
- valid_fp_op、illegal_fp_normal、illegal_fp_reduction恢复合法性短路分支，普通算术SEW8限制保留。

flags比较实验已完成，但与仍在跑的算术实验共用accrue_fflags，因此整体暂缓；转换饱和实验也未结束。其他格式的NaN出口、其他向量/BF16 mask循环及IEEE异常事实的内部表达式不在本轮已测范围，不能宣称全部控制条件已恢复。

## Sail和Isla协同

修改发生在Sail-RISC-V建模层，需完整重生RV32、RV64 VLEN128/256/512共四配置、五份IR。Isla后端关闭eager_control_flow，因此Sail if应生成真实Jump；永久回归还检查mask分支对运算的控制关系，不能只数整个execute的Jump。

底层fp_is_nan等只计算谓词，保留其数据流实现；本轮不改变Sail编译器或Isla通用ITE接口。工具链源、实际浮点库、生成参数与模型文件哈希以IR provenance为准。Sail前端约束检查使用其既有Z3 4.16.0，Clause运行链接官方Z3 1fd1d3613，二者分别记录。

## 前置提交与验证状态

Isla `09ffa91`记录官方Z3链接与CLI默认/Make具体策略，`09678a7`记录先前已验的三种指令表示和ExecuteAs续执行修复。二者作为可复现运行依赖一并固定，未更改memory分支。

Isla `f152290e`已提交四配置五IR、provenance及永久分支回归。普通严格检查、四配置严格SYMBOLIC生成、五IR24步回归、真实make solve-FMINM_S（12条）及GCC/Clang72项精确编码检查通过。独立GPT-6.1 Sol对源码和新IR最终签收无阻断。

组合七Clause当前5项PASS，其余2项仍运行；提交中的validation结果是本次快照，不能视为最终预算结论。未运行全量Clause或硬件重放，未推送远端。

详细独审见[报告](../agents/explicit_branch_restore_20261102/review/report.md)，具体版本见[记录](../agents/explicit_branch_restore_20261102/versions.json)。


## 2026-11-02 最终后台验证结果

七项新组合Clause全部退出0、finished、无错误或超时。FVVTYPE 3121.758秒（329条），VFUNARY1 1880.107秒（520条），RFVVTYPE 290.252秒（184条），其余四项15.471–150.914秒；均低于完整Clause7200秒预算。以validation/report.md和summary.json的最终记录为准，旧“运行中”记录仅适用于提交时快照。

单变量消融84/84已结束。flags算术和转换饱和的显式分支B各三次均触及7200秒外限，故不符合本轮恢复条件，保留ITE；不能写成这些情况不需要控制流或覆盖已经完整。其他格式/循环、右源独立NaN、BF16融合及多lane异常等仍有覆盖验证义务。
