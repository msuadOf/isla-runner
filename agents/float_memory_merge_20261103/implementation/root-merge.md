# 父仓合流实施记录（2026-11-04）

候选父仓：`31ef3b9a8aa3a9db4c03a1d99c191cadf1aadaef`（memory）；待纳入：`0665526d7e14a207eb9928e282e627584b5635fe`（float）；共同基线：`a85d6dfb8a906f17d6710cb85f26668b753729ce`。

标准 `git merge --no-commit --no-ff 0665526d` 因父仓 commit-graph `fatal: invalid commit position. commit-graph is likely corrupt` 未启动；临时 `-c core.commitGraph=false` 的 ort 策略在追溯 Isla 子模块对象 `ba729ce95d22be88abd0a8d3cad77ab553c424db` 时失败，该对象在候选子仓不可读。未修复或改写共享 commit-graph，未移动子仓 checkout。随后执行 `git -c core.commitGraph=false merge -s resolve --no-commit --no-ff 0665526d`，形成 `MERGE_HEAD=0665526d` 的未提交父仓合流。resolve 策略留下九条冲突：七个父仓文档/元数据文件，加 `isla` 与 `sail-riscv` 两个 gitlink。

七个父仓冲突采用版本限定的合并：`GIT.md`、`README.md`、`docs/RESULTS.md`、`docs/json-semantic-validation-20261030.md`、`specs/TODOs.md`、`specs/topic-version.json`、`specs/topic-versions.md`。memory 为当前 topic；两分支旧验证仅历史保留。版本文件用 JSON null 表示未取得的最终组件提交和 IR SHA；主 agent 在 gitlink 与最终 IR 确定后必须回填，不能以候选模板发布。`feat/witness-randomization` 仍排除；旧 float/general 排除项合流后取消。全部工作只涉及父仓文件，子仓冲突由各负责人处理。

最终父仓定稿时检查：两个 gitlink 与 `components.*.commit` 相同；主 IR 的 SHA-256 与 `ir.sha256` 相同且 provenance 指向实际 manifest；当前状态与测试记录仅署本次受测源码/配置；父仓两个 parent 可达且无未解决冲突。正式远端可获取性另核。本记录不计任何组合测试 PASS。

## 原 memory Isla 工作树的两处未提交改动保护

2026-11-04 只读复核 `.worktree/runner-memory/isla`：HEAD `bdd047bc67c357f3c6e9c4d34b5ec9daaf81ab57`，仅 `README.md` 与 `scripts/run.mk` 有未暂存改动，暂存区为空。两文件 `git diff --binary` 的 SHA-256 为 `e67728f312f49c5505cd651be547c5514064a5709e78432df865b06dbc93e5d8`；完整文件 SHA-256 分别为 `ac4003d412be230cc1efd2b853495b5ac7fce450924c26359a479a07a449225c`、`683c2b49ffee648ab38a303e2f3db7b7e0b89ea08d3c6d670607d29e11fb318c`。本次未 stash、未改写该原工作树。

原补丁的语义点：`scripts/run.mk` 为 `ALL` 中的目标指定 `qfaufbv`，再为 `FD_FLOAT` 中排除 `MEMORY` 的目标指定 `qffp`；命令行 `TASTIC=...` 仍可覆盖，直接运行 `isarch` 不传 `--tastic` 保持 `default`。`build-isarch` 通过 `RUSTFLAGS` 加入版本化 `Z3_PREFIX` 的库搜索路径及 RPATH，默认前缀指向官方 Z3 `1fd1d3613c1f34c4dff36cba3209b2234f6c6d2b`。README 记录 `solve-FLEQ_S` 为 `qffp`、`solve-LOAD` 为 `qfaufbv`，以及前缀覆盖方式。候选子仓当前 `scripts/run.mk` 与 README 已有对应规则和说明，但具体 Make 展开、动态链接版本及运行效果由 Isla 负责人在最终源码上验证；此处不把文本对应写作测试 PASS。

最终验收完成后，若这两处 dirty 阻碍原 memory Isla checkout 快进：先重新核对 HEAD、`git status --porcelain`、上述补丁及两个完整文件 SHA，确认仍只有这两处未暂存改动且暂存区为空；将补丁和文件 SHA 留作收据。随后仅在原 memory Isla checkout 对 `README.md`、`scripts/run.mk` 执行带 pathspec 的 `git stash push`，记录 stash commit SHA，并用 stash tree 的两文件字节哈希核对原值。该 stash 保留，不 drop；它保存原字节与补丁，不是丢弃。确认最终合流提交包含原 HEAD、原 checkout 无其他变化后才 `git merge --ff-only` 到最终 Isla 提交。因为效果已纳入合流候选，不机械 reapply stash；出现新增改动、哈希不符或非快进时停止并重新核对，不碰其他路径，不用 reset/clean。

## 组件双亲提交与父仓暂存 gitlink

模型提交 `bf861b3e687894480aec701a886a38d4e50b8a99` 的父链为 `c70482a73be2a67c5a89d88b1e6c2bbea224940c`、`0f7b8fbc6724103f91f929ef6918f123df75d6c9`，tree `8b991abd601777a07c62504ad457651b9728fab2`。Isla 提交 `7cce7834b6f1376293dfce1d52b7e944fa237941` 的父链为 `bdd047bc67c357f3c6e9c4d34b5ec9daaf81ab57`、`591693df2bc32019ea300511509ed683df09522e`，tree `88a930026ca31c23225d5f9509b2b23502d14f77`。两子仓 checkout 均 clean。父仓将两个 gitlink 暂存到这些提交，原九个冲突已全解；`MERGE_HEAD=0665526d` 继续保留，未提交父仓。

主 IR `isla/rv64d.ir` 与 V128 别名 SHA-256 为 `40f34f706963afcca7dfbf8504ee888bdd004cd0c437712f097b7dda64a705c9`，`isla/ir/provenance/manifest.json` SHA-256 为 `8e06ec617ca8378d965f8d9b2f0f882e7262520e9ac5cb488604f7470949268b`。`specs/topic-version.json` 已回填两个 gitlink 与主 IR 的实际值。此段实施时 `validation.status` 待动态验收；现经最终 Release 二进制[独立限定签收](../review/acceptance/limited-signoff.md)记为 `limited-pass`。核心源码独立报告为[core-final-report](../review/core-final-report.md)；旧 v2 结果不能改署最终版本。

## Isla 测试兼容后继提交

双亲合流 `7cce7834` 后的测试兼容提交为 `4d085b14aa0f987436b86d72f41fab1df9e9a132`，父提交精确为 `7cce7834b6f1376293dfce1d52b7e944fa237941`，tree `3d852a5fac6a07ae906e502a430a8ee14a65c075`。相对双亲合流只改 `src/isarch/{exec,memory_model,mod,target}.rs` 的测试初始化与断言，生产区逐字不变，最新独立签收见[核心报告](../review/core-final-report.md)及[最终 seal](../review/core/workspace-init/final/final-refseal.json)。父仓 gitlink、`topic-version.json` 的 Isla commit 已从 `7cce7834` 更新为 `4d085b14`；模型 gitlink与 IR 哈希不变。新 Release 二进制和冻结输入须按最终完整哈希及独立运行结果另核，之前动态结果只保留历史版本边界。父仓仍未提交。
