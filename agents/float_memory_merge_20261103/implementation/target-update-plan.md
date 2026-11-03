# 最终发布与原 memory 目标更新操作稿

本文件只准备命令与收据格式，尚未执行发布、stash 或目标快进。操作人先取得最终双亲的 Isla、Sail-RISC-V、父仓三个完整 SHA，以及最终冻结源码清单、IR manifest 和独立签收。旧 core 预冻结树 `56609a6a`、清单 `d63f38c3`、输入 `d8899681` 已被两处 runner 兼容修覆盖，只作失效快照；正式身份以新冻结并完成独审的版本为准。

## 发布前核对

- 原 memory 根 HEAD 仍为 `31ef3b9a8aa3a9db4c03a1d99c191cadf1aadaef`；原 Isla HEAD 仍为 `bdd047bc67c357f3c6e9c4d34b5ec9daaf81ab57`，原 Sail-RISC-V HEAD 仍为 `c70482a73be2a67c5a89d88b1e6c2bbea224940c`。三个最终提交分别是对应原 HEAD 的后代；父仓提交有 memory 与 float 两个父提交，两个 gitlink 与 `topic-version.json` 完全相同。
- 原 memory Isla 暂存区为空，`git status --porcelain=v1 --untracked-files=all` 仅显示 ` M README.md` 与 ` M scripts/run.mk`；两文件补丁 SHA-256 仍为 `e67728f312f49c5505cd651be547c5514064a5709e78432df865b06dbc93e5d8`，文件 SHA-256 分别为 `ac4003d412be230cc1efd2b853495b5ac7fce450924c26359a479a07a449225c`、`683c2b49ffee648ab38a303e2f3db7b7e0b89ea08d3c6d670607d29e11fb318c`。原模型树及根仓除子模块状态外须无其它未提交改动。任一条件变化先重新核对，不继续操作。
- 用正式 URL 核远端目标分支当前 SHA 及最终提交是否可从对应候选仓推送。组件目标分支此前观测为缺失，发布前须重读；并行推进时只接受非强推的快进，不覆盖远端。

## 组件先发布，父仓后发布

以下变量取最终签收的完整 SHA；命令只作为执行稿。使用正式 URL，候选子仓的 `origin` 指向本地原 clone，不能作为发布目标。

```sh
ISLA_MERGE_SHA=<final-isla-40-hex>
MODEL_MERGE_SHA=<final-model-40-hex>
ROOT_MERGE_SHA=<final-root-40-hex>

git -C .worktree/merge-float-memory-20261104/sail-riscv push https://github.com/msuadOf/sail-riscv.git "$MODEL_MERGE_SHA:refs/heads/feat/sail-riscv-memory-by-model-20261022"
git ls-remote https://github.com/msuadOf/sail-riscv.git refs/heads/feat/sail-riscv-memory-by-model-20261022

git -C .worktree/merge-float-memory-20261104/isla push https://github.com/ariscv/isla.git "$ISLA_MERGE_SHA:refs/heads/feat/memory-consistency"
git ls-remote https://github.com/ariscv/isla.git refs/heads/feat/memory-consistency

git -C .worktree/merge-float-memory-20261104 push https://github.com/msuadOf/isla-runner.git "$ROOT_MERGE_SHA:refs/heads/memory"
git ls-remote https://github.com/msuadOf/isla-runner.git refs/heads/memory
```

每次 `ls-remote` 的完整 SHA 必须与刚推送的目标一致；不使用 `--force`。若远端推送或回读失败，保留已发布结果并记录实际状态，停止后续步骤，不虚报整组发布成功。

## 原目标的最小快进

发布与最终验收都完成后才处理原 Isla 的两处 dirty。先将原补丁和两个完整文件字节、哈希保存为收据；再次执行上面全部 HEAD/status/hash 检查。仅针对两个精确路径创建 stash：

```sh
git -C .worktree/runner-memory/isla stash push -m 'float-memory-merge-preserve-original-two-files-20261104' -- README.md scripts/run.mk
git -C .worktree/runner-memory/isla rev-parse 'stash@{0}'
```

立即记录 stash commit 完整 SHA，核 `git show <stash-sha>:README.md` 与 `git show <stash-sha>:scripts/run.mk` 的 SHA-256 等于原文件。这个 stash 保存原字节，不 drop，也不机械 reapply：两处 Make/Z3 效果已在候选中按最终源码和运行结果复核。确认原 checkout 清洁且最终提交为原 HEAD 后代，再分别在原两个 detached 子模块 checkout 执行 `git merge --ff-only <对应最终完整SHA>`；最后在原根仓 `memory` 分支执行 `git merge --ff-only <父最终完整SHA>`。父仓若因子模块 checkout 状态拒绝快进，停止并核对 index、工作树与目标 gitlink，不用 reset、clean 或强制 checkout。子模块任何一步失败时保留 stash 和已更新 HEAD，不做回滚式覆盖。

## 收据字段

最终在本议题记录一个小型 JSON：`date`、三仓 `before`/`after` 完整 SHA、根提交两个 parent、父 gitlink 与 metadata/IR 哈希、两文件原补丁/完整文件 SHA-256、stash commit SHA 与其两个 blob SHA-256、各正式 URL/目标 ref 的推送前值与回读值、每一步命令的退出码、最终 `git status --porcelain`。只写实际取得的值；失败或未执行的步骤标 `not-run` 或失败码，不填推测值。收据不包含本机绝对路径、构建产物或原始 trace。
