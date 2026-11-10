# witness 采样注入独立对抗复核（2026-09-28）

复核对象：`isla/.worktrees/value-sampling`（分支 `feat/solve-value-sampling`，基线 = HEAD f4f8e45 + 主树未提交 diff + 4 个主树未跟踪文件）。复核方式：只读代码审查 + 独立重跑构建/测试/端到端场景，未修改任何源文件。验证产物：`isla/target/float-solve-evidence/witness-sampling-audit-20260928/`（off/on_a/on_a2/on_c 四组 JSON+日志、audit_analyze.py、三份对比输出）。

## 结论：通过

七项逐条全部 CONFIRMED，无阻断项。三项轻微改进建议见文末，不构成"有条件通过"条件。

## 逐项复核

### A. 改动边界与 diff 干净度 — CONFIRMED

用 `diff -rq`（排除 target/.git）将 worktree 与**主 isla 工作树**逐文件比对：差异仅 5 个文件 —— `src/isarch/exec.rs`、`src/isarch/mod.rs`、`src/isarch/target.rs`、`src/isarch_main.rs` 修改，`src/isarch/witness_sampling.rs` 新增；其余（configs/、isla-lib/、scripts/ 等大量未提交内容）两树零差异，均属基线自带，非本次引入。与声称的文件集合一致，无越界改动。`target.rs` 改动是把 `constrain_pre_state` 内联的 SEW/LMUL/VLMAX 枚举循环原样提取为 `rvv_vlmax_bounds`（逐行比对逻辑等价）+ 新增容错版 `try_integer_let_from_lets`。diff 无调试残留（无 dbg!/println!）；新代码中的 panic/assert 均符合仓库"防御性编程、禁止 Fallback"规范；UNSAT/Unknown 回退 plain check 是设计内语义。

### B. 默认关闭零行为 — CONFIRMED

代码路径：CLI 无 `--witness-sampling` 时 `witness_sampling=None` → `WitnessSampler` 不构造、`validate_dimensions` 不执行 → `materialize_finished_case` 中注入块为 `match None => None`，仅多一层元组包装；serde 两侧 `skip_serializing_if = "Option::is_none"`，无隐藏默认值（config 无 Default impl、无环境变量读取，来源仅 `opt_str` 一处）。实测：`cargo test --lib` 96 过（含"默认关闭不输出新字段"断言）、`--bin isarch` 23 过；我的 off.json 与开发方 off 基线顶层/summary/terminal/gen 键集合逐项相等，全文 0 处 `witness-sampling` 字样。

### C. assumption 不入增量栈 — CONFIRMED

调用链 `apply_samples` → `Solver::check_sat_with`（smt.rs:2616）→ `timeout_Z3_solver_check_assumptions`（z3_timeout.rs:284）→ `Z3_solver_check_assumptions(ctx, solver, 1, ptr)`。assumption AST 仅作为单次 check 的假设数组传入，无 `assert`、无 push/pop（不需要——Z3 该 API 本身不入 assertion stack）。后续 blocking 枚举走 `assert` 路径不受影响；单测 `assumption_never_enters_assertion_stack` 侧面验证（两次注入独立判定、模型携带当次值）。

### D. 采样确定性 — CONFIRMED（采样元数据层面）

`WitnessRng = splitmix64(seed ^ path_signature)` + 单调 counter，无任何时间源。`fresh_random_seed()`（smt.rs:594，SystemTime 纳秒）是主树既有代码且 smt.rs 两树零差异——它只喂 Z3 相位，影响 fallback case 的 plain 模型取值，不影响采样元数据。实测同 seed=1234 两跑：252/252 terminal 采样元数据逐条完全一致（test-ins 多重集本次也一致）；seed=4321 与 1234 的元数据 252/252 全不同。两层面区分成立：仅要求"采样元数据确定性"——满足。

### E. 独立 A/B 重跑 — CONFIRMED（数字见下）

命令照 RESULT.md 记录复刻（`-T 1 --smt-timeout 1m --tastic qfaufbv`，二进制为本次重新构建的 release+`smt-thread-interrupt`）：

