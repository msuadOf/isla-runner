# 根仓float／memory版本分支

根仓分支 `float` 和 `memory` 分别用两个gitlink记录Isla与Sail-RISC-V的精确提交。它们从共同根仓基线 `a85d6df` 建立；根仓该基线的harness与文档为共同内容，不把原工作区未提交材料隐式归入某一议题。

| 根仓分支 | Isla | Sail-RISC-V | 当前定位 |
| --- | --- | --- | --- |
| float | 591693df，77处纯数据回退收敛 | 0f7b8fbc，模型收敛 | 2026-11-03 限定验收；合流后须复验 |
| memory（合流前） | bdd047bc，内存与JSON修复 | c70482a7，内存模型与预算坐标 | 2026-10-30 历史定向验收 |
| memory（合流候选） | 4d085b14，双亲合流后的测试兼容提交 | bf861b3e，双亲合流 | 来源与已测定向范围限定签收；原域 partial 单列 |
| feat/memory-enum（本轮） | d7c25993，含区域合并/枚举，已合入4d085b14 | d79d8b32，新页表模型及vstart早退补件 | 五入口IR重生；本机定向复验见[本轮报告](../agents/memory_enum_ir_20261107/final-report.md)；待发布 |

每条分支的 `specs/topic-version.json` 是本分支的组件记录，gitlink是实际检出依据。float包含已合并通用支持、初态位模式配置、浮点支持及返回值具体化修复，不包含独立见证随机化分支；memory含PMA/CSR、value hints和encoding slices等已提交策略，新增SC双结果覆盖配置与不完整诊断。创建版本分支不代表接纳全部策略或完成联合功能验收。

## 本机入口

在原根目录使用：

```sh
git -C .worktree/runner-float status
git -C .worktree/runner-memory status
git diff float memory -- isla sail-riscv specs/topic-version.json
```

每个根仓worktree下均有独立的 `isla/`、`sail-riscv/` 子模块检出，可以分别进入运行。原根工作区继续位于master，原子仓dirty层保留。不要在原dirty工作区为切换议题运行reset或clean。

## 获取与更新

根仓分支和子模块分支是两层历史。更新子模块代码时先在对应子仓形成提交，再在对应根仓分支显式更新gitlink、manifest与证据，最后提交根仓。`git fetch` 只获取引用，不自动移动gitlink；不要用 `git submodule update --remote` 隐式换版本。

线上发布前，须先将manifest引用的精确子模块提交推送到 `.gitmodules` 中正式远端的可获取分支，再推根仓议题分支。合流前 memory 版本只从本机源仓获取子模块对象，未重新核实正式远端可获取性；float 版本的远端回读证据见[发布记录](../agents/float_review_closure_20261102/publication/final-components.json)。本次合流候选的两个最终子模块提交已从正式目标分支逐 SHA 回读一致，见[组件发布收据](../agents/float_memory_merge_20261103/publication/components.json)；根仓议题分支仍待提交与发布。

发布完成后的根仓更新流程如下（以float为例，memory替换分支名与目录）：

```sh
git -C .worktree/runner-float fetch origin
git -C .worktree/runner-float status --short
git -C .worktree/runner-float merge --ff-only origin/float
```

只在父仓与两个子仓都干净时快进更新。若gitlink变化，在该隔离工作树内先确认子仓无修改，再显式运行 `git submodule update --init --checkout` 对齐记录版本；已有修改时先保留并处理，不能强制覆盖。随后 `./init.sh --submodules-only` 核对版本。新机器可在发布后分别以 `git clone --branch float --recurse-submodules <根仓URL>` 和memory创建两套完整目录。

## 构建与验证边界

合流前两套版本的全部五个IR文件均从各自固定模型完整生成，配置、模型文件与工具哈希见`isla/ir/provenance/manifest.json`。工具链为浮点扩展Sail0.20.1快照；普通同版本发行版不能替代，快照的完整源码树未重新核验。源码预算区域在各自历史版本完成迁移；合流版须重新核对。

