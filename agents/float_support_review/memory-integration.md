# 浮点访存、内存分支与 RV32 集成门槛

**范围修订：本文仅保留原先的只读调查历史。用户已明确内存分支独立于本浮点任务；本任务不修改、集成或验收 `isla/.worktrees/memory-consistency`。本文的交接建议不再作为当前浮点任务的执行步骤，访存条目在[动态索引](e-coverage.md)标未验收。**

日期：2026-09-26。源码只读核对时段为 **05:46–05:53（Asia/Shanghai）**，最后一次工作树及哈希核对为 05:53。本文只新增审查记录，没有修改或执行被审查代码，没有产生浮点访存或 RV32 功能 PASS。内存 worktree 正由其他负责人修改；下列行号、缺口和哈希只对应此时点，集成前必须重新核对。

实施入口见[浮点计划 E](plan.md)、[浮点实施记录](implementation.md)和[内存实施计划](../memory_support_review/plan.md)。内存固定分支基线的调查见[内存报告](../memory_support_review/report.md)。本文给出两个议题的交接条件，不代替它们的动态验收。

## 1. 所查版本与工作树边界

| 对象 | 本次核对状态 |
| --- | --- |
| 浮点 Isla 主工作树 | HEAD `f4f8e4584a70588c66c9e7a6286cc20211618f18`；A 阶段未提交修改仅在 `isla-lib/src/primop/float.rs`、`isla-lib/src/smt.rs` |
| 内存 worktree | `isla/.worktrees/memory-consistency`；HEAD `f06371ffb420becb6d325772aeeaf2336276bd16`；修改 `README.md`、`isla-lib/src/smt.rs`、`src/isarch/exec.rs`、`src/isarch/mod.rs`、CLI 测试，另新增 `src/isarch/memory_model.rs` |
| 两个提交的共同祖先 | `0008fae76f4cff86dae1a036d889f0414c228e9d` |
| Sail-RISC-V | HEAD `f8ce8490981eac6396a31013180a2e718615757d` 加本轮浮点工作区修改；访存路径依据当前源码核对 |

以下路径以各自 Isla 工作树为根，SHA-256 用于区分正在变化的源码快照：

| 工作树 / 文件 | SHA-256 |
| --- | --- |
| 浮点 `isla-lib/src/primop/float.rs` | `de257e37910d2b5c2312034183a44d3703e73a7b8895e496458326254b4716ba` |
| 浮点 `isla-lib/src/smt.rs` | `968101d2aabab1ec160499c57b0ddf01e784982abbe770c3a89c68c1887fdea4` |
| 内存 `src/isarch/exec.rs` | `c175cba34cb9f6c00b4f21ee624b40cd9cde6515dd510099b30b86a4d4cb8cc7` |
| 内存 `src/isarch/memory_model.rs` | `3b5bcb6a75c3792028c44238c7fa01a93b64c25b5c2040e62c2737b29bb8500a` |
| 内存 `isla-lib/src/smt.rs` | `a5991d0781c87861ad584b7fa4226ecb2b60c17f1dcbee02712a4f7e046b561d` |

现有正式 `isla/rv64d.ir` 哈希为 `6fc39efd0f72b0ee8eae247d9965e680b6874f9954334c20d748b42c0987792c`，内存 worktree 的同名 IR 为 `7c626989a03056c43c67c81de8f40f611cef4c43ed1069a81526b37856d7e37b`。两个文件不能互代；两者也都不是完成 C/D 后待生成的正式浮点候选。任何内存分支测试结果须先保留原受测 IR，再在最终候选上复验。

## 2. 十个 clause 的实际执行范围

89 个 `FD_FLOAT` 条目与 `MEMORY` 的交集是下表十项。条目数量不是具体指令或宽度组合数量。

| Clause | 合法配置与宽度 | 当前 Sail 执行路径 |
| --- | --- | --- |
| `LOAD_FP` | FLH=2 字节，需 Zfhmin 或 Zfbfmin；FLW=4，需 F；FLD=8，需 D；另要求宽度不超过 FLEN | `vmem_read` 成功后 `F(rd) = nan_box(result)` |
| `STORE_FP` | FSH=2、FSW=4、FSD=8，扩展条件同上 | 按宽度截取 `F(rs2)` 低 16/32/64 位，调用 `vmem_write` |
| `C_FLD` | Zcd、D、Zca；8 字节；RV32/RV64 | 压缩寄存器映射、立即数左移 3 后，直接 `execute(LOAD_FP(...))` |
| `C_FLDSP` | 同上；SP 寻址 | 立即数左移 3，直接 `execute(LOAD_FP(...))` |
| `C_FSD` | 同上；8 字节 | 压缩寄存器映射后，直接 `execute(STORE_FP(...))` |
| `C_FSDSP` | 同上；SP 寻址 | 直接 `execute(STORE_FP(...))` |
| `C_FLW` | Zcf、F、Zca；4 字节；RV32 | 压缩寄存器映射、立即数左移 2 后，直接 `execute(LOAD_FP(...))` |
| `C_FLWSP` | 同上；SP 寻址 | 直接 `execute(LOAD_FP(...))` |
| `C_FSW` | 同上；4 字节；RV32 | 压缩寄存器映射后，直接 `execute(STORE_FP(...))` |
| `C_FSWSP` | 同上；SP 寻址 | 直接 `execute(STORE_FP(...))` |