| 指标 | 我的复跑 | 开发方声称 | 判定 |
| --- | --- | --- | --- |
| off gen/counts | 252 / {illegal 189, non-enc 3, retire 63} | 同 | 一致 |
| off vl 分布 | 6 值 {0:141, 3:39, 7:43, 15:18, 31:10, 63:1}（0 占 56%） | 6 值 {0:149,…}（59%） | 值集合一致；计数差属 off 基线自身相位漂移（15/18、31/10、63/1 完全相同，佐证 0/3/7 为半自由维度） |
| on(1234) vl | 15 个不同值，新增 {1,2,4,6,8,16,22,29,30,46} | 同一集合 | 逐值一致 |
| on(1234) vtype | 27 值（off 13 值） | — | 一致方向 |
| ws_summary | {seed 1234, attempted 252, accepted 17, fallback 235, unknown 0} | 同 | 一致 |
| verdict 一致性 | counts 与 (助记符, verdict) 多重集 off/on 全等 | 同 | 一致 |
| test-ins 差异 | 3 条 case 的 vs 寄存器号 v17→v24 | 同性质 | 一致 |
| on(1234) 复跑 | 采样元数据 252/252 一致 | 同 | 一致 |
| on(4321) | accepted 18，元数据全不同 | 同 | 一致 |

### F. 重放一致性（安全性）— CONFIRMED

采样值只钉住 witness 物化的**输入**状态维度，输出侧 `gen[].isa-state` / `isa-state-complete` 由注入后的模型读出、完整记录该值：accepted case 中 `isa-state.vl == samples.vl` 实测 17/17（seed 1234）与 18/18（seed 4321）零 mismatch（`vfmv.f.s f13, v24` 样例 `vl=8` 与采样目标 8 相符）。重放工具以该状态为初值即可复算，无需采样器或 seed 参与；fallback case 保持 plain 模型。不存在"注入值未入记录导致 replay 不可复算"的路径。

### G. fmt 与警告 — CONFIRMED

`cargo fmt --check` 通过。`cargo build --bin isarch` 共 53 条警告，全部位于本次未触碰文件（isla-lib 各文件与 `src/isarch/args.rs`、`args_yaml.rs` 等）；本次改动的 5 个文件零警告。用户点名的 smt.rs:2750 `use std::sync::{Arc, OnceLock}` 位于 `#[cfg(test)] mod tests` 内，且 smt.rs 两树零差异——预存，非本次引入（二进制构建警告中无 OnceLock）。

### 测试与回归（独立复跑）

- `cargo test --lib`：96 过（含 witness_sampling 13 项 + exec.rs 记录流转 1 项 = 声称的 14 项）。
- `cargo test --bin isarch`：23 过。
- `cargo test -p isla-lib`：不加过滤会在 `get_multi_member_enum_const_after_checkpoint_replay` 等处以 "enumeration sort name is already declared" 异常退出（多线程下表现为 SIGSEGV）；单线程跳过这 3 个预存用例后 lib 260 过 + 3 filtered out，与声称一致，且与 docs/RESULTS.md W2-W10 的预存记录吻合；isla-lib 源码两树零差异，预存性与本次改动无关。

## 轻微建议（非阻断）

1. `apply_samples` 对 `SmtResult::Error`（如 Z3 超时中断）直接上抛 `ExecError::Smt`，该 case 走错误诊断路径而不回退 plain check——与"绝不丢 case"意图有出入（显式报错、非静默，故仅建议）。可考虑 Error 时也尝试一次 plain 回退。
2. `resolve_bitvector_dimension` 中模型缺该变量（`None`）会落入"不是位向量模型变量"panic，报错文案未区分"模型缺少条目"与"类型不符"。
3. 标量 clause（pre-state 无 vl 等）跑 `--witness-sampling` 默认维度会在 `validate_dimensions` assert panic——fail fast 合理，建议 CLI 层预检给更友好的报错。

## 复核命令记录

```
# 构建（worktree）
RUSTFLAGS="-L native=/home/linuxbrew/.linuxbrew/opt/z3/lib -C link-arg=-Wl,-rpath,/home/linuxbrew/.linuxbrew/opt/z3/lib" cargo build --release --bin isarch --features smt-thread-interrupt
# 测试
cargo fmt --check; cargo test --lib; cargo test --bin isarch
cargo test -p isla-lib -- --test-threads=1 --skip get_multi_member_enum_const_after_checkpoint_replay --skip get_single_member_enum_const_after_checkpoint_replay --skip get_struct_with_enum_field_after_checkpoint_replay
# 端到端（audit 目录下）
isarch -A rv64d.ir -C configs/riscv64_difftest_fd.toml --tastic qfaufbv -T 1 --smt-timeout 1m [--witness-sampling <seed>] solve-state --clause=VFMVFS
python3 audit_analyze.py off.json on_a.json   # 及 on_a2/on_c 两两对比
```

