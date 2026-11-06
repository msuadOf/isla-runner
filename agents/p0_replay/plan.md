# E0 实施计划

按 [既定设计](design.md) 完成框架探针，不扩展到 E1—E4。

- 范围：新增 `difftest-xiangshan/paging_replay.py` 与定向测试；保留现有 pipeline 和分析器。
- 输入：只读使用 isla-enumerate 的 samples v1 与 pt_decode；记录 SHA-256。
- 步骤：先测试红灯；实现 Sv39 ld 的严格解码、重定位、规范化和 ELF；逐个运行五例与错误期望负对照。
- 验证：记录完整 stdout/stderr、退出码、GOOD/BAD/ABORT、符号和 CSR 证据；单次 emu 最多 600 秒。
- 未决：L2TLB 是否在异常提交前阻断；NEMU 高 PA 行为；页异常强制同步的实际效果。
- 边界：不写其他工作树、不做 Git 写操作、不重编 emu。运行产物统一在 `output/e0/`。

详细结果见 [E0 报告](e0-results.md)，摘要见 [status](status.md)。
