# 证据快照边界

[状态](status.md)和[动态报告](validation/report.md)记录本轮实际版本、配置、预算与结果。保留生成命令、源码/IR/工具哈希、日志、输出 JSON、独立复核脚本及检查结果。

生成的完整 IR、定向包装 IR、编译 target、程序二进制、Sail SMT 缓存和汇编中间文件不纳入父仓提交。正式五份 IR 固定在 Isla `8e5a3f7`；四配置来源在 `saturation/generation/*/driver.json`，定向 wrapper 由验证脚本和配置重建。工具链中间 `.bin` 字节已由独立 Sol 就地复核，汇总记录保存哈希，完整文件仍在本机。

旧 flags/sat 输入沿用上一轮冻结的原 IR 与配置，来源、哈希及原始命令见 `validation/inputs.json` 和 `validation/runs/*/command.json`。未改变输入来替代完整 Clause 性能验收。精确命令记录含运行当时路径，仅为实验来源，不作为公共安装入口。

修订版源码为 Isla `cf1aa14`，模型仍为 `6202e23`、IR 与 `8e5a3f7` 相同。初版与修订版程序分别按 SHA 冻结；`validation/runs/` 保存初版，`validation/runs/selective/` 与 `validation/selective/` 保存修订版，不能跨版继承 PASS。官方库 Rust 单测的独立编译目录也不纳入，脚本、哈希、ldd 和实际装载证据保留。