---

# 重构复核 r2（2026-09-28：机制下沉 isla-lib smt 封装层）

对象：`isla/.worktrees/value-sampling` 同一 worktree 的第二轮重构（删 `src/isarch/witness_sampling.rs`，机制移入 `isla-lib/src/smt/witness.rs`，isarch 侧只剩 `witness_randomization.rs` 胶水，CLI 改 `--witness-randomization <seed>`）。方式：只读审查 + 独立重跑，未改源文件。验证产物：`isla/target/float-solve-evidence/witness-sampling-audit-20260928/r2_*.json/.log`、`r2_analyze.py`、`r2_analysis_output.txt`、`r2_audit_RESULT.md`、各测试日志。二进制经增量 release 构建 no-op（md5 不变）证明与当前源一致。

## 结论：有条件通过（整改项见文末）

机制本体（采样、一次注入、二分丢弃、回退、确定性）全部核实成立；两处声称失实需整改：fmt 不干净、RESULT.md 对 f* sort 的描述错误。均非机制缺陷。

## 摘要（≤250 字）

复核确认：改动集合与声称一致（5 改 2 增 1 删，smt.rs 仅 +1 行挂模块）；旧 witness_sampling.rs 已删净，维度语法仅存于"拒绝旧语法"单测；rvv_vlmax_bounds 因 constrain_pre_state（target.rs:673）真实复用而保留属实。机制上：二分调度恰 ⌊log₂n⌋+1 次（e2e attempted=101、rounds≤6）；回退后重跑 plain check 且模型保留路径约束；assumption 走 Z3_check_assumptions 不入栈（回退能 SAT 即反证）；RNG 无时间源——我的独立跑与开发方产物同 seed 252/252 元数据逐条全等（跨进程最强验证）。默认关闭零新键，off schema 与 r1 版逐键全同；off/on verdict、test-ins、ret_val 多重集全等。测试 88/23/273 复现。两处失实：cargo fmt --check 报 7 处 diff（全在 witness.rs，主树为 0）；"f* 为 Float sort"错误——e2e 中 f* 是 BitVec(64)，Float(to_fp) 仅单测覆盖。

## 逐项复核

### A. 改动边界 — CONFIRMED

`diff -rq`（排除 target/.git/output/.worktrees）：worktree 相对主树仅 `isla-lib/src/smt.rs`（diff 恰 1 行 `pub mod witness;`）、`src/isarch/{exec,mod,target}.rs`、`src/isarch_main.rs` 修改；新增 `isla-lib/src/smt/witness.rs`（13 单测）、`src/isarch/witness_randomization.rs`（5 单测）；`src/isarch/witness_sampling.rs` 仅存在于主树、worktree 已删。grep 全 worktree：`witness_sampling/witness-sampling` 0 处，残留 witness 字样均为上游注释或模块挂载。维度采样残留：witness_randomization.rs 无任何 vl/vtype 取值域知识（vl 仅作测试夹具名）；exec.rs 的本地 splitmix64/bitvector_candidate 已删、改 import 封装层（diversify 既有用法复用）。`rvv_vlmax_bounds` 保留理由属实：唯一调用方在 RV64 `constrain_pre_state`（target.rs:561 函数、:673 调用）；r1 加的容错版 `try_integer_let_from_lets` 已随域知识下线删除、恢复严格版。主树独有的 `outputs/`、`scripts/__pycache__`、`.tmp-merge-backup-20260928` 与本轮无关。

### B. 机制正确性 — CONFIRMED（④限定，见失实项）

