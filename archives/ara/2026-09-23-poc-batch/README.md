# Ara PoC 档案（整理日期 2026-09-23）

完整复制自 `agents/ara_poc_batch/`，保留 `snapshot/` 及其父层 bugs/plan/status，以保持报告的相对引用。共 253 个源文件，逐文件大小、来源和 SHA-256 见 `manifest.json`；复制后再次校验源集合和源哈希。原文件未删除。

入口：[实验报告](snapshot/REPORT.md)、[含修订的现象清单](bugs.md)、[历史状态](status.md)。日期是整理日期，不是重跑日期。VLEN=128 的非官方实验与 VLEN=2048 合法配置复验分别保留，不合并成同一基线。

历史记录包含阶段性结论和后续纠正；例如 mask tail 写 1、vsetvli rs1=x0 特例的早期判断已被后续记录否定。以 bugs.md 的后续修订及合法配置证据为阅读依据，本次未重新核验全部科学结论或远端 issue 状态。

4 个 10 MiB 以上的 JSON（input.json 及三份 outcome 结果）是完整输入/结果集合，最大约 15.7 MiB，随普通 Git 保存；未仅留摘要。`tmp-artifacts/` 是已有 triage 证据，不因名称含 tmp 而删除。

历史绝对路径、`/tmp` 路径和工具默认值原样保留，新机器不能保证直接执行。模拟器、完整上游源码和未纳入原 snapshot 的其他 work 输出不在此包中。此快照不可覆盖重跑，维护入口是根 `ara/pipeline.py`。
