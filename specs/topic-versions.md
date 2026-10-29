# 根仓float／memory版本分支

根仓分支 `float` 和 `memory` 分别用两个gitlink记录Isla与Sail-RISC-V的精确提交。它们从共同根仓基线 `a85d6df` 建立；根仓该基线的harness与文档为共同内容，不把原工作区未提交材料隐式归入某一议题。

| 根仓分支 | Isla | Sail-RISC-V | 当前定位 |
| --- | --- | --- | --- |
| float | 8fae36a9，通用＋浮点与JSON修复 | afff3822，模型与汇编修复 | IR同步、双工具链定向验收 |
| memory | bdd047bc，内存与JSON修复 | c70482a7，内存模型与预算坐标 | IR同步、定向内存语义验收 |

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

线上发布前，须先将manifest引用的精确子模块提交推送到 `.gitmodules` 中正式远端的可获取分支，再推根仓float/memory。当前版本已在本机形成根仓提交；本轮只从本机源仓获取子模块对象，未重新核实正式远端可获取性，也未推送。尚不能把本机成功初始化当作其他机器可从GitHub复现。

发布完成后的根仓更新流程如下（以float为例，memory替换分支名与目录）：

```sh
git -C .worktree/runner-float fetch origin
git -C .worktree/runner-float status --short
git -C .worktree/runner-float merge --ff-only origin/float
```

只在父仓与两个子仓都干净时快进更新。若gitlink变化，在该隔离工作树内先确认子仓无修改，再显式运行 `git submodule update --init --checkout` 对齐记录版本；已有修改时先保留并处理，不能强制覆盖。随后 `./init.sh --submodules-only` 核对版本。新机器可在发布后分别以 `git clone --branch float --recurse-submodules <根仓URL>` 和memory创建两套完整目录。

## 构建与验证边界

两套版本的全部五个IR文件均从当前固定模型完整生成，配置、模型文件与工具哈希见`isla/ir/provenance/manifest.json`。工具链为浮点扩展Sail0.20.1快照；普通同版本发行版不能替代，快照的完整源码树未重新核验。源码预算区域已分别迁移到当前模型。

定向JSON、GCC/Clang文本编码往返、浮点helper/状态和内存数组测试通过，具体范围见[验证记录](../docs/json-semantic-validation-20261030.md)。JSON明确记录采样、错误、未完成和裁剪；`finished`也不宣称源码控制流全覆盖。没有完成全部77浮点clause、全部访存/异常域或硬件重放验收。

## 版本更新记录

2026-10-30：float从Isla be1296b／模型3ea3cbaf更新为b0138b7／18389a89；memory保留Isla47ac90c，模型从4f2ac293更新为1fa93117。同步manifest、gitlink及独立子模块检出，版本核对与`./init.sh --submodules-only`通过。本轮未重新生成IR、编译组件或执行联合功能/硬件测试；旧组件测试不自动转记为当前根仓成套验收。

2026-10-30复审修复：同步当前两套模型IR、迁移workaround坐标，补JSON结果合同及SC覆盖配置；汇编要求GCC与Clang双通过。当前组件版本及定向验收见上文，前一次未重生IR的结论保留为历史版本记录。
