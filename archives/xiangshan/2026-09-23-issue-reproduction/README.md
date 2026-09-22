# XiangShan Issue 草稿复现档案

2026-09-23 完整复制自 `agents/vext_issue_draft_reproduction/`，保留 plan/status 与 issue1/issue2/issue3 的相对关系。37 个文件的来源、大小、SHA-256 见 `manifest.json`，源文件保留；本轮没有重新编译 ELF 或执行仿真。

入口：[历史复现状态](status.md)。每项包含汇编、链接脚本、ELF 与原始 stdout/stderr；已有退出码和 ELF 校验文件一并保留。原报告引用的草稿及 emulator 在其他子仓库内，未复制进本包，不宣称本包独立包含完整构建环境。

Issue 1 只具备超时/未达 GOODTRAP 的观测，没有完整 itrace/VCD，不能据此证明永久挂死或最后提交位置。历史状态里的“永久挂起”应按此证据边界理解。Issue 2/3 差异日志原样保存。历史远端版本说明仅指当时核验，不表示本轮联网核验。
