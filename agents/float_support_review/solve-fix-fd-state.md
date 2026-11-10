# FD 状态写回修复记录（2026-09-26）

本包在已确认的 [修复方案](solve-fix-performance.md) 内修改 `sail-riscv/model/extensions/FD/fdext_regs.sail`，负责 FPR 快速读写状态和 `accrue_fflags` 的 SYMBOLIC 路径。正式 IR、严格配置和 77 项官方目标由集成人另行验证；本记录不把旧 IR 的结果算作新源码的 PASS。

## 修复与语义边界

- `__isla_vector_fpr` 为 true 的 `set_F_bits`、`set_F` 原来直接写向量寄存器，漏掉 `wF` 所执行的 Ext_F 断言、原值 `freg_write_callback` 和无条件 `dirty_fd_context`。现在两入口均按原 `wF` 顺序执行断言、`fregval_into_freg` 转换写入、原值回调、Dirty 更新。非向量臂仍由 `wF` 完成这些动作，不重复执行。
- 同一开关为 true 的 `get_F_bits`、`get_F` 原来直接读向量寄存器，漏掉普通 `rF` 的 Ext_F 断言和 `fregval_from_freg` 转换。现在只在快速读取臂补齐这两步；原索引、非向量臂以及所有寄存器状态保持不变。此补充由本轮架构审查批准。
- SYMBOLIC `accrue_fflags` 先计算 `old | flags` 并写入 fcsr，再以 `changed` 选择完整 `mstatus.bits`。候选 Dirty 状态只修改命名字段 FS、SD，RV32/RV64 的 SD 位置由模型字段决定。原扩展不变量仅在 `changed` 时生效，使用 strict Bool 断言维持原域。P1 最初的 `old != f` 虽已消除 flags 控制流 Jump，仍经 `neq_bits` 的急切 SAT 查询在真实 sqrt 负载超时；后续最小修订把 `changed` 换成 `not_bool(eq_anything(old, f))`，保持布尔关系而让符号相等式直接进入 SMT 表达式。
- 非 SYMBOLIC 的 `accrue_fflags` 函数体保留原条件写回、Dirty 调用和三个 callback 的相对次序与值。SYMBOLIC 下原条件 Dirty callback 是空实现；新的状态 ITE 不保留逐项函数调用 trace 或同值写事件计数。末尾 fflags/fcsr 回调仍在原位置；以后若 SYMBOLIC callback 有外部效果须重新审查。

## 红例与隔离验证

- 旧 IR `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409` 上，FADD.S `1.5+2.0`、FS=Initial、无新 flags：结果为 `0xffffffff40600000`、fcsr=0，但 mstatus 实得 `0x2600`，预期 `0x8000000000006600`。差异 SAT，旧 runner 退出 101。原始命令、输入和日志由主 agent 在仓库外红例目录保留；这是改动前的 FAIL，不代表新源码已失败。
- P1 状态修复的 `fdext_regs.sail` SHA-256 为 `393abf4daf6ad5fc190517dcd4cd93df955a51cb029bb86e3eba899902588301`。后续性能一行修订后的当前 SHA-256 为 `5cc769261a4716a4238c3446a36bbba9692a5ac74fe2a9615ca0c3d5eb5c1fa2`；下述 P1 动态结果只对应前者。在 `sail-riscv/model/` 运行 `sail -D SYMBOLIC --strict-var --strict-bitvector --strict-exponentials --require-version 0.20.1 --all-modules --config <RV64D/V128/E64 JSON> --just-check riscv.sail_project` 与去掉 `-D SYMBOLIC` 的同命令，Sail 0.20.1 对当前源码两次均退出 0。JSON 取自本轮已冻结 IR 批次，SHA-256 为 `89923ebff21718bb382df38bf246207cbb1eb5ae0cd314d078d87c0ab2b9f625`；类型检查的 memo 路径设在仓库外，输出只有既有 effect 弃用警告与 23 条被抑制警告。`git -C sail-riscv diff --check` 退出 0。
- `python3 sail-riscv/test/symbolic_fp/solve_fd_state_equivalence.py` 使用 Z3 对 XLEN32/64、F/Zfinx 合法及不合法配置证明条件更新与 ITE 更新在任意完整 fcsr、mstatus 和任意五位 flags 上输出及断言域相同：8 个差异 UNSAT。每个配置单独先验 `changed=false` 域 SAT；合法配置 `changed=true` 域 SAT，不合法配置的该域 UNSAT。还逐配置遍历 32×32 flags 对和五个 mstatus 样本。RV32 的 Mstatus 载体仍为 64 位，只有 SD 命名字段的位置改为 bit31。这是状态方程的隔离证明，不代替实际 Sail 函数的 IR 执行。

