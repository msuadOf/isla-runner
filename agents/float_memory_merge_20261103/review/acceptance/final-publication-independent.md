# float→memory 提交与发布终核

**限定交付终核通过，无未关闭的新增实现阻断。** 根提交为 `29aa47656e437d7f41e87d90a894edd125f429c2`，实际 tree `13e56bad2901b7f2c9e863178e45df77db611b61` 与独立签收的暂存树精确相同。双亲依次为 memory `31ef3b9a8aa3a9db4c03a1d99c191cadf1aadaef`、float `0665526d7e14a207eb9928e282e627584b5635fe`。

Isla gitlink 为 `4d085b14aa0f987436b86d72f41fab1df9e9a132`，模型为 `bf861b3e687894480aec701a886a38d4e50b8a99`。独立核对限定元数据、1620 份精选证据实际字节与 SHA、五 IR、源文件和配置均通过。正式 GitHub 远端的根 memory 与两个组件分支已分别通过独立 `ls-remote` 逐 SHA 回读。[暂存树](final-staged-root-independent.json)、[提交后封存](final-29aa4765-refseal-independent.json)、[组件远端](component-remotes-independent.json)、[根远端](root-remote-independent.json)。

原 memory 根仓及两子仓均精确快进到上述提交，完整 status（含未跟踪文件）为空；原 float 三仓 HEAD 与 diff 保持。原 memory Isla 的 README 与 run.mk 保存于保留 stash `26dd19b95545fb1012be38a98e3b3f85ab16f723`，父提交为原 `bdd047bc`。两份完整文件 SHA 与原值相同，实际重读补丁 SHA 为 `e67728f312f49c5505cd651be547c5514064a5709e78432df865b06dbc93e5d8`，与预检原件相同；stash 仍在列表中。首次 guard 因 index 行对象 ID 缩写长度变化暂停的事实留在 owner 收据，未据此删改原始证据。[目标与保护独核](final-promoted-29aa4765-independent.json)。

行为范围仍以[限定联合签收](limited-signoff.md)为准：F1 具体/符号内存不一致仍在；LOAD_FP、STORE、C_LD 原域为 partial；三个 Poison 代表的继承分类不外推全部 922/112/7；STORE/C_LD 旧完整预算长尾未结束，全域无退化未证。float 全 77 预算、全控制流、硬件重放及冻结 OPEN 策略仍不在本次签收范围。

本文件与提交后的收据仅保存在本地审查目录，未修改已签根提交，不为自引用追加提交。提交内“父仓发布待完成”准确记录提交时点，最终发布状态由这些后验收据补充。