源码入口：[普通浮点访存](../../sail-riscv/model/extensions/FD/fext_insts.sail)、[Zcf](../../sail-riscv/model/extensions/FD/zcf_insts.sail)、[Zcd](../../sail-riscv/model/extensions/FD/zcd_insts.sail)。`fext_insts.sail:255–262` 的 `float_load_store_width_supported` 明确包含 2 字节；只登记 F/D 会漏掉 FLH/FSH。`STORE_FP` 源码虽有 width=1 分支，合法译码谓词对 width=1 返回 false，不能将它计为合法浮点字节存储。

八个压缩浮点条目在当前模型中递归执行普通浮点访存。整数压缩指令 C_LD/C_SD 返回 `ExecuteAs` 而需执行入口续跑的缺口，不直接适用于这八项。内存分支的 `ExecuteAs` 修复仍需自身验收，但 C_LD/C_SD 通过不能代替压缩浮点的真实读写证据。

Zcf 的 RV32 条件同时有两类证据：`zcf_insts.sail` 的 assembly mapping 带 `when xlen == 32`；真正的 encdec guard 使用 `currentlyEnabled(Ext_Zcf)`，其 `hartSupports` 在 [core/extensions.sail](../../sail-riscv/model/core/extensions.sail) 明确合取 `xlen == 32`。RV64 下直接构造 C_FLW 等仍可进入其 execute 函数，不代表该编码在 RV64 能合法译码。

浮点访存移动原始位串，不需要 SoftFloat 作为数值参考。应检查载入后的上部全 1 boxing、存储只取低位、NaN payload 和 sNaN 位保持、`fflags` 保持，以及加载引起的 FPR/FS 状态变化。对于 FLEN64，FLH/FLW 的高 48/32 位应全 1，FLD 保存全部 64 位；STORE 不应因来源不是合法 boxed 值而把原始低位替换成 canonical NaN。NaN boxing 定义见 [fdext_regs.sail](../../sail-riscv/model/extensions/FD/fdext_regs.sail) 的 `nan_box`。

## 3. 与内存五项目标的交接

内存计划五项目标是字节数组一致性、区域约束、pre/post 内存、事件顺序和 ExecuteAs 续执行。浮点 E 主要依赖前四项；第五项须保持整体执行器回归，但不是八个压缩浮点条目缺失的调用步骤。

本次快照中已看到数组回调及输出实现，尚未独立运行它们。集成前须处理或明确支持边界的源码问题如下：

| 门槛 | 已核实的源码事实 | 集成前所需证据 |
| --- | --- | --- |
| 地址位宽 | 内存 `exec.rs:1324` 按 `target.xlen()` 声明数组；RV32 因而是 BV32。Sail `core/xlen.sail:22` 的 RV32 物理地址为 34 位，而 `core/phys_mem_interface.sail:64–72` 又明确统一零扩展到 **bits64**；两个 `Mem_*_request` 也固定 64。Isla `primop/memory.rs` 把原始地址直接传给 Memory | 数组索引按实际 IR 内存接口位宽设置，不能用 XLEN 代替；RV32 的真实读写不得出现 BV32/BV64 sort 不一致，且要覆盖高于 32 位的物理地址接口契约 |
| 区域为空与无合法访问不同 | `memory_model.rs:81–89` 把 `smt_address_constraint` 返回 false 当成“不加约束”；该 false 也可能表示所有区域太小，或不存在当前访问种类允许的区域 | 无配置时按约定允许；有配置却没有合法范围时必须不可满足。两种情况分别测试 |
| 完整访问范围 | 具体地址在 `region_address_constraint` 中直接跳过检查；底层具体地址未命中任何 region 仍可走 default。现有 `memory.rs` 的范围式是 `addr + bytes < end`，会排除恰好到达区间末端的合法访问 | 具体和符号地址同样受所声明范围限制；整段满足 `start <= addr` 且无回绕的 `addr + bytes <= end`；覆盖最后一字节、恰好整段、跨末端及回绕 |
| Concrete 初值与可写内存 | `MemoryBuilder` 构造 Concrete 零快照；`Memory::read` 的 Concrete 分支绕过数组回调；数组未载入 Concrete 初值。普通写可更新数组，但后续 Concrete 读仍取原快照 | 可写数据使用 Symbolic RAM，并证明同址读读、写后读和部分覆盖。若 Concrete 继续为只读，必须限制/拒绝写入并明确该边界；不能宣称所有配置区域都已成为统一可变 RAM |
| 路径与事件 | `Memory` 和回调支持 Clone；本快照把 trace 反转后提取读写事件，按字节重建 pre/post | 同一指令内多事件、重叠访问及路径 fork 独立性动态验证；写数据取 `data`，写入 Bool 结果不能当写数据；未知值不能用占位零宣称可重放 |