合流前两套版本的定向JSON、GCC/Clang文本编码往返、浮点helper/状态和内存数组测试结果见[历史验证记录](../docs/json-semantic-validation-20261030.md)。JSON明确记录采样、错误、未完成和裁剪；`finished`也不宣称源码控制流全覆盖。没有完成全部77浮点clause、全部访存/异常域或硬件重放验收。

## 版本更新记录

2026-10-30：float从Isla be1296b／模型3ea3cbaf更新为b0138b7／18389a89；memory保留Isla47ac90c，模型从4f2ac293更新为1fa93117。同步manifest、gitlink及独立子模块检出，版本核对与`./init.sh --submodules-only`通过。本轮未重新生成IR、编译组件或执行联合功能/硬件测试；旧组件测试不自动转记为当前根仓成套验收。

2026-10-30复审修复：同步当前两套模型IR、迁移workaround坐标，补JSON结果合同及SC覆盖配置；汇编要求GCC与Clang双通过。当前组件版本及定向验收见上文，前一次未重生IR的结论保留为历史版本记录。

2026-10-31：float更新Isla80231ce9／模型9c339044，恢复nan_unbox原Sail if并完整重生IR；两侧见证与数值回归见[本次记录](../docs/nan-unbox-branch-restore-20261031.md)。没有由局部Jump减少推断整Clause提速。memory版本不变，其他独立review问题未在本轮修复。


2026-11-07：根仓 `feat/memory-enum` 基于 memory `29aa4765`，Isla 更新来源为 `d7c25993` 的 `feat/postprocess-enumeration`，包含区域合并/枚举功能且已合入 `4d085b14`。Sail-RISC-V 为 `d79d8b32`，在 `bf861b3e` 上增加 Svnapot、Svpbmt、非叶 PTE 的 U/A/D 保留位检查三项语义补丁，并包含 `70b4d10` 的全寄存器访存早退清零 vstart 与 vmtype 坐标补件。使用相同浮点 Sail 0.20.1 快照与 Isla 插件重新生成全部五入口；旧生成配置因缺新扩展项被 Isla 拒绝后，按当前模型模板补齐 RV64=true、RV32=false，从新缓存重跑成功。新主 IR SHA-256 为 `1220297d0e7dc202c43bb0cee1d95941c4bc3cf62be6fd141d35dbd5a3ad2059`；四配置、命令、工具与历史哈希见 `isla/ir/provenance/manifest.json`。本轮定向结果和限制见[交付报告](../agents/memory_enum_ir_20261107/final-report.md)，旧 `4d085b14/bf861b3e` PASS 和主 IR `40f34f70…` 只保留原版本结论。publication 为**待发布**；本轮未做 Git 写操作、gitlink 更新或远端回读，IR/provenance 尚未提交。


## 2026-11-04 float→memory 合流

根仓以 `31ef3b9a8aa3a9db4c03a1d99c191cadf1aadaef` 为 memory 父提交，纳入 float `0665526d7e14a207eb9928e282e627584b5635fe`。保留 `topic=memory`；模型已形成双亲合流提交，Isla 双亲合流提交之后另有测试初始化兼容提交 `4d085b14`，父仓 gitlink 已暂存指向最终候选。组合 IR SHA-256 和来源见 `topic-version.json`、`isla/ir/provenance/manifest.json`；新二进制的已测定向范围获[限定签收](../agents/float_memory_merge_20261103/review/acceptance/limited-signoff.md)，原域 partial 与全域无退化未证单列，父仓提交/发布仍待完成。旧两分支的 PASS 不迁记。float 的77处纯数据回退、NaN/trap 保留与 OPEN 范围见[交接](../agents/float_review_closure_20261102/handoff-to-memory.md)；本轮不新增通用配置、不研究 OPEN。`feat/witness-randomization` 继续排除；旧 memory 清单中的 float/general 分支在合流后成为祖先，不再列作排除项。

2026-11-07：memory 的 Isla 由 `ae1a3355` 推进到 `78b04e3`（在同一新 IR 之上并入 judge 模式：`--check-samples-judge`，2836 种子五项验证通过，`cargo test` 1108 通过；IR 与来源记录未变）。Sail 仍为 `d79d8b32`。发布状态仍为“待发布”，无独立签收；推进前 `memory` 固定 `ae1a3355`，如需回退用反向提交。
