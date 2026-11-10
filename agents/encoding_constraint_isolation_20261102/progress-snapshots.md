# 进展快照（历史）

以下记录仅反映各源码阶段当时状态；当前结论见[状态](status.md)。

# 当前状态

源码与新 IR 已提交，独立 Sol 源码、IR 和定向结果复核通过；旧 flags 完整 Clause 性能验收仍运行，尚不能宣布全部完成。

- Isla：`de00adb` 分离编码候选探索和完整约束验证；`8e5a3f7` 同步四配置五份 IR 与永久 CFG 回归。
- Sail-RISC-V：`6202e23` 恢复活动 lane 内 f16→i16 饱和 overflow 显式分支，其他未验宽度与 flags changed 不改。
- 四配置严格 SYMBOLIC 生成、ordinary strict、79 配置/132 源码区域/22 锚点核对通过；规范化 2054 函数只改变目标 helper；25 步 IR 回归通过。
- 新模型完整 `VFUNARY0`：37.16 秒 finished，46 JSON，错误/超时为零；使用原 sat 配置，未缩域。
- 56 项定向验证：156 JSON、3518 断言通过；Sol 另核 9272 个初态值、饱和数值与 flags。
- GCC/Clang 三种表示检查 78/78；正式 `make solve-FLEQ_S` 3.51 秒 finished，另 48 项双工具链检查通过。
- 旧 flags 显式 B 和旧 sat 显式 B 使用新程序、相同冻结输入及 seed17 继续运行，整 Clause/单次 SMT 均为 7200 秒。旧 sat 是旧 eager lane 行为的诊断输入；新模型验收使用上面的完整 VFUNARY0。

[方案](plan.md)、[实施](implementation/report.md)、[动态结果](validation/report.md)、[源码复核](review/encoding-source.md)、[模型复核](review/model-source.md)、[IR 复核](review/ir-review.md)。定向域和 vl≤2 不代表全部浮点控制流覆盖；最终性能结论待完整旧 flags 结束。未推送，根 float 同步处理中。

## 后续修正进行中

300秒隔离诊断已返回：完整候选验证1280次，其中1069次UNSAT（83.5%），验证累计89.69秒；辅助Jump合计1.37秒。初版去除所有原Assert使辅助域过宽。正在TDD补充保留仅依赖instruction字段的原断言子集，最终完整域与全部候选验证不变。Sol已审设计通过，源码、动态及最终性能仍待后续签收。初版三条完整Clause继续原预算，结果分版本保存。[诊断](implementation/diagnostic/report.md)、[设计复核](review/selective-retention-design.md)。

## `cf1aa14` 修订版验收进展

源码已独立 Sol 签收；官方 Z3 下 15 项 Rust 定向回归亦由 Sol 独立重跑通过。四配置 IR 未再变化。新饱和完整 Clause 22.34 秒、当前生产 IR 浮点算术完整 Clause 1127.51 秒均 finished、无错误/partial；56 项定向、126 项双工具链及真实 Make 入口通过。Sol 已核数值、flags、初态与编码。新饱和 46 条、生产算术 728 条、定向 156 条与初版同输入输出逐项一致，仅说明本批实际产物。

原显式 flags B 的修订版完整计时仍运行；初版该输入已在 2884.43 秒 finished，328 条见证经独立核对正确。旧 eager lane 饱和 B 仅为诊断输入，仍运行，不与正式新模型饱和混用。最终性能以各版本 `result.json` 为准。

一项未改动的枚举重放单测失败，单独记录于[边界](implementation/diagnostic/baseline-enum.md)及[官方库测试](implementation/diagnostic/official-targeted-tests.md)，不计入 15 项通过数。[修订版动态报告](validation/selective-report.md)、[独立动态复核](review/selective-dynamic-review.md)。
