# XiangShan harness 整理快照：2026-09-21

来源为根目录 `difftest-xiangshan/`，本目录保留其相对路径。日期是整理日期，不是全部实验的执行日期；未重跑 RTL，也未重新审核历史结果的正确性。

- `inputs/`：全部现有批次输入。
- `poc-final/`：3 份汇编源码与 3 份既有 ELF；外层 harness 仍保留可维护的源码。
- `work/`：各批次 JSON/NDJSON 清单、结果及 Markdown 汇总，不含 `case-*` 逐例目录。
- `manifest.json`：源路径、快照路径、字节数、SHA-256、源修改时间以及本地大型档案信息。清单本身不递归计算自身哈希。

完整 `work/`（含逐例程序、日志等）与旧模拟器保存在根目录 `archives/_raw/xiangshan/2026-09-21-harness/work-and-baseline.tar`，不进入普通 Git。它只是同机保全，**不是远端备份**，新 clone 不含该 tar。全部源文件和运行路径仍保留，本次没有删除。

一致性限制：tar 打包成功，但随后 `tar --compare` 返回 1，仅报告 `work/rerun-c8d7b3a/shards/monitor.log` 大小与修改时间已变化，其他成员未报告差异。因此这是非原子采集，不能称为整个运行批次的同一时刻完整快照。未停止任何用户进程；另将该日志的较新版本独立复制到本目录对应 `work/` 路径并校验哈希。若需要严格一致的全量归档，需用户先停写后另建新批次。

还原时应先检查 manifest 中 tar 的 SHA-256，再解包到新建空目录；不要覆盖活跃运行目录。清单与结果中的原始绝对路径未改写，历史路径不保证在其他机器直接有效。

## 复现边界

当前 checkout 的 SHA 仅作整理环境记录，不意味着每个历史结果都由当前版本生成。`emu-baseline-7bf51a8` 的完整历史构建参数未核实，不凭文件名补造版本或配方。

PoC 注释提到的 `link.ld` 在原 `poc-final/` 和已检查的 `work/` 中未找到；旧 ELF 也未与当前汇编重新构建比对，不能宣称二者严格对应。本次原样保全，不补写源码或用其他实验的 linker script 冒充原文件。更完整的 issue 复现记录仍见根 `agents/vext_issue_draft_reproduction/`，尚未纳入本批次。

单元测试现有 14 项中 10 项通过、4 项报错：测试 mock `subprocess.run`，实现已使用 `subprocess.Popen`，导致 mock 未拦截并尝试启动不存在的 `emu`。这是原有测试与实现不一致，不是归档产生的代码修改；本批次仅记录，不修复。四个运行入口的 Bash 语法检查通过。
