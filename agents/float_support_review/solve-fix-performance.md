# 浮点 solve 修复：异常累计与状态写回（2026-09-26）

本文件是已获用户授权的 solve 审计修复中的性能与状态语义工作包，由 Astra xhigh 审定边界，供主 agent 分配实现。生产代码尚未由本文作者修改。现有证据见[审计汇总](solve-audit.md)、[运行器方法](solve-audit-method.md)、[d012 官方批次](solve-audit-batch.md)。其他修复和最终整体验收由该轮主计划统筹。

## 1. 根因证据与本包范围

d012 IR 的官方 77 项中 40 项退出 0、36 项外限超时、1 项 SMT 错误。11 个目标合计 61 条 `CheckSatAssuming` 超时均定位于 `fdext_regs.sail::accrue_fflags` 的 `old_fflags != old_fflags | flags`。这个条件要求求解浮点异常是否产生新置位，包含符号 FPR 选择和 FP 运算；其作用仅是选择 CSR 更新及 Dirty 副作用。把它表示为符号状态的 ITE，可以同时保留两种结果，避免为了这次条件状态更新枚举两条执行路径。

另一个独立正确性缺陷已由标量代理取得红例：开启 `__isla_vector_fpr` 时，`set_F_bits` / `set_F` 直接调用 `wF_from_vector`，绕过原 `wF` 的 Ext_F 断言、`freg_write_callback` 和 `dirty_fd_context`。FADD.S `1.5 + 2.0` 不产生新 flags，初始 `mstatus=0x2600`（FS=Initial），应得到 `0x8000000000006600`，d012 实得 `0x2600`；差异检查 SAT、runner 退出 101。外部证据目录标识 `isla-scalar-dirty-red-20260926.e9sriqox`，由标量代理维护。

**这两项交由同一名 Sol 独占 `sail-riscv/model/extensions/FD/fdext_regs.sail`。**本包不修改执行器分发、寄存器符号化策略、向量上下文约束或全局 workaround；不改变已经通过的内部五 Bool 异常事实、原生 RM、generic 分类与出口共享 flags 结构。

## 2. 必须保持的语义

设旧五位状态为 `old`，本次输入为 `flags`，则：

```text
new = old | flags
changed = old != new
fcsr.FFLAGS' = new
fcsr 的其他位保持旧值
mstatus' = changed && Ext_F ? dirty_fields(mstatus) : mstatus
dirty_fields 仅将 FS 置 Dirty、SD 置 1，其他位原样保留
```

当 `changed=false`，即使旧 FS/SD 不是 Dirty/1，也必须保持旧 FS/SD。Zfinx 配置不置 FS；扩展不变量 `Ext_F != Ext_Zfinx` 原来仅在 `changed=true` 时断言，改写后不能把此断言无条件加到原本允许 `changed=false` 的输入上。

`set_F*` 写 FPR 则应**无条件**具备原 `wF` 的副作用，包括同值写入和无新 flags 时的 FS/SD 更新。该规则与 `accrue_fflags` 的条件 Dirty 不同，不可混用。

## 3. Astra 审定的 callback 边界

- 非 `SYMBOLIC` 路径保留 `accrue_fflags` 原条件和原 C++ callback 调用顺序、次数与值；不能把有外部效果的 callback 改成无条件调用。
- 当前 `SYMBOLIC` 的 `csr_full_write_callback` 是 `core/callbacks.sail` 中的 pure 空函数体，FD 配置还将它映射为 `()`。其函数调用诊断事件与同值寄存器 write 计数不属于本包所保持的 ISA 状态语义。`SYMBOLIC` 状态 ITE 路径可以不调用原条件分支中的 `long_csr_write_callback`；两条末尾 `fflags` / `fcsr` callback 保留原位置和参数。
- 这意味着新旧 `--trace-all` 的函数调用事件、寄存器写事件**不是逐项等价**。后续日志/trace 元数据必须明确这一点，不能宣称原条件分支仍被动态走过。普通 C++ callback 则仍严格保留。
- 若后续将 symbolic CSR callback 换成有可观测外部效果的实现，本改写需重新审查；不能自动外推当前空体/常量配置的论证。

## 4. 可直接派发的实现边界

### 4.1 `accrue_fflags`

只为 `SYMBOLIC` 增加值选择实现；非 `SYMBOLIC` 保留原代码。实现可按下列顺序组织，使用已有 `ite`、strict Bool 和命名 bitfield 字段，不写 ISA 专用 Rust primop：

1. 读取旧 `fcsr[FFLAGS]`，计算 `f = old | flags` 与 `changed = old != f`。
2. 写回 `fcsr[FFLAGS] = f`；其他 fcsr 位保持不变。
3. 用 `assert(strict_or_bool(not_bool(changed), hartSupports(Ext_F) != hartSupports(Ext_Zfinx)))` 保持原条件断言的域。正常合法编译配置中扩展条件为具体 true，不引入 flags 可满足性查询。
4. 在具体的 `hartSupports(Ext_F)` 分支内，复制旧 `mstatus` 为局部值，将局部 `FS` 设为 `extStatus_to_bits(Dirty)`、`SD` 设为 `0b1`，再以 `ite(changed, dirty.bits, mstatus.bits)` 选择完整位串写回。使用命名 `FS` / `SD` 字段，保留 RV32/RV64 各自的字段位置，不能硬编码 RV64 的 bit63。
5. 不在这个 symbolic 分支调用有条件的 Dirty callback；保留函数末尾现有 `csr_write_callback("fflags", ...)` 和 `csr_write_callback("fcsr", ...)`。

`changed` 只能成为 ITE 条件，不能被新 assert 固定为 true/false，也不能用模型值具体化。不可为避免超时把旧 flags 固定为零、把 FS 固定为 Dirty 或限制 FPR 编号。

### 4.2 `set_F_bits` 与 `set_F`

在两条 `__isla_vector_fpr` true 路径恢复与 `wF` 相同的检查和副作用顺序：

1. `assert(hartSupports(Ext_F))`。
2. 按已有 `fregval_into_freg` 约定向 FPR 写入原数据；当前 `fregtype=flenbits`、转换为恒等函数，但不要以此绕过模型约定。
3. `freg_write_callback` 使用原始写入值与正确 Fregidx：bits 入口直接使用其索引，fregno 入口采用与 `wF` 相同的 `Fregidx(to_bits(r))`。
4. `dirty_fd_context()`，保持原 `wF` 的 callback 在前、Dirty 在后。

可复用一个有两处实际调用的本地写回辅助，也可在两臂明确写出上述短序列；不得把非 vector 臂也额外重复 Dirty 或 callback。相关 effect 声明由 Sail 类型检查核实，不能通过删检查或扩大到 unrelated primop 规避编译错误。

## 5. 先红后绿的验证门槛

1. **保留确定红例。**先保存上述 FADD.S FS=Initial 输入的当前失败记录，再验证修复后结果位、旧 flags、FS/SD 与全部其他 mstatus 位；另加 FS=Clean、已经 Dirty、写回同值及 exact/no-new-flags 输入。两个 `set_F*` 入口都须覆盖；不能只测试因 `accrue_fflags` 新异常碰巧置 Dirty 的情况。
2. **全状态等价证明。**隔离 harness 以任意 32 位 fcsr、任意完整 mstatus 和任意五位 flags，比对旧条件更新关系与新 ITE 关系，先确认前置域 SAT，再证明差异 UNSAT。`changed=false/true` 分别检查；32×32 flags 组合可作具体交叉检查。保持所有 FRM/reserved/mstatus 非 FS/SD 位。至少覆盖 F、Zfinx，以及扩展不变量不成立时 `changed=false` 仍允许、`changed=true` 仍断言失败。
3. **动态路径门槛。**调用实际新 `accrue_fflags`，五位 flags 和旧五位状态都未知；在正常固定扩展配置下完成一条路径，最终 SAT，产生的 fcsr/mstatus 等价。旧版应展示该条件引起的分叉；新 IR 不得再含这个数据条件的 Jump。
4. **真实 FP 负载。**保留未知输入与真实 helper 调用，以 f64 add/FMA、f32 窄化及一个向量 FMA 代表指令复验；保留最终 SAT、数值/flags 既有差异检查和所有符号寄存器选择。分别记录候选/旧 IR 哈希、执行完成、SMT 超时来源、elapsed/RSS，不只看速度。
5. **C++ callback 回归。**非 symbolic 源码分支不变仍须编译；若测试环境可拦截 callback，核对 changed=false 无 mstatus callback、changed=true 的 mstatus/mstatush（按 XLEN）先于末尾 fflags/fcsr，值和次数不变。至少以源码/生成体差分确认未误改原后端。
6. **正式 IR 集成。**由既有集成人重新生成 V128 IR，更新全部严格配置并核对源码区域/锚点；恢复既有 helper、指令状态和错误状态测试，再逐项跑 77 个官方目标。原 d012 结果只作为历史证据。

## 6. 向量问题仍需单独处理

flags 累计解释了 61 次已定位的 SMT 超时，不能解释所有外限目标。原日志有大量 vtype/FRM/寄存器组合法性分叉以及 collector 编码守卫重入；真实有限的 `SEW × LMUL × vl/vstart × mask/tail × register` 组合不能被当成非法状态删掉。两个现有 VFMERGE/VFMV workaround 还存在全调用树采样范围，不能把它们当成穷尽验收。

此包先移除已有语义等价的状态更新分叉并修复 FPR 状态遗漏。新候选完成后，再以路径/查询来源判断剩余向量成本；不在此包扩张到向量 lane 循环重写或新增上下文限制。VPR fast 写是否有同类 Dirty/callback 遗漏由向量负责人另行复核，并由主 agent 指定独占文件边界。

## 7. 外部超时查询的单因素诊断

本轮取 d012 批次 `stage2/output/timeout-smt/zF_BIN_RM_TYPE_D-pid3560766-CheckSatAssuming-event1.smt2` 作外部诊断。原文件 SHA-256 为 `76a4ec194370707cca45adb10198549fba6de7c35021be524238c2d2a9b1e771`；两个顶层 assert 分别是包含 FP 运算的临时 flags 条件（18,650 字符）及其余路径上下文（3,237 字符，无 FP 运算）。原文件和控制文件分别保存为 `RUN_DIR/original.smt2` 与 `RUN_DIR/path-only.smt2`，目录标识 `isla-float-accrue-query-q41b5u9c`；`report.json` 保存原哈希、工具版本、退出码与时间。

控制实验只在仓库外副本移除这个临时分叉条件，保留全部其余路径上下文和 `(check-sat)`，没有修改原始证据或生产求解器。Z3 4.16.0、相同 `timeout 8s z3 -T:5 FILE`：

| 查询 | stdout | 墙钟 | 退出码的解释 |
| --- | --- | ---: | --- |
| 原查询 | `timeout` | 5.110 秒 | CLI 退出 0，但求解未完成，不能记 SAT/PASS |
| 仅其余路径上下文 | `sat` | 0.106 秒 | 此控制公式可满足 |

这为临时 flags 分叉条件确实引入困难查询提供单因素证据，**不构成模型等价或指令功能证明**。正式候选需要用 ITE 保留两侧状态结果，并满足第 5 节的全状态等价验证；不得把本诊断的“删除临时条件”直接做成执行器跳过约束的实现。实验也没有确定 Z3 内部具体慢在哪个算子，不能据此把所有向量超时解释为同一原因。

## 8. 待当前候选实测后决定的第二阶段

Astra 已审查一个有限的后续候选，但它尚未获生产实施放行：仅在 `SYMBOLIC` 的 `V/vext_fp_utils_insts.sail::valid_fp_op` 与 `illegal_fp_*` 中，把 total 纯 Bool 合取/析取改为 strict Bool，最终合法/非法出口保持完整两臂。原 `rm==5/6/7` 和各合法性子条件的短路会拆出多个相同 Illegal 返回，增加 collector 工作；合并表达式不应改变任何被接受/拒绝的输入。

`valid_vtype` 仅读取 vill；`valid_rd_mask` 比较 vm 与 rd；名字为 `assert_vstart` 的函数实际仅比较 `unsigned(vstart)==i`；`valid_eew_emul` 对 EEW/EMUL 只做整数比较。这些谓词提前求值没有副作用或部分定义运算。若要消除 `valid_rd_mask` 自身的短路，可在浮点文件局部使用 strict 适配，或由主 agent 单独移交共享文件；不得顺便把 `valid_reg_group` 的幂/取模、寄存器重叠 helper 等未经全域证明的函数改成提前求值。

生产前置门槛是原/新 guard 在全符号参数上的前置域 SAT、接受/拒绝差异 UNSAT，以及短 IR 的路径数 A/B。现有向量负责人维护的 d012 392 条全状态输入（含 66 非法 FRM、22 vill、21 vstart、15 masked-vd0、8 EMUL、41 对齐及合法/policy/LMUL 例）可作为后续指令回归，不能替代 guard 全域等价。

当前先冻结并验证本包状态修复；待新 IR 的官方目标仍显示相应热点时，由主 agent 决定是否启用此第二阶段。不以旧日志热点直接宣布新候选也有相同瓶颈。

## 9. 掩码 lane 的真实 IR 原型

主 agent 随后授权在当前候选复验期间并行研究 lane 改写；以下原型已完成，尚不代表生产指令全量通过。原型在仓库外生成，目录标识为 `isla-float-lane-prototype-20260926`，没有修改生产模型、全局 simplifier 或 executor dispatch。

### 9.1 方法与结果

原型直接载入当前生产 `prelude`、`ieee_fp_exceptions`、`softfloat_symbolic` 与 f16 helper，以 Sail 0.20.1 和同一 Isla plugin 生成一份小 IR。每个入口的 mask、全部输入 lane、全部旧目标 lane 和旧五位 flags 均未知；操作为普通 Sail `riscv_f16Add`，RM=3。固定 lane 数 2/4/8 是原型的受测形状，不是对正式向量输入域的配置变更。

- A：按 lane 的 `if mask[i]` 进入真实 helper，写结果并累计 flags。
- B：每 lane 先调用纯 helper 取得 `(flags, bits)`，将 `ite(active, flags, 0)` OR 到旧 flags；结果以现有 `isla_vector_select(mask, old, computed)` 合并。
- 等价入口：在同一组未知输入上执行 A/B，每条 A 路径先检查前置约束 SAT，再断言两边任一结果 lane 或 flags 不同，检查 UNSAT。没有以 Sail optimistic assert 冒充等价证明。

