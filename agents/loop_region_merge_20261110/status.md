# 循环内分叉合并：状态摘要

| 项 | 状态 |
| --- | --- |
| 阶段 | M0+M1 已提交（`194c84d2`）；M2 已提交（`cbd25fc3`）；`vector_update` 改纯已提交（`9a6cd0ac`）；动态实测受浮点 helper 缺失阻塞 |
| 方案 | [plan.md](plan.md)：M0 静态测量 → M1（汇合点按不以断言失败结束的路径计算 + 活跃性在重新声明处截断）→ M2（区域内读写全局状态的通用合并，方案见 plan.md M2 节）→ M3 跨轮合并按结果再定 |
| 代码 | isla 工作树 `.worktree/isla-loop-merge-20261110`，分支 `feat/loop-region-merge`，基于 daf61c04；M0+M1 已提交 194c84d2，M2 由 Codex gpt-6.1-sol high 实施 |
| clause 分组 | [clause-status-20261110.json](clause-status-20261110.json)：347 个中跑通 52、2h 超时 10、被停 4、未跑 178、快速失败 103（见下） |
| 验证 | M1：`cargo fmt --check` 通过；Claude 复跑 `cargo test -p isla-lib --lib region` 123 通过 0 失败；Codex 报 isla-lib 单元测试 809→819 通过，已知失败与 daf61c04 相同。未做 isarch 实测 |

## clause 分组（旧全量实测 + 已停的缓存实测，2026-11-10）

| 组 | 数量 | 说明 |
| --- | ---: | --- |
| 跑通 | 52 | 不再重跑 |
| 2h 超时 | 10 | FVFMATYPE、FVFMTYPE、FVFTYPE、FVVMATYPE、FVVMTYPE、FVVTYPE、FWFTYPE、FWVFMATYPE、FWVVMATYPE、FWVVTYPE |
| 被停/中断 | 4 | FWVFTYPE、FWVTYPE（会话退出）、MASKTYPEI、MASKTYPEV（跑约 50 分钟时停） |
| 未跑 | 178 | 其中 V 运算 106 |
| 失败：译码回环返回 Poison | 39 | 多为 qfaufbv tactic；第二轮原计划改 default 补跑，未执行 |
| 失败：浮点函数不存在 | 31 | 如 `riscv_f64Add does not exist`，与合并无关 |
| 失败：当前路径不存在合法机器编码 | 10 | AES32*、BITYPE、C_FLW 等 |
| 不完整：有未完成路径 | 22 | 多为压缩访存，几秒内结束 |
| 失败：panic | 1 | LOAD_FP，`primop.rs:163` nat 不变量 |

快速失败的几组与循环合并无关，用户要求逐类修复，另立议题 [QUICKFAIL-01](../isarch_quick_failures_20261110/status.md)。

## M0 测量（10 个 2h 超时 clause，按旧日志拒绝次数加权）

详见 isla 工作树 `agents/loop_region_merge/m0.md`。

- 拒绝权重共 11,395，其中有回边的 847。M1 后 837 变为无环，10 仍有环。
- M1 后的全部无环区域里，能通过现有静态预检的只有约 770；其余约 10,600 都被 `callee_state_write` 拒绝，写入方全是 `accrue_fflags`，写的是 `fcsr`，经由 fp_add、fp_muladd、fp_eq 等浮点辅助函数调用。所以 M2 是这批 clause 的关键。

## M2 结果（`cbd25fc3`）

- 新选项 `region_global_state` 默认关闭，isarch 在 `--path-merging` 下打开。区分前态读和内部读；放开被调函数写全局、重复写、读后写、写后读；前态足迹做拓扑合并。
- 同口径静态测量：能通过预检的权重从 768 增至 8969，`callee_state_write` 降为 0。仍有 2416 被拒，首个证据都是 `vector_update`：它被标成 `WritesState`，唯一的理由是一行 `eprintln`。
- FVFTYPE 5 分钟冒烟：合并尝试 45 次、成功 35 次，无 panic，未跑完。
- 测试：isla-lib 单元测试 830 通过；Claude 复跑区域测试 134 通过；失败名单与 194c84d2 相同。
- 阻塞：V 浮点会调用只有声明、没有函数体的 `riscv_f32Add` 等 helper（见 QUICKFAIL-01），不补上这些函数体，超时 clause 跑不通。

## vector_update 改纯（`9a6cd0ac`）

- 同口径静态测量：能通过预检的权重 8969 → 11385，预检拒绝 2416 → 0；仍有环的 10 不变。也就是说，10 个旧超时 clause 里被拒的分叉，除了 10 次真回边，现在全都能进入合并。这是静态结论，不等于运行时一定合并成功。
- isla-lib 单元测试 834 通过，失败名单与 cbd25fc3 相同。

## 关键发现（2026-11-10）

- FVFTYPE 的 has_back_edge 拒绝主要是误判：循环体内 `if mask[i]` 和 `match funct6` 的直接后支配点被 `VF_VSLIDE1DOWN` 臂的断言失败边拉到函数出口，区域因此包含回边（pc29135→28810）。
- pc29115（`i < last_elem`）区域本就无环，仍因活跃性不按重新声明截断而失败 361 次 incompatible_state。
- FVVTYPE、FWVFMATYPE 的主要障碍是 `callee_state_write`（fcsr），与回边无关。
- 审核补充：FVFTYPE 修完回边后，区域内 `fp_add` → `accrue_fflags` 写 fcsr 仍会被预检以 callee_state_write 拒绝，所以 M2 是 V 浮点放开合并的关键。


## 合并前审查补记（2026-11-10）

本轮已在对应工作树完成未提交修复，原提交的历史验证不自动覆盖修复后源码。限定审查、TDD、测试前后对比和合并取舍见 [两分支审查](../isla_premerge_review_20261110/review.md)。无新增测试失败，顶层仍有原有缺 IR 七项失败；未跑 isarch 长时实测。
