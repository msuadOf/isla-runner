# isarch 快速失败修复：计划（2026-11-10）

## 目标

path merge、无 execution limit 下，有 103 个 clause 几秒到一分钟内就报错或留下未完成路径（名单见 [clause 分组](../loop_region_merge_20261110/clause-status-20261110.json)）。用户要求逐类修好（2026-11-10）。

| 类 | 数量 | 用户要求 |
| --- | ---: | --- |
| 译码回环返回 Poison | 39 | 重视。把 Z3 升级到最新提交，编译安装到用户前缀；isla 启动时检测 Z3 版本，低于该提交的版本号就报错 |
| 浮点函数不存在（如 `riscv_f64Add`） | 31 | 查明原因并修复 |
| 当前路径不存在合法机器编码 | 10 | 情况特殊，需要关注后修复 |
| 压缩访存等留有未完成路径 | 22 | 与上一类类似，情况特殊，需要关注 |
| LOAD_FP panic（`primop.rs:163`） | 1 | 查明并修复 |

## 做法

1. **Z3**：Claude 在 `/data1/baiyifan/build/z3-latest` 克隆官方最新提交，Release 编译，安装到 `~/.local/opt/z3-official-<短提交号>`（沿用现有 `z3-official-1fd1d3613` 的约定）。随后改 isla：Make 默认 `Z3_PREFIX` 指向新前缀；运行时读取 Z3 版本，低于最低版本即 panic，最低版本取该提交的版本号。
2. **其余四类**：Codex 在独立工作树 `.worktree/isla-quickfail-20261110`（分支 `fix/isarch-quick-failures`，基于 daf61c04）里**先诊断不改代码**，报告写在工作树的 `diag/report.md`。Claude 审完后定修法，再派 Codex 实现。
3. 修法须通用：不改 Sail 已实现的标准行为，不屏蔽差异，不加 execution limit 或 workaround。

## 验证

每类修完后重跑该类全部 clause（path merge、无 limit、`-T 32`），以“跑通、无错误、无未完成路径”为准；RV64 下本来没有合法编码的 clause，以“正确报告为不适用”为准。