| lane 数 | A 完成路径 / real 秒 | B 完成路径 / real 秒 | A/B 等价 |
| --- | --- | --- | --- |
| 2 | 4 / 0.10 | 1 / 0.07 | 4 条路径分别 SAT、差异 UNSAT；0.20 秒 |
| 4 | 16 / 0.33 | 1 / 0.08 | 16 条路径分别 SAT、差异 UNSAT；1.22 秒 |
| 8 | 256 / 5.97 | 1 / 0.12 | 256 条路径分别 SAT、差异 UNSAT；39.82 秒 |

时间来自同机同 runner 的 `/usr/bin/time -p`，包含小 IR 解析；每项外限 45 秒、退出均为 0。该数据支持消除每 lane 掩码分叉，但不能外推为全指令同倍数加速，也未包含向量合法性、寄存器组选择及完整 CSR 写回成本。

IR SHA-256：`36db1b75f618cbebb3cdae599ff35e074d377c0e6b6ad5cd0b4a68fd6885d5c0`；Sail 原型：`e6188e4cc775077950a555113da55859a50160465d7018e0e7d79cd8158a5301`；首轮 runner：`fff9e89c5f3ce09345d1c2f134aedc321ac6a8238fbce54fada95f7391d0e8a0`。`report.json` 保存完整命令、各项返回码和日志；`probe_{a,b,eq}{2,4,8}.log` 保存原始输出。

首轮 A 的全 inactive 路径合法地没有 helper 调用，因此不使用每条路径必须进入 helper 的旧单入口断言。随后 `runner_trace` 对 B2/B4/B8 检查普通 `riscv_f16Add` 的实际进入次数分别恰为 2/4/8，并重跑 eq2 检查至少两个普通 helper 调用；均退出 0、路径 SAT，eq2 差异仍 UNSAT。补充命令、二进制哈希和结果见 `trace_report.json`，没有绕过真实 FP 实现。

### 9.2 已核实的复用接口

- 生产 `V/vext_utils_insts.sail::vector_select_masked(mask, initial_result, new_value)` 已封装 `isla_vector_select`。生产改写优先使用该接口，避免新声明同义 extern。
- 底层 primop 的参数 2 是 false/旧值、参数 3 是 true/新值。顺序不可照普通 `ite(cond, true, false)` 猜测。
- `init_masked_result` 的 SYMBOLIC extra-ops 路径已使用 `isla_init_mask`，保留 start/end、fractional LMUL 与初始目标；继续复用其返回 mask。不能固定 mask、vl、vstart、vtype 或 LMUL 来取得单路径。
- `init_masked_source` 当前仍逐 lane 构造 mask。归约仅改数值循环不能消除其上游分叉，需要单独指定该共享 helper 的 owner 和证明边界。

## 10. 已审定的第一组生产实现边界

architecture 已批准第 10.1 节的第一组 12 个 clause：十个普通算术/FMA/widen execute 和两个比较 execute，以及所需的纯 tuple helper。主 agent 在 P1 快照完成后分配一名 Sol 独占三个 V 源文件；本文作者负责独立复核，不占用生产文件。第 10.3 节其余包仍待独立审定，不能随第一组一并修改。完成类型检查后再冻结下一份 IR。

### 10.1 普通算术、FMA 与比较

1. `V/vext_fp_utils_insts.sail`：为 add/sub/mul/div、四种 muladd 符号组合、min/max、eq/lt/le/gt/ge、widen 提供返回 `(bits_fflags, result)` 的**纯**计算接口。复用现有 `riscv_f16/32/64*`，符号变体维持原 negate 位操作，不新增运算近似。既有带 `accrue_fflags` 的 helper 保留原外部接口和调用者行为，非 SYMBOLIC 的 callback 顺序/次数不能改变。`fp_widen` 的纯接口需显式传 RM，不读取/写入 fcsr。
2. `V/vext_fp_insts.sail`：优先仅修改 `FVVTYPE`、`FVVMATYPE`、`FWVVTYPE`、`FWVVMATYPE`、`FWVTYPE`、`FVFTYPE`、`FVFMATYPE`、`FWVFTYPE`、`FWVFMATYPE`、`FWFTYPE` 十个 execute clause 的 SYMBOLIC 数值循环。先由既有合法性检查、SEW、LMUL 和 opcode match 选定唯一运算，然后每 lane 计算候选值与 flags；结果由 `vector_select_masked` 合并，活动 flags 累计后一次 `accrue_fflags`。不 eager 计算所有 enum 分支，也不修改 guard、编码/汇编或寄存器布局。
3. `V/vext_fp_vm_insts.sail`：`FVVMTYPE`、`FVFMTYPE` 同理，但目标是 bits mask；每位用纯 Bool/bit ITE 保留旧位。不能把整条目标 vmask 的 tail/prestart 行为改成普通向量目标语义。
4. min/max 的纯接口必须将 NaN、正负零及 quiet 比较选择写为 total 位串 ITE；原 quiet NV 规则保持。gt/ge 用 strict Bool 或 ITE 实现原“有 NV 则 false，否则取反”，避免继续以 flags 值分叉。符号分解复用现有 generic 分类，不改内部五 Bool 异常表示。
5. widening lane 需要同时 OR 每个输入转换的 flags 与最后运算 flags，再用活动 mask 屏蔽；即使转换在数值上精确，sNaN quieting 的 NV 也不能丢失。

第一组的聚合 `accrue_fflags` 位于整条指令最终向量写回之前；`init_masked_result` / `init_masked_result_cmp` 及其 mask/tail/prestart 语义保持原样。min/max 新纯 ITE 必须与旧 helper 在未知数据上比较，并保留已审 NaN/正负零位级样例；gt/ge 仍为“NV 则 false”，不能简化成无条件 not-le/not-lt。

数据结果可以提前计算，因为这些接口必须在已合法的格式/RM 域上 total 且无写状态、callback、断言失败或异常。**不能**直接把现有带副作用的 `fp_add`、`fp_widen` 等放入 `ite` 参数，也不能通过保存/恢复 fcsr 伪装纯计算。

### 10.2 状态累计与 trace 边界

对各活动 lane 的 flags `f_i`，最终 fcsr 为 `old | OR_i(ite(active_i, f_i, 0))`，非 FFLAGS 位保持。逐次 `accrue_fflags` 置 Dirty 的条件等价于最终结果与 old 不同：OR 只增不减，一旦置 Dirty 后续仍 Dirty。因此 SYMBOLIC 一次累计保持最终 FS/SD；全部 inactive 或全部 flags 已置位时保持原 FS/SD。其他 mstatus 位不得变化。

此推理仅允许在当前 symbolic callback pure 空体/FD 常量映射的条件下合并调用；普通 C++ 后端仍逐活动 lane 调用。函数调用 trace 与同值写事件数有意变化，应同步日志解释，不能声称等价改写“动态覆盖了原 if 的两侧”。正式测试需另以任意五位 lane flags 与任意完整 fcsr/mstatus 验证该累计关系；小 FP 原型已验证 bits/flags，但未运行正式 CSR helper。

另已完成独立 SMT 关系证明：8 个未知 active 位、8 组任意五位 lane flags、任意 32 位 fcsr 和 64 位 Mstatus，对 XLEN32/64 × 四种 F/Zfinx 配置比较逐活动 lane 累计与一次累计；比较最终 flags、全部 Mstatus 位及断言接受域，8 组均先前置域 SAT、差异 UNSAT。RV32 采用模型实际的 64 位 Mstatus 载体、SD 在 bit31。原型目录中 `aggregate-xlen*-f*-z*.smt2` 保存公式，`aggregate_report.json` 保存哈希与 Z3 输出。它验证了聚合状态方程，仍不替代生产 Sail/IR 的调用和写回验证。

### 10.3 后续独立包与暂不混入的分支

- `VFMV` 可直接对既有 mask 和广播 scalar 使用 `vector_select_masked`。`VFMERGE` 的 body 内 scalar/vs2 选择可用位串 ITE，但它当前 fractional `real_num_elem` 公式是 `n / (-LMUL_pow)`，与 `init_masked_result` 的 `n / (2 ^ (-LMUL_pow))` 不同。不能直接替换整个初始化而静默改变旧语义；这处疑点需独立判定与红例。
- `VFUNARY0`、`VFWUNARY0`、`VFNUNARY0` 中转换很多已直接获得纯 tuple，但部分窄整数饱和适配仍有数据相关 if。应单独审定这些 total 边界，再按同样方式抽出 flags，不能仅删除 lane if 就宣布所有分叉解决。
- `VFUNARY1` 中 sqrt 可复用已迁移的纯 helper，classify 可纯化；Recip7/Rsqrte7 尚含归一化、查表与值分支，本包不能未经审查把它们用于全部 inactive lane，也不能宣称其执行无分叉。
- `V/vext_fp_red_insts.sail` 的 `RFVVTYPE`/`RFWVVTYPE` 保留 `vl==0` 早退且不写目标；按原 lane 顺序逐次 `candidate=pure_op(sum, src[i]); sum=ite(active,candidate,sum)`。不能改成平衡树，也不能为 unordered 另选数值结果。widening 归约仍计转换 NV，再按活动 lane 累计。
- `bfloat16/zvfbfmin_insts.sail`：窄化用原 `riscv_f32ToBF16` tuple，宽化使用现有 `bf16_to_f32` tuple，避免带累计的包装。`zvfbfwma_insts.sail`：VV 的两个转换 flags 和 FMA flags 全部保留；VF 的 scalar 转换 flags 仅在至少一条 active lane 时贡献。允许 symbolic 每 active lane 重复 OR 同一 scalar flags（幂等），非 SYMBOLIC 首 active 的 callback 行为保持。

### 10.4 生产验证门槛

每组先 strict SYMBOLIC/非 SYMBOLIC typecheck，再保留旧模型输入与新 IR 全状态差异检查。至少覆盖全部 inactive、仅首/末 lane active、交替 mask、vstart>0、vl=0、fractional LMUL、tail/mask policy、sNaN 在 inactive lane、预置 flags、FS=Initial/Clean。普通算术/FMA需未知 mask/数值/旧目标的 SAT 与差异 UNSAT；widening补转换 NV，compare补 NaN/正负零，归约补依赖顺序及零 VL，BF16补首 active 的 scalar NV。完整指令的有限 SEW/enum 分支保留，只要求每个选定合法形状不再按 mask 子集指数分叉。最终仍需新 IR、严格配置区域同步与 77 项官方入口复验。

## 11. 已追加审定的 BF16 与顺序归约包

architecture 随后批准本节两包，与第 10.1 节并行；由主 agent 分配不同 owner。第 10.3 节的 unary/estimate 与 VFMERGE/VFMV 仍不因此自动获得写入范围。

### 11.1 BF16 四 clause 与纯宽化 helper

单一 BF16 owner 独占 `bfloat16/zvfbfmin_insts.sail`、`zvfbfwma_insts.sail`、`zfbfmin_utils.sail`：

- 四 clause 为 `VFNCVTBF16_F_F_W`、`VFWCVTBF16_F_F_V`、`VFWMACCBF16_VV`、`VFWMACCBF16_VF`。
- 窄化直接调用原纯 `riscv_f32ToBF16`；宽化调用 `bf16_to_f32`；FMA 可直接调用纯 `riscv_f32MulAdd`，或在第一组纯接口冻结后复用。不能调用 `bf16_to_f32_set_flags` 或原带累计的 `fp_muladd` 作为 ITE 参数。
- 每 lane 的所有转换 flags 和 FMA flags 先 OR，再按最终 mask 屏蔽；循环后一次 `accrue_fflags`，位置在 `write_vreg` 前。结果用已有 `vector_select_masked(mask, initial_result, computed)`。
- VF 保留原外层一次 `F_BF16` 读取及 NaN-boxing。scalar flags 可重复加入每条活动 lane 的 OR，或通过 any-active ITE 一次加入；全部 inactive（含零 VL）不得贡献 scalar NV。普通后端的首 active callback 次数和顺序保留。
- guards、LMUL/EMUL、初始化、目标布局、清 vstart 和已修复的 assembly mapping 均保持原样。

`bf16_to_f32` 虽无状态副作用，当前源码仍有数值 if。仅删除外层 lane if 会把 mask 分叉换成分类分叉，因此其 SYMBOLIC 体一并改为 pure ITE：

```text
nan   = strict_and(exp == all_ones, mant != 0)
snan  = strict_and(nan, mant[6] == 0)
flags = ite(snan, NV, 0)
value = ite(nan, canonical_NaN_S(), v @ zeros(16))
```

原 non-NaN 的 inf 分支和普通分支在位级上均等于 `v @ zeros(16)`。独立 SMT 对所有未知 16 位输入先 SAT、再比较原 signed-mant 判定和新最高位判定，以及 flags/value，差异 UNSAT；另逐一比较全部 65,536 个输入通过。公式 SHA-256 为 `0a0cbd84a261292b5a57e0e7ead58e782d2a502f77d25b00c3729c0c61f9b07c`，保存在原型目录 `bf16_expand_equivalence.smt2`；`bf16_expand_report.json` 记录 Z3 输出及枚举计数。这仍是公式证明，生产 owner 还须执行真实 Sail 新旧 helper 的差异检查，并证明新 helper 未知输入单路径、SAT；非 SYMBOLIC 原 helper 体保持。

复用现成 BF16 用例时，必须保留 inactive/首 active/旧 flags 与全状态观察，特别是 sNaN scalar 但全部 inactive，以及首 active 不在 lane0。不能靠预置 NV 掩盖新异常缺失。

### 11.2 顺序归约与共享源 mask

单一归约 owner 独占 `V/vext_fp_red_insts.sail` 和共享 `V/vext_utils_insts.sail` 的 `init_masked_source` 小范围；不能与第一组的 `vext_fp_utils_insts.sail` 混淆。

