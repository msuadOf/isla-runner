# 两分支试合并与原工作区对照（2026-10-08）

## 目标与计划

核对 `feat/float-only-20261008@be1296b` 与 `refactor/general-support-20261007@09fe582` 合入 `feat/float-support@7b7337b` 后，是否等于当前 `isla/` 最终工作区内容（包括暂存与未暂存改动）。仅在 `.worktree/` 试合并，不移动生产分支、索引或父仓库 gitlink。

步骤：保存原 HEAD、索引、两层补丁和源码文件哈希；以独立 detached worktree 模拟基线快进通用分支后合入浮点分支；记录自动合并冲突，必要时在试验目录保留两边职责并解决；逐文件比较内容与模式，定位新增修复、测试或遗漏；核验原工作区保持并同步摘要。热点为 `src/isarch/exec.rs`、`target.rs`、`isla-lib/src/primop/float.rs`、旧 IR 和 legacy runner。验证以实际 Git 合并和文件比较为准；文件相同不外推全输入行为等价，差异存在时区分生产逻辑与测试。

## 结果

**按用户澄清的口径，代码意图与预期效果一致。** 用户所说的“等价”允许实现差异及 bug fix，比较的是要实现的能力和目标效果。两个分支保留原工作区的浮点支持与通用支撑目标；后续修复使这些目标在 MixedBits 消费者、宽状态、编码见证和 FPR 状态副作用等边界正确生效，没有从这些差异中发现独立的新功能目标或原目标被替换。

前一轮“不等价”采用文件树及精确行为相同的口径，判断口径与用户本意不同。下面15个原有文件差异和14个新增文件仍是有效实现事实，但不据此否定意图一致。编码约束参与求解改变实现流程，目标仍是生成与原执行路径一致、可编码的同模型见证；MPP及FPR修复仍服务于合法架构状态与正确副作用。

比较冻结于 `feat/float-support@7b7337b0dea0c4105644436a606dbec5ae9b3fea`、`feat/float-only-20261008@be1296bbe66ca03a3c17c17ad7b9039a9cefc9c9`、`refactor/general-support-20261007@09fe5821142cfefb6760d93310337aa9fce68353`。原工作区包括24个 dirty 路径，比较采用其最终文件内容，不只比较索引或 HEAD。

## 试合并与冲突解决

基线是两个分支的共同起点，先快进通用分支，再在 detached 工作树合入浮点分支，模拟合入 feat/float-support 的最终代码树：

```sh
git -C isla worktree add --detach ../.worktree/isla-merge-check-20261008 refactor/general-support-20261007
git -C .worktree/isla-merge-check-20261008 -c rerere.enabled=false merge --no-commit --no-ff feat/float-only-20261008
```

自动合并失败，两个冲突文件：`isla-lib/src/primop/float.rs`、`src/isarch/exec.rs`。前者保留浮点分支的新类型检查、原生 MixedBits 位串转换及旧专用分派退役，通用分支的独立 FP 转换回归仍保留。后者保留通用编码可行性流程，并把浮点 FS/VS 偏好移入各编码可行 checkpoint，避免偏好提前排除合法编码域；两边测试断言保留。此顺序与此前已验证通用组合版本一致，见[第二轮修复](../general_support_review/fix2-20261008.md)。

候选位于 `.worktree/isla-merge-check-20261008`，无未解决冲突、无未暂存差异，合并停在待提交状态；index tree=`54fb4e8e26bcf654dc182a470f604439a1380028`。未创建合并提交、移动生产分支或 push。若自行采用其他冲突解决，须重新核对其 tree。

## 文件对照

按 Git 源文件清单核对 SHA-256 与 Git 模式（包括符号链接目标），排除 ignored 构建缓存和运行产物：原工作区1001个文件／链接，候选1015个；986个相同，15个原有文件不同，新增14个，没有缺失路径，也没有模式差异。