- ① **二分调度**：`bisection_schedule(total)` 产出 `[n, n/2, …, 1]`，长度恰 `⌊log₂n⌋+1`（单测遍历 1..199 断言 + 收尾到 1）；循环逐轮 `truncate(keep)` 后单次 `check_sat_with`，UNSAT continue、Unknown break 记 `unknown`。e2e 实测 attempted=101、rounds 分布 {1:29,…,6:22}、无一超上限。
- ② **回退**：`!accepted` 时重跑 `check_sat` 并对 Unsat panic（不变量）；tactic 模型与最近一次 check 关联——回退后的 `Model::new` 绑定该 plain check，非旧部分注入状态。单测 `randomization_falls_back_when_constrained` 断言回退后模型保留路径约束值；e2e 12/252（1234）/9/252（4321）fallback case 正常物化输出。
- ③ **assumption 不入栈**：`randomize_witness` 内无 assert/push/pop；`check_sat_with`（smt.rs:2617，预存代码，本轮未改）→ `Z3_solver_check_assumptions`。结构性反证：若 assumption 入栈，UNSAT 后的回退 plain check 必然仍 UNSAT 而 panic——单测 16 个路径签名中 rejected>0 全部通过，e2e 252 例无一 panic。
- ④ **Float 读回**：单测 `float_symbols_are_sampled_by_sort` 以 `ToIEEE` 在模型内反查位模式与采样一致，通过。**但 e2e（VFMVFS）中未走到该路径**：32 个 f* 采样值全为十进制（`sample_bitvector` 的 `value.to_string()`），isa-state 记 `64'h…` ⇒ 本 IR pre-state 的 f 寄存器是 BitVec(64) 而非 Float sort。RESULT.md"机制事实"中"f* 为 Float sort，按位模式采样后 to_fp 构造"与事实不符（详见失实项 2）。
- ⑤ **RNG**：`WitnessRng` 为局部结构（`splitmix64(seed^path_signature)` 基 + 单调 counter），无 static、无 SystemTime/Instant；采样序按 Sym id 规范化、Struct 字段按 Name 排序（胶水层），多线程无关。最强证据：我方独立复跑（重建验证过的二进制、独立进程）与开发方 dev-20260928 产物同 seed 1234/4321 的 252 条采样元数据逐条全等（按 index 与 sorted 双口径）。
- 附加核实：`sample_float` 位宽=ebits+sbits 与 `FromIEEE`→`mk_fpa_to_fp_bv` 类型规则吻合；>64 位宽路径 `bitvector_candidate` 每 64 位独立混合、元数据记录的"低 64 位"恰为 word 0（`splitmix64(seed+0)`），与单测 `wide_bitvectors_are_sampled` 的模型比对一致；Fisher-Yates 洗牌后前缀截断保证丢弃子集无偏。

### C. 默认关零行为 — CONFIRMED

CLI 不传时 `opt_str` 为 None → `witness_randomization_seed=None` → `materialize_finished_case` 内 `match None => None` 短路（无收集、无 check）；serde 两侧 `skip_serializing_if = "Option::is_none"`。实测 off：全文 0 处 `witness-randomization`/`witness-sampling`；顶层 {gen,summary,terminals}、summary 8 键、gen-item 12 键、terminal 13 键与 r1 版 off（本目录 off.json，其亦无 witness-sampling 键）逐项全同。

### D. 独立重跑 — CONFIRMED（两处计数漂移，均可归因仓库既有时间源）

- 测试：`--lib` 88 过、`--bins` 23 过、`-p isla-lib --lib` 273 过 + 3 filtered（总数 276 = 主树 263 + 新增 13，口径自洽）；3 个 enum 崩溃两树同位置复现（`get_multi_member_enum_const_after_checkpoint_replay` 等，"enumeration sort name is already declared"，与 W7-W10 预存记录一致）。
- VFMVFS（T1，每跑约 25s）：四跑 counts 均 {illegal 189, non-encodable 3, retire 63}、gen=252；off vs on(1234) 的 test-ins 与 ret_val 多重集全等（差异 0 条，优于 r1 的 3 条）。
- on(1234)：vl 14 值与声称逐值一致；accepted 240/252、rounds {1:29,2:78,3:56,4:45,5:22,6:22}、injected 总 4418（均值 17.5）、attempted=101/skipped=1（cur_privilege 枚举）——全部与声称一致。
- on(4321)：accepted 243/252 与声称一致；vl 我方 17 值 vs 声称/dev 产物 18 值（差值为 1 个 fallback case 的 plain 模型 vl=63，相位漂移）。
- off：我方 5 值 {0:148,3:38,7:40,15:18,31:8} vs 声称/dev 7 值（0:147）——off 基线自身漂移（r1 已记录 `fresh_random_seed` 纳秒时间源喂 Z3 相位；三个 off 样本核心值集 {0,3,7,15,31} 稳定，非本轮引入）。
- 同 seed 1234 复跑：252/252 元数据逐条一致（case-id 对齐 255/255）；异 seed 252/252 全不同。声称均成立。

### E. 语义边界 — CONFIRMED

