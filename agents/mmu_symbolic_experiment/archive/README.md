# MMU 处理后数据

这些文件属于2026-11-03历史实验，本轮仅整理归档，没有重新运行或重新计算哈希。现行结论见[最终报告](../final-report.md)。

- `summary.json`：各批次的已返回路径、耗时、查询和退出摘要；超时计数只表示下界。
- `selected-witnesses.json`：两条历史页表见证的状态、解码和核验结果，不代表当前IR的重新认证。
- `manifest.json`：历史版本和输入来源记录；不把哈希作为有效性门槛。
- `comparison_report.json`、`ab-comparison.csv`：A/B批次统计。旧JSON的`valid_cases_verified=36`只记录手写公式检查，已于2026-11-05撤回“语义合法”解释。
- `historical-report.md`：原报告及归档说明；原始模型、脚本和日志路径不再可用。
- `archive-inventory.json`：本轮筛选范围、旧文件数和数据量，不含其他工作树。

只保留Markdown与处理后JSON/CSV，不保留原始运行文件、二进制、IR和构建缓存。