- `RFVVTYPE` / `RFWVVTYPE` 保留原 `vl==0` 早退的准确位置；不提前读 seed、不写目标，也不补执行本来未走到的 `set_vstart`。
- `vl>0` 按原 `i=0..n-1` 顺序计算 `candidate=pure_op(sum, src[i])`，再 `sum=ite(active, candidate, sum)`。所有后续 lane 使用已经选择后的 sum，不能并行求和或重排。ordered/unordered 继续使用当前顺序实现。
- widening 的输入转换 flags 与 add flags 先 OR，再按 active 屏蔽。循环后一次累计，随后保留原 `write_single_element` 和 `set_vstart`。全 mask 但 `vl>0` 时仍按原语义写 seed，sNaN payload 原样，不因为提前计算了一个未选中的候选而 quiet 它。
- 共享 `init_masked_source` 保留原 `assert_vector_num_elem`、`assert_lmul_pow`、`get_start_element` 的 Err、end 和 fractional `real_num_elem` 公式与断言顺序。在原 foreach 前，仅于 SYMBOLIC 且 `__isla_use_extra_ops` 时返回 `Ok(isla_init_mask(num_elem, start, end, real_num_elem, vm_val))`；否则执行原循环。不得改其它公共 mask helper 或内存调用者。

`isla_init_mask` 已核对每位为 `start <= i && i <= end && i < real_num_elem && vm[i]`，与原分支链相同。独立 SMT 对 2/4/8/64 lane、任意 signed BV128 start/end/real 和未知 mask 比较每位，四组均先 SAT、差异 UNSAT；这个证明域包含模型实际受限整数域。公式及哈希见原型目录 `source-mask-*.smt2`、`source_mask_report.json`。它验证活动条件，不替代生产 `get_start_element` 错误返回和 helper 调用检查。

顺序加法另有真实 Sail→IR 小原型：未知 mask、全部 f16 源、seed 与旧 flags，RM=0。2 lane 原 if 为4路径、ITE为1路径；4 lane 为16路径与1路径。两种长度分别在所有4/16条旧路径上先 SAT，再验证最终 sum bits 与 flags 差异 UNSAT，分别约1.5/41.8秒（45秒外限、退出0）。4 lane 两种执行约11.8/4.0秒；顺序依赖使 ITE 表达式仍随 lane 增长，不能据此宣称归约是常数成本。`red_probe.sail`、`red_probe.ir`、`red_report.json` 和对应日志保存实际命令、哈希与结果。

生产门槛复用向量负责人已验证的 forward/reverse/mask-lane1 顺序辨识例、全mask sNaN seed、零VL无写，以及新增40条 normal/widen × ordered/unordered × source/seed NaN 例。后者生成器为 `tools/solve_vector_coverage/reduction_hazards.py`，旧 d012 输入 SHA-256 `06a33c01bfb780e582c71a78af9ebae9e4ee3bde990a3794c67801fca9f7997d`，属于旧版本证据；P2须重新运行。至少观察全部 vector registers、fcsr、Mstatus 与 vstart，不能只检查目标第零元素。

## 12. 第一 owner 顺序追加的 move/merge 与转换

以下是第 10.3 节之后新批准的范围，仍由第一组 owner 顺序编辑其已持有的两个 FP 文件，不新增并写 owner。实际纯接口已经统一为 `fp_*_pure`，输出顺序 `(flags, bits)` 或 `(flags, bool)`，宽化显式传 RM；`_with_flags` 不是现行接口名。

### 12.1 Move/merge 与采样绑定退出

architecture 已批准：`VFMV` 的 SYMBOLIC 循环替为 `vector_select_masked(mask, initial_result, vector_init(rs1_val))`；`VFMERGE` 保留原 start/end、get-start 错误、SEW/LMUL 和 fractional `real_num_elem` 公式，以 `isla_init_mask(n, start, end, real, ones())` 得到 body mask，先按 vm 在 vs2/scalar 广播之间选择，再按 body mask 在旧 vd/候选之间选择。非 SYMBOLIC 原循环保留，不引入 flags 或 `accrue_fflags`。

原 merge 的 fractional 公式与通用 mask 不同，但在 `0 <= vl <= n / (2 ^ -LMUL_pow)` 时，end 已提供更强界限。独立整数 SMT 对 LMUL_pow=-1/-2/-3、任意非负 n、满足此界限的 vl、任意 start/i 证明两公式的活动谓词差异 UNSAT，前置域 SAT；见原型目录 `merge-fractional-*.smt2` 与 `merge_fractional_report.json`。此结论有明确的合法 vl 前提，不用于消除其它注入状态；本改写仍保留原公式，避免混入无关域变化。

源优化与动态回归完成后，集成人从 `isla/scripts/run.mk` 删除 `solve-VFMERGE`、`solve-VFMV` 两条 `EXECUTION_LIMITS_CONFIG` 绑定，保留各自 `ISA_CONFIG`。最小迁移可暂留两份 TOML 并清楚标为未启用历史配置，维持既有79配置同步流程；是否删除文件及调整清单数量由主 agent 统筹。不能只移除 lane region 而继续保留全调用树 `max_forks_per_branch=1`。

正式验收同时核对实际命令没有这两项采样配置，运行 manifest/summary 没有 sampling、concretize 或 region quota 命中；仅 dry-run 少一个参数不足以宣布穷尽。若外部或 CLI 超时，仍记录 incomplete。保留未知 mask、vl/vstart、policy、fractional LMUL 与寄存器选择，全状态回归包括零VL及 prestart/tail。

### 12.2 三类转换与窄整数适配

主 agent 已批准在当前候选继续修改 `VFUNARY0`、`VFWUNARY0`、`VFNUNARY0`：保持原操作码/格式/RM 选定关系，从原各 arm 提取纯 tuple，按 mask 合并结果和异常，循环后在写回前统一累计；固定 RTZ 与 ROD 的特殊 RM 保留。

六个仍有内部数据 if 的窄整数适配为 `riscv_f16ToI16`、`riscv_f16ToI8`、`riscv_f32ToI16`、`riscv_f16ToUi16`、`riscv_f16ToUi8`、`riscv_f32ToUi16`。SYMBOLIC 先照旧调用32位转换得到 `(flag, sig32)`，再：

- 有符号目标宽 D：`fits = sig32 == sign_extend(sig32[D-1..0])`；不 fits 时按 sig32 bit31 选择目标最小/最大值，异常**覆盖为 NV**；fits 时保留原 flag 与截断位串。
- 无符号目标：高 `[31..D]` 非零则饱和全1并覆盖 NV，否则保留 flag 与截断位串。
- 使用位串等值、strict Bool 与 ITE，不再经过 `signed/unsigned` 整数比较的执行器试探求解。非 SYMBOLIC 原函数体保留。

独立 SMT 对任意 sig32 与任意旧五 flags、D=8/16 × signed/unsigned 四组，比较原有上下阈值与新位串判据，结果位和全部 flags 均前置 SAT、差异 UNSAT。公式及哈希见 `narrow-{signed,unsigned}-{8,16}.smt2`、`narrow_report.json`；生产仍需真实转换 helper 的未知输入与边界值测试。

**不能无条件提前拒绝 SEW8 的不支持 arm。**`VFWUNARY0` 的 XU_F/X_F/F_F/RTZ_XU_F/RTZ_X_F，及 `VFNUNARY0` 的 F_XU/F_X/F_F/ROD_F_F，原 `Illegal_Instruction` 位于活动 lane 内；全 inactive 会正常走后续写回/清 vstart。可在确定不支持形状时仅于 `mask != 0` 拒绝，否则保初始结果并继续原后续状态；也可该形状保留原循环（第一活动 lane 即拒绝，路径至多线性）。不能因为 encoder 通常排除了它们就悄悄修改 direct execute 的域。

architecture 随后冻结 `VFUNARY1` 本轮仅追加 sqrt/class：sqrt 复用纯 `riscv_f16/32/64Sqrt` tuple；class 复用 `float_decompose` 并用 strict 纯位串谓词拼 onehot，位序为9 qNaN、8 sNaN、7 +inf、6 +normal、5 +subnormal、4 +0、3 -0、2 -subnormal、1 -normal、0 -inf，flags=0。不能调用短路 `float_classify`。门槛为 H/S/D 各10类位级例，以及未知输入的新旧分类关系前置 SAT、差异 UNSAT 和恰好一个输出位为1。

Recip7/Rsqrte7 保留原 masked loop，以外层有限 enum 分派与新 sqrt/class 路径分开。后两者有分类、归一化、查表及数据分支，不能仅因纯 tuple 就对全部 lane eager 执行并宣称消除指数分叉；P1 代表诊断用于判断是否需要下一份独立设计和候选，不在本轮已经冻结的追加范围中静默修改。

## 13. FD 与第一组 helper 的独立实施复核

P1 IR `f5141217f2695fb53a0584c1bc7dfa059eac15df51c07ae3f02307099e4b4a61` 已完成实际 `accrue_fflags` 验证：旧 fcsr 全32位、Mstatus 全64位和输入五 flags 均未知；changed 两域分别 SAT，实际函数只有一条完成 SAT 路径，完整 fcsr/Mstatus 与状态关系差异 UNSAT。FADD.S 无新异常、FS=Initial 的旧红例在该 IR 转绿。具体读写矩阵涵盖两入口、fast/普通臂、32 FPR 哨兵、FS三态与同值写；独审发现测试曾用十六进制构建五位参数导致实际 BV4/BV8，owner 已修为 `B129::new(value,width)` 并校验长度后重跑通过。Ext_F=false 的真实源提取 fixture 确认旧 fast 读取接受而普通拒绝，新两入口 fast/普通均拒绝。完整证据由 [FD实施记录](solve-fix-fd-state.md) 维护；这是 P1 定向放行，非77全组通过。

第一组 min/max 初稿调用旧 `f_is_*` 时仍有内部短路分叉，独审后已改用 strict `ieee_is_nan` 与正负零位串等值。生产新 helper 提取 fixture 对 f16/f32/f64 min/max/gt/ge 做未知值测试：新函数各单路径 SAT，与去掉状态累计后的旧数值体在全部旧 fixture 路径上差异 UNSAT；f16 NaN/sNaN/正负零定向完整 flags 通过。25入口日志在目录标识 `isla-vector-helper-probe-20260926`；IR SHA-256 `80e3da18f6cffcef3e1ddd7e3ea7829c4dd3a2e6f22841ef976e265884748a9a`。旧 fixture 将分类器替为等价 strict 分类，因此其 min/max 的12路径、gt/ge的2路径不是旧生产 helper 的实际路径数。该隔离证明不覆盖完整指令状态，P2仍需全状态回归。

## 14. P1 真实负载发现：纯等值仍会主动求解

### 14.1 诊断结果与根因

目录标识 `isla-float-official-p1-diagnostic-20260926` 保存同一 P1 IR、当前运行器快照、完整 itrace 的三目标诊断。预算为外部90秒、CLI80秒、单次SMT15秒，三目标并发、每目标2线程；实际命令及源码/二进制哈希见其中 `evidence/manifest.json`。它不是正式77项验收，也不适合与无完整 trace 的旧运行直接比较性能。

| 目标 | 退出与已记录终态 | 判断 |
| --- | --- | --- |
| `F_UN_RM_FF_TYPE_S` | 外限124；2 retire、3 illegal、1 nonencodable、10 error | 10个 error 均为 `fdext_regs.sail` 的 `old != f`，原P1行545，15秒 SMT timeout。 |
| `VFUNARY1` | 外限124；149 illegal、3 nonencodable | 未记录 retire 或显式 SMT error；主要仍处于合法性检查，不能归因于 Recip7/Rsqrte7。 |
| `FVVMATYPE` | 外限124；127 illegal、3 nonencodable | 未记录 retire 或显式 SMT error；不能以此宣称纯lane性能已验收。 |

P1 `zaccrue_fflags` 中 `changed` 确实已无数据相关 Jump，但其生成 IR 调用 `zneq_bits`。`isla-lib/src/primop.rs` 的 `eq_bits`/`neq_bits` 使用 `binary_primop!`，符号输入进入 `try_concretize_bool_exp`：先查询否定条件，再查询正条件，尝试将 Bool 具体化。因此，把 `if` 改成 ITE 并不足以消除这些查询；flags 若来自 sqrt/FMA，查询会包含真实浮点表达式。先前仅传独立未知五位 flags 的状态探针验证了状态关系，却没有覆盖这种表达式成本。

既有 `eq_anything` 对符号标量直接 `define_const(Eq(...))`；`not_bool` 直接构造 Bool 否定，均不执行这两次 SAT 试探。Sail 已导出 pure `eq_anything`。架构审核批准 SYMBOLIC `changed = not_bool(eq_anything(old, f))`，保留所有状态方程、扩展断言域和非 SYMBOLIC 体。修改门槛是生成 IR 仍调用 generic equality、实际FD状态回归通过，以及真实 sqrt 不再在该位置产生 timeout；本节记录根因时修复尚待该动态复验，不能先记绿。

### 14.2 纯数据 helper 的同类检查

下表按当前生产源码与已生成小IR核对；这些是明确的主动查询入口，不表示每处都已动态观察到 timeout。

| 位置 | 数据来源与生成行为 | 局部修正范围 |
| --- | --- | --- |
| min/max 的8个正负零判断 | 普通 `==` 生成 `eq_bits`；归约 sum 可为上一 lane 的 FP 结果。 | SYMBOLIC纯 helper 的显式 generic equality。 |
| gt/ge 的 NV 位判断 | `fflags[4] == 1` 直接依赖比较异常表达式。 | 保持 NV 时 false 的规则，仅换比较构造。 |
| class 的符号及 exp/mant/quiet 判断 | `float/common.sail` 的 `is_all_zeros/is_all_ones/is_highest_zero` 内部也调用 `eq_bits`。 | 保留 `float_bits/float_decompose`，在纯 helper 中构造无查询的字段比较。 |
| 六窄整数适配 | 6个 overflow 等值和3个 sign 等值依赖 FP→32位整数结果。 | 保留饱和值及 NV 覆盖规则，仅换纯比较。 |
| 既有 `ieee_is_*` 与异常计算的 sign 判断 | 共享分类间接调用上述 common 比较；顺序归约可传入 computed FP。 | 单独审核模型纯数据范围；不修改上游 common 库、全局 primop 或合法性 guard。 |

本轮不得回退内部五 Bool 异常表示，也不修改 native RM、泛型类型、指令选择、合法性检查或运行域。每个修改后的生产 helper 仍需绑定源码与 IR 哈希，未知输入先证明 SAT，再证明结果/flags 差异 UNSAT，并把新入口单完成路径作为测试断言。第一组 runner 现已加入 `paths > 0` 与 `new_*`/`probe_new_*` 恰一完成路径断言，避免空路径或仅日志展示被误算为 PASS。

