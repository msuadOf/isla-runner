# 两条源分支术语调整状态

2026-10-29完成。general `refactor/general-support-20261007@cc7700b`、float-only `feat/float-only-20261008@99a28b0` 各自包含TRANSLATOR.md、AGENTS入口及符号值具体化用词/命名调整。目标feat/float-support依次由2fe1173合general、75e7440合float，最终75e74400ca8353b92d72534bdc0f96d191944c0d。

concretize/concretization表示按求解模型取得具体值；变量用concrete_*。general的model_materialization.rs改名model_concretization.rs。延迟生成SMT-LIB2文本的TimeoutSmtDump::materialize接口保留，中文说明改为文本生成。根和两源分支/目标的术语文档字节一致；分支能独立读取规范，不依赖父工作区文档。

验证：general90库＋3具体化测试通过；float-only65库通过（跳过原有rv64_target_trait失败），独立float_ir runner cargo check退出0；最终组合94库＋3具体化测试通过，fmt/diff通过。仅命名/注释/测试名/文档调整，无新增逻辑，不重复数值/全指令/硬件测试；既有功能验证仍适用相同逻辑，未新增全量PASS。

独立GPT-6.1 Sol subagent只读复核：相对daa8bb1没有语义回退；ret_val同模型、错误传播、正确测试断言、runner兼容字段均保留，未恢复已删除SoftFloat特判。

general原dirty工作树完整备份stash08c3182150ed2b1e49c1b58855f49da7b6b4359d；恢复时两个文件有文本冲突，用原文件内容应用同样术语替换解决。逐文件核对8个dirty文件内容与预期一致，未跟踪文件hash一致，索引为空。该工作树仍含原有浮点剩余；独立测试使用干净.worktree/isla-general-terms-20261029。float-only及目标工作树干净。未push、未移动父gitlink。

[计划](plan.md)、[版本/测试/备份](versions.json)。命令输出保存在同目录*-terms-*.log，历史证据不改写。

## 按用户澄清重做原merge（2026-10-29）

用户要求重做原2dbad3b与9217e17，而非在其后新增同步merge。现已重建feat/float-support第一父链：0df2388（父7b7337b/cc7700b）替换原general merge；42ac15e（父0df2388/99a28b0）替换原float merge；其后重放ret_val修复为b0138b7c2ff8addb81f68f42669600a2a9c2b813。额外2fe1173/75e7440同步merge不在当前分支祖先链中。两源分支仍cc7700b/99a28b0，不改其提交。

新旧最终tree均ca8542752be6dc29d33105d25b9f7649fd5e5abc，git diff为空，代码和术语文件没有变化，已有同tree验证继续适用，未重复跑测试。独立GPT-6.1 Sol只读核对父链及tree通过。旧75e7440历史保存在refs/backup/float-support-before-merge-rewrite-20261029；当前工作树干净，未push、未改父gitlink。上文首次追加merge记录保留为历史，不代表现行提交结构。

2026-10-29后续：按用户“旧历史不用备份”的要求，已删除refs/backup/float-support-before-merge-rewrite-20261029。当前feat/float-support仍b0138b7，工作树不变。此前保存用户未提交内容的stash不属于该历史备份，保持原样；未执行reflog过期或对象清理。上文备份存在的描述仅适用删除前。
