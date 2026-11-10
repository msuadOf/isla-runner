# 按顺序合入feat/float-support

用户授权：先把refactor/general-support-20261007@ef882f0合入feat/float-support，再把feat/float-only-20261008@be1296b合入；独立GPT-6.1 Sol subagent审阅，遵循改动必要、复用原结构原则。追加授权修runner构造器缺字段和ret_val未最终模型具化两项。

主agent独占修改/合并；subagent只读审阅，不创建/编辑共享工作树。先在既有隔离组合候选补最小修复和TDD，然后运行必要测试；备份原isla的staged/unstaged/文件状态，使用持久stash保存，按序产生两个merge提交。旧dirty内容已是待合提交的早期实现，不盲目apply覆盖修复，逐文件核对其归属并保留备份。目标最终树须与受测候选一致。

验证：split编码模型的ret_val必须等于同模型后态；库/核心/集成与独立浮点runner；make短入口的编码/完整初态/返回值检查。独立review最终复核后完成合并；不push、不移动父仓gitlink。状态证据同步到status/TODO/RESULTS。