| 差异 | 具体范围及影响 |
| --- | --- |
| 通用消费者及物化修复 | `isla-lib/src/{error.rs,executor.rs,ir.rs,memory.rs,primop.rs,smt.rs}`：MixedBits 算术、地址访存、执行器具化兼容；超宿主宽度模型值使用分段表示，原工作区对应物化会报 Type。 |
| 编码求解与诊断修复 | `src/isarch/{exec.rs,mod.rs}` 和新增 `encoding.rs`：编码可行性参与见证求解、合法替代前态／压缩域接续、错误退出传播；原工作区仍是选模后编码校验及有限错误记账。 |
| 特权状态修复与测试整理 | `src/isarch/target.rs`：MPP 随 S 能力约束，并保留当前模型 reset 的0例外；浮点分支为独立基线适配的测试也与原组合测试不同。 |
| 五份 IR 修复 | `rv64d.ir`、`rv32d.ir` 和 `ir/rv64d_v{128,256,512}_e64.ir`：默认 IR 快速 FPR getter/setter 恢复能力断言／转换／callback／Dirty；四份旧 IR 还补齐普通浮点 helper。原默认 SHA-256=`d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`，候选=`aea104c88a3c90f5e3030365d38dbcbc97a058dcfaf22b77b6717bffae59b544`。 |
| legacy 测试适配 | `test/softfloat_legacy/runner/src/main.rs` 多了 MixedBits 规范化，防止因值表示误报。 |

新增14个文件：4份 `isla-lib/tests/` 通用集成测试、`src/isarch/encoding.rs`、`scripts/migrate_float_ir.py` 和8份 `test/float_ir/` 回归／配置。`isla-lib/src/primop/float.rs` 的合并候选最终与原工作区逐字相同，两个冲突并不都成为最终差异。

以上证明文件树和部分实际行为不同，差异属于原目标的 bug fix、实现调整及验证补充；按用户的代码意图口径，不能据此判为不等价。意图一致不表示每个输入的旧行为被保留，也不把单测通过外推为全输入证明。

## 本轮验证与保全

候选执行 `cargo fmt --all -- --check`、默认 `cargo check --offline -q -j 8 -p isla --bin isarch` 均退出0。Rust回归采用 `--offline -q -j 8 --features itrace,smt-thread-interrupt -- --test-threads=1`：`-p isla --lib --bin isarch` 通过93库＋25bin；`-p isla-lib --lib primop::float::generic_float_tests::` 通过10项；四份集成测试分别8、2、2、3项通过。构建缓存使用 `.worktree/general-review-20261007/cargo`；本轮没有运行 make solve、全库、全77项或硬件差分，限定 PASS 仅覆盖合并后的上述检查。

原 `isla/` 的 HEAD、三分支引用、完整索引条目、staged／unstaged binary patch、status 清单和全部1001个源码文件／链接均核验不变，父 gitlink 未移动。

证据目录 `.worktree/isla-merge-check-evidence-20261008/`：`comparison.json` 保存完整差异清单及计数，`original-to-merged.patch` 保存逐文件补丁，`resolution.json` 与 `*.conflicted` 保存冲突和解决选择，`checks.json` 与各日志保存验证命令／结果，`preservation.json` 保存保全结论。最初 merge 与末尾保全脚本的 write-tree 在普通沙箱因 Git 元数据目录只读而未完成；前者在获准的隔离工作树 Git 操作后重试，后者复用已成功记录的 tree 值后完成，不计生产测试失败。


## 创建 float-support 基线工作树

用户要求在 `.worktree/` 创建 feat/float-support 工作树。该分支仍由原 isla 工作区检出；计划保留原目录及其 HEAD／索引／补丁，在 `.worktree/isla-float-support` 创建分支当前提交的 detached 工作树。此目录用于独立操作，不自动复制原未提交改动或接入上文合并候选。创建后核对新目录版本／干净状态及原工作区保全。

已创建并核验：`.worktree/isla-float-support` 为 detached `7b7337b0dea0c4105644436a606dbec5ae9b3fea`，与 feat/float-support 当前提交一致，工作树干净。原 isla HEAD／分支／完整索引条目／两层补丁／status 及父 gitlink 保持；创建证据为 `.worktree/isla-float-support-creation-20261008.json`。不涉及源码修改或功能验证。
