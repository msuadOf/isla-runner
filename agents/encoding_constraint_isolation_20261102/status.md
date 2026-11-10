# 编码约束分离与活动 lane 饱和分支

正式源码、本轮限定验收与独立 GPT-6.1 Sol 复核已完成；float 父仓同步组件与证据（本地未推送）。旧 eager lane 饱和输入仅作诊断，在 7200.20 秒外限退出 124，不替代正式模型验收。

## 版本与改动

- Isla `de00adb` 分离编码候选探索与完整执行约束验证，`8e5a3f7` 同步四配置五份 IR，`cf1aa14` 保留仅依赖指令字段的原断言，减少无效候选。最终仍恢复全部原约束；普通编码优先、压缩拒绝域、全部候选和异常处理不变。
- Sail-RISC-V `6202e23` 恢复活动 lane 内 f16→i16 的 overflow 显式分支；公式、饱和值与 flags 不变。其余未验宽度及生产 flags changed 仍保留原实现。
- 根 float 同步 `cf1aa14` / `6202e23`；源码分支分别为 `feat/float-support` 和 `feat/sail-riscv-general-float-by-model-20261022`。本轮不推送。

## 实际验收

修订版程序 SHA256 `abce451a…853a1a`，官方 Z3 `1fd1d3613`/库 `899cbc70…9970`，新 V128 IR `a877e245…f97e`。完整 Clause 与单次 SMT 均为 7200 秒、T1、qffp、seed17。完整命令、配置及各自哈希见[修订版报告](validation/selective-report.md)。

| 完整 Clause | 墙钟秒 | 结果 |
| --- | ---: | --- |
| 原显式 flags B，原 IR/配置 | 2626.07 | finished，328 条 |
| 当前正式 IR 浮点算术，原 flags 配置 | 1127.51 | finished，728 条 |
| 新模型 VFUNARY0，原 sat 配置 | 22.33 | finished，46 条 |

三项错误、采样和所有 partial 计数均零。56 项定向验证、156 条见证、3518 条断言，GCC/Clang 三表示 126 项、真实 Make 入口 3.19 秒与官方库 Rust 定向 15 项均通过；定向固定域与 vl≤2 不代表全部浮点控制流覆盖。初版完成值分别为 2884.43 / 1615.96 / 37.16 秒；机器有其他并行负载，逐次时间不作为严格加速比。

四配置严格 SYMBOLIC 生成、ordinary strict、79 配置/132 源码区域/22 锚点核对及 25 步 IR 回归通过。规范化 2054 函数仅目标转换 helper 改变；永久 CFG 回归检查 NV 只从 overflow 真臂可达。

[最终独审](review/final-report.md)、[源码复核](review/selective-source.md)、[模型复核](review/model-source.md)、[IR 复核](review/ir-review.md)、[动态复核](review/selective-dynamic-review.md)。一项未改动的枚举重放单测仍失败，见[基线边界](implementation/diagnostic/baseline-enum.md)及[官方库测试](implementation/diagnostic/official-targeted-tests.md)，未计入 15 项通过数。

[方案](plan.md)、[实施](implementation/selective-retention.md)、[初版报告](validation/report.md)、[历史快照](progress-snapshots.md)、[证据边界](ARCHIVE.md)。

旧 eager lane 饱和 B 的初版诊断最终 7200.20 秒外限退出 124、无完整 JSON，未计为 PASS；其原始命令和终态见[诊断结果](validation/runs/old_sat/result.json)。正式新模型 VFUNARY0 为上表 22.33 秒 finished，二者输入模型不同，不能据此单独归因编码优化速度。