范围末端问题来自已有 `smt_address_constraint`，不是本轮数组实现新写的代码；接入该函数使其成为当前声明范围语义的一部分。上述门槛也不能以“MemoryCallbacks 单测存在”代替实际命令和结果。

独立内存议题当前不包含 `difftest-xiangshan/pipeline.py` 消费 pre/post 的实现。E 可以验证 Isla 内存和指令状态，并用独立模型核对；这不自动产生 XiangShan 硬件重放 PASS。最终报告须保留这条边界。

## 4. 两个 Isla 分支如何安全集成

只读执行 `git -C isla merge-tree 0008fae f4f8e45 f06371f` 得到：固定提交间 `scripts/run.mk` 有真实文本冲突；`executor.rs`、`src/isarch/exec.rs` 两边都修改，但此固定提交合并未出现冲突标记。该查询不包含双方未提交内容，不能据此声称正在实现的内存版本可无冲突合并。

| 文件或边界 | 集成要求 |
| --- | --- |
| `scripts/run.mk` | 浮点主树用 `ISA_CONFIG`、FD target-specific 配置、79 份严格配置及 Z3 链接设置；内存固定提交改用 `SOLVE_CONFIG`。保留主树入口并明确内存/FP 组合配置的传参，不能让合并后变量静默失效 |
| `isla-lib/src/smt.rs` | 主树 `ae33bdf` 已改为必须先 `configure_tastic`，探测并要求当前 tactic 支持 seed；A 又增加 `scalar_sort`。内存 worktree 的旧实现改成“不支持 seed 则跳过”。不能整文件覆盖或带回旧初始化机制；内存新增测试须在主树要求下初始化 SMT |
| `isla-lib/src/executor.rs` | 保留内存 `initial_memory` 参数及 `set_memory` 的接线；D/E 删除旧 SoftFloat 分发必须与新 IR 同批。两种改动虽然位于不同区域，仍须编译所有调用方和相关测试 |
| `src/isarch/exec.rs`、`isarch_main.rs` | 内存 worktree 大幅调整 collector 和 ExecuteAs 续执行；迁移须保留主树已有初始化、错误传播、限额、超时和 trace 行为，并复验路径状态/内存 clone |
| 正式 IR 与配置 | 内存分支现有 IR 不能覆盖新浮点候选；从已审定 Sail 源码重生成 V128/ELEN64，完成 79 份严格配置的哈希、源码坐标与锚点核对后同批集成 |

配置不能简单二选一：当前 `riscv64_difftest_fd.toml` 启用 FP，但没有所需的 `memory_regions`；内存示例 `riscv64_difftest_mem.toml` 的 `sys_enable_fdext=false`。应由集成人建立明确启用所需 F/D/H 扩展、FS、合法地址空间和数组模式的浮点访存配置，记录最终命令实际采用的文件和开关。受测值应来自当前 IR/config 的实际定义；旧名称仍出现在 TOML 中不等于新 IR 使用了它们。

推荐在依赖负责人交付稳定快照后，用隔离候选整合其必要代码与测试，以浮点主树的 SMT/API 为基线。避免对正在写入的 worktree 做切分、重置或整目录复制。集成后重跑 A 通用浮点测试、内存核心测试及 CLI 回归，不能沿用两个不同二进制各自的 PASS 作为联合候选 PASS。

## 5. RV32 入口及最小安全验证方案

浮点 E 的 RV32 专用项包括四项 Zcf 和 Zfa 的 `FMVH_X_D`、`FMVP_D_X`。当前 [isarch_main.rs](../../isla/src/isarch_main.rs) 的 solve-state 在 `xlen == 32` 分支立即 `panic!("RV32 solve-state 暂不支持")`（本快照约 505–508 行），后面的 RV32 target、MemoryBuilder 和 solve 调用不可达。`riscv32.toml` 还关闭 FD；仅生成 RV32 IR 或传这个配置不能消除入口限制。

