# ExecuteAs 完成边界修复（2026-11-02）

## 问题与最小修复

原入口在 `zexecute` 首次返回 `ExecuteAs(ITYPE(ADDI))` 时即输出 finished。C_ADDI4SPN 机器编码 `0x1fe0` 的输入 x2=7、立即数1020，旧JSON却给 x8=7；完整执行应为 x8=1027。

修改根 `isla/src/isarch/exec.rs`：在 collector 具体化前识别 ExecuteAs，将载荷交给现有 `LocalFrame::new_call`，沿用终态寄存器、lets、memory、路径签名、累计执行时间、分支限制与 SMT checkpoint；由同一 TaskState/task_id 的后续执行轮继续运行。只有最终非ExecuteAs返回才生成JSON；编码、助记符、初态仍取原请求指令。未重启初态、未增加新执行器抽象。

初始 LocalFrame 现在也接收原函数参数 `initial_memory`（旧 helper 调用未接线）。路径限时仍比较新 frame 继承的累计执行时间，不因续执行重置；每条 Clause 的外部预算仍由原运行入口负责。

## TDD 与验证状态

- [真实旧程序红例](red/checks.json) 已取得：官方新Z3下，0x1fe0仍返回ExecuteAs且x8=7，说明更换求解器不会修复此执行边界。
- 新增 Rust 测试 `collector_executes_execute_as_payload_without_resetting_state`：首段先改mstatus bit63，ExecuteAs载荷再改bit62，要求最终返回Retire_Success且两个修改都存在。可检出未续执行、从初态重启、过早具体化三类错误。
- [真实CLI回归脚本](regression.py) 对每条C_ADDI4SPN编码解码rd/立即数，检查最终x[rd]=x2+imm且无ExecuteAs返回。单次路径/SMT预算显式7200秒。
- 主agent已运行真实红绿例、最终make入口与runner独立CLI；所有见证均以生成的实际编码解码立即数验证后态，见[主状态](../status.md)。

运行方式（从根目录）：

```sh
cargo test --manifest-path isla/Cargo.toml --release --lib collector_executes_execute_as_payload_without_resetting_state -- --test-threads=1
/usr/bin/python3 agents/float_review_completion_20261102/executeas/regression.py --binary isla/target/release/isarch --ir isla/rv64d.ir --config agents/independent_topic_review_20261030/float/c-addi4spn/config.toml --output agents/float_review_completion_20261102/executeas/green
```

Cargo须沿用主agent已配置的官方Z3链接/RPATH参数，不在此重复编译共享target。未提交/推送，未修改memory分支。

## 生命周期 API 复审修订

首次 collector 队列保存 `LocalFrame<'ir>` 时，旧 `Collector<'ir>` 同时要求闭包捕获值活到IR寿命，`start_multi` 又将 collector 引用寿命绑定为同一 `'ir`；Mutex队列使IR寿命不可缩短，导致局部闭包/配置不能借用。不是SMT或业务执行错误，不能靠Arc解决。

保留兼容别名 `Collector<'ir,B,R>`，新增 `ScopedCollector<'ir,'collector,B,R>`；仅多线程runtime及零线程共用helper区分IR与调用作用域寿命。无unsafe、无泄漏、无延长引用寿命。编译回归固定静态IR、借用局部String并把frame放入Mutex队列：旧API在[红例](api-red.log)中E0597失败；新API实际运行1测试通过，见[绿例](api-green.log)。

同时发现完成帧只保留上次fork时的SMT统计，续执行会漏计尾段。先新增真实check_sat的无fork回归确认失败（[红例](stats-red.log)），然后在run返回前刷新frame的累计SMT统计；[绿例](stats-green.log)实际1/1通过。

`new_call`未复制function_assumptions/pc_counts/taken_interrupts。当前isarch入口只设置ExecutionLimits、不设置PC重访限制/interrupt，也不调用reset_registers装配function_assumptions，因此这些字段为空。本轮不修改全局new_call语义；未来若入口增加这些自定义执行环境，需要同步复审续执行状态。

make正式Release已在首次API修复后退出0（[构建](build-api.log)），主agent已运行真实CLI绿例。统计刷新与fixture字段接线后的最终make构建退出0，见[构建](build-final.log)。根与runner已同步构建，版本/链接及最终make烟测见[最终核验](../final-verification.json)。

## 已完成限定验证

- [collector库测试](collector-green.log)：11/11通过，包含ExecuteAs前段bit63/载荷bit62同时保留、最终Retire返回以及原有同模型/编码/后态断言。使用 `--lib --test-threads=1`，不是bin零匹配。
- [三表示模块测试](representation-green.log)：5/5通过。
- [API回归](api-green.log)和[SMT统计回归](stats-green.log)：各实际1个测试通过。
- 主agent负责真实CLI绿例及runner-float同步，详见本议题总状态；我未修改这些生产检出。
- 相关代码仅格式化 `src/isarch/exec.rs`、`isla-lib/src/executor.rs`，未全仓fmt。`implementation.patch` 是这两文件当前集成diff（包含主agent三表示接线），`api.patch` 仅含executor API/SMT统计及测试。

最终 `make -C isla build-isarch` 退出0，耗时68秒，见[最终Release构建](build-final.log)。共享target已释放，后续主agent负责runner同步与集成回归。上述限范围结论不等于全指令或全模型控制流验收。