## 候选 IR 验证

### 性能修订的隔离门槛

P1 官方诊断中的 `F_UN_RM_FF_TYPE_S` 有 10 条 15 秒 SMT 超时定位到 `fdext_regs.sail:545`；即使不再以 `changed` 作 Jump，旧 `neq_bits` 仍在 `try_concretize_bool_exp` 中急切查询。以最小 Sail 函数 `not_bool(eq_anything(bits5, bits5))` 生成 IR，产物 SHA-256 `663c9ca472b871098b1c725928f504079234c6e424121acb2e4f144485aaa5ad`，其函数体明确调用 extern `zeq_anythingzIB5zK` 后调用 `znot_bool`，没有重降为 `eq_bits`/`neq_bits`。仓库外 `isla-fd-eq-probe/` 保留源、IR 和命令。另一独立真实 FP 计算探针对未知 f16/f32 `Sqrt(RNE)` 后的 flags 非零判断，只改变末比较方法：旧 `0 != flags` 两例在 22 秒外限均退出 124；新 `not_bool(eq_anything(0, flags))` 两例约 0.108 秒退出 0、单条 SAT 路径。仓库外 `isla-fp-equality-query-probe-20260926/{manifest,report}.json` 固定 IR、runner 哈希及四条命令。此结果证明所选 primitive 避开该 sqrt 构造瓶颈，仍需下一完整 IR 的实际 `accrue_fflags`、状态和官方目标复验。

P1 外部候选 IR SHA-256 为 `f5141217f2695fb53a0584c1bc7dfa059eac15df51c07ae3f02307099e4b4a61`，模型快照 manifest 明确包含上述 `fdext_regs.sail` SHA-256。Isla 执行配置为 RV64 E 配置 SHA-256 `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`，`__isla_vector_fpr` 的用例由 runner 明确设置。直接测试 runner 用 P1 的 Isla 快照库外部构建，二进制 SHA-256 为 `c7a4a68305280e62ac0c2db58b429643da5aab88c7122db3cbebfc1603c1b5d3`；源码在 `sail-riscv/test/symbolic_fp/solve_fd_state_runner.rs`。runner 使用 `B129::new(value, width)` 保持五位索引和 flags 的实际位宽，`cargo fmt --check` 通过。以 `solve-fd-state-probe-p1 <P1 IR> <RV64 E TOML>` 运行，退出 0；原始参数、逐文件哈希和输出在仓库外证据目录 `p1.command.json`、`p1.stdout.log`、`p1.stderr.log`。

| P1 直接真实 IR 检查 | 结果 |
| --- | --- |
| `get_F_bits`、`get_F` | F=true 下各测 f0/f31 不同位型、`__isla_vector_fpr` true/false，返回位相同；全部 32 个 FPR 分别给哨兵并确认保持，fcsr、mstatus 也完整保持。每调用一条完成 SAT 路径。 |
| `set_F_bits`、`set_F` | 各测 fast/normal、FS=Initial/Clean/Dirty、目标同值/异值写。f31 原始位串正确，其余 31 个 FPR 的独立哨兵及 fcsr 保持，mstatus 均为 Dirty/SD=1；每调用一条完成 SAT 路径。旧 d012 IR 对 fast 写的实测红例为 mstatus `0x2600`，新 P1 为 `0x8000000000006600`。 |
| `accrue_fflags` | 具体状态覆盖无 flags、旧 flags 已有、增加 flag，FS=Initial/Clean；fcsr 全宽及 mstatus 符合条件更新。追加的测试 IR wrapper 只保存原始 fcsr/mstatus、构造未知五位 flags 并调用实际 `zaccrue_fflags`；旧 fcsr、旧 mstatus 和新 flags 均保持符号，`changed=true/false` 两域 SAT，实际调用仅一条完成 SAT 路径，完整 fcsr/mstatus 差异 UNSAT。新 IR 中仅有一处按固定扩展支持位选择的 Jump，旧 `changed` 数据条件 Jump 已消失，mstatus 选择由 `zitezIB64zK` 表示。 |

