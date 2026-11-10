# BF16 SYMBOLIC lane 改写（2026-09-26）

本包实现 [性能设计](solve-fix-performance.md)第 9–10 节、architecture 预审批准的 BF16 四条 execute 路径。源文件限于 `sail-riscv/model/extensions/bfloat16/` 下的 `zfbfmin_utils.sail`、`zvfbfmin_insts.sail`、`zvfbfwma_insts.sail`。工作树此前已有的 assembly 文本修复、VF 合法性断言位置和首个 active lane 累计 scalar flags 的普通后端修复均保留。独立内存 worktree、主 IR 和严格配置未改。

## 实施

- `zfbfmin_utils.sail:13` 的 `SYMBOLIC` `bf16_to_f32` 用 strict Bool 判定 NaN 和 sNaN，三处位串分类比较显式用 `eq_anything`/`not_bool` 保持在通用比较入口；结果为 `ite(is_nan, canonical_NaN_S(), v @ zeros(16))`，NV 只在 `is_nan && mant[6]==0` 时置位。普通后端完整保留原函数体。
- `zvfbfmin_insts.sail:18,117` 的窄化、宽化及 `zvfbfwma_insts.sail:18,122` 的 VV/VF 乘加，仅在 `SYMBOLIC` 执行中先生成每 lane 的纯 tuple；各转换和 FMA flags 合并后用 mask 位 ITE 贡献给一次总 `accrue_fflags`。计算结果通过已有 `vector_select_masked(mask, initial_result, candidates)` 选取。VF 保持 `F_BF16` 一次读取，scalar 转换 flags 每个 active lane OR 一次，零 active 时不贡献。普通后端维持首 active callback 及原循环。
- guard、SEW/LMUL、重叠检查、boxing、`init_masked_result`、整组 `write_vreg`、`set_vstart` 和 assembly 的语义均未改；Sail 条件编译要求 top-level，故两个后端各有一份 execute 函数体。

## 验证与证据

在 Sail-RISC-V HEAD `f8ce8490981eac6396a31013180a2e718615757d` 加本轮工作树、Isla HEAD `f4f8e4584a70588c66c9e7a6286cc20211618f18` 加本轮工作树、Sail 0.20.1 `446fb477` 下，配置来自仓库外 P1 目录 `isla-float-solve-fix-p1-20260926.0i6jAp` 的 `rv64d_v128_e64.json`（SHA-256 `89923ebff21718bb382df38bf246207cbb1eb5ae0cd314d078d87c0ab2b9f625`）：

1. 先新增 `sail-riscv/test/symbolic_fp/solve_bf16_lanes/check_clauses.py`，代码修改前运行 `python3 test/symbolic_fp/solve_bf16_lanes/check_clauses.py`，退出 1，明确因缺少 `bf16_to_f32` 的 SYMBOLIC 实现；修改后退出 0，四条 lane 均有 masked vector 选择、一次 flags 累计且无 lane mask 控制分叉。
2. 在 `sail-riscv/model/` 运行 `sail -D SYMBOLIC --strict-var --strict-bitvector --strict-exponentials --require-version 0.20.1 --memo-z3-path <仓库外缓存> --all-modules --just-check --config <上述配置> riscv.sail_project` 及去掉 `-D SYMBOLIC` 的同一命令。在共享 `core/ieee_fp_exceptions.sail` 修复 Bool singleton 类型错误、SHA-256 为 `6a53eb013721787194a4fb370974e785fd0751f35f9d6cb66bb360ff82d6faeb` 后，两模式均退出 0，只有既有 effect 弃用和 23 条被抑制警告。小修期间共享 core 的一次中间状态曾使 SYMBOLIC 严格检查失败，修后已复验。
3. `bash test/symbolic_fp/solve_bf16_lanes/run.sh <仓库外输出目录> <本轮 Isla plugin>` 在 generic 小修后退出 0；本轮输出目录标识 `isla-bf16-lane-equivalence-20260926`，plugin 来自 `isla-float-ir-final-20260926.q1Auj4`。隔离工程直接编入生产 `zfbfmin_utils.sail`，把旧函数体置于对照函数：未知 16 位输入的旧/新比较共 **4 条完成路径**，每条先 SAT、再证 `(flags,bits)` 差异 UNSAT；新函数入口恰 **1 条**完成路径且 SAT。检查同一小 IR 中生产 `zbf16_to_f32` 函数体恰有三处实例化 `eq_anything`，没有 `eq_bits` 或 `neq_bits`。小 IR SHA-256 为 `63147a86d0e92ba7b0667fcbc51deb29b54bb4dcce893c141de8b6b3ad35d2b6`；仓库外输出目录的 `run-result.log`、`run-final.log` 和 `report.json` 含运行结果、完整命令输出及源码/IR/runner 哈希。`run.sh` 使用 Cargo offline 和仓库外构建目录；初次不带 offline 的独立手动 Cargo 调用因网络失败，改 offline 后通过。
4. 性能设计代理另完成独立公式证明：`bf16_expand_equivalence.smt2` 用 Z3 输出 `sat`（前置）和 `unsat`（差异），并穷举 65536 个输入；证据留在本轮仓库外原型目录，与上述真实 Sail 小 IR 分开理解。`git -C sail-riscv diff --check` 退出 0。

当前三份生产源 SHA-256：`zfbfmin_utils.sail` 为 `2c0693f4c578e6b237cc5de39d4a0014b6e46580cc69f66efdeb00f1785c6f07`，`zvfbfmin_insts.sail` 为 `062ccfc5b247bf2a0bd553a4ac7edbec7bf70f574049c669f2ab7c8b951550a2`，`zvfbfwma_insts.sail` 为 `bdabf5ad2823f203e4bf1c53e11860da58c5fbb1c594f0c376ce98697ac87bac`。

完整指令的 NaN/FMA/flags/全目标组验证仍依赖新主 IR 与 BF16 coverage suite；旧 IR 的 898 例 PASS 仅为历史证据。新候选须由 IR 集成人更新严格配置，再对 922 例扩展 suite 和官方入口复跑，最终结果回填状态表。先前 C++ 两例测试使用旧 `zvfbfwma_insts.sail` 哈希 `81400805…`，不是当前候选的普通后端动态回归；BF16 汇编测试负责人已接收当前三文件哈希，待联合源冻结后重建。