- **case 身份枚举**：assumption 不入增量栈 ⇒ 约束栈与不开启时完全一致；off/on 的 counts、test-ins/ret_val 多重集、gen 数、complete=true 全同，枚举集合未被改变（每 case 的 solver 独立经 checkpoint 恢复，且 materialize 后不再复用）。
- **itrace/probe**：`submit_itrace_for_local_frame_with_metadata` 只消费符号执行期构建的 `frame.itrace_path` 与终端元数据（case-id/status/phase/path-signature，均不依赖采样值），不读求解模型；probe（`--probe-all` 调试标志）在本场景未启用，机制上亦不消费物化模型。
- **replay 输入完整性**：`isa-state`/`isa-state-complete`/`isa-state-post` 由随机化后的同一个 `Model` 读出；isa-state-complete 含 102 键（101 采样维 + cur_privilege），完整记录模型实际值，重放以记录值为初值即可复算，无需 seed 参与。
- **元数据语义注意（非缺陷）**：`samples` 记录全部 101 个采样值（含被二分丢弃的；生效数见 `injected`，均值 17.5/101，且生效子集的身份不可从元数据得知）。用 case-id 对齐实测：accepted 240 例中 isa-state.vl==采样 vl 仅 47 例——与"injected<attempted 时多数假设被丢弃"的设计一致（代码注释已声明），但消费侧若把 samples 当"注入值"会误读。r1 的 17/17 全一致口径不适用于 r2（r1 只注入 2 维且 accepted 即全量生效）。

### F. fmt 与警告 — fmt REFUTED；警告 CONFIRMED

- `cargo fmt --check`（worktree，rustfmt 1.8.0-stable）**exit=1，7 处 diff，全部在 `isla-lib/src/smt/witness.rs`**（:208/:258 主代码、:471/:553/:576/:604/:630 测试代码）；主树同命令 exit=0。声称"fmt 干净"失实，属本轮引入（证据 r2_wt_fmt.log）。
- 警告：两树 `cargo clean -p isla-lib -p isarch` 后 `cargo check --bin isarch` 对比，逐文件警告数与文本完全相同（isarch_main 12、mod 9、exec 6 等），本轮零新增；主树 witness_sampling.rs 的 1 条随文件删除消失（顺带净减 1 条）。

## 整改项（合并前须完成）

1. **[必改] cargo fmt**：对 worktree 执行 `cargo fmt`（7 处，全在 witness.rs），并在 RESULT.md 修正"fmt 干净"的记录。
2. **[必改] 修正 RESULT.md 机制事实**：e2e（VFMVFS/rv64d.ir）中 f* 寄存器是 BitVec(64)，不是 Float sort；"Float 位模式+to_fp"路径目前仅单测覆盖。若需 e2e 覆盖 Float sort，需另找/构造含 Float 符号 pre-state 的 clause。

## 备注（非整改）

- samples 含被丢弃假设值、生效子集不可辨识——建议后续如需精确消费再加"生效符号名单"字段。
- off 基线相位漂移（fresh_random_seed 时间源）为仓库既有，与本轮无关；如需逐字节复现仍需固定 Z3 相位（r1 遗留 1 的延续）。
- `SmtResult::Error`（如 Z3 超时中断）仍直接上抛走错误诊断路径而不尝试 plain 回退（r1 建议 1 的延续，本轮未处理，显式报错非静默）。

## 复核命令记录（r2）

```
# worktree 内（绝对路径 cd）
cargo fmt --check; cargo test --lib; cargo test --bins
cargo test -p isla-lib --lib -- --test-threads=1 --skip get_multi_member_enum_const_after_checkpoint_replay \
  --skip get_single_member_enum_const_after_checkpoint_replay --skip get_struct_with_enum_field_after_checkpoint_replay
cargo clean -p isla-lib -p isarch && cargo check --bin isarch        # 警告对比（主树同法）
RUSTFLAGS="-L native=/home/linuxbrew/.linuxbrew/opt/z3/lib -C link-arg=-Wl,-rpath,/home/linuxbrew/.linuxbrew/opt/z3/lib" \
  cargo build --release --bin isarch --features smt-thread-interrupt   # 增量 no-op 证二进制=源
# 端到端（audit 目录，JSON 落 output/rv64_zVFMVFS.json 后拷贝）
…/target/release/isarch -A …/rv64d.ir -C …/configs/riscv64_difftest_fd.toml --tastic qfaufbv -T 1 \
  --smt-timeout 1m [--witness-randomization 1234|4321] solve-state --clause=VFMVFS
python3 r2_analyze.py r2_off_run.json r2_on_a_run.json r2_on_a_repeat.json r2_on_c_run.json off.json
```
