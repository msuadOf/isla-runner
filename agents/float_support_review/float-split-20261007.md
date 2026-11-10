# 浮点专用改动按类型提交（2026-10-07）

## 目标与范围

在`.worktree/isla-float-20261007`新建`feat/float-support-split-20261007`，以通用8提交末端2792afd为基线，完整带入原isla当前文件。原isla及通用工作树的HEAD、索引与文件内容不变，只在新分支提交浮点专用剩余。用户要求按类型分明，不合成大提交，也不拆成逐函数碎片。

## 步骤与提交边界

1. 保存两处索引/HEAD、通用工作树剩余补丁及原24个修改文件的哈希与副本。
2. 顺序提交六类：类型化浮点primop及SMT类型查询；现有生成IR；专用SoftFloat分派退役与35例语义回归迁移；fcsr符号状态；官方77项FS/VS见证偏好；FD非访存入口与配置。
3. 首层保留旧专用实现，以保证后续生成IR切换前的依赖完整；第三层删除旧实现并带入替代回归。IR单列便于审查巨大生成差异。
4. 隔离候选按层验证，使用刷新后的文件时间戳避免Cargo误用旧产物。最后逐项核对新工作树文件和原24文件快照，新分支工作区应干净。未push，不移动父gitlink。

## 验证计划与已知边界

浮点primop定向测试、旧SoftFloat 35组普通helper回归、Target/collector及isarch测试、fmt、Make目标展开与FD配置核验；最终make solve的MRET及一个非访存浮点clause要检查gen而非仅退出码。IR保留当前d012哈希，生成来源见[IR记录](ir-refresh.md)，本次不重新生成。

新近[通用审查](../general_support_review/report.md)确认基线的MixedBits算术消费者、VLEN256物化回归及MPP能力域遗漏；这些不在本次提交整理范围，不记为修复。浮点primop层会带入已有的MixedBits浮点转换支持，但不能据此宣称通用基线完整通过。生成IR来源含Sail-RISC-V未提交源码，本次只固定当前生成产物，不能声称固定完整源码链。

证据目录`isla/target/float-split-20261007/`。实施及限定验证已完成，见下文。

## 完成记录

工作树`.worktree/isla-float-20261007`，分支`feat/float-support-split-20261007`；继承2792afd及其8个通用提交，本轮仅新增下列6个浮点提交。

| 提交 | 内容 |
| --- | --- |
| `bc7bc59` | 完善浮点 primop 的类型校验、位模式转换与运算支持 |
| `0843c79` | 更新 RV64 浮点模型 IR 为普通 Sail helper 实现 |
| `2028551` | 移除专用 SoftFloat 分派并迁移旧语义回归 |
| `45bb33a` | 将 fcsr 纳入 RISC-V 符号前后态 |
| `aabca5f` | 为官方浮点指令选择可编码的 FS/VS 见证 |
| `2d46ce7` | 增加 RV64 非访存浮点求解入口并调整 FD 配置 |

原isla HEAD/索引及原24文件、通用工作树HEAD/索引/残余补丁及24文件均核验不变。新分支工作树干净，完整跟踪内容与提交tree逐项一致，未push。相对原副本仅新增测试runner修正：具体结果经过既有`replace_mixed_bits`归一化后再做位值断言；生产代码保持迁入内容。

### 验证

各层`cargo fmt --all -- --check`通过；独立runner另用`cargo fmt --manifest-path test/softfloat_legacy/runner/Cargo.toml -- --check`通过。以下cargo测试均`--offline -q`、`--features itrace,smt-thread-interrupt`、`-- --test-threads=1`：

- 第1层及第3层：`-p isla-lib --lib primop::float::generic_float_tests::`，各10项通过。
- 第4层：`-p isla --lib isarch::target::tests::`，35项通过。
- 第5层：`-p isla --lib --bin isarch`，83库＋25bin通过。
- 第6层：默认`cargo check --offline -q -p isla --bin isarch`通过；Make展开确认FCVT_S_BF16使用FD配置，TOML解析确认启用F/D。
- 第2层用wrap.py核验普通helper体并生成15个包装器；第3层`cargo run --offline -q --manifest-path test/softfloat_legacy/runner/Cargo.toml -- <wrapped.ir> test/softfloat_legacy/cases.tsv`，35/35通过，检查完整结果/flags差异为UNSAT。

首轮浮点单测过滤误写`primop::float::tests::`导致0项，不计PASS，已改正确模块并重跑。首轮legacy在首例具体MixedBits上失败，复用现有接口修正runner后35项通过；失败日志保留于`initial-*`。不改预期向量，不缩减断言。

在新工作树执行：

```sh
CARGO_TARGET_DIR=<原isla/target> CARGO_NET_OFFLINE=true make solve-MRET solve-fd-nonmem   FD_NONMEM_RV64=FCVT_S_BF16 THREADS=1 ITRACE=1   OUTER_TIMEOUT=90s SOLVE_TIMEOUT=70s SMT_TIMEOUT=20s TASTIC=qfaufbv
```

退出0。MRET为4 gen（3 Retire、1 Illegal），FCVT_S_BF16为39 gen（36 Retire、3 Illegal），逐项有机器编码，两项均intime。组合目标进度计数显示`[1/]`/`[2/1]`，这是直接目标和聚合目标共享计数的现有显示行为，不用它核算结果。没有跑全77项或硬件差分，不能宣称浮点全面验收；基线通用回归仍见前述审查。

IR与两个配置、二进制SHA-256见`smoke.json`；详细测试命令在`checks.json`，逐层提交和文件列表在`after.json`，原始快照在`manifest.json`/`full/`。`target`链接复用原构建缓存，输出保存在新工作树，不覆盖原output。此次生成IR提交保留历史生成provenance，不包含或固定当前Sail-RISC-V源码改动。

## 2026-10-08 撤回

用户已要求删除feat/float-support-split-20261007及对应工作树，已完成。源码无后续更改，output证据迁至isla/target/float-split-20261007/withdrawal-20261008；原isla HEAD/索引/两层diff核验不变。下次从指定7b7337b仅提取浮点，见[新计划](float-only-20261008.md)。
