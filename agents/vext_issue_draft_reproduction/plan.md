# V 扩展 Issue 草稿复现计划

目标：只依据 `isla/agents/validation/Vext-test-9-16-difftest-xiangshan/issue草稿-原创bug.md` 的文字和内嵌 PoC，从零生成三份源文件、链接脚本和 ELF，并在同一份最新 XiangShan 构建上独立复现三个 Issue。不得检索、复制或使用既有 testcase、ELF、日志或结论。

1. 确认可共享的 XiangShan `emu` 与 `kunminghu-v3` 最新远端跟踪提交一致；若不一致，先向用户报告相差提交数并等待指示。
2. 三名执行者分别按草稿原样创建 Issue 1、2、3 的 `poc.S` 和 `link.ld`，使用草稿指定的交叉编译命令从零生成 ELF。
3. 分别执行草稿指定的 `--no-diff` 或 `--diff ready-to-run/riscv64-nemu-interpreter-so` 命令，在受控超时内保存原始 stdout/stderr 与 commit trace。
4. 针对每个 Issue，依据草稿中的明确观测条件判定“已复现”“未复现”或“环境阻塞”；不以既有产物或历史报告作证据。
5. 汇总运行命令、工具与 DUT/REF revision、输出路径、关键证据以及任何与草稿不一致处。

验收：三项都拥有从本轮源文件重新编译出的 ELF 和独立运行日志，且结论可由日志中的停顿、`mtval` 差异或 vreg 差异直接核验。

根据根目录 `AGENTS.md`，本计划写入后等待用户审阅/确认再启动实际复现。
