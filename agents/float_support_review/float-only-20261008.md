# 仅浮点支持分支（2026-10-08）

**复审修复（2026-10-08）**：本分支已追加`5ceb3ad`和`be1296b`两个`fix`；旧IR兼容性与FD快速访问状态缺陷已修，最终限定验证通过。下面原六提交及d012测试记录为修前历史，当前默认IR为aea104c8。[修复交付](../float_only_review/fix.md)。


**后续复审（2026-10-08）**：分支整理与下述限定测试记录仍有效；独立复审发现全局删除分派未同步迁移另外4份自带IR的新增回归，且d012保留旧FPR Dirty缺陷。新增327例／67helper数值差分及BF16无活动元素修复通过，但不能验收为全部旧行为保持正确。[报告与动态对照](../float_only_review/report.md)。


## 目标与边界

用户指定从7b7337b0dea0c4105644436a606dbec5ae9b3fea直接分支，不得含通用修改。新工作树`.worktree/isla-float-only-20261008`，分支`feat/float-only-20261008`。原isla及通用工作树保持不动；本次仅迁入浮点专用改动，新工作树不保留通用未提交层。上一版继承2792afd的分支已按用户要求删除，历史证据仍保留。

## 计划

按六类提交：浮点primop；现有生成IR；旧SoftFloat分派退役与旧测试迁移；fcsr符号状态；官方77项FS/VS见证偏好；非访存FD入口与配置。实现与对应测试放同一个提交，IR单列。smt.rs仅类型查询，executor.rs仅删专用分派；exec.rs不引入完整前后态、mapping重构或通用诊断；target.rs仅fcsr及测试，不引入RV64域约束。依赖新通用API的测试改用基线已有FmtVal和寄存器接口。

先快照原HEAD/索引/两层diff和24文件哈希，隔离候选逐层fmt、定向测试、35例legacy；完整候选做默认编译及MRET/BF16 smoke（检查gen）。完成后逐文件核对最终tree，首提交父必须是指定base，原工作区不变，未push。基线已有x0/PC测试预期错误不夹带修复，记录明确测试范围。证据目录`isla/target/float-only-20261008/`。

IR保留现有d012产物，本次不重新生成；源版本与生成配置见[IR记录](ir-refresh.md)。仅固定产物，不宣称固定未提交Sail-RISC-V源码链。

## 已完成

分支`feat/float-only-20261008`位于`.worktree/isla-float-only-20261008`。首提交的直接父为`7b7337b0dea0c4105644436a606dbec5ae9b3fea`，与通用分支2792afd的merge-base也为该基线；共新增6个提交，无通用8提交。

| 提交 | 内容 |
| --- | --- |
| `28f626a` | 完善浮点 primop 的类型校验、位模式转换与运算支持 |
| `8c45fb2` | 更新 RV64 浮点模型 IR 为普通 Sail helper 实现 |
| `d5ce1b7` | 移除专用 SoftFloat 分派并迁移旧语义回归 |
| `280ef32` | 将 fcsr 纳入 RISC-V 符号寄存器状态 |
| `06a9ef3` | 为官方浮点指令选择可编码的 FS/VS 见证 |
| `d04883b` | 增加 RV64 非访存浮点求解入口并调整 FD 配置 |

最终工作树干净，没有通用未提交层。原isla HEAD、索引、staged/unstaged补丁及24个改动文件哈希全部核验不变；通用分支和修复工作树未操作，未push。相对原浮点差异，测试适配基线已有FmtVal/寄存器与JSON接口；runner保留已验证的MixedBits归一化最小适配。

### 边界核验

`primop.rs`、`fmtval.rs`、`ir.rs`、execution_limits.rs、frame.rs、isarch/mod.rs、isarch_main.rs的blob与7b7337b完全一致。smt.rs仅新增16行浮点类型查询，executor.rs仅删除34行旧专用分派；target.rs生产区仅两处fcsr清单插入。exec.rs仅浮点名单/FS-VS偏好及对应测试，不含完整前后态schema、mapping状态具化、通用错误诊断或state-domain。混合文件的审查补丁保存在证据目录`*-boundary.patch`。

### 验证

按层运行`cargo fmt --all -- --check`通过；独立runner另行fmt检查通过。Rust定向测试均使用`cargo test --offline -q`、features `itrace,smt-thread-interrupt`和`-- --test-threads=1`：

- 第1/3层：`-p isla-lib --lib primop::float::generic_float_tests::`，各10项。
- 第4层：`-p isla --lib isarch::target::tests::`，23项；跳过基线原有rv64_target_trait。
- 第5层：`-p isla --lib --bin isarch`，68库＋25bin；同样明确跳过1项基线失败。
- 基线先单独运行`isarch::target::tests::rv64_target_trait`，退出101，失败在原`regs.contains(x0)`断言；该测试未修，不计全量PASS。
- IR wrapper要求普通helper体存在，生成15个包装器；`cargo run --offline -q --manifest-path test/softfloat_legacy/runner/Cargo.toml -- <wrapped.ir> test/softfloat_legacy/cases.tsv`，35/35通过，完整结果及flags差异为UNSAT。
- 默认`cargo check --offline -q -p isla --bin isarch`与FD目标dry-run通过。

在新工作树执行（CARGO_TARGET_DIR指向原isla/target，CARGO_NET_OFFLINE=true）：

```sh
make solve-MRET solve-fd-nonmem FD_NONMEM_RV64=FCVT_S_BF16 THREADS=1 ITRACE=1   OUTER_TIMEOUT=90s SOLVE_TIMEOUT=70s SMT_TIMEOUT=20s TASTIC=qfaufbv
```

退出0且两项intime；MRET 4 gen（3 Retire、1 Illegal），FCVT_S_BF16 39 gen（36 Retire、3 Illegal），全部有编码。IR哈希d012不变，配置与二进制哈希在`smoke.json`。本轮没有跑全77项、全isla-lib或硬件差分，不能宣称全面浮点验收。原通用分支审查的问题不作为此独立基线分支的结论。

`checks.json`保存逐层命令/退出码，`after.json`保存提交链、tree和原工作区不变性结果；make输出在新工作树output中，不覆盖原output。
