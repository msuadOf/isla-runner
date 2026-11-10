# solve 见证值采样注入（assumption injection）实施计划

状态：**r4 纯净分支交付（2026-09-28）**——`feat/witness-randomization`@`2fefa72`（纯 f4f8e45 基线，仅 witness），`feat/float-support`@`fc9ba69` 仅含浮点批次，后续合并时再合 witness。r1–r3 演进与两轮独立复核记录见文末（[独审](witness-sampling-independent-review.md)）。前置研究：[z3-random-model/SUMMARY.md](z3-random-model/SUMMARY.md)（Z3 无原生随机满足赋值；UF 包裹/自由变量恒 0；check-sat-assuming 域内 100% 命中；开销标量 <1%、向量热点 +4~6%）。

## 目标

官方 solve 的 case 枚举按身份维度取 witness，Z3 对不在身份里的维度（vl、寄存器载荷等模型变量）恒给极小模型（0），导致数据通路分支系统性未达（见 [branch-coverage/SUMMARY.md](branch-coverage/SUMMARY.md) B 节）。本改动在 case 物化前的 check 上加**调用方随机采样 + assumption 注入**：对指定多样性维度先采样目标值，`check-sat-assuming (= sym k)`，SAT 则 witness 携带该值；UNSAT 则回退 plain check（绝不丢 case）并计拒绝数。

## 设计约束

1. **默认关闭，字节级零行为变化**：新增 isarch CLI 开关（形如 `--witness-sampling <seed>[:dims]`），不开时全部现有测试与官方 run 行为不变。这是官方运行二进制改动的硬前提。
2. **注入点**：case 物化路径的模型 check（`src/isarch/exec.rs` 的 SolveCollectorState/materialize 链与 isla-lib 中产生该 check 的 executor case 事件；具体行号由实施 agent 定位并回填本文件）。assumption 只作用于当次 check，不进入增量约束栈。
3. **采样维度**：phase 1 = 初始状态里**已是模型变量**的维度（vl、vstart、vtype、fcsr 等按实际符号表确定）；寄存器载荷若非符号变量则 phase 2 另议（需扩初始化，风险更大，单独审批）。采样分布：均匀 + 重点值混合（0、vlmax、边界）；RNG 种子由 (run seed, case 序号) 确定派生，输出记录 seed/分布/拒绝计数以保可复现。
4. **UNSAT 回退**：注入失败 → plain check 照常出 case，仅计数。案例集与 verdict 集合不变（同路径同身份），只改 witness 取值。

## 步骤

1. worktree：`git -C isla worktree add .worktrees/value-sampling -b feat/solve-value-sampling`，应用主树 tracked diff 与 4 个未跟踪源文件（scripts/solve_process.py 等），保证基线=当前 runtime 源。
2. TDD 红：现有小场景（或新增单测）证明不开开关时 vl 恒 0（复现退化）；绿：开开关后 vl 分布非退化、case/verdict 集合与不开时一致、拒绝计数正确、同 seed 复跑逐位一致。
3. 单元测试：采样器确定性/域约束/回退路径。
4. 构建：worktree 内 `cargo build --release` 通过，现有 isla-lib/isarch 测试全绿（默认路径零回归）。
5. A/B：小 clause（VFMVFS 或 F_UN_F_TYPE）复制既有 stage 目录分别跑 开/关，核对 case 数、verdict 分布、vl/载荷分布差异，产出对比记录。
6. 独审：由独立 agent 复核（代码 + 测试 + A/B 证据）。
7. 合回：worktree 内 `git diff main基线..HEAD` 导出补丁，应用到主 isla 工作树（当前分支 feat/float-support 的未提交状态之上），不 commit、不动 gitlink；主树既有未提交内容保持。
8. 记账：本文件记录实施与验证，status.md/TODOs.md 同步；A/B 结果不并入官方完成账目。

## 文件边界

- 实施仅限 worktree `isla/.worktrees/value-sampling/` 内：isla-lib（注入点）、isarch（CLI 开关与采样器）、对应测试。
- 不碰 `isla/.worktrees/memory-consistency`；不改主树 sail-riscv；不跑官方全量 solve。
- 文档：本文件 + 状态表，由主 agent 维护。

