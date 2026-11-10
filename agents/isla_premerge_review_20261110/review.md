# 两分支合并前审查（2026-11-10）

## 范围与版本

- loop：`feat/loop-region-merge@9a6cd0ac`，含 `194c84d2`、`cbd25fc3`，相对 `daf61c04`。
- quick：`fix/isarch-quick-failures@9a4f5c91`，相对 `daf61c04`。
- 两树原有状态已核对并保留；不审历史，不做 Git 写操作。设计依据保持只读。
- 本轮修复先加测试复现，再修改实现；两个工作树分别记录在 `agents/premerge_review/`。

## 集中发现与修法

| 严重程度 | 分支 | 问题 | 修法 |
| --- | --- | --- | --- |
| P2 | loop | M1 默认启用断言死端过滤和槽位活跃性新分析，改变通用库用户的区域边界 | 增 `region_loop_analysis` 默认关闭，仅 isarch path merge 打开；区域缓存隔离选项；执行器断言死端处理同步受开关控制 |
| P2 | loop | 内层只有一臂读前态，汇合后再次读取时去重未扩大 guard，足迹遗漏条件 | 重复前态读时 OR 当前 guard，保持只发布一次读取事件 |
| P2 | quick | RISC-V 平台随机函数进入通用原语表，无体 val 自动接线扩大到所有同名原语 | 平台适配移至 `src/isarch/`，复用动态 Reset 和已有 extern/const_primops；删除 lib 全局隐式接线，保留模型函数体 |
| P2 | quick | RV64 初态域默认 true 放入通用配置，超出 isarch 范围 | lib 恢复默认 false，isarch 独立缺省 true，保留显式 false；同步 README |
| P2 | quick | 初态本身 Unsat 也被误报为编码域不适用 | 编码前检查初态可满足性，Unsat/Unknown/Error 明确报错；只有可满足输入域下编码路径全部被证明排除，才报告不适用 |

修复后关键位置：loop 的 `isla-lib/src/ir/regions.rs:484`、`executor/execution_limits.rs:124`、`executor/region_merge.rs:57`；quick 的 `isla-lib/src/config.rs:2735`、`src/isarch_main.rs:588`、`src/isarch/platform.rs:11`、`src/isarch/exec.rs:1829`。详细分支报告分别见 [loop 报告](../../.worktree/isla-loop-merge-20261110/agents/premerge_review/report.md)、[quick 报告](../../.worktree/isla-quickfail-20261110/agents/premerge_review/report.md)。

## 已核对的边界

- M1 的失败边过滤仅用于区域汇合点；终止性、效应摘要及保守活跃性使用完整图。
- M2 的全局状态开关默认关闭；整寄存器写后读归内部读，是设计明确接受的口径。该模式的寄存器 trace 不承诺精确访问序列。
- `vector_update` 有效分支只返回新向量；移除错误分支打印后归 Pure 合理。错误/符号长度仍由区域事务拒绝或回滚。
- RV64 域的 S/U/H 能力通过模型的 hart 支持查询取得；相关约束实现继承基线，本次只审新增默认启用范围。
- `Context::new` 的一次性 Z3 版本检查覆盖所有新上下文和相关可执行程序，符合用户的全局最低版本要求；无需新增开关。
- 编码入口检查在数组声明、初态及 CSR/PMA 约束后执行；编码辅助路径经完整约束验证，Unknown/Error 不当作空域。
- 执行前编码约束与收尾编码检查同时保留：前者限制可执行输入，后者验证执行后的可编码性。

## 合并预判

原提交三方文本合并：四个共同修改文件均无冲突（只读 `git show` 与 `git merge-file -p`，未更新任何索引或引用），见 [text-conflicts.json](text-conflicts.json)。修复后再次检查，共同修改的 `executor.rs`、`ir.rs`、`src/isarch/exec.rs` 均无文本冲突，见 [text-conflicts-after.json](text-conflicts-after.json)。

