# 定向验收脚本预运行签收

已读最终准备脚本与预期，当前无阻断，可在**最终冻结 inputs 和已签来源资产**到位后运行。受审文件精确版本见[SHA-256清单](harness-reviewed-hashes.json)；本签收是脚本与fixture的方法审查，尚不签任何新 IR 动态结果。文件后续变化须复审变化。

- flags：五份IR各60例，直接调用实际 `zaccrue_fflags`，隔离目标寄存器写带来的Dirty；普通Sail状态规则单独复算fcsr/mstatus。实际IR中两个callback调用的次数和顺序是静态合同，未运行动态callback observer；Ext_F配置范围明确。
- conversions：六窄及十二普通包装共819 helper输入、282 scalar及183 vector编码；源FP原始位串、五RM/RTZ、可达边界、NV/NX、NaN/Inf、RV64 W/WU写回符号扩展。直接测试程序核译码/执行/反编码、具体后态及差异UNSAT；observe只覆盖列明的源组、目的组、部分无关寄存器与CSR。实际tactic为旧直接runner固定的Qfaufbv，不计isarch JSON/qffp或完整Clause。
- exceptions：315例由259 scalar/ROD/ordinary conversion、30 H/S/D向量、26 BF16组成。核实际输入、结果位、五flags、完整目的寄存器、mstatus、相关寄存器保持、seed及JSON自身输入来源。每CPU独立串行队列，避免按job轮转CPU造成同核并发。定向超时预算独立记录，不代替正式Clause7200秒。
- representations/make：从最终程序/IR生成新JSON，GCC与Clang分别验证助记符、精确字节、`.insn`；Illegal BF16布局的Clang助记符拒绝独立记录。真实Make调用当前run.mk recipe和冻结isarch，属于固定初态的smoke。工具版本/哈希、实际命令、输出哈希保留。

独立复核[819项转换预期](conversions-expected-independent.json)采用Python精确有理数FP解码、整数五舍入和目的范围规则，不调用被改helper；全部bits/flags一致。源格式能精确表示时已补整数端点，并区分FP前驱与整数最大值。[315项异常预期](expected-independent.json)逐条重放独立SoftFloat命令，全部结果/flags一致。它们只签预期，不证明新IR动态正确。

预审查出的flags ROOT路径/tactic不一致、转换LMUL2机器码目的字段/源对齐与mstatus错误、弱seed/schema门、异常执行器CPU分配与来源缺失均已由owner修正。本审查者没有修改生产代码或owner测试文件。

剩余覆盖必须与动态通过分开：全部调用入口/宽化/归约/估算十类、FMA四变体、所有符号组合、全LMUL/vl/SEW/VLEN分区、Zfinx及全域数值均未因这些有限fixture而闭合。完整64受影响+13兼容Clause由单独调度与runner门执行；新源码/IR变动后旧结果不迁移。

转换fixture补端点后重跑819项精确有理数预期与465项编码检查均通过。旧806项attempt1 helper实际退出0，但启动器将末尾汇总行误计为第807条而停止；记录保留，旧批次不计新版整体完成。新版仅计`PASS riscv_`逐例行。

flags source manifest已加严：模型须列全tracked；Isla仅允许final-input-independent.json列明的8项旧IR/provenance/test fixture排除，且排除项也与git show@42000be字节哈希相同。实际Cargo依赖为runner-float/isla/isla-lib，未混用根isla。