同一 FADD.S FS=Initial 红例在 P1 候选 IR 上用既有非访存 runner 重新执行，exit 0、译码/重编码和 `Retire_Success` 正确、执行一条路径、状态差异 UNSAT；f3=`0xffffffff40600000`、fcsr=0、mstatus=`0x8000000000006600`。原始输入与旧 FAIL 不变，P1 结果在仓库外 `fadd-green.command.json`、`fadd-green.result.json`、对应 stdout/stderr。

另用运行态审查提出的 FLI.S 旧烟测输入做独立指令重放：编码 `0xf0108053`、目标 f0、旧 fcsr=0、旧 mstatus=`0x0000000a00002000`（FS=Initial）。P1 退出 0、`Retire_Success`、一条执行路径、状态差异 UNSAT；f0=`0xffffffff00800000`，fcsr 保持 0，mstatus=`0x8000000a00006000`（FS=Dirty、SD=1，其他位保持）。仓库外 `fli-initial-case.json`、`fli-initial.command.json`、`fli-initial-result.json` 及 stdout/stderr 为独立证据；旧运行态烟测本身不计作新 IR PASS。

同一版 B129 runner 以 `--legacy-bits-only` 运行旧 d012 IR（其 IR 没有保留 Fregno 两函数体），对 32 个 FPR 的读取检查通过；首个 fast `zset_F_bits` 的状态检查取得 mstatus=`0x2600`，预期 `0x8000000000006600`，exit 101。五位索引由 `B129::new(31, 5)` 构造，排除先前测试代码的位宽误差；证据在仓库外 `old-red.command.json`、对应 stdout/stderr。

Ext_F=false 的直接 guard 检查由独立审查者从旧冻结源码和当前源码逐定义抽取 `rF`、`rF_bits`、两 getter，另以 stub 固定扩展支持为 false。旧源码两 getter 在普通臂各 exit 1、快速臂各错误地 exit 0；新源码四组合均 exit 1。仓库外 `isla-getter-guard-review-20260926/report.json`、每例源码哈希和 C/Sail/运行日志保存此 8 例。这项只验证 assert 顺序；F=true 的真实数值与只读行为以上述 P1 完整 IR 为准，不把小 fixture 当作 F=false 全 IR 指令验收。

### P2 完整 IR 与官方 sqrt 结果

最终 P2 外部候选 IR SHA-256 `d86655a415441ad17533742b9d0ee726b43b64acaf2c0fc0754d27979c7859a9` 的模型快照含 FD 源 `5cc769…`、VPR 源 `6682f5…`，manifest SHA-256 `128d59a5661c3efdba566682c58ee6733f4799d9afd19fa3c6a542d24d95f346`。`zaccrue_fflags` IR 体明确调用 `zeq_anythingzIB5zK` 后 `znot_bool`，不含 `eq_bits`/`neq_bits`，mstatus 仍由 `zitezIB64zK` 选择。P2 冻结 Isla 库重建的直接 runner SHA-256 `75eb3896308f9cdc6dee49fae3dbb750dfa0d0958c90f143fa35e9ceaff5bdd0`，同一 RV64 E 配置运行 exit 0：上述两 getter、两 setter、具体 flags 矩阵再过；完整旧 fcsr/mstatus 与新 flags 均未知的实际 `accrue_fflags` 只有一条 SAT 完成路径，changed 真/假两域均 SAT，完整状态差异 UNSAT。证据在仓库外 `isla-fd-state-probe-p2-final/p2.{command.json,stdout.log,stderr.log}`。同一 FADD.S、FLI.S 初始 FS 红例对 P2 重放也各 exit 0、单条执行路径、状态差异 UNSAT，原始结果在同目录 `fadd.*`、`fli.*`。

