# 编码与执行约束分离及饱和控制流恢复

## 目标与范围

用户授权实现已讨论的修改并由Sol独立复核。保持正常编码优先、仅正常拒绝域探索压缩编码、候选不取单一模型、最终编码/初态/后态同一模型；纯数值算法不变。恢复已测f16→i16 overflow显式分支，协同更新完整Sail/Isla IR和根float版本。生产flags changed是否恢复不在本次默认源码范围，先验证新流程对旧显式B的效果。

## 分工和写边界

- implementation/：GPT-6 Sol写isla-lib/src/smt.rs的最小checkpoint原语、src/isarch/encoding.rs与相应测试；主暂不改这些文件。
- saturation/：GPT-6 Sol只改runner-float模型vext_fp_utils_insts.sail的f16ToI16 helper及准确注释；独立生成四配置IR与ordinary strict，主安装和更新版本。
- review/：独立GPT-6.1 Sol只写审查证据，源码/IR/动态结果分别签收，不参与实现。
- 主agent：配置/构建、实际Clause与编码验证、文档/提交和float父gitlink；保留根脏工作树。

## 设计及风险

辅助探索checkpoint去除原Assert，保留声明、定义、枚举、事件及next_var。每个终态的新增trace后缀与完整原checkpoint结合后检查可达性，UNSAT才过滤，Unknown/Error明确传播。候选成功/拒绝/其他异常都须核完整域，避免辅助扩大域中的不可达异常污染原路径。保留原路径全部事件用于trace/超时dump；符号不得重号，不能复制错误祖先的增量。

## 验证

先TDD红绿：符号ID/enum定义、跨路径候选互斥、normal优先和compressed拒绝域、不可达辅助异常、完整约束下过滤及全候选保留。按需cargo fmt；独立源码签收后正式Release构建。冻结程序/IR/config/种子，完整Clause及SMT预算7200s、T1；实际make solve与GCC/Clang助记符/二进制/insn三形式、最终模型一致性。四配置完整IR与provenance、25步IR回归。

性能分别以旧flags显式B冻结IR/原配置（隔离编码改动）及新模型IR（组合验收）检查，不以旧ITE输入或缩小域代替；不以后台启动当完成。

## 受控诊断后的最小修正

初版全去Assert扩大了辅助域，300秒诊断83.5%的终态完整检查为UNSAT。后续仅保留原Assert子集：由instruction.symbolic_variables()和原序DefineConst依赖传播判定指令字段纯依赖，含未知App保守移去，不把Assert关系作别名定义。定义、枚举、事件、符号编号和最终原完整域验证均保留。任意保留子集仍满足完整域蕴含辅助域；该判定只影响辅助探索成本。新增TDD覆盖派生输入、状态混合、App和完整恢复，并再次Sol源码和动态复核。分版本冻结二进制与完整输入，旧计时继续，新版另测，不混用PASS。
