# Scalar boxing, register and comparison witnesses

2026-09-26 静态生成件。入口为 `boxing_registers.py` 的 `generate(repo_root: Path) -> dict[str, list]`，返回 `positive` 组；从仓库根目录执行 `python3 agents/float_support_review/tools/solve_scalar_coverage/boxing_registers.py OUTPUT_DIR` 写 `positive.json`。`OUTPUT_DIR` 应位于仓库外。脚本只读取 `agents/float_support_review/tools/e_scalar_cases/scalar-cases.json` 与 `enum-ops.json` 的真实汇编编码、constructor、字段模板和既有独立预期；每个改变的 rs1/rs2/rs3/rd 同时更新机器字与 `expected_fields`。d012 冻结 IR 上的动态结果由主 agent 另行记录；此处不冒称全分支 trace。

当前生成 **550 条**，覆盖审计范围内 **49 个 RV64 非 BF16 scalar clause**。构成：112 条每个具体 op 的高号寄存器、117 条同 bank 源目的 alias、34 条写 x0、15 条从 x0 读、108 条 H/S 各 F 源位置非法 NaN boxing、2 条 FMV 原位搬运、12 条 FMA 负数 negate、150 条五种比较操作 × H/S/D × 10 输入类别。条目携带 `branch_ids`；这些 ID 是对源码条件的输入映射标签，**不是插桩执行得到的分支命中率**，也不把状态笛卡尔积称为全覆盖。

## 分支 ID 与源码位置