另以 P2 冻结 Isla 源在独立 stage 构建 release `isarch`，二进制 SHA-256 `20e6e0118624ebe14352a5823af83b27086ed10b52d6930a37bf38af8bbb33da`，基础 FD TOML SHA-256 `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`。按 P1 同口径运行 `make -o build-isarch solve-F_UN_RM_FF_TYPE_S ITRACE=1 Z3_TIMEOUT_IMPL=thread_interrupt IR_FILE=./rv64d.ir ISA_CONFIG=./configs/riscv64_difftest_fd.toml THREADS=2 OUTER_TIMEOUT=90s SOLVE_TIMEOUT=80s SMT_TIMEOUT=15s TASTIC=qfaufbv TIMEOUT_SMT_OUTPUT=file TIMEOUT_SMT_DIR=output/timeout-smt`，`make -n` 确认未传 execution-limits config。P2 退出 0，JSON `complete=true`：79 个终态中 retire 60、illegal 18、non-encodable 1，emitted 78、suppressed 0；日志 0 执行错误、0 SMT 超时、0 timeout SMT2。P1 同参数基线有 10 条 SMT 超时。仓库外 `isla-fd-official-p2-diagnostic/evidence/diagnostic-summary.json` 固定命令、P2 源/IR/config/binary/日志/JSON/trace 哈希，`stage/output/` 保存原件。

P2 尚属外部候选；正式主 IR/config 和完整 77 项官方批次仍由集成人及全组验收负责。C++ callback 的运行时拦截验证尚未单独做；非 SYMBOLIC `accrue_fflags` 函数体已与旧冻结源码逐字节核对相同。

最终额外保留四个旧 helper 函数体的完整 IR SHA-256 `c5cbb0bbdaa9369b669aa7330531bfb1a0cf1ef7d905b071f14f510d10c7385c` 与 P2 使用同一 Sail 源。以 MixedBits 冻结库（`isla-lib/src/primop.rs` SHA-256 `6c6d5a4248d9874405bbc48f850f5c32b77e60f0762212244e1a173fa13f4a20`）重建 FD direct runner，二进制 SHA-256 `72e0f9b5953bd3fad5eeaa6b5e857169ead63a35cba55f9b2c5dc779ef52c580`，对该 IR 重跑两 getter/两 setter、具体及全符号 `accrue_fflags` 全部 exit 0。命令、IR/config/runner 哈希及原始输出在仓库外 `isla-fd-state-probe-p2-mixedbits/final.{command.json,stdout.log,stderr.log}`。该 runner 用 `execute_ir_function`、`Model::get_val`、B129 位串和 `smt_value`/SMT 差异查询，不经过 `FmtVal`、`BitVal::from_bv` 或 `Model::get_fmtval`；若最后仅修 `fmtval.rs` 的 >64 位序列化，本直接数值结论不受影响，须先核最终库差异确实只有该文件。

## 统一最终 IR/runtime 直接复验（2026-09-27）

真实 Sail 生成的统一 IR SHA-256 `1dcc80812b8beaba49abaebf605e8090c2796b5930aefa36635b478c5f2b8180`，模型/运行时快照 manifest SHA-256 `28fb65ee77e2c5e5c629c50b239a2e009337b47936b2fdbb897bf9c11bca055e`。同一快照的 `primop.rs`、`ir.rs`、`fmtval.rs`、`smt.rs` 分别为 `6c6d5a42…`、`d26e7923…`、`43806138…`、`3ce7310d…`。用 [direct 重建脚本](tools/solve_fix_helpers/run_direct_state.py) 从该冻结 `isla-lib` 新建 Cargo crate，使用 RV64 E 配置 SHA-256 `8247c8d4…`；FD runner 二进制 SHA-256 `f19333a6a3610880a94e1505ed8f2b4fd378dafb43f78c690df736b261b4a68a`。

真实 `get_F_bits/get_F` 读值与只读状态、`set_F_bits/set_F` 的 fast/normal 写回及 Dirty 状态、具体 `accrue_fflags` 矩阵、完整旧 fcsr/mstatus 与新 flags 均未知的 `accrue_fflags` 四组全部 exit 0。每次调用由 `execute_ir_function` 完成一条 SAT 路径；符号 flags 真/假域各 SAT，完整状态差异 UNSAT。脚本精确构建/执行命令、源码与配置哈希、原始日志见 `isla/target/float-solve-evidence/direct-state-final-1dcc8081/reports/summary.json`，SHA-256 `1f6124fdb7d72322807ea5947551325f3ae0ec2322fb4508593f660ed627d314`。这项为 direct 状态验证，不代替正式整指令 77 项结果。
