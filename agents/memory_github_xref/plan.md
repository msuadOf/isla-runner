# GitHub 内存 issue 与本仓求解／重放对照计划

日期：2026-09-29。

## 目标与范围

按 clause 组对照上游已报告的内存问题、当前工作区源码及既有 W19/W24 记录，判断漏检发生在模型／输入域、符号执行与见证选择、JSON 物化、ELF 生成、模拟器／参考模型哪一段。重点为 VSSEG、SC／AMO、错位向量访存与 PMP。上游 issue 正文和评论是上游状态依据，本仓原始结果按其记录的版本适用。

只读取当前工作区、公开 GitHub 和在当前工作区保存的定向测试产物；不进入 `isla/.worktrees/memory-consistency`，不读取或使用其他工作区的代码、二进制和运行目录。不启动新的全量求解或批量模拟。

## 热点文件与分工

- 主 agent：核对 `isla/src/isarch/exec.rs`、`sail-riscv/model/sys/vmem_utils.sail`、`sail-riscv/model/extensions/V/vext_mem_insts.sail`、`difftest-xiangshan/pipeline.py`；组织当前工作区两组定向 PoC，写本专题报告和状态。
- `github_memory_cases`（Sol high，只读）：核对 XiangShan #6475/#6486/#6316/#6296/#6605 上游正文、评论、修复与本仓 clause 对应；不改文件。
- `memory_cause_review`（唯一 Astra high，只读）：独立审查 #1574、segment 越界、VLSEGFF 与错位访存的语义和分阶段归因；不改文件，不建下级代理。

## 步骤与验证

1. 记录源码 HEAD、IR／pipeline／emu 哈希及历史 W19/W24 版本边界；查 GitHub 原文与维护者评论。
2. 对每个 issue 追踪：触发谓词 → 生成 JSON 是否含对应编码和值 → `prepare/build` 是否保留 → ELF 到达 payload 时的状态 → DUT/REF 观察。
3. 在本工作区做少量定向对照，单独标为定向测试，不并入官方求解分母；保存输入、ELF、日志和哈希。
4. 给出确定、可排除与仍缺原始逐例证据的归因；同步专题状态及全仓摘要。

未决：历史 W19/W24 原始 JSON／ELF 与 E 线详细 PoC 记录于工作区外，本轮不读取。只能对当前工作区内的源码、上游附件和新定向探针做逐字节核账；历史统计沿用本仓文档并明确版本。
