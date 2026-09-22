# Ara 外层 harness

`pipeline.py` 是主仓库管理的 Isla JSON → Ara/Spike 测试工具，包含 `prepare`、`build`、`run`、`diff`、`golden` 子命令。`ara/` 内层是独立上游 checkout，不随本目录提交；`work/`、`work-*/`、trace 和缓存为本地运行输出。

在工作区根目录运行 `python3 -B ara/pipeline.py --help`，各子命令可继续加 `--help` 查看参数。依赖 Python 3.10+、RISC-V 交叉工具链，以及按实验配置准备的 Ara emulator / Spike；golden 提取需要适配交互协议的 MOD Spike。初始化上游和构建仿真器不是本次整理的一部分。

## 使用边界

- 默认输入为 `isla/output/`，默认输出为 `ara/work/`；默认 VLEN=128、emulator 位于内层 `hardware/build-v128/`。这是历史实验配置，不能当作官方支持的 Ara 配置；已记录的合法 `2_lanes` 复验使用 VLEN=2048。
- 使用其他 VLEN 时，需显式一致地设置 prepare/build/golden 的 `--vlen-bits`、run 的 `--emulator`，以及 Spike 的 ISA 设置；不能只切换 emulator。
- `build --mode check` 需提供 `--golden-dir`；已有输出目录可能被 build/run 覆写，新实验应指定独立目录，不直接操作档案副本。
- `run` 按后端分类结果；Ara 达到周期上限可能返回 0，但缺少 `Core Test` 标记时不会记为成功。进程退出码不能单独证明测试通过。
- 本次源码原样纳入版本控制，只做 CLI/静态和纯函数冒烟检查，不声称真实 RTL 或全部功能回归通过。

实验材料见 [根目录 Ara 档案](../archives/ara/2026-09-23-poc-batch/README.md)，分析记录见 [agents/ara_poc_batch](../agents/ara_poc_batch/status.md)。历史档案中的 `snapshot/poc/pipeline.py` 是冻结副本，不代替本目录的维护入口。
