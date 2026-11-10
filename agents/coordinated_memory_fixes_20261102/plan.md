# 内存协同正确性修复计划

日期：2026-11-02。用户授权修复[协同审阅](../coordinated_memory_review_20261102/report.md)中的正确性问题，并要求修改完成后由Sol独立审阅本轮改动。

## 目标与范围

以模型c70482a7、Islabdd047bc为起点，保留原有模型/MemoryCallbacks/Target结构，修复F1 concrete/数组状态分离、F2 GPR初态遗漏、F3全寄存器访存早退未清零vstart、F4返回值未按最终Model具体化、F5字段具体化错误进入gen。同步源模型与四配置生产IR、provenance及受影响预算位置。已有README/scripts/run.mk及其他工作树修改保留，不自动提交或推进父仓gitlink。

## 分工与边界

| 执行者 | 可写范围 | 交付 |
| --- | --- | --- |
| Sol memory_state_fix | Isla memory.rs、memory_model.rs及紧邻测试 | memory/内TDD与实现记录 |
| Sol witness_output_fix | Isla target.rs、exec.rs、solve_summary.rs及紧邻测试 | witness/内TDD与实现记录 |
| Sol vstart_model_fix | 模型vext_mem_insts.sail；隔离生成/回归脚本 | model/内源码、工具链与验证记录 |
| 主agent | 统一计划/状态、集成回归、IR/provenance安装、预算核对 | 总体证据及独审调度 |
| 独立Sol（实施后新派） | 只读本轮diff、源码、测试及新探针；可写独审报告 | independent-review/报告；不参与实现 |

所有agent共享工作树，禁止跨边界编辑；cargo使用同一官方Z3与一致RUSTFLAGS，通过cargo锁协调构建，不清理已有target/输出。最终构建与测试在所有实现完成后统一执行。独审指出的本轮问题修复后须再次独审。

## 步骤和验证

1. 保存起点版本/已有diff，先建立针对实际失败的RED回归，再实现GREEN。
2. 核对concrete/符号同址、写后读、跨边界、页表及Custom后端；GPR来源一致、sd x6前导后恢复；递归返回值与ModelEval错误传播。
3. 模型普通/SYMBOLIC严格检查，四配置从冻结的准确源码生成IR，不手改生产IR；准确记录dirty源码和补丁哈希，按实际来源写provenance。
4. 重跑完整IR最小反例、后态断言、相关Rust/Python回归和正式make solve冒烟；核对汇编/编码及预算位置。任何partial/超时如实记录，不以退出0替代完整完成。
5. 实施结束后派未参与实现的Sol独立检查diff及实际证据，处理其发现，再更新总结和全仓状态。

## 未决

- concrete零区域与稀疏页表如何高效、准确地接入数组且保留设备分派。
- 字段求值失败如何沿现有diagnostics/summary表达，避免混淆合法首写自由初值null。
- 生成脚本要求clean源码；冻结dirty来源应完整记录，不伪造已提交版本。
- 既有自由地址store的SymbolicLength是额外能力限制，本次首先修五项确证正确性问题，验证时继续披露其partial。