不能只删除 panic 就称 RV32 支持完成。RV32 target 目前没有 RV64 的 `vector_context_registers`/`constrain_pre_state` 实现；主入口静态 PMP 应用还硬用 `RV64::default()`；上述数组地址位宽也是独立问题。若启用公开 RV32 solve-state，应先限制和验证本轮六个标量条目需要的上下文，核对寄存器/CSR 类型、禁用未验 PMP 或补相应实现，并增加 CLI 失败转成功测试。

本轮可先选更窄的隔离验证：准备完整 RV32 候选 IR 和专用 harness，按以下链路执行：

1. 使用真实 16/32 位指令编码，通过候选 IR 的实际解码入口得到 instruction，核对构造器、寄存器与立即数；Zcf 和 Zfa 都要求扩展使能真实生效。
2. 在同一候选 IR 中执行解码结果，设置合法 RV32 寄存器/CSR 和所需 FLEN；访存安装与联合候选一致的 MemoryCallbacks，地址接口为 BV64。
3. 比较完整寄存器、`fflags` 和退休/异常结果；访存再比较地址、宽度、读值/写数据及 pre/post。用已知位串、规范规则和独立 Sail C/C++ 具体执行作为参考。
4. 对受限符号输入先证可满足，再证明与预期不同不可满足；对非法/未启用编码单独验证拒绝，不能将其归为合法指令通过。

这种完整 IR **decode → execute** harness 可以证明列出样例的 RV32 合法译码及指令语义，也可满足 E 对这些条目的隔离语义证据要求；它不证明公开 RV32 solve-state 可用、生成器可在该入口生成这些指令或 CLI 能输出可重放 JSON。最终应明确写“RV32 指令语义经专用 harness 验证；solve-state 仍受限”。若验收要求 89 个 clause 都从公共 solve-state 完成合法生成/执行，则必须另外修复并验证该 gate。

只在 C 模拟器中合法 decode/execute，再在 Isla 直接注入 clause 或测试 helper，缺少 Isla 候选自身的译码链证据，不能代替上面的完整 harness。直接注入可以做单独执行语义测试，结果名称要准确。

## 6. E 的最小可审查验收矩阵

| 层次 | 必需内容 | 可何时做 |
| --- | --- | --- |
| 浮点算术与纯位串 | A–D 全部 helper、NaN/boxing 辅助、非访存标量/RVV 指令及 BF16 mask/vstart；保持 V128/ELEN64 | 现行浮点候选可独立做，不等待内存分支 |
| 合法译码 | RV64 候选全部适用条目；六个 RV32 专用项用独立 RV32 IR；合法编码和真实 decoder 对应 | 可先用完整 IR harness 做；不与公共 solve-state 能力混写 |
| 内存基本契约 | SAT 后同址读读/写后读/部分覆盖的差异 UNSAT；具体与符号范围、末端、路径隔离、事件顺序和 pre/post | 内存稳定快照先验；迁移到联合候选后复验 |
| FP 成功访存 | 十项逐个真实事件；LOAD/STORE 另拆 2/4/8 字节；普通/压缩寄存器及 SP 寻址；原始 NaN 位、boxing、flags 和 FPR/内存变化 | 依赖内存基本契约与组合配置；四项 Zcf 另依赖 RV32 地址接口和执行入口/harness |
| FP 异常与拒绝 | 禁用扩展/非法宽度、地址/对齐/权限相关异常及未完成访问后的状态；保留模型定义的异常路径 | 固定对应配置，不能用 `__isla_always_aligned=true` 的成功组证明未对齐异常 |
| 最终运行边界 | 新源码、新 V128 IR、79 严格配置一起；普通 `make solve` 与明确的 FD 清单分别记录结果；命令、工具、哈希、资源、退出状态、超时和失败清单 | 联合候选稳定后；旧 IR/其他分支的通过数不迁移 |

浮点成功样例应至少包含非对称字节图样、正负零、qNaN/sNaN payload，旧 `fflags` 取 0 和非零，确认访存保持它们。未知读取若还存在 `null`/任意位，不能作为已经可重放的确定初值通过；应使用可追溯的受限输入或明确记录未定值。一个 Finished、空 `memory-events`、只有合法整数访存、只有 C 模拟器结果或只有字段存在，均不足以完成 FP 访存验收。

截至本文时点，十项浮点访存、RV32 合法译码/执行及联合版本动态测试仍为**未测/依赖未满足**。上述静态问题交由相应文件负责人处理；修订后由集成人更新此记录及[clause 矩阵](clause-matrix.md)，主 agent 再同步[议题状态](status.md)、全仓状态与逐次测试结果。