## 未决问题

- f/v 寄存器载荷是否为模型变量（决定 phase 2 是否需要扩初始化）——实施 agent 实测后回报。
- 注入是否影响 `--probe-all`/itrace 物化一致性（A/B 中核对 trace 前缀）。

## 实施记录（2026-09-28）

- worktree `isla/.worktrees/value-sampling` 分支 `feat/solve-value-sampling`，基线=HEAD f4f8e45＋主树未提交 diff（99 文件）＋4 个未跟踪源文件，`cargo check` 基线绿后开工。
- 改动（与计划一致，审计 A 项核对无越界）：新增 `src/isarch/witness_sampling.rs`（splitmix64 采样器、CLI 解析、14 单测）；`exec.rs` 注入接线（plain check SAT 后、`Model::new` 前，经 `smt.rs` `check_sat_with`→`Z3_solver_check_assumptions`，assumption 不入增量栈，UNSAT 回退重跑 plain check）＋terminal/summary 采样元数据；`target.rs` 提取共用 `rvv_vlmax_bounds`；`mod.rs`/`isarch_main.rs` 接 `--witness-sampling <seed>[:dims]`。
- TDD：7 项骨架红→绿；默认关闭零行为（config=None 全链短路、serde skip）。
- 端到端 VFMVFS A/B（off/on）：verdict 集合全同（189/3/63、252 gen）；vl 由 6 值（0 占约 56–59%）→15 值含 VLMAX；同 seed 采样元数据 252/252 一致、异 seed 全不同；接受率 17/252（路径硬约束，回退兜底）；accepted case 的 isa-state.vl==采样值 17/17。
- 独立复核：A–G 全 CONFIRMED（diff 干净、默认零行为、assumption 不入栈、RNG 无时间源、A/B 独立重跑复核、重放输入完整、fmt 过且 53 条警告全为预存）。
- 合回：worktree 与主树差异精确 5 文件，已复制至主 isla 工作树（feat/float-support 未提交状态之上，未 commit/未动 gitlink）；主树复验 `--lib` 96 过、bin 23 过、witness_sampling 14 过，零失败。原文件备份 `isla/.tmp-merge-backup-20260928/`；worktree 保留。
- 关键事实：f/v 寄存器载荷全部是模型变量（f* 为 SMT Float）——phase 2 载荷注入无需扩初始化，仅需 Float 值域采样。主树本底 `fresh_random_seed()`（纳秒相位）使 off 模式两跑亦不逐字节相同，属既有属性。
- 遗留：`nonencodable_witness` 未接采样（负例无需多样化）；phase 2（Float 载荷维度）待批；官方启用前须按 stage 流程预检并单独记账。

## r2 重构记录（2026-09-28，按用户架构修正下沉 smt 封装层）

- 用户裁定机制应整体下沉 smt 封装层、上层不感知维度/分布。重构后：新增 `isla-lib/src/smt/witness.rs`（机制+13 单测：splitmix64(seed^path_signature) 采样、BV 宽度掩码均匀、Float(to_fp) 位模式、`check_sat_with` 一次注入、UNSAT 按 RNG 序二分丢弃 ≤⌊log₂n⌋+1 轮、仍 UNSAT/Unknown 回退 plain 重跑并分别计数）与 `src/isarch/witness_randomization.rs`（胶水+5 单测）；删 `src/isarch/witness_sampling.rs`；exec/mod/target/isarch_main 移除维度语法与 vlmax 采样域（`rvv_vlmax_bounds` 因 constrain_pre_state 真实复用保留）；CLI 改 `--witness-randomization <seed>`。
- 复核 r2（[独审文档](witness-sampling-independent-review.md) "重构复核 r2"节）：有条件通过→整改后通过。核心确认：跨进程同 seed 252/252 元数据逐条全等；verdict/test-ins/ret_val 多重集 off=on diff=0；二分上限、回退语义、assumption 不入栈、枚举与 replay 输入完整性均 CONFIRMED。整改两项已闭：fmt（witness.rs 7 处，双包复验 CLEAN）与 RESULT.md 事实更正——**f* 在 e2e 为 BitVec(64) 非 Float**（状态记 64'h…；Float(to_fp) 仅单测覆盖），据此"phase 2 需 Float 载荷采样"的旧判断撤回：f/v 载荷本就是位向量，载荷采样已随本机制生效。
- 备注收录：samples 元数据含被二分丢弃的值，生效判定以 `injected` 字段为准。
- VFMVFS 复验（r2）：off 7 值（0 占 147）→ on 14/18 值（seed 1234/4321），accepted 240/252；两处计数漂移归因仓库既有 `fresh_random_seed` 时间源。
- 主树合回（替换 r1）：复制 5 改+2 新文件、删 `src/isarch/witness_sampling.rs`；主树复验 fmt CLEAN、`--lib` 88/`--bins` 23/`-p isla-lib --lib witness` 13 全过零失败。r1 备份仍在 `isla/.tmp-merge-backup-20260928/`；worktree 保留。

