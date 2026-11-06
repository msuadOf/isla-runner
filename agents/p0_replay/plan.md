# E0 实施计划

按 [既定设计](design.md) 完成框架探针，不扩展到 E1—E4。

- 范围：新增 `difftest-xiangshan/paging_replay.py` 与定向测试；保留现有 pipeline 和分析器。
- 输入：只读使用 isla-enumerate 的 samples v1 与 pt_decode；记录 SHA-256。
- 步骤：先测试红灯；实现 Sv39 ld 的严格解码、重定位、规范化和 ELF；逐个运行五例与错误期望负对照。
- 验证：记录完整 stdout/stderr、退出码、GOOD/BAD/ABORT、符号和 CSR 证据；单次 emu 最多 600 秒。
- 未决：L2TLB 是否在异常提交前阻断；NEMU 高 PA 行为；页异常强制同步的实际效果。
- 边界：不写其他工作树、不做 Git 写操作、不重编 emu。运行产物统一在 `output/e0/`。

详细结果见 [E0 报告](e0-results.md)，摘要见 [status](status.md)。

## P0 批次 A（2026-11-07）

按 design v2 执行，顺序为 E-exit、设备区、扩展场景。第一部分失败不阻断后两部分。

- 可改：paging_replay.py、定向测试、本议题结果与摘要、全仓状态和发现。design.md 保持原样。
- E-exit：先补归类及 ELF 静态检查测试并确认红灯；实现正向 PC 匹配、哈希校验和原因码；重跑 E0 正负例及 X1—X5。旧正例 PASS 在代码变更后待复验。
- E-dev：冻结 E-cfg 运行器和 IR，低端设备窗口分别使用 mmio+excluded、仅 mmio；T64，单次 1200 秒。统计实际访问与 AF 目标，必要时定向约束目标验证判死。
- 扩展：Sv39 STORE、Sv48 LOAD/STORE；T32，最多同时 4 个，单次 1200 秒。记录路径、类、形状、地址和禁读区断言。
- 输出均在 output/；不做 git 写操作、不写其他工作树或 /home。逐次命令和哈希随结果保存。
- 未决：设备区 excluded 能否阻止访存前的 AF 分支；STORE 解码和直方图须区分数据写与 PTE 读。
