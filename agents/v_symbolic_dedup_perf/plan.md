# 符号执行性能审查与对照测试

用户已授权独立 subagent review 和使用 ../isla 的性能测试。

- 独立只读 review：源码、生成 IR 与 Isla 调用/采样机制。
- 同一 Sail 工具链生成 HEAD 5f1a0de0 与未提交重构的 RV64 VLEN128/ELEN64 IR。
- 使用同一已复制的 release isarch、相同 ISA 配置、qfaufbv、8 worker、60 秒外层/路径/SMT预算；不固定 vtype/vl/vstart 等运行态。
- MOVETYPEV、MASKTYPEI、VREV8_V、VIMCTYPE，各执行三轮交替 A/B；历史 rv64d.ir 额外同机复跑。
- 临时配置保留 strict，绑定各自 IR hash，MASKTYPEI region 按源码准确迁移。正式配置与原 output 不修改。
- 收集 wall/CPU/RSS、完成/成功路径、fork、错误；限额导致的采样身份改变需与纯执行开销区分。

产物目录：/tmp/sail-dedup-perf-00rgqu2_

## 2026-09-25 审核意见 P2 补全

用户已确认补全基准脚本。将原测试的 base/new/history/direct IR 以压缩快照纳入本目录，保留三份原始限制配置模板；让 `bench.py` 和 `helper-bench.py` 在运行前展开并验证 SHA-256，提供只准备输入的入口。核对展开结果与原始测试产物逐字节一致，再执行一次 MOVETYPEV 小样本验证脚本可实际运行。
