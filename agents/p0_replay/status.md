# P0 重放器状态

**E0 已完成实验与取证，整体验收 FAIL（2026-11-07）。** 五个原始 Isla 正例的 C1+C2 通过。错误期望进入 `fail_unexpected_trap`，但现有 emu 把约定的 a0=1 XSTrap 仍报 GOOD，没有达到必须 BAD 的要求。

| 项目 | 当前状态 |
| --- | --- |
| 最小重放骨架 | 已实现；新增文件，原 pipeline/分析器未改 |
| 定向测试 | 9/9 PASS，含 ELF 实际链接；红绿证据在 `output/e0/` |
| L2TLB | 事件宏已编入；检查器未启用；保留位正例未 ABORT；启用后的行为未测 |
| 高 PA | 有效 RAM 低位别名探针中，NEMU 与 DUT 都 AF，无强制同步 |
| 页异常 | 动态确认 guided_exec 强制同步，C1 一致不代表独立 PF 检查 |
| 负对照 | C2 正确分支；实际 BAD 要求 FAIL；解析器已防止误记 GOOD |
| 后续 | 先决定受测 emu 的 XSTrap 退出码问题，再签收 E0；E1—E4 未测 |

- [既定设计](design.md)：保留原文；其中 L2TLB 门控及 a0 退出码假设的修订证据见报告。
- [实施计划](plan.md)
- [E0 结果、命令与边界](e0-results.md)
- 原始输入、ELF、哈希、完整日志与只读 SO 观测器均在 `output/e0/`；总账 `output/e0/evidence.json`。

未执行 Git 写操作，未修改其他工作树，未重编 emu。