架构随后批准模型内统一的局部边界：既有 `ieee_is_*` 五分类直接对 `float_decompose` 的字段使用 generic equality；同文件 add/sub/sqrt/FMA 的数据 sign 等值，以及三个 `softfloat_symbolic_f16/32/64.sail` 的饱和 sign 等值同理。V1 min/max 继续复用 `ieee_is_nan`，不另造重复分类接口。BF16 owner 同步只改 SYMBOLIC `bf16_to_f32` 的 exp/mant/quietbit 三处。RM 判断、模型算法、五 Bool facts、普通后端体均保持。mask 活动位比较本轮保留；其作用是选择活动 lane，尚无实际查询超时证据。

### 14.3 同 IR、同未知 FP 输入的比较 A/B

为把根因与完整指令调度分离，另建目录标识 `isla-fp-equality-query-probe-20260926`，复制并冻结P1所用七个生产依赖；`manifest.json` 记录各源哈希、Sail生成命令、plugin与runner来源。四入口置于**同一个 IR**：f16/f32各两入口均令 `raw = undefined`，调用同一普通生产 `riscv_fNSqrt(0b000, raw)`，仅返回条件不同：

```sail
// 旧入口：会由 neq_bits 主动查询复杂 flags 条件。
0b00000 != flags
// 新入口：构造语义相同的 Bool 表达式，不主动求解。
not_bool(eq_anything(0b00000, flags))
```

| 入口 | 22秒外限内结果 | 完成路径与可行性 |
| --- | --- | --- |
| `old_sqrt16` | 124，22.036秒 | 未完成。 |
| `new_sqrt16` | 0，0.107秒 | 1完成路径，SAT。 |
| `old_sqrt32` | 124，22.081秒 | 未完成。 |
| `new_sqrt32` | 0，0.108秒 | 1完成路径，SAT。 |

IR SHA-256 为 `da62c60b0a4b5d772452af95977e5bea5c8e859fc69996981a19c79e00a416e8`；旧入口实际调用 `zneq_bits`，新入口调用 `zeq_anythingzIB5zK`（extern `eq_anything`）及 `znot_bool`。全部四次运行使用同一二进制、IR及预算；四进程并发是本次设置，数字只表示该次隔离对照。

runner 源码为可提交的 [runner.rs](../../sail-riscv/test/symbolic_fp/solve_vector_lanes/runner.rs)，SHA-256 `1f64e1e1797cfa63e8ce71d5b3174e48c4d369352a0d12cf7e2d2c023498b3de`，与实际编译临时工程的源码逐字相同；可通过 [build_runner.sh](../../sail-riscv/test/symbolic_fp/solve_vector_lanes/build_runner.sh) 用当前 Isla库重建。复现实验先按外部 `manifest.json` 的命令生成同源 IR，再逐入口执行：

```sh
bash sail-riscv/test/symbolic_fp/solve_vector_lanes/build_runner.sh "$RUNNER_BUILD" isla/isla-lib
timeout 22s "$RUNNER_BUILD/target/release/vector_helper_runner" "$PROBE_DIR/probe.ir" "$PROBE_DIR/new_sqrt32.names"
```

`PROBE_DIR` 指向上述冻结目录，names文件每个仅含同名入口；另外三个入口命令在 `report.json`。runner 会先要求所有完成路径 SAT，再对 `new_*` 硬断言恰一条完成路径。此对照仅验证表达式构造成本，未声称旧完整执行结束或完成任意 sqrt 的数值证明；正式 sqrt 指令、新FD状态回归及77项最终结果仍须在新候选 IR 上复验。

### 14.4 后续源码与小 IR 复核

V1 的 generic equality 修改经独立静态复核：class 的 quiet 位为 f16 bit9、f32 bit22、f64 bit51，sign/exp/mant 的等值与 onehot 位序保持；六窄适配的 overflow、正负饱和值与 NV 覆盖方向保持。Recip7/Rsqrte7 和 unsupported SEW8 仍由外层有限形状选择原 masked loop；全 inactive 的非法格式接受域未被提前改变。49项 helper 验证增加三格式未知分类、恰一位 onehot 与每格式10种类别、六窄整数未知输入；旧 core 上的结果仍为中间验证，统一 core 冻结后须重跑。

BF16 generic 小修的小 IR `63147a86d0e92ba7b0667fcbc51deb29b54bb4dcce893c141de8b6b3ad35d2b6` 已独审：`zbf16_to_f32` 函数体恰好三个实例化 `eq_anything`，对应8位exp、7位mant和1位quiet bit，没有 `eq_bits`/`neq_bits`；实际生产源码 SHA-256 `2c0693f4c578e6b237cc5de39d4a0014b6e46580cc69f66efdeb00f1785c6f07`。未知16位输入的每个旧新比较路径均 SAT、差异 UNSAT，新入口恰一完成路径。详细证据仍由 [BF16实施记录](solve-fix-bf16-lanes.md)维护。

共享 core 的 FMA 外层 sign Bool 不等在原 IR 中也经过 `neq_bool`→`eq_bool` 主动查询。直接将它换成泛型 Bool equality 遇 Sail singleton 类型错误；批准的最终形式使用 strict Bool XOR：`or(and(p,not(c)),and(not(p),c))`。这只改布尔表达式构造，不改变无穷乘积与加数异号的 invalid 判据；须在新 IR 中检查该位置无 `eq_bool/neq_bool`，不能为通过类型检查回退旧的急切比较。

统一 core 最终冻结为 `6a53eb013721787194a4fb370974e785fd0751f35f9d6cb66bb360ff82d6faeb` 后，V1 已重新完成49入口验证。独审重新运行生产提取器至外部目录标识 `isla-vector-helper-final-independent-20260926`，确认新生成 fixture 与受测 fixture 逐字相同，全部依赖哈希与当前源一致；实际 IR `6dbb358e4e8f401bf7dc99285391224cf396ebffb9889c3fb6c67e0a73e75d8f` 的12个选定纯 helper 无 `eq_bits/neq_bits`，class/minmax/gtge 也无 Bool eager equality。日志与强断言确认全部49入口，class 三格式分别覆盖原10路径、未知新入口1路径、exact-onehot 和10类定向结果。生产 utils SHA-256 为 `8a642a1d4c317e7908f4a0951e14835a555792716b9997165c0ebd919998379d`；详细记录见 [V1实施验证](solve-fix-vector-lanes.md)。

共享 core/FD 四文件的27入口同源等价也已独审通过，目录标识 `isla-float-pure-compare-20260926`。三种格式各验证一次五分类，以及 Add/Sub/Sqrt/FMA/四种整数转换；原始位串未知，RM由未知三位输入满射至合法0–4。runner 对完整新旧 flags 和 bits 配对，先断言完成域 SAT，再断言任一输出差异 UNSAT，并强制唯一完成路径；27个逐例日志均符合。四份新快照逐字等于当前生产源；分类调用闭包7个函数和24个sign/饱和函数本体的 IR 检查无主动 BV/Bool 等值。IR SHA-256 `a529bc743fe4b3a170b06f0fbd754da184a44f96f79a8d47c4df49eb885030a3`，结果表 SHA-256 `0c7bf69a52eccf71e89aeef82d273a43f855af64e2c2550dcb6a9b6e45683273`。这是局部纯化等价的放行，完整P2与277未知入口、正式77项仍由集成回归验证。

## 15. P2 向量前端诊断与固定片段丢失

### 15.1 实际到达范围

P2 IR `d86655a…` 的 compact itrace 诊断目录位于 `isla/target/float-solve-evidence/p2-vector-diagnostic-20260926/`，两目标均使用外部90秒/CLI80秒/SMT15秒、2线程、并发2，无活动workaround：

| 目标 | 已记录终态 | 实际到达 |
| --- | --- | --- |
| `VFUNARY1` | 161 Illegal、3 non-encodable，外限124 | 所有终态的函数集合均未含 `riscv_f*`、向量寄存器读取或结果初始化；主要停留在 `get_num_elem` / `illegal_fp_normal`。 |
| `FVVMATYPE` | 131 Illegal、3 non-encodable，外限124 | 同上，尚无纯lane运行证据。 |

compact 输出仍分别约184.3MB/151.6MB；记录89.7万/72.9万条branch edge，其中 wrapper 的 decoder阶段约63.8万/51.7万、encoder阶段约21.6万/17.9万，execute阶段约4.3万/3.4万。**这些计数包括每条终态重复保存的共享前缀，不能相加当作进程实际CPU成本。**外部分析目录标识 `isla-p2-vector-hotspots-20260926` 的 `report.json` 保留逐case函数集、边数、阶段和末尾位置。

具体的有限前置分叉已经确认：`zencdec_backwards` 的 LPAD arm 在运行时pc322先调用 `currentlyEnabled(Ext_Zicfilp)`，由 `get_xLPE(cur_privilege)` 分权限模式；随后才判opcode是否 `0010111`，而本次向量编码的opcode固定为 `1010111`。其它逆mapping同样可能先检查变体/寄存器/RM，再排除不匹配的固定字段。`assert_lmul_pow` 还按七种LMUL值分叉。现有证据支持有限枚举组合与重复前缀成本，未发现本轮不收敛来自无限状态循环，也不能据未见Retire判合法域不可达。不能为了减少路径跳过真实decoder、改变guard调用顺序或固定运行态。

### 15.2 SMT 成本的独立观测

系统 `perf` 因 `perf_event_paranoid=4` 无法取得事件，本轮未改系统设置。改用运行器已有路径诊断：同一P2二进制、IR、配置和完整符号domain，保持2线程、SMT15秒；仅把诊断路径预算设为1秒、外限30秒，并取消itrace文件输出。目录标识 `isla-p2-path-profile-20260926` 保存精确命令和日志。**此预算只用于触发现有耗时统计，不是正式验收或性能PASS。**

64条路径在decoder阶段触发统计，每条累计370–686次正常SMT调用，SMT用时占该路径active_wall的80.2%–91.3%；没有单次SMT操作达到15秒上限。最高频调用点 `12185` / `12193` 对应实际 IR `encdec_rounding_mode_backwards_matches` 的 `000` / `001` 等值比较，某条路径分别104/52次。对 FVVMATYPE，编码bits14..12已固定为 `001`，这些比较仍需要SMT恢复常量。其它频繁项包括 `width_enc_backwards_matches`。统计包含继承前缀，不能将64条耗时再次求和当作进程耗时。

源码定位是通用表示：当前 `append(Symbolic, Bits)` / 反序会创建整体 `Symbolic(Concat(...))`，随后固定范围slice即使对应已知常量也返回 `Symbolic`，等值再走 `try_concretize_bool_exp`。已有 `MixedBits` 和 `mixed_bits_slice` 可以保留固定片段并直接返回具体位串，因而优先复用它们；无需改Sail模型、decoder或全局等值策略。

### 15.3 表示的单因素原型与候选边界

外部目录标识 `isla-mixed-encoding-probe-20260926` 保存同一Sail→IR的两个探针：输入为未知25位前缀拼固定7位opcode `0x57`，观察低7位slice，或重复200次同一opcode判断。runner分别使用当前真实 `append` 返回值，以及手工构造的**现有** `MixedBits` 两片段作为函数参数，不修改生产primop。

| 输入表示 | slice实际返回 | 200次判断中的SMT调用 |
| --- | --- | --- |
| 当前 append | `Symbolic` | 200次，约8.11ms累计SMT。 |
| 现有 MixedBits | 具体 `Bits(7,0x57)` | 0次。 |

两种表示的探针均唯一完成路径，先SAT再证明观测结果差异UNSAT。该原型验证固定opcode观察与查询成本，尚不替代任意完整位宽/片段组合的等价门槛。

架构预审的最小候选限于：`Symbolic + 非空Bits` 及反序产生两片段MixedBits，继续复用既有 MixedBits append 路径；纯Symbolic+Symbolic与纯Bits+Bits保持。配套必须修 `mixed_bits_slice(length=0)` 返回具体零宽Bits，不能因扩大MixedBits使用而引入空segment列表或SMT BV0。生产实施前先TDD，覆盖片段顺序、两方向、连续追加、跨片段/全宽/末端/零长slice、动态及有符号索引、空位串与超过宿主最大宽度，并对未知输入证明完整结果与原Concat关系SAT/差异UNSAT；真实16/32位编码与decoder结果也须一致。最终还须重跑P2官方代表，不能用此微原型声称全组已收敛。

### 15.4 最终表示修复与真实 decoder 独立证明

生产 `primop.rs` 冻结 SHA-256 为 `6c6d5a4248d9874405bbc48f850f5c32b77e60f0762212244e1a173fa13f4a20`。除两条 append 臂外，配套处理零宽 slice、MixedBits 两侧追加空串，以及固定索引/长度转换的内部不变量：先保留原零长结果，再用 checked conversion 防止 `±2^32` 截断成0；正长度越界直接失败。动态符号索引仍走原 SMT 路径。这些错误输入没有合法的原 Symbolic Extract 语义，不能把新增 fail-stop 描述成所有错误诊断逐字不变。独审确认没有修改 Sail decoder、guard 顺序或运行态约束。

独立探针和最终证据保存于 `isla/target/float-solve-evidence/mixed-bits/decoder-proof/`，其中 `README.md` 给出重建命令，`manifest.json` 绑定库、源、配置与IR；`results.json` 的 SHA-256 为 `040db3095c61d7603d8805d39bc56dda42a8b8447bee6509c87bd39b04c2d40b`。探针链接与最终运行器同次构建的 Isla 库，使用真实 `zencdec_backwards` / `zencdec_compressed_backwards`；同一组未知编码字段分别组成旧整体 Concat 和实际新版 append。它直接调用现成 `RV64::setup_pre_state`，由实际 IR 的 `hartSupports` 得到 S/U=true、H=false 的 M/S/U 合法域，保留该入口完整 mstatus、向量运行态和寄存器未知域，没有固定单权限或单 vtype。

每个形状先证明两种完整编码 SAT、差异UNSAT，再双向逐首轮完成路径携带同一 solver checkpoint 执行另一表示；完整返回构造器及全部 payload 差异必须UNSAT。任何执行错误、未完成、第二侧无完成路径或架构寄存器写入均使测试失败。