| `branch_ids` 前缀 | 源码条件与输入 | 限制 |
| --- | --- | --- |
| `nan_unbox.h.invalid.<op>.<rs>` / `nan_unbox.s.invalid.<op>.<rs>` | [fdext_regs.sail:49](../../../../sail-riscv/model/extensions/FD/fdext_regs.sail#L49) 的 upper bits 非全 1 → canonical qNaN；[同文件:327](../../../../sail-riscv/model/extensions/FD/fdext_regs.sail#L327) 与 :339 的 H/S 读取。`FCVT` 的源格式从具体 enum（如 `FCVT_H_S` 的 S 源）确定。每个 H/S op 的每个 F 源位置单独构造，其他 F 源保持有限值。 | D 是 FLEN64 同宽，没有 H/S boxing 分支；FMV.X.H/W 用原位读取，不应归入 unbox。合法 boxing 已由现有基本例见证。 |
| `fmv.h.raw_no_unbox` / `fmv.s.raw_no_unbox` | [zfh_insts.sail:818](../../../../sail-riscv/model/extensions/FD/zfh_insts.sail#L818)、[fext_insts.sail:918](../../../../sail-riscv/model/extensions/FD/fext_insts.sail#L918)：非法上位仍按低位原样搬到 X，并按低宽符号扩展；无新 flags。 | 低位取负号和非零 payload，使它与 unbox 的 canonical qNaN 结果可区分。 |
| `register.high.*` / `register.alias.rd_*` | [fdext_regs.sail:122](../../../../sail-riscv/model/extensions/FD/fdext_regs.sail#L122)、:163 的 rF/wF，及 [regs.sail:151](../../../../sail-riscv/model/core/regs.sail#L151)、:190 的 rX/wX。每个 op 用 29/30/31 作源、28 作目的；同 bank 每个源位置另与目的 3 alias。 | 属于每具体 op 的输入见证；未穷尽全部 32 编号组合。F 与 X 同编号是不同 bank，不称 alias。 |
| `register.x0.read_zero` / `register.x0.write_discard` | [regs.sail:153](../../../../sail-riscv/model/core/regs.sail#L153) 从 zero_reg 读；[同文件:192](../../../../sail-riscv/model/core/regs.sail#L192) 写 0 不更新。X 源 op 读 0；X 目的 op 写 0 后观察各源、fcsr、mstatus 和未相关 x27 哨兵。 | runner 的状态快照没有可观察 `x0` 寄存器，故**不把 `x0` 放在 `observe` 或 `initial`**；写 0 的固定不变量仅由语义和其他寄存器未变联合检查，不能单靠目的状态读回证明。 |
| `fma.negate.negative_input.<op>.<rs>` | [zfh_insts.sail:259](../../../../sail-riscv/model/extensions/FD/zfh_insts.sail#L259)、[fext_insts.sail:381](../../../../sail-riscv/model/extensions/FD/fext_insts.sail#L381)、[dext_insts.sail:268](../../../../sail-riscv/model/extensions/FD/dext_insts.sail#L268)：FMSUB 的 rs3、FNMSUB 的 rs1、FNMADD 的 rs1 与 rs3 分别给负值，触发 [negate_H:37](../../../../sail-riscv/model/extensions/FD/zfh_insts.sail#L37) 等 sign=1→0。 | 有限精确输入 1.5、2、±0.5，按乘加代数独立算输出。未覆盖 0×∞ 等其他 FMA 数值域。 |
| `compare.<op>.<variant>` | FEQ/FLT/FLE 在 [zfh_insts.sail:415](../../../../sail-riscv/model/extensions/FD/zfh_insts.sail#L415)、[fext_insts.sail:826](../../../../sail-riscv/model/extensions/FD/fext_insts.sail#L826)、[dext_insts.sail:758](../../../../sail-riscv/model/extensions/FD/dext_insts.sail#L758)；quiet FLEQ/FLTQ 在 [zfa_insts.sail:581](../../../../sail-riscv/model/extensions/FD/zfa_insts.sail#L581) 起各格式执行体。每 op/格式单独给 qNaN/sNaN 左、右、双、两序 ±0、有序 false、相等。 | 比较真值与 NV 由 IEEE 规则计算：FEQ 与 quiet 比较仅 sNaN 置 NV；FLT/FLE 任一 NaN 置 NV；NaN 均 false，±0 相等。旧 DZ=0x8 应保留。 |

非法 boxing 的独立 oracle：普通 MIN/MAX 单 NaN 返回另一有限数；Zfa MINM/MAXM 任一 NaN 返回 canonical qNaN；SGNJ 系列先把非法源视为 canonical qNaN，再按原位符号位组合，无 flags；普通算术、FMA、SQRT、ROUND、浮点格式转换输出目的格式 canonical qNaN；FP→整数的 qNaN 输出 signed max 或 unsigned max 且 NV，`WU` 的 32 位结果按 RV64 规则符号扩展；FCLASS 输出 qNaN 位 9；`FCVTMOD.W.D` 源 D 不属于 H/S boxing。初始 `mstatus=0x8000000000006600`（FS=Dirty/SD=1）与不变预期一致，避免把本组混作 FS 状态转换验证。

## 静态核对与未纳入分支

命令 `python3 agents/float_support_review/tools/solve_scalar_coverage/boxing_registers.py OUTPUT_DIR` 生成 550 条；另逐条核对 rs1/rs2/rs3/rd 的 `expected_fields` 与机器字 bit[19:15]/[24:20]/[31:27]/[11:7] 一致、`observe` 与 `expected` 键相等，550/550 通过。此为**生成件静态检查**，不是结果测试。

[fdext_regs.sail:368](../../../../sail-riscv/model/extensions/FD/fdext_regs.sail#L368) 的 Zfinx/Zhinx/Zdinx 走 X 路由、[dext_insts.sail:219](../../../../sail-riscv/model/extensions/FD/dext_insts.sail#L219) 的 RV32 Zdinx 奇偶寄存器对均非本次 RV64 Ext_F 配置可达，不能标 PASS。`rF`/`wF` 的非法编号臂也不可能由 5 位 encdec 字段产生。版本边界：d012 冻结 IR 的 `SYMBOLIC` 向量 FPR 写入绕过普通 `wF` 的 Dirty 更新；当前源码 [fdext_regs.sail:273](../../../../sail-riscv/model/extensions/FD/fdext_regs.sail#L273) 已由生产 owner 增补 Dirty/转换/callback，尚不能用旧 IR 的动态结果给新源码标 PASS。本组固定 FS=Dirty，Clean/Initial→Dirty 由主 agent 独立验证。
