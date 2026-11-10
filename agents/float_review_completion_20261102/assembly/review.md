# ExecuteAs 修复独立代码审查（最终源码复核）

最终受审源码与SHA256见 review-snapshot.json；最初发现时的快照保存在 review-initial-snapshot.json。本 agent 没有修改生产文件或运行共享构建。

## P2 已关闭：续执行丢失前段 SMT 统计（历史发现与最终修复）

`executor.rs::run()` 进入 run_loop 前恢复 frame.path_smt_stats；run_loop 的 fork 点会 capture，但正常返回前并不更新 frame 内快照。新的 ExecuteAs collector 调用 `frame.new_call()`，该方法只复制旧快照；下一段 run_loop 会用旧快照覆盖线程统计。因此最后一次 fork 到 ExecuteAs 返回之间的 SMT 调用统计丢失。无 fork 时可能丢掉第一段全部统计。

实际路径预算来自独立 path_timing，已复制，不受此诊断问题影响。建议 run() 在结束阶段 capture 当前路径 SMT 统计，再把 frame 交给collector，并加总统计回归。这不应通过重新计时或重置预算解决。

## 本次修复代码成立的部分

- collector 在收到 ExecuteAs 时先入队并立即返回，位于 sampled/unfinished统计、最终编码、状态JSON及trace提交之前，不会把中间返回算作完成样例。
- new_call 携带 regs、lets、memory、execution_limit_state 和 path_timing。路径签名/已采样标记/累计fork预算均在execution_limit_state中；task重建使用相同 TaskId、TaskState。因此这些状态不会按新指令重置。
- run() 在返回时暂停 active slice，续段开始时再启动；path_timing 是共享累计句柄。每轮 start_multi 虽重建runtime，路径超时比较仍读取frame累计值。
- 每次使用 collector 的 solver checkpoint 重建续段任务，前段约束/事件保留，没有用初态重新求解payload。
- 最终 encoding_paths、model.get_val 与 requested-instruction 仍使用原 fun_args；后态取最终frame，返回值在同一最终Model具体化。因此不会误将32位payload编码替换原16位机器编码。
- 初始帧构造与旧 execute_ir_function_with_checkpoint_multi_thread一致（另显式应用传入initial_memory），续执行采用相同start_multi调度器。
- API修改把IR存活期与collector捕获存活期分开，仅改变Rust借用约束；Collector旧公开别名仍保留。MultiRuntime/ScopedCollector变更中未改变调度逻辑、原子操作顺序、run函数及solver处理；线程仍在thread::scope内全部结束，短collector不会逸出。

## 需要保留的边界说明

new_call 本身清空function_assumptions、pc_counts、taken_interrupts，这是已有API行为。当前isarch构造的TaskState只有execution_limits，没有PC限制/interrupt，也没有显式reset_registers建立的function_assumptions，未发现当前机器指令路径受影响的证据。若以后复用本续执行机制到支持这些配置的入口，应先定义其跨阶段继承，不能把本结论推广到全部executor调用方。

Sail step对压缩指令只展开一次ExecuteAs，而本实现循环展开直到最终返回。现有模型payload为普通非压缩指令，未发现递归ExecuteAs构造；针对该已知模型范围一致。异常payload构造panic属内部模型不变量检查。

真实三批端到端验证已完成，见 report.md 与 production-e2e/summary.json：13条JSON及78项双工具链检查符合预期，C_ADDI4SPN保留16位原编码并续执行到x8=0x403。该动态binary冻结于统计修复前，统计修复本身以最终源码检查和独立回归证据核对，不复用为统计修复后的CLI PASS。


## 最终复核（2026-11-02）

最终 `executor.rs::run()` 在 `pause_active()` 后立即调用 `frame.capture_path_smt_stats()`，再将frame交给collector。下一段new_call复制的就是已完成阶段的全部SMT统计，原P2关闭；该行不修改solver、寄存器、路径约束或执行预算。函数返回错误的分支也保存同一快照。

已独立阅读 `executeas/stats-red.log` 与 `stats-green.log`：同一 `completed_frame_retains_final_smt_statistics_for_continuation` 测试先因完成帧遗漏最后SMT统计而失败，修复后1/1通过，断言快照调用次数非零且等于当前线程累计值。没有将其说成多项测试。

最新exec.rs已取消临时fun_args_ref/symbolic_regs_ref别名，collector直接借用原变量；检查最终原指令编码/请求文本与最终frame后态的关系仍成立。ScopedCollector保留IR和捕获变量分离的生命周期，闭包对象不移出本作用域。无新增阻断问题。

该结论限定于当前isarch入口与固定模型；上述已有new_call功能边界保持，不宣称全部executor配置的通用续执行保证。