探针初始化采用 `initialize_architecture(..., AssertionMode::Optimistic, false)`，未运行正式入口的 `assertions_to_jumps` 转换。因此它与R1相同的是直接复用的初态符号化和合法性约束，不能声称所有初始化/assert模式都与官方入口一致；比较发生在同一探针运行器的两种输入表示之间。

| 编码形状 | 编码未知量与明确常量 | 每方向完成路径／比较数 | 完整返回分布 | 进程墙钟 |
| --- | --- | --- | --- | ---: |
| C.ADD家族16位 | rsd、rs2共10位未知 | 11／11 | C_ADD 5、C_EBREAK 1、C_JALR 1、C_NTL 4 | 12.816秒 |
| FADD.S 32位 | rd5位未知；rs1=1、rs2=2、RM=1 | 12／12 | F_BIN_RM_TYPE_S 6、ILLEGAL 6 | 112.295秒 |
| 保留opcode32位 | rd5位未知；opcode=0x7f，其余位为0 | 6／6 | ILLEGAL 6 | 80.370秒 |

三项均以120秒外限退出0，总计58对先SAT后完整差异UNSAT。IR仍是P2 `d86655a415441ad17533742b9d0ee726b43b64acaf2c0fc0754d27979c7859a9`，配置 `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`，探针二进制 `630a063cd394c38a09817d8bad92f04e6fbb591944e70d14bae92143a65fe91a`。初稿另试FADD的18位未知字段及保留opcode的25位未知字段，120秒未完成，保留于 `initial-noncompletion.json` 和原日志，未算通过；这些初步运行没有最终库完整绑定。定向编码形状仅是本证明范围，不改变正式求解输入域。耗时包括两种表示及证明，不能当作性能比率。

源码与测试独审还确认：连续 Mixed+Mixed 拼接保持顺序；B64承载71位、B129承载135位的完整位串比较先SAT再UNSAT；动态128位有符号索引在全部合法0–12域上与旧切片结果一致；Model/FmtVal现有出口可处理具体化后的MixedBits。完整AST等价使用 `eq_anything`，没有比较可能因片段显示形式而变化的诊断字符串。局部primop测试67/67通过；整套库测试另见实现负责人记录，不能从本地子集外推全库PASS。此节放行通用表示优化的所述语义边界，正式77项与最终新IR仍需统一验收。

## 16. c5 终态物化、看门狗与向量有限分叉的实测

### 16.1 版本与测量方法

本节证据位于 `isla/target/float-solve-evidence/materialization-timing-c5cbb-20260926/`。它从 `official-c5cbb-20260926-204047/stage` 复制运行器、IR 和配置，仅改诊断副本。IR 为 `c5cbb0bbdaa9369b669aa7330531bfb1a0cf1ef7d905b071f14f510d10c7385c`，FD 配置为 `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`，release 开启 `itrace,smt-thread-interrupt`。各阶段源码、二进制和诊断工具哈希在 `evidence/profile-baseline-hashes.json` 与 `profile-cache-manifest.json`。同副本继承旧 FmtVal，因此本节只给性能与缓存一致性证据，**不记正式指令或输出语义 PASS**。

第 15.4 节关于 FmtVal 出口的旧放行仅覆盖当时样例；后续已发现具体 B129 宽于 64 位的输出错误，该泛化结论不再成立。修复与新回归见[宽位输出修复](solve-fix-fmtval.md)。本节不将旧诊断输出作为新运行器功能验收。

接续时实际检查发现 `evidence/exit-code.txt` 已为 0，最后一轮 FLI_S 有 97 完整终态、`execute_all=5.908s`；没有复现所传递的中间 exit 2。原 `make.log` 和 `instrument.py` 均保留。随后通过[分层计时工具](tools/materialization_profile.py)添加计数：

- 每阶段记录墙钟、真实工作线程的累计 SMT 计数；这些计数不随路径 checkpoint 继承，避免把共享前缀重复计为 CPU 开销。
- SMT wrapper 同时量全部调用时间和内部原始 `Z3_*` FFI 时间；差值包含 watchdog 的创建、握手、完成通知、join 与线程调度，不把整个差值都声称为纯 CPU。
- trace 分别量终态渲染和异步 writer 的 `writeln!`；后者是交给操作系统的写入时间，未执行 fsync，不能解释为持久化落盘延迟。
- 所有诊断运行均为单目标、2 worker、外限 300 秒／路径 270 秒／SMT 30 秒、`qfaufbv`、完整 trace 和原 102 寄存器状态，不启用采样或收窄输入域。编译与其他团队任务仍可能争用主机，所以单轮墙钟只作实测信号。

[汇总工具](tools/materialization_summary.py)输出阶段时间与 SMT 计数。阶段总和是 worker 区间之和，两个 worker 可以重叠；`collector` 包含其各子阶段，不能再相加。只有 `execute_all` 是整次执行的墙钟。

### 16.2 完整 VFMVFS 与 300 秒 VFMV 的基线

VFMVFS 自然退出 0，255 终态为 63 Retire、189 Illegal、3 不可编码；252 条架构终态全部输出 102 字段的完整 pre/post。VFMV 仍外限 124：在最后一个完整 collector 边界计到 3280 条（3 Retire、3274 Illegal、3 不可编码），末尾两个正在物化或写 trace 的终态不能算完整结束。

| 量 | VFMVFS 完整组 | VFMV 外限组 |
| --- | ---: | ---: |
| `execute_all` 墙钟 | 17.934s | 未完整；进程约 301.12s |
| collector worker 区间之和 | 23.302s | 351.719s |
| legacy pre | 2.500s | 35.591s |
| 给汇编构造具体 pre registers | 4.036s | 57.740s |
| 完整 pre 输出 | 4.154s | 58.451s |
| 完整 post 输出 | 4.083s | 58.890s |
| ModelEval 次数 | 157,648 | 2,042,611 |
| ModelEval wrapper／原始 FFI | 14.729s／0.251s | 210.099s／3.124s |
| trace render | 2.357s | 34.355s |
| trace writer | 0.419s | 7.800s |
| trace 字节 | 377,001,171 | 4,370,043,077 |

证据分别为 `evidence/profile-VFMVFS.{log,json}` 与 `profile-VFMV.{log,json}`。表内 SMT 累计在已观察的工作线程快照截止，外限最后的未完成调用不包含在内。VFMV 运行期间有诊断编译和旧 trace 分析，不能与原官方批不同负载下的终态数直接求加速比。

源码和计数共同解释重复来源：`materialize_finished_case` 先取过滤的 legacy pre，再把全部 pre 具体化给汇编打印，随后又对全部 pre 与 post 求值。完整 102 字段的一轮实际是约 169 次 ModelEval：128 位寄存器还会对两个 64 位分块求值，enum 还有 recognizer 求值。VFMVFS 的 `pre_regs_102` 与 `complete_pre` 各为 42,588 次，即 252×169。所有这些调用当前都创建、握手并回收一个看门狗线程。VFMV 没有复杂 FP 数值计算，仍有约 207 秒 worker 时间花在 ModelEval 的 wrapper 与调度，故复杂 FP 不能解释这部分成本。

### 16.3 最小缓存实验与实际边界

[缓存诊断工具](tools/materialization_cache_probe.py)只在每个 `Model` 内缓存 `get_var` 已成功返回的具体 `ModelVal::Exp(Bits64/Bits/Bool/Enum)`，保存 typed clone。Arbitrary 和任何错误均不缓存；`set_complete_model` 的标志切换清空缓存；`get_exp` 原路执行，缓存不跨 Model、solver 修改或任务复用。没有移除 timeout、修改 solver 参数或减少状态字段。

诊断单测 2/2 通过，覆盖 Bool、enum、64/129 位 BV、MixedBits 消费、complete 标志切换、新 Model 隔离、Arbitrary→`get_exp` completion 后再读取，以及重复 Unbound 错误未入缓存。初版测试错误地假定非 completion 的 `get_exp` 会补未赋值变量，因此失败；修为显式 completion 后通过，原失败日志 `cache-tests.log` 保留，最终为 `cache-tests-final.log`。本诊断未做动态 timeout 注入。后续生产缓存已由Astra核定 `get_ast(...)?` 在插入前传播所有错误，包括Timeout；稳定的unsupported sort和Unbound负例另有动态测试。Timeout只按控制流结构证明不缓存，不记动态PASS，见[生产缓存记录](solve-fix-model-cache.md)。

另开启 `DIAGNOSTIC_MODEL_CACHE_VERIFY=1`：每个缓存命中都按原 `get_var` 再求值，断言两个完整 typed 表达式相等。VFMVFS 全部 255 终态运行退出 0，见 `cache-verify-VFMVFS.log`。跨进程比较时 252 个 `path-signature` 全部吻合，但 39 条 witness 的可自由选择状态不同；这是独立模型选值存在差异的观测，不能据此宣称 JSON 逐字等价。缓存一致性的直接证据是同一 Model 内逐次原求值比较。旧 FmtVal 的已知缺陷仍然适用。

| VFMVFS 同域同 trace 单轮 | 无缓存 | 有缓存 |
| --- | ---: | ---: |
| 完整终态（Retire／Illegal／不可编码） | 63／189／3 | 63／189／3 |
| 执行墙钟 | 17.934s | 13.771s |
| collector worker 区间之和 | 23.302s | 14.912s |
| ModelEval 次数 | 157,648 | 73,100 |
| ModelEval wrapper／FFI | 14.729s／0.251s | 7.165s／0.104s |
| 完整 pre 输出时间／ModelEval 次数 | 4.154s／42,588 | 0.025s／0 |
| 完整 post 输出时间／ModelEval 次数 | 4.083s／42,525 | 0.241s／2,079 |

ModelEval 调用减少约 53.6%，collector 区间减少约 36.0%。有缓存的 post 2,079 次恰为 63 条退休路径×33：FPR 快速写回为 32 个 FPR 建立新符号，另有 Mstatus；Illegal 的未改寄存器直接复用同 Model 值。缓存后仍有约 7.06 秒 ModelEval wrapper 非 FFI 时间，占 collector 总区间约 47.4%，主要来自 legacy pre 和第一次完整 pre。不能为继续提速改变 legacy arbitrary 过滤语义。

VFMV 随后使用同一 300 秒预算、完整输入域和 trace 做缓存组。该组仍退出 124、没有最终 JSON，不能把更多终态视为整项通过。证据为 `cache-VFMV.{log,json}`：

| VFMV 300 秒诊断 | 无缓存 | 有缓存 |
| --- | ---: | ---: |
| 完整 collector 数 | 3280 | 3836 |
| 其中 Retire／Illegal／不可编码 | 3／3274／3 | 18／3815／3 |
| 每 collector 平均区间 | 107.231ms | 73.050ms |
| 每条物化平均区间 | 82.738ms | 48.065ms |
| 每条完整 pre／post 平均区间 | 17.831／17.965ms | 0.101／0.169ms |
| ModelEval 次数 | 2,042,611 | 1,075,247 |
| ModelEval wrapper／FFI | 210.099s／3.124s | 112.469s／1.627s |
| trace render／writer | 34.355s／7.800s | 40.894s／8.185s |

基线另有一条 Illegal 已写出 `PATH_RESULT`，但未完成 trace submit 就被外限终止；因此其 PATH_RESULT 总数 3281 与完整 collector 数 3280 并不矛盾。缓存组在两个新的 collector 物化中被外限终止，按阶段分别统计，不补齐缺失终态。缓存组多完成约 17% collector，但两轮的前沿、主机争用和具体路径成本不同，不能将该比率外推为完整向量加速比。该结果支持继续联合减少不必要 decoder 分叉；它未给出全域剩余路径数或完成时间上界。

本轮主 agent 已决定先将缓存与纯 mapping 匹配优化联合复验，暂不实施 watchdog 重构。若新冻结版本仍被 miss 的包装开销主导，再评审复用看门狗线程的方案；它必须保留每次调用自己的 deadline、迟到中断隔离、超时错误/制品和上下文生命周期，不能直接取消 ModelEval 超时。

### 16.4 decoder 与形状分叉、trace 的无损重复

旧官方 FVVMATYPE 在 300 秒内记录 1951 终态（1948 Illegal、3 不可编码），没有 Retire。对其约 2GB trace 用[流读工具](tools/terminal_trace_profile.py)建立完整边文本的精确 prefix trie，结果为 `FVVMATYPE-old-trace-profile.json`。只比较相同父前缀的不同后继，得出 **1950 个已观察分叉点**；这与直接相加重复边有区别。

| 已观察的分叉位置 | 数量 | 解释 |
| --- | ---: | --- |
| decoder 总计 | 1008 | 包含固定 opcode 排除之前的纯 mapping 字段匹配 |
| `encdec_nreg_forwards_matches` 四比较 | 352 | 四个位置各 88，调用点 `encdec_backwards:25211` |
| `vext_vs1_backwards_matches` 四比较 | 352 | 四个位置各 88，调用点 `encdec_backwards:26083` |
| `get_xLPE` 两个权限分派 | 128 | LPAD guard 在不匹配 opcode 排除之前运行 |
| execute 总计 | 923 | 其中 LMUL 枚举 732、`illegal_fp_normal` 177、`valid_fp_op` 14 |
| encoder 总计 | 19 | 当前记录到的有限枚举 |

八个 nreg/vext_vs1 比较合计占已观察 decoder 分叉的 69.8%。1948 个 Illegal 中，1574 条在 `valid_rd_mask` 的 vd=0、vm=0 条件退出；这条相同拒绝结果已经被前置 decoder 和形状枚举复制。记录到 12 组 LMUL/SEW 序列不意味着全域只有 12 组，当前 trace 是外限截断后的前沿。没有完整队列/未探索状态清单，不能用已有终态吞吐推断精确剩余时间，也不能声称只延长 300 秒就能收敛。

该 trace 含 10,627,304 条 branch edge，其中共享前缀重复保存；精确 trie 有 2,297,301 个节点，完整 edge 文本只有 9,647 种。原边文本 2,095,213,242 字节，按前缀只保存一次为 470,595,886 字节，约 77.5% 是完全相同的前缀字节。此数字尚未计算新引用/索引开销，也不是某个已实施格式的压缩率。当前 `ItracePerPath` 的 records/edges 是 Vec；冻结帧用 Arc 包住已 clone 的 trace，解冻又 clone 整体 Vec，它不是现成的持久化事件 DAG。若未来做无损共享，必须保持 catalog、case-id、path-signature 与完整有序边的可重建关系，不能删边或丢完整终态绑定。