- `executor.rs`：合入 loop 的断言事务处理及默认开关；quick 的诊断与平台适配不覆盖它。
- `primop.rs` 与 `primop/effects.rs`：保留 loop 的 `vector_update` Pure；quick 的随机接口移出通用表后，只在 isarch 动态 Reset 标记 WritesState。
- `src/isarch/exec.rs`：同时保留 isarch 的 M1/M2 开启逻辑、编码检查点、前态可满足性检查、Poison 诊断和不适用摘要。
- 新编码检查点会先分割执行输入域，区域合并只能在各自输入域内合并；不要删除收尾编码核验，也不要把编码辅助函数视为纯数值函数。
- 合并树尚未编译运行。两分支分别通过的结果不能替代合并后的检查。

## 修复后验证

使用用户指定 Z3 5.4.0 库与 RUSTFLAGS；若 rustdoc 未继承运行时路径，用同前缀 LD_LIBRARY_PATH 复核并单列环境差异。

修复前 loop：isla-lib 单元 834 通过，集成/文档通过；顶层 233 通过、7 失败。
修复前 quick：isla-lib 单元 815 通过；3 个 doctest 加载系统旧 Z3 而失败；顶层 235 通过、7 失败。
顶层相同 7 项均缺 `rv64d.ir`，不是本轮新增失败。

不跑 isarch 长时实测。已有 LOAD_FP 类型约束丢失、缺浮点 helper、CPOP/CPOPW 超时属于原议题剩余问题，本轮不宣称解决。


| 检查 | loop 修复前 → 修复后 | quick 修复前 → 修复后 |
| --- | --- | --- |
| `cargo fmt --check` | 修后通过 | 修后通过 |
| `cargo test -p isla-lib` 单元 | 834 → 839 通过；7 个忽略不变 | 815 → 814 通过；6 个忽略不变（平台测试移到 isarch） |
| isla-lib 集成／文档 | 53／3 → 53／3 通过 | 集成 53 → 53 通过；3 个文档测试经指定 Z3 链接参数复核后通过 |
| 顶层 `cargo test` | 233 通过／7 失败 → 233／7 | 235 通过／7 失败 → 240／7 |
| 新增失败 | 无 | 无（指定 Z3 环境下） |

quick 的 RUSTFLAGS-only 完整库测试实际失败：rustdoc 没有使用指定 RPATH，加载系统 Z3 4.13.3，触发正确的最低版本检测。设置同值 `RUSTDOCFLAGS="$RUSTFLAGS"` 后完整命令退出 0；没有修改生产版本检查绕过问题。两树使用：

```sh
export RUSTFLAGS="-L $HOME/.local/opt/z3-official-d6c9b4fbb/lib -C link-arg=-Wl,-rpath,$HOME/.local/opt/z3-official-d6c9b4fbb/lib"
# quick 文档测试同时设置
export RUSTDOCFLAGS="$RUSTFLAGS"
cargo fmt --check
cargo test -p isla-lib
cargo test
```

两树顶层都因以下原有 7 项缺 `rv64d.ir` 而退出 101，未标为全量 PASS：

- `isarch::exec::tests::encdec_guard_f5_继承策略与固定前置权限`
- `isarch::exec::tests::encdec_guard_压缩编码回环与构造子校验`
- `isarch::exec::tests::encdec_guard_向量段store编码回环`
- `isarch::exec::tests::encdec_guard_回环拒绝amoswapq非法编码`
- `isarch::exec::tests::encdec_guard_回环拒绝ldu非法编码`
- `isarch::exec::tests::encdec_guard_回环放行合法load编码`
- `isarch::exec::tests::encdec_guard_非位向量编码报错`

完整命令、TDD 红绿证据和日志位于两树各自 `agents/premerge_review/`。合并时须纳入 quick 新增的 `src/isarch/platform.rs`；它目前未跟踪，普通已跟踪 diff 不包含其全文。本轮只保留限定结论；未对已跑通 clause 重新作全量模型差分，未运行合并树或 isarch 长时实测。

## 结论与未决事项

两个分支在带上本轮未提交修复后，可以进入合并；原提交本身仍包含上表问题，不建议直接合并旧 HEAD。没有需要额外架构裁决的本轮阻塞项。

Claude 合并时须同时带上 isarch 的平台适配、M1/M2 开关和编码/初态核验，再在合并树检查。若要求全部顶层测试为绿，需准备测试所需的 `rv64d.ir`，不能将缺资产七项失败改成通过或删除历史测试。LOAD_FP 类型约束、缺浮点 helper、CPOP/CPOPW 超时仍按原议题处理。