## r3 增强记录（2026-09-28，自动 seed + TOML 启用）

- CLI：`--witness-randomization` 无值时自动生成 seed（复用 `smt::fresh_random_seed`，与 Z3 相位 seed 同源）；seed 打进启动 stderr 一行与输出元数据（r3 实测两跑 seed 513841614/410575003 不同、各自 terminal 元数据自洽）。带值行为不变。
- TOML：`isla-lib/src/config.rs` 新增 `witness_randomization` 键（`true`=自动 / 整数=固定 / 缺省=关）；优先级 CLI > TOML > 关。`configs/riscv64_difftest_fd.toml` 加注释示例（中文说明两种写法、默认关、只影响 witness 分布、CLI 优先），注释行不改变解析；79 份 strict 配置无键零行为。
- 改动：config.rs（Setting+getter+2 测）、smt.rs（fresh_random_seed 转 pub）、executor.rs（测试字面量补字段）、opts.rs（拆 parse_with_args）、witness_randomization.rs（auto 重写/合并+4 测）、isarch_main.rs、主配置 toml。
- 验证：isarch `--lib` 91、`--bins` 23、isla-lib 新 config 测 16/16（全套因预存 enum-sort 崩溃中止属 W7–W10 已记录，0 FAILED）；fmt 双树 CLEAN。e2e：TOML=true→自动、TOML=42→固定 42、三跑 verdict 均与 off 一致、vl 16/21/15 值非退化；证据 r3_* 在 witness-sampling-dev-20260928/。
- 主树合回：7 文件复制（r2 的 exec/mod/target/witness.rs r3 未动、保持一致）；主树 fmt CLEAN、--lib 91/bins 23/config 16 全绿。

## r4 纯净分支交付（2026-09-28，按用户指示）

- 交付形态改为两条独立线：**`feat/witness-randomization`（worktree `isla/.worktrees/witness-pure`，提交 `2fefa72`）= 纯净 f4f8e45 + 仅 witness**（10 文件 +1255/−8：witness.rs 647、witness_randomization.rs 394、exec.rs +121、config.rs +51、isarch_main +30、toml +7、opts +6、smt/executor/mod 共 7）；**`feat/float-support` 回退至 `fc9ba69` 仅含 6 个浮点批次**，witness 提交 6a7dde1 已从该线撤销。后续合并时 `git merge feat/witness-randomization` 即可，冲突面仅接线处。
- 纯树验证：依赖 API（check_sat_with/fresh_random_seed/PreStateCtx/Model::new 物化点）在 f4f8e45 均存在；基线 --lib 58+1 预存失败（rv64_target_trait），改后 67+同一预存失败、bins 23、新增测试全绿（stash 复核预存失败与基线一致）；e2e（纯树自带 rv64d.ir，VFMVFS T1）：off=on 16 case verdict/test-ins 多重集一致、vl 5 值→8 值、accepted 16/16、同 seed 元数据逐位一致、off 无新键。证据 witness-sampling-dev-20260928/pure_*。
- 与浮点版差异：元数据适配纯树 schema（挂 gen[] 条目+顶层 summary，无 terminals 结构）；exec.rs 保留自有 splitmix64 私有副本（纯树无浮点基线拷贝，不做去重挪移）；机制/CLI/TOML 行为一致。
- 主树二进制当前为回退前构建（仍含 witness）；如需纯浮点二进制请重新构建。