当前先处理每 Model 缓存与这两类纯 mapping matches；保持真实 decoder、guard 的接受域和调用顺序，架构负责人另审纯表达式合并。trace 渲染确有成本，但本节 VFMVFS 的渲染仅 2.36 秒 worker 区间，尚不足以优先推动大格式重构。也没有证据要求改变向量符号域、固定寄存器/LMUL/SEW、采样、跨入内存一致性分支或只增加 timeout。

## 17. 1dcc 新冻结批次的只读诊断（2026-09-27）

### 17.1 版本、稳定文件和观测边界

新批次为 `isla/target/float-solve-evidence/official-1dcc-20260927-002314/`，IR `1dcc80812b8beaba49abaebf605e8090c2796b5930aefa36635b478c5f2b8180`、二进制 `f46d36c9d58ab71cec8e6a620ca8f4cd636e5b9c399009b21f3f5a22dcdf891f`，FD 配置仍为 `20851fdb…723d0`。它已包含具体 Model 值缓存、FmtVal 修复和两个纯 mapping 成员谓词。官方设置仍为 300/270/30 秒、4 目标并行、每目标 2 线程、完整 trace。

本节与批次 owner 确认目标退出后，只读其稳定日志与 trace；没有重跑求解、写生产、改配置或读取内存 worktree。独立证据目录为 `isla/target/float-solve-evidence/performance-1dcc-20260927/`，`manifest.json` 绑定批次、源文件、分析工具及两个已稳定 trace 的哈希。`ended-target-logs.json` 是分析时已结束的 17 个外限目标快照，不是整个仍运行批次的最终状态。

其中前 12 个向量目标均仅有 Illegal 与 3 条不可编码终态；包括 FVVMATYPE 的 2772 Illegal、FVVTYPE 的 3268 Illegal、FWVTYPE 的 4791 Illegal。未见这些目标的 Retire 或显式 SMT timeout 错误。另五个标量超时已进入实际运算：

| 目标 | 已记录 Retire | Illegal | 不可编码 | 实际 FORK 日志数 |
| --- | ---: | ---: | ---: | ---: |
| F_BIN_RM_TYPE_H | 1732 | 480 | 4 | 3798 |
| F_BIN_RM_TYPE_S | 3088 | 894 | 4 | 4371 |
| F_MADD_TYPE_D | 2744 | 387 | 4 | 10827 |
| F_MADD_TYPE_H | 714 | 81 | 4 | 6523 |
| F_MADD_TYPE_S | 1028 | 147 | 4 | 8399 |

这些目标均退出 124、没有最终完整 JSON；部分 Retire 不构成整项目通过。没有显式单次 SMT timeout，也不能排除进程被外限终止时仍有未返回的 SMT 调用。

官方二进制没有第 16 节的 collector 分段计时。当前完整 trace 的 `active_wall` 仍包含继承的前缀，且不能提供单独 ModelEval/watchdog/collector 占比。因此本节明确诊断**分叉来源和到达前沿**，不把旧 c5 的秒数作为 1dcc 的实测比例。生产缓存减少重复成功求值的源码事实仍成立，miss 的看门狗和 trace 成本本轮未独立测量。

### 17.2 FVVMATYPE：成员函数内部收敛后，外层格式判定仍分叉

对该目标全部稳定 trace 建立精确前缀树，2775 完整终态对应 2774 个两侧均已观察到的分叉点：decoder 957、execute 1791、encoder 26。见 `FVVMATYPE-trace-profile.json`。全部已完成路径的函数集合中没有 FP `riscv_*` 运算、向量寄存器读取或结果初始化；本次证据尚未涉及 lane 数值成本。

| 已观察分叉 | 数量 |
| --- | ---: |
| 两个外层 decoder 的成员 Bool 判断 | 454（nreg 209、vext_vs1 245） |
| LPAD 中的 `get_xLPE` 权限分派 | 226 |
| decoder 的 `bool_bit_backwards_matches` | 175 |
| execute 的 LMUL 枚举 | 1278 |
| `illegal_fp_normal` 的 mask 条件 | 415 |
| `valid_fp_op` 的 RM 条件 | 98 |

两个新成员 helper 本体没有再产生内部 Jump；剩余 454 个分叉来自它们的调用者。精确 CFG 摘录为 `outer-mapping-ir.txt`：

- VMVR：`encdec_vreg_backwards_matches`（恒 true）→ pc25211 nreg 成员 → pc25213 对成员结果分叉 → vd matcher（恒 true）→ pc25227 opcode=0x57 → pc25237 funct3=011 → pc25247 vm=1 → pc25257 funct6=100111。完整格式通过后才在 pc25265/25267/25269 转换值，pc25280 起调用原 `currentlyEnabled`／`get_sew` guard。
- VEXT：vs2 matcher（恒 true）→ pc26083 vext_vs1 成员 → pc26085 分叉 → vd matcher（恒 true）→ pc26099 opcode=0x57 → pc26109 funct3=010 → pc26119 funct6=010010。值转换在 pc26127/26129/26131，原 guard 从 pc26142 起。

这里与浮点向量不匹配的最早固定字段是 **funct3**：FVVMATYPE 为 001，VMVR/VEXT 分别为 011/010；三者的 opcode 都是 OP-V 0x57。不能把它们描述为 opcode 不匹配。成员分叉至固定判定之间只有 total 的成员检查、位等值和局部 Bool，无寄存器读写、异常或 guard 调用。当前布局先对未知 vs1 分割路径，之后才发现整条格式不匹配。

实际日志另记录 9207 次 FORK，其中 LMUL 4398、mask 1842、RM 主条件 832、两个 outer 成员条件 1263。执行器在两侧 SAT、准入 `Fork` 后才打印该日志，并为每次 fork 提交一个子任务；每个完成任务调用一次 collector。因此 `1+9207−2775≈6433` 表示已创建却尚无 `PATH_RESULT` 的任务量，尾部两个工作线程的日志/入队/collector 窗口可能有小偏差。这不是最终剩余终态数：队列任务仍会继续 fork，不能用该数除以当前吞吐声称完整完成时间。前缀树只统计已记录终态共同前缀的两侧，不应与实际 FORK 数混淆。

### 17.3 标量 FMA：不匹配的 AMO 格式与纯符号位选择

F_MADD_TYPE_D 的稳定 trace 有 3135 完整终态，已观察分叉 3134：decoder 1838、execute 1269、encoder 27。完整数据为 `F_MADD_TYPE_D-trace-profile.json`。

decoder 中 `encdec_amoop_backwards_matches` 的十个比较合计 1478 个已观察分叉；实际日志为 3840 次。AMO 在 pc3752 先匹配输入 bits31..27，再检查 aq/rl 的 bool matcher、寄存器及 width 成员，直到 pc3802 才比较 opcode=0x2f；FMA 的固定 opcode 已与之不同。所有值转换在 pc3810 之后，`amo_encoding_valid` 在 pc3840 才调用。证据 `amo-mapping-ir.txt` 保存完整顺序。此分析仅涉及主模型 decoder，未进入 AMO 执行或内存一致性分支。`amo_encoding_valid` 具有可能的 Fatal 行为，任何候选都必须保留它原来的调用域、顺序和异常结果。

execute 中，`negate_D` 的符号位 `if sign==0 then 1 else 0` 产生 370 个已观察分叉、2539 次实际 FORK，是该目标最大的单源码位置。它只做 `fsplit_D`、符号位翻转和 `fmake_D`，没有状态副作用。同形状的 `negate_S`、`negate_H` 分别位于 `fext_insts.sail` 和 `zfh_insts.sail`。另一组 RM 选择及 bits→enum 转换贡献大量有限枚举；它包含动态 FRM 的合法性和 reserved behavior，不能顺手固定 RM 或删拒绝域。

### 17.4 交给架构审查的最小候选

本节只提出范围和门槛，没有实施以下生产修改。

1. **两条 V 完整编码的 total matcher**：按架构代理建议，把各条 32 位拼接抽成 Sail 原生 tuple↔bits32 mapping helper，只显式定义 `backwards_matches` 为“全部固定字段匹配 AND 原 bits5 成员”的 strict Bool。成员和固定片段都是 total 纯表达式，保持外层 instruction clause、原 `when` guard 的位置与顺序。value 函数仍用原切片／拼接与部分值关系；非法值不补默认值。这样 MixedBits 已知的 funct3 不匹配可使总 Bool 直接为 false，不先对成员分叉。需要小 fixture 先确认 tuple mapping 的真实 Sail lowering，随后验证完整未知 bits32 接受域、合法与非法 payload、guard/异常域以及真实旧新 decoder 等价；此前两成员小模型的 PASS 不替代这个门槛。
2. **H/S/D 的纯符号位翻转**：只将 `negate_*` 的 `new_sign` 改为 `sign xor 0b1`，保留原 split、make 和所有调用位置。任意原始 16/32/64 位输入（含 signed zero、NaN payload、inf）都应逐位等价；未知输入新体应单路径，原各路径先 SAT、差异 UNSAT，并复跑依赖这些 helper 的 FMA 完整 bits/flags/状态。普通后端是否同改由架构 owner 明确，本诊断没有扩大授权。
3. **AMO 完整格式 matcher 为后续独立候选**：只有 V 的完整 matcher 小原型可行后，再评同方法能否限定到 AMO 的纯格式层。`amo_encoding_valid` 及其 Fatal 结果始终在原位置；不修改 AMO 执行。仅把十值 `amoop` 成员改成一个 Bool 会复现本轮 V 的局限，外层仍会在 opcode 前分叉，不能作为已解决声明。

没有证据支持改 execute 中 assert/合法性 guard 顺序、固定 LMUL/SEW/寄存器或 FRM、采样，或者仅延长预算作为通过。当前优先顺序是消除已证实的纯格式和纯符号位分叉，再在同一冻结运行器/IR 上量合法路径进展；若 collector 成为新主导，再申请独立分段计时确认，之后才评看门狗实现。

## 18. 348147 接续诊断与预算分层

2026-09-27 的统一双后端IR `348147` 已完成两个代表的300/270/30秒对照，两者仍外限124且无最终JSON。真实trace确认VMVR/VEXT纯布局和`negate_D`改动已消除其原分叉；剩余向量合法性及AMO前端匹配热点见[独立报告](../../isla/target/float-solve-evidence/unified-performance-review/review.md)。这修订了上节“候选未实施”的当前含义，上节仍保留其1dcc调查时点。

下一包已按[架构边界](solve-fix-architecture.md)实施：V四个total纯判断，以及AMO完整格式matcher。完整未知域、E寄存器约束、raw i64宽度、value/when/Fatal次序须先证明保持，不能以局部自然退出或输出数量代替语义门槛。

