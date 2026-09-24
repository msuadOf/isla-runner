# 2026-09-23 验证完成

独立 subagent review、三轮交替 A/B、历史 IR 同机复跑和 helper 隔离测试均已完成，共34个有效测量。详见 report.md 与 review.md。

MOVETYPEV 中位耗时 5.015→5.115s；MASKTYPEI 60秒窗口完成路径217→216；VREV8_V 133→134；VIMCTYPE 57.146→57.348s、路径均121。helper隔离对照5.113→5.114s、路径均69。未发现新增执行错误。测试仅覆盖当前生产配置下四类指令，不是全量V扩展性能验收。

正式源码、Isla配置、历史output均未修改。测试快照与当前三文件diff哈希一致。正式workaround绑定旧IR hash和源码坐标，部署新IR前需更新。

原始产物：/tmp/sail-dedup-perf-00rgqu2_/。

## 2026-09-25 审核意见 P2 补全

四份原测试 IR 已压缩保存到 `snapshots/`，原始 SHA-256 固定在 `prepare.py`。`fixtures/` 保存三份旧限制配置，准备脚本按测试版本改写哈希和 MASKTYPEI 行号；`bench.py --prepare-only` 和 `helper-bench.py --prepare-only` 均通过。展开的四份 IR 及九份历史配置与 `/tmp/sail-dedup-perf-00rgqu2_/` 原始产物逐字节一致。运行所需的 release `isarch` 哈希也先行校验，避免用不同版本误称复现。

`python agents/v_symbolic_dedup_perf/bench.py MOVETYPEV` 已实际完成七次运行：base/new 各三轮、history 一轮，全部退出 0，每轮均 69 条完成路径、22 条成功路径、零错误。新结果位于被忽略的 `runs/` 和 `results.jsonl`，原始报告统计未改写。
