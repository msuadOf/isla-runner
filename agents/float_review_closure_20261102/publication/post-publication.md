# float发布后独立回读收据

结论：**PASS_ROOT_COMMIT_AND_THREE_REMOTE_REFS_VERIFIED**。根仓float已发布为`0665526d7e14a207eb9928e282e627584b5635fe`，两个组件与根仓正式远程分支的独立`git ls-remote`回读均准确一致。

| 仓库/分支 | 实际远程SHA |
| --- | --- |
| isla-runner / float | `0665526d7e14a207eb9928e282e627584b5635fe` |
| isla / feat/float-support | `591693df2bc32019ea300511509ed683df09522e` |
| sail-riscv / feat/sail-riscv-general-float-by-model-20261022 | `0f7b8fbc6724103f91f929ef6918f123df75d6c9` |

根commit的parent为a6b6ecd，2173个变更路径；移除新增两个refseal后，完整树精确等于独审的2171路径暂存树。两refseal与主topic逐字一致，rootfloat工作树含两个子模块clean。精确tree与证据锚点见[机器收据](post-publication.json)。

这是主工作区的本地外部收据，不属于其引用的根commit，也不要求创建第二个根commit。已提交float文件和原final-signoff保持原封字节；限定验收与OPEN延期memory范围均保持，不新增全77预算、全域覆盖或硬件验证结论。