[预算分层](solve-fix-architecture.md#性能对照预算与完整验收预算)区分同条件性能对照与完整自然收敛验收。300秒不是用户指定的最终上限；在新trace和错误审计支持后，可以另记更长全域完整运行，但不能把延长预算计为优化，也不能将当前超时改记通过。下一候选仍先按原预算复验，再依据实际剩余工作确定完整批的资源和时限。


## 19. nan86f 的最小 Z3 调用诊断（2026-09-27）

本轮依据[最小诊断合同](solve-fix-architecture.md#最小-z3-耗时诊断合同)，只在独立 binary 记录现有受保护 `CheckSat`、`CheckSatAssuming`、`ModelEval`。默认关闭，显式 `ISLA_Z3_DIAGNOSTICS` 指向不存在的新 JSONL 才开启。phase 一律 null；真实 function/PC/task 保留，run 外上下文清空。不增加查询，不修改求解输入、配置、timeout、fork 或当前官方 binary。

### 19.1 版本、独审与隔离运行

v1 独审发现 phase 标记混淆及 consumer 拒绝条件缺口；旧包和失败证保持原字节。v2 单独修订并通过[独立复审](../../isla/target/float-solve-evidence/z3-call-diagnostics-independent-review-20260927/v2/report.md)：24 项 consumer 控制、默认 9＋interrupt 9＋独立 watchdog 1＋旧 solver/model 契约 2；实际 29 形状、83 终态、每模式 1,580 个具体比较及 4,180 个完整 operation 的旧 off／新 off／新 on 结果一致。有限结果相同不保证耗时或 timeout 轨迹相同。

v2 producer manifest 为 `9b72dfbd0a1278ab5e1a2f7201d09cb0fe98a3659620e7a515d294bbe1891a6b`，518 源清单为 `b037faff886c6e02a5bcaa8ae6a1945daaac83902689e6bbb332e63af81c1e54`，独立 `isarch` 为 `e7ba503a2d4bffd313b0580e5eee335aeb351736806901b1616655e974010f81`，独证为 `10115c84c92091bf4f0ddcb1fca34b15f3c6ac769e766d3e2ad0737d6b54a056`。

[隔离运行目录](../../isla/target/float-solve-evidence/z3-diagnostic-nan86f-fvftype-20260927/) 的 `runtime-source/` 保存原 518 源；`stage/` 明确覆盖 1 个 IR 和 77 份活跃 strict，2 份归档保持原 d012，Rust 与脚本未改。模型为 nan IR `86f1121b09634575e60629c272cfddb741c809182a2fa4b337acb6755b17e61f`；79 配置逐项绑定 nan strict/source 独证，完整 IR 绑定其结构独证，未混入随后归约 a040。1,242 文件准备包、实际六项动态库、初始化、配置及 make dry-run 已核。

batch 于 **10:38:02 UTC** 实际启动 FVFTYPE，全输入、完整 trace、j1×T2、1800/1740/30 秒，5 秒监控 RSS 96 GiB / MemAvailable 48 GiB。精确命令和环境见[运行计划](../../isla/target/float-solve-evidence/z3-diagnostic-nan86f-fvftype-20260927/evidence/diagnostic-run-plan.json)。此节的阶段结果不计入官方完成库存。

### 19.2 首个固定前缀的实际观测

[前缀证据](../../isla/target/float-solve-evidence/z3-diagnostic-nan86f-fvftype-analysis-20260927/prefix-005m/) 于 **10:44:04.364740 UTC** 固定，启动后 **362.364740 秒**；目录名表示预定检查点，实际并非恰好 5 分钟。读取原 JSONL `[0, 37269980)`，SHA `ad32d688266c43be5e7c0d60419c0f41171e7c7419633712c83c806f1650b26d`，重读同区间确认一致，无 partial tail。严格 v2 consumer 与[独立核账](../../isla/target/float-solve-evidence/z3-diagnostic-nan86f-fvftype-analysis-independent-review-20260927/prefix-005m/report.md)均通过，独证 SHA `2e6de8eef1a04b243115e60cbb494acc1c94a01fe4b65155958e866958953613`。

| 范围 | worker 数 | 完成受保护 FFI 墙钟（秒） | 匹配 worker 观测窗口（秒） | 比例 |
| --- | ---: | ---: | ---: | ---: |
| 全部已注册 worker | 131 | 701.210038542 | 718.657033341 | 97.572278% |
| 已关闭 worker | 128 | 694.925908113 | 712.266470057 | 97.565439% |
| 未关闭 worker | 3 | 6.284130429 | 6.390563284 | 98.334531% |

已完成 47,258 个 operation：CheckSatAssuming 6,538 次／502.646459771 秒，CheckSat 1,385 次／198.445675342 秒，ModelEval 39,335 次／0.117903429 秒。wrapper 累计 707.783681547 秒，差额包括原 watchdog 创建、握手、join 与调度。日志此时有 125 Illegal、3 non-encodable，无 Retire；这是日志前缀，未重复扫描终态 trace。

3 个 open worker 包括主线程 worker 1 和当时的 worker 130/131；主线程只到最后 end 的 4.787473 毫秒窗口，不延展到采样时刻。两个 begin 无 end 只表示 operation 未完成，不能补 FFI 时长或称为 FFI 耗时下界。上述分母是各 worker 的匹配有限观测窗口之和，不能用进程墙钟替换，也不是 CPU 利用率。记录中的跨 worker 时间戳可因日志锁前取时而倒序，独审已核单 worker 序列和计时不变量。

### 19.3 查询发起点与下一调查入口

[发起点完整报告](../../isla/target/float-solve-evidence/z3-diagnostic-nan86f-fvftype-analysis-20260927/prefix-005m-call-sites/report.md)按 operation＋真实 function/PC＋SourceLoc 聚合，保留 closed/open 两组前 20 项、全部 125 组／98 个不同位置、单次最大值与最大 20 个查询身份。只读取固定 runtime branch catalog 头部 `[0, 6902734)` 的 25,594 项，未扫描 trace 正文。非 branch 对应原 IR 指令，使用已核对的位置保持规则；unknown query SourceLoc 仍保持 unknown。

- `valid_reg_group:29` 的末尾 `zeq_int`：458 次、216.367412552 秒，单次最大 1.376521809 秒；closed 为 450 次／211.064064460 秒，open 为 8 次／5.303348092 秒。对应 `extensions/V/vext_utils_insts.sail:54`，结果为 412 SAT／46 UNSAT。
- 无上下文的 CheckSat：628 次、173.243630146 秒，不猜具体 solve phase。
- `zexecute:29144` 的真实 guard Jump：189 次、104.953490703 秒；closed 188 次，open 1 次，对应 `extensions/V/vext_fp_insts.sail:1904–1908`。

查询发起点只说明何处调用 solver。其公式可能包含此前累计的 FP/BV 约束，不能由 PC 或 SourceLoc 宣称 FP 因果、单算子成本或潜在加速幅度。`translate_exp`、其它 Z3 API、collector 其余工作、render/output 及诊断观测开销仍未归因；未被受保护 FFI 计到的窗口也不全部归给解释器。

架构后续只读调查已指向 `valid_reg_group` 最后整数相等，保留公共任意 int／原 EMUL 分支与 pow/mod 顺序；是否形成候选须另按实际语义与既有 primop 接线证明。本前缀统计不授权删查询、收窄域或生产应用。完整 30 分钟退出和最终封包待 batch 实际运行结束后追加。


### 19.4 完整诊断结束后的统计

本次诊断于 **11:08:06 UTC** 结束。supervisor 实际 child wait 为 **124**、1800.549713 秒；无额外监督器信号、无资源保护停止，make/monitor 外层返回 2，不能混淆两层退出。没有最终结果 JSON。日志局部完整终态为 **2 Retire／537 Illegal／3 non-encodable**；本次统计未扫完整 trace，不声明 trace/JSON 守恒或官方完成。

[最终分析包](../../isla/target/float-solve-evidence/z3-diagnostic-nan86f-fvftype-analysis-20260927/final-030m/report.md)冻结全部 157,818,104 字节 JSONL，SHA `43b87f5589e1b585c4c8c4a4a4371564da9645d848023da532929e27016e07e3`；首个固定前缀精确延续，1,242 个准备文件无漂移。最终包 manifest 为 `72038562ec8048aaa86fd38ea69e1db57fc594a0246f02d3a5dce9b8d155a822`，summary 为 `809be802d13d2165df4b8b5559937d00181ea7e77bc9d7ee72bb8c80d594250e`。实施方严格 v2 consumer 退出 0，最终独立核账另目录进行，不迁首前缀独证。

| 范围 | worker 数 | 完成受保护 FFI 墙钟（秒） | 匹配 worker 观测窗口（秒） | 比例 |
| --- | ---: | ---: | ---: | ---: |
| 全部已注册 worker | 545 | 3519.092413404 | 3593.033153190 | 97.942108% |
| 已关闭 worker | 542 | 3445.355107861 | 3519.106224237 | 97.904266% |
| 未关闭 worker | 3 | 73.737305543 | 73.926928953 | 99.743499% |

共 199,501 个完整 operation：CheckSatAssuming 23,973 次／2666.686864418 秒，CheckSat 5,839 次／851.892042611 秒，ModelEval 169,689 次／0.513506375 秒。wrapper 共 3546.734133892 秒。结果为 19,273 SAT、10,539 UNSAT、169,689 evaluated；没有已完成的 Unknown、interrupted 或 evaluation_failed。最后两个 CheckSatAssuming operation 未完成，分别位于 `get_start_element:39`、`:40`，不补 FFI 耗时或下界；没有 partial tail。

最终发起点仍以 `valid_reg_group:29` 最大：**1,789 次／843.498757342 秒**，1511 SAT／278 UNSAT，全属已关闭 worker；单次最大 1.376521809 秒。无上下文 CheckSat 共 2,699 次／661.753590435 秒，真实 `zexecute:29144` guard Jump 共 726 次／374.946681169 秒。全部 146 组／114 个不同位置、closed/open 前 20 项和最大 20 个单次调用均已记录并关联实际 IR；保持第 19.3 节的发起点与因果边界。

345 次资源采样的 peak RSS 为 3,663,104 kB，peak HWM 为 3,800,708 kB，最低 MemAvailable 为 120,039,256 kB。上述 FFI 比例只相对于匹配的 worker 观测窗口，不转换为 CPU/FP 比例，不按累计耗时预测优化收益。

最终[独立核账证](../../isla/target/float-solve-evidence/z3-diagnostic-nan86f-fvftype-analysis-independent-review-20260927/final-030m/review.json)随后已封，SHA `9a9ea14e8d317bc86b26fccc6ab60ae7c0d716b99a807754e6d038e82cd8427c`，状态为 `PASS_SCOPED_FINAL_DIAGNOSTIC_ACCOUNTING_AND_QUERY_POSITIONS`。单次独立扫描确认完整/前缀哈希、199,503 begin／199,501 end、全部 worker、146/114 组及每点累计/最大值/结果/top20；40 个 branch、71 个非 branch、3 个无上下文组合分列。7 文件窄补包只补足 IR files 表中 ID 2／50 的路径与标准库/模型源 SHA，原最终包未改。独审签函数/PC 和数字 SourceLoc；全局 IR 绝对行号保留为来源记录，未声称重扫完整 IR/模型全文。最终交接见 [final-handoff.json](../../isla/target/float-solve-evidence/z3-diagnostic-nan86f-fvftype-analysis-20260927/final-handoff.json)。

### 19.5 a040 的独立对照基线准备

后续末尾相等候选将以 a040 为源码基线。为避免把 nan→a040 的两归约 helper 变化混入比较，root 已授权先另跑 a040 FVFTYPE 同条件诊断。[新目录](../../isla/target/float-solve-evidence/z3-diagnostic-a040-fvftype-20260927/)于本轮准备完成，manifest 为 `1828ad369e6f34598177d8a9790c6c178d54eaa3b527b243d3cf516859126de3`，运行计划为 `6f858c85f0522c9bda174f9c7d58dc5d55381da242e26665ea406b7c3cbf79db`，此准备状态尚不代表启动或完成。

原 518 源和 e7ba binary 保持，stage 只覆盖 raw a040 IR 与 77 份活跃 strict，2 份 d012 归档原样。直接消费 a040 完整结构、strict/source、67 helper 和 89 回放既有独证，没有重跑模型门。1,239 个准备文件、166 模型源、六项实际动态库已核；配置与初始化除 IR 身份外、完整 CLI、诊断 schema/consumer、1800/1740/30 秒、j1×T2 及资源保护均与 nan 诊断对应。candidate 原 `isla/rv64d.ir` 的旧 56cc 不作为本次模型入口；新 raw IR 为 `a04050747af5354db3db507097d9ed52e3bd9daa157f2ab043b48ef2952dfa7d`。batch 单独负责实际启动与退出监督，本方分析在同级新目录进行。

a040 基线随后由 batch 于 **11:30:43 UTC** 实际启动，PID 86112；仍用同一 e7ba binary、完整域/trace 和预算。首个固定前缀于 11:36:32.883889 UTC、实际 349.883889 秒采样，35,138,244 字节，45,020 个完成 operation／125 worker（122 closed、3 open），2 incomplete、0 partial。实施方严格消费所得 FFI 677.352805251 秒／匹配窗口 694.397426370 秒＝97.545408%；此时 119 Illegal／3 non-encodable。该阶段仍在运行、尚无独审或最终完成结论，不能和 nan 的 362.364740 秒前缀按计数比宣称快慢。证据见[独立 a040 分析目录](../../isla/target/float-solve-evidence/z3-diagnostic-a040-fvftype-analysis-20260927/prefix-005m/)。


### 19.6 a040 完整预算诊断与最终核账

该独立基线于 **12:00:44 UTC** 结束。原始 supervisor 实际 child wait 为 **124**、1800.596795 秒；无额外监督器信号、无资源保护停止，外层 make/monitor 返回 2。没有最终结果 JSON。日志完整局部终态为 **2 Retire／536 Illegal／3 non-encodable**，本方未扫描 trace 正文，不声明 trace/JSON 守恒或官方完成。

[最终分析包](../../isla/target/float-solve-evidence/z3-diagnostic-a040-fvftype-analysis-20260927/final-030m/report.md)冻结全部 155,837,644 字节 JSONL，SHA `347f964ade3e5f0e743691e3cb99d649c2280e5cffba231d74843d3c93a3acf8`。首个 35,138,244 字节前缀精确延续，1,239 个准备文件与 187 个完整模型输入文件无漂移。45 文件最终 manifest 为 `8aa9f2093b01b89062d48f283ab4669aac265516b655acabdb0988cfc800303f`，summary 为 `905daccdcf3f483fbabf8427f41f856c19ed124c02a4a1aa29fbbfbe580ec084`。实施方严格 v2 consumer 返回 0；完整最终独审已另目录发起，此时尚未取得独证。

| 范围 | worker 数 | 完成受保护 FFI 墙钟（秒） | 匹配 worker 观测窗口（秒） | 比例 |
| --- | ---: | ---: | ---: | ---: |
| 全部已注册 worker | 544 | 3516.985722783 | 3593.730093966 | 97.864493% |
| 已关闭 worker | 541 | 3495.196294871 | 3571.879780123 | 97.853134% |
| 未关闭 worker | 3 | 21.789427912 | 21.850313843 | 99.721350% |

共 199,006 begin／199,004 end：CheckSatAssuming 23,835 次／2654.252505114 秒，CheckSat 5,818 次／862.210993693 秒，ModelEval 169,351 次／0.522223976 秒；wrapper 合计 3544.651770870 秒。结果为 19,201 SAT、10,452 UNSAT、169,351 evaluated，无已完成的 Unknown、interrupted 或 evaluation_failed。2 个未完成操作位于 `assert_vector_num_elem_upto_128:72` 和 `:83`，query SourceLoc 保持原 unknown，不补 FFI 耗时或下界；无 partial tail。

全部 140 个 closed/open 分组、114 个不同查询位置已关联完整 a040 raw IR、数字 SourceLoc 和实际 files 表。最大合并发起点仍为 `valid_reg_group:29`：**1,789 次／875.449186734 秒**，1511 SAT／278 UNSAT，单次最大 1.440618990 秒。无上下文 CheckSat 为 2,694 次／680.952063045 秒；`execute:29144` guard Jump 为 726 次／390.934643566 秒。完整模型源和 Sail 库源预先冻结于 [model-inputs](../../isla/target/float-solve-evidence/z3-diagnostic-a040-fvftype-analysis-20260927/model-inputs/)，不迁 nan 的位置独证。

344 次资源采样的 peak RSS 为 3,651,548 kB，peak HWM 为 3,801,076 kB，最低 MemAvailable 为 121,042,548 kB。比例仍只相对于匹配 worker 窗口，不是 CPU/FP 成本；nan 与 a040 的模型不同，两次均为全预算外限且未完成，不能按较少查询或局部终态计数宣称加速或收敛。本包作为后续 valid_reg_group 相等候选的 a040 同预算基线。

最终[独立审核证](../../isla/target/float-solve-evidence/z3-diagnostic-a040-fvftype-analysis-independent-review-20260927/final-030m/review.json)随后已封，状态为 `PASS_SCOPED_A040_FINAL_DIAGNOSTIC_ACCOUNTING_AND_QUERY_POSITIONS`，SHA `8e213656ea26b4c78a5fb1cebb50cf0deed0935fca293dbe94da9b4228399c6c`。独立单次 JSONL 流扫复核全部 counters、窗口、分组、排名与结果；本轮另完整扫描 a040 IR 的 2,049 个函数、155 项文件表、24 份函数摘录、111 处绝对 IR 行号/PC，以及 166 模型源＋15 个 Sail 库源和 73 份源码摘录，40 branch／71 非 branch／3 无 context 分列一致。45 个最终输入、187 个模型输入及 5 个外部绑定均一致。实施方重新核了 9 个审核文件与证书的精确输入绑定；[最终交接](../../isla/target/float-solve-evidence/z3-diagnostic-a040-fvftype-analysis-20260927/final-handoff.json)已封。本独证仍只签诊断核账及来源位置，不签官方完成、完整语义、FP 因果或优化收益。


### 19.7 fc4ce valid_reg_group 候选的同条件诊断准备

root 已授权在新完整 IR/C++ 与 strict/source 双门齐后，保持第 19.6 节 a040 的诊断运行器与预算进行配对。正式 [模型层交接](../../isla/target/float-solve-evidence/unified-backend-build/model-valid-reg-group-eq-build-20260927/candidate-ir-layer-handoff.json) SHA 为 `d52b93220890e96ff14150456f1cc2d7469d95529406bc0c67dfc23f73cb892c`，完整 IR/C++ 独证为 `b2fcac07432c4d1537f0bdd86f48961789dd3021b7c7d2ab0e4c35f0fb59be6f`，strict/source 独证为 `618b90ef6f084e76bdda99de91a43097684c421ccbec65a9350fa3f4bd58f888`，同绑 freeze `2df4ce8295175f231ead616f41ffa1d12f115fcd2707919e63c95c3f01e85586`。本方已核该 freeze 的 25 项直接输入及全部 79 份配置哈希。

[新诊断目录](../../isla/target/float-solve-evidence/z3-diagnostic-fc4ce-fvftype-20260927/)由 performance 唯一准备，batch 唯一启动/监督。只消费正式交接的模型层：raw IR 为 `fc4ce9091c91b654351672c89b51304afba0876cea435f251193b4537a686415`，77 份 active strict 对应新 IR，2 份 d012 档案保持。诊断运行层仍是已审 v2 的 518 文件与 e7ba binary；正式 sidecar 中的 517/b42 官方来源链不充作诊断运行层。未引入 v3 caller 字段。

最终 1,244 文件准备 manifest 为 `4baff1e19d6e2ba347581b783d73c077d81bbf715db841d6e634966b72b1e591`，运行计划为 `a3efd81d4616ffe57d5da229a882106cf02a7b934475a0febd03eb77180d6aff`，stage 源树为 `3db5871e3eacb6f1d9bbd9de5a7f0c0d1c9bb0e223928af89fce439efd19c409`。make logical CLI 与 a040 逐字一致；初始化仅 IR 哈希改变，FD 配置与六项实际 ldd 解析 SHA 保持。全输入/完整 trace、FVFTYPE、j1×T2、1800/1740/30 秒、5 秒资源采样与 RSS 96 GiB／MemAvailable 48 GiB 沿用基线。准备阶段未重编运行器或重跑模型门，67/89 新回归由各 owner 另行完成。

首次准备因校验脚本按 `make -n` 物理行拆分而拒绝，完整未启动草稿与原因保存在 [attempt-1](../../isla/target/float-solve-evidence/z3-diagnostic-fc4ce-preparation-20260927/attempt-1.json)。修正续行归并后，实际 CLI 与 a040 逐字相同，新目录重新装配并复核全部 1,244 文件；未删除失败记录、未改模型输入或运行参数。最终[准备交接](../../isla/target/float-solve-evidence/z3-diagnostic-fc4ce-preparation-20260927/preparation-handoff.json) SHA 为 `dbfb3c4d7297551be3a892aa26f72728ebebec0313eb79aace30d64a12998243`。

完整 fc4ce IR、166 模型源、15 个实际 Sail 库源及双证另冻在[独立分析输入](../../isla/target/float-solve-evidence/z3-diagnostic-fc4ce-fvftype-analysis-20260927/model-inputs/)，187 文件 manifest 为 `7e18ebf3dc44969510edad2ec1dcc8eb35d1805645f80808ecda49cb96b32174`。此处只记录准备完成，实际启动/退出与性能结果由后续证据追加，不提前记完成或收益。

batch 随后于 **12:48:19 UTC** 实际启动该 fc4ce 诊断，supervisor PID 1802393／isarch PID 1802403；运行 cwd、诊断 JSONL 环境、无 execution limits、j1×T2 和原预算/完整 trace 已由 batch 核对。此时仍在运行，最终判断等待真实退出及核账。

### 19.8 末尾整数match顺序隔离候选（2026-09-28）

fc4最终诊断已外限124且无JSON，[汇总](../../isla/target/float-solve-evidence/z3-diagnostic-fc4ce-fvftype-analysis-20260927/final-030m/summary.json) `97ebd663…9466`显示`assert_vector_num_elem_upto_128`的`<=16`五个Eq共1612次／642.207秒。只读核实际IR：五个Eq后都有Jump，末尾`==16`的168次查询全UNSAT，不能直接沿用`valid_reg_group`的泛型Eq收益，也不把FFI位点统计解释成完整目标加速。

隔离源码副本[清单](../../isla/target/float-solve-evidence/num-elem-order-candidate-20260928/source-manifest.json) `10649f20…c8b2`仅将该五个互斥match臂由`1,2,4,8,16`重排为`16,8,4,2,1`，保持其它分支、断言及行数。整数全集成功集合的SMT差异查询为UNSAT，另核-1024至1024共2049点一致。完整同源C++/IR构建自然退出0，报告`303507a1…2121`，新IR `58663c4e…d1b3`；2049个IR函数中只有`zassert_vector_num_elem_upto_128`变动，函数外全部字节相同，函数内仅四个常量位置与对应源码列跨度变动，[精确差异](../../isla/target/float-solve-evidence/num-elem-order-candidate-20260928/ir-diff.json) `84b02696…4acb`。这只证明隔离候选结构和整数返回集合，Sail/Isla异常与SMT超时行为、实际官方收敛仍待动态比较；生产模型及正式主IR未切换。

79份候选strict配置中，只有`rivvtype.toml`和`rmvvtype.toml`有`vext_control.sail`局部region，均为512–515行，与变动函数138–159行不交叠；其余IR函数字节相同。纯静态边界[证据](../../isla/target/float-solve-evidence/num-elem-order-candidate-20260928/strict-region-boundary.json) `75923b88…a64b`，活跃77配置的IR哈希重绑另经预检0问题；此证不替代全体selector动态独审。

为对照，复用e7ba诊断runtime分别装配fc4基线与新IR两份五分钟stage，均保留完整符号域、ITRACE、j1×T2及300/270/30秒预算。77活跃strict只替换IR哈希、2归档保留，79配置预检问题0；基线先启动，候选待基线退出后运行。目录为`num-elem-order-baseline-5m-20260928/`与`num-elem-order-candidate-5m-20260928/`，两份manifest分别`b15b2168…8717`／`207a458c…dc8c`。该对照只用于性能诊断，不能计官方77或源码分支闭合。

两份五分钟运行现已实际结束，子进程分别300.328／300.216秒外限124，监控/make均退出2，无最终求解JSON；没有资源止损。v2 JSONL流扫分别完整读出46,786／47,647次完成调用、各2个未完成、零残行，独立完整trace正文未签。五处目标Eq的完成调用162→30，累计FFI 64.787→16.006秒；包含该函数其它查询时200→80次、78.730→36.670秒。日志完整终态前缀128→131；总已完成FFI均约577秒，不能由此推导整个求解收敛。机器对照[short-comparison.json](../../isla/target/float-solve-evidence/num-elem-order-candidate-20260928/short-comparison.json) SHA`d77a2b78…0669`逐项绑定两份manifest/IR/e7ba binary/JSONL/摘要/退出/资源。该局部减少足以继续候选验证，尚不足以迁入生产或给77目标增加完成数。

同e7ba运行器及新IR的独立30分钟全域诊断随后已启动，目录`num-elem-order-candidate-30m-20260928/`，manifest `dabf2441…e406`，79配置预检0问题、make dry-run核实际FVFTYPE/1800-1740-30秒、j1×T2/ITRACE，诊断JSONL及5秒资源监控已增长。它与旧fc4 30分钟诊断按各自版本/主机负载对照；启动和局部计数不签自然完成，待真实退出和最终JSON核账。

该30分钟诊断现已自然到外限：supervisor无signal，child 1800.599秒退出124、monitor/make退出2，只有`status.timeout.log`，**无最终求解JSON**。v2 JSONL完整读出245,494次完成/2次未完/0残行，687 worker；匹配worker窗口已完成FFI为97.497826%，不作CPU/FP成本归因。残缺日志局部684终态＝4 Retire＋677 Illegal＋3 nonenc，trace 805,760,136字节已哈希但未签完整守恒；资源峰RSS和最低可用内存见[机器对照](../../isla/target/float-solve-evidence/num-elem-order-candidate-20260928/long-comparison.json) `ed51cb64…9a95`。相对旧fc4同e7ba/1800秒诊断的219,605已完成调用、606局部终态，候选为245,494／684；五处Eq完成调用1,612→384、FFI642.207→144.109秒，整个`zassert_vector_num_elem_upto_128`为2,023→891次、FFI799.135→318.747秒。两轮实际时间和宿主负载不同，这些是各自完整预算内的局部观察，不证明整项收敛；FVFTYPE仍OPEN、官方57/77不变。新前沿热点转为`zexecute`与`zread_vreg_extra`等位置（因路径数量不同，不能把位置总FFI直接当作退化）。

新候选的真实剩余调用位点：`zexecute`在`vext_fp_insts.sail:1904–1908`复合非法guard的Jump为1,204次／607.175秒；`zread_vreg_extra`在`vext_control.sail:365`的LMUL符号判断为299次／117.975秒，函数总2,083次／514.5秒；`riscv_valid_rm_to_ieee`在`softfloat_symbolic.sail:24–27`四个合法RM选择各112次，四处累计228.736秒。此为位置和完成查询耗时，既不能把复合guard简化为单一谓词，也不能因合法RM各臂耗时删减输入域；下一隔离候选须先逐点证明状态、错误和分支等价，并用完整域/同runtime对照。

### 19.9 RM转换纯比较第二隔离候选（2026-09-28）

在19.8的独立模型上，仅将`softfloat_symbolic.sail`中`riscv_valid_rm_to_ieee`四处`rm == 0b000/001/010/011`替换成同模型已经使用的`eq_anything(rm, bits3)`，保持五个RM返回选择和原四层ITE、fallback及行数；3-bit输入八值逐个核对返回选择。输入源清单`f80399e5…6038`锁两处模型改动。完整同源CPP/IR构建自然退出0，[报告](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-build-20260928/model-build.json) `06b84fdd…1f3c`，新IR`73dfb2e1…d2a`；相对前一`58663c4e`的2049函数仅`zriscv_valid_rm_to_ieee`改变，四个`zeq_bits`变为已有`zeq_anything(B3)`，[结构差异](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-candidate-20260928/ir-delta.json) `1933456f…d5c8`。79份strict配置没有指向该源文件的局部region，77活跃新IR哈希预检0问题；这只是静态边界，不授予完整selector审查。

83条接线smoke与17,586条完整helper语料在**该新CPP/新IR/独立native SoftFloat**真实三方运行均退出0、逐项零差异，[总证](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-crosscheck-20260928/overall-summary.json) `3c36b568…7d01d`绑定构建/IR与各输入结果。只覆盖67 helper列定具体输入，完整符号RM/整指令与性能须另验。独立FVFTYPE五分钟完整符号域/ITRACE/j1×T2/300-270-30秒诊断在`num-elem-order-rm-eq-5m-20260928/`已启动，manifest`526ba2f3…1a30`，同e7ba运行器与19.8短诊断对照；最终退出/JSON及位点统计待核。

五分钟新诊断现已child124、monitor/make2、无最终求解JSON；Z3完整流扫49,550次完成调用、2次未完，对照上一顺序候选47,647次；残缺日志136对131终态。**两轮五分钟前缀在`zriscv_valid_rm_to_ieee`均零调用**，所以这些差异不能归因于新RM比较。为进入真实RM数值路径，已用同e7ba运行器、新IR、77活跃strict哈希重绑及79配置预检0问题启动独立1800/1740/30秒完整域诊断`num-elem-order-rm-eq-30m-20260928/`，manifest`4e321db6…4ea9`。待自然退出后，先核函数调用位点与最终JSON，再决定是否继续候选。

30分钟新版诊断现已实际结束：supervisor无signal、child 1800.601秒外限124、monitor/make2、无最终求解JSON；JSONL完整读出261,566已完成/2未完/0残行，735 worker。与前一顺序候选同e7ba/预算对照，RM转换位点的已完成提前查询**448次／228.735秒→0次／0秒**；总完成调用245,494→261,566、局部完整日志终态684→732，残缺trace857,221,274字节已哈希。 [机器对照](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-candidate-20260928/long-comparison.json) `3c1b584a…c6bb`绑定两轮IR、运行器、JSONL、资源、日志/trace及退出侧车。两个时间窗的宿主负载不能视为相同，且无最终JSON，故只能签该位点提前查询消除和有限前缀进展；FVFTYPE及全77仍未完成，不因helper三方PASS迁成整指令等价。下一成本仍集中在`zexecute`复合guard与`zread_vreg_extra`，改变这些函数前须另证错误/状态/分支边界。

首个 fc4ce 固定前缀于 **12:53:47.918031 UTC**、实际启动后 **328.918031 秒**采样，37,624,486 字节，SHA `0d47fd9556c45294bedaa85169a1e848c7dbfa3cacc0648f261030c43d526b6e`。严格 v2 consumer 返回 0；47,763 次完成 operation、134 worker（131 closed／3 open）、2 incomplete／0 partial，FFI 631.810580526 秒／匹配窗口 652.791926226 秒＝96.785906%。日志局部为 128 Illegal／3 non-encodable，无 Retire。本前缀尚无独审，且采样时刻与 a040 前缀的 349.883889 秒不同，不按局部计数推加速或收敛；完整退出仍待 batch。证据见[fc4ce 首前缀](../../isla/target/float-solve-evidence/z3-diagnostic-fc4ce-fvftype-analysis-20260927/prefix-005m/)。
