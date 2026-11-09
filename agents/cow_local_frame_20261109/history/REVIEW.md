> 2026-11-03 旧候选历史记录。仅归档 Markdown，文中的日志路径属于原工作树；不能代签 2026-11-09 候选测试。当前结果见 [议题状态](../status.md)。

# 任务分叉写时复制独立审查

审查模型：`gpt-6.1-sol high`。日期：2026-11-03。

结论：在仓库现用内存回调与区域实现范围内，未发现需要阻塞本次交付的正确性、线程安全或生命周期缺陷。冻结与解冻共享所列重型状态，正常写入通过 `Arc::make_mut` 分离。通用外部回调的内部可变状态存在兼容性边界，见下文；不能把本结论扩大为任意第三方回调均与旧版等价。测试最终结果由实施记录单独给出，本审查不代签测试 PASS。

## 范围与版本

- 短期基线：`bdd047bc67c357f3c6e9c4d34b5ec9daaf81ab57`。
- 逐行审查该基线到候选工作树的 `isla-lib/src/executor/frame.rs`、`isla-lib/src/executor.rs` 全部差异，包括补充的内存区域写隔离、调用栈、独占写和 itrace 共享分离测试。
- 追踪 `memory.rs`、`register.rs`、`primop/memory.rs`、`execution_limits.rs`、`path_timing.rs`、`tracetool/itrace.rs`、`src/isarch/memory_model.rs` 和 `isla-axiomatic/src/page_table.rs` 的相关实现。
- 审查结束时两份源码 SHA-256：`executor.rs` 为 `1acc52b0d3ac770ca40f0c91968803912b73a5e8ceebbf731bf0bf8557b94d5c`；`frame.rs` 为 `c5b517bb795d43eb9ec46ad31b0132e93d99f6a5ca8203cdaac41f8fd2d5335a`。
- 只读审查源码并运行 `git diff --check`，该检查无输出、退出码 0。未构建、未运行测试，避免竞争实施 agent 使用的构建缓存。唯一写入文件是本报告。

## 严重程度发现

未发现适用于现用实现的 P0、P1 或 P2 缺陷。以下为审查证据和非阻塞边界。

## 线程安全、生命周期与写入隔离

1. [frame.rs:144](../../isla-lib/src/executor/frame.rs#L144) 与 [frame.rs:200](../../isla-lib/src/executor/frame.rs#L200) 不改变 `'ir` 的引用关系；指令与类型仍由原调用方持有，容器通过 `Arc` 拥有，没有新增裸指针、`unsafe`、生命周期延长或自引用。调用栈仍为原有 `Arc<dyn Fn + Send + Sync>`，没有新增闭包捕获局部可变状态。
2. `BV` 原生要求 `Send + Sync + 'static`。`LocalState` 的绑定、值和寄存器不含本轮引入的内部可变共享对象；可变访问器在 [frame.rs:286](../../isla-lib/src/executor/frame.rs#L286)、[frame.rs:313](../../isla-lib/src/executor/frame.rs#L313)、[frame.rs:328](../../isla-lib/src/executor/frame.rs#L328)、[frame.rs:364](../../isla-lib/src/executor/frame.rs#L364) 先取得独占容器。新增编译期断言覆盖 `Frame<'static, B64>` 和 `LocalFrame<'static, B64>` 的 `Send + Sync`，没有手写不安全 trait 实现。
3. 核对了执行器中的赋值、延迟初始化、寄存器同步、reset、interrupt、函数假设、PC 次数、调用与返回、错误回溯、分支预算及 monomorphize 写入点：均经 `Arc::make_mut` 或既有可变访问器。`eval_exp` 和 `RegisterBindings::get` 可能初始化值或更新 relaxed 寄存器读状态，保留可变访问是必要的。不能将这些调用简单替换为共享读取。
4. [frame.rs:498](../../isla-lib/src/executor/frame.rs#L498) 的调用栈 push/pop 保持原来的变量交换顺序，栈容器写前分离。调用恢复闭包仍只恢复调用者 PC、指令、变量和闭包链；寄存器、内存等沿当前路径继续演化。[executor.rs:1903](../../isla-lib/src/executor.rs#L1903) 的 backtrace push 和返回 pop 均已分离。
5. 两个分叉点分别在 [executor.rs:1658](../../isla-lib/src/executor.rs#L1658) 与 [executor.rs:2104](../../isla-lib/src/executor.rs#L2104) 对子、父路径独立推进签名，先复制再变更的语义保持。没有把一条路径的预算写回兄弟路径。
6. `tracetool` 条件编译范围内，逐指令记录、分支条件、超时和限制摘要均先分离 itrace 容器；完成路径仍按原接口复制实际 `ItracePerPath` 值。其原有 backtrace 内容复制未误变为共享可变引用。

## 内存回调与通用扩展边界

现用实现正确性已追踪到具体读写链路：

- [primop/memory.rs:50](../../isla-lib/src/primop/memory.rs#L50) 的普通读、取指和独占读均走 `frame.memory().read`；[memory.rs:486](../../isla-lib/src/memory.rs#L486) 的 `Memory::read` 与 `read_symbolic` 都是 `&self`，读前没有 `Arc::make_mut`。
- [primop/memory.rs:77](../../isla-lib/src/primop/memory.rs#L77) 的普通写和独占写经 `memory_mut()`，先分离 `Memory`，其派生 `Clone` 会复制区域并调用回调的 `clone_box`，然后才运行 `symbolic_write(&mut self)`。所以父路径写入不能改变兄弟路径持有的旧 `memory_var`。
- 候选树内唯一 `MemoryCallbacks` 实现是 [memory_model.rs:40](../../src/isarch/memory_model.rs#L40) 的 `SeqMemory`。字段只有 `Sym` 与 `u32`；派生 `Clone` 无副作用；`symbolic_read` 仅修改传入的路径私有 solver；[memory_model.rs:183](../../src/isarch/memory_model.rs#L183) 的 `memory_var` 更新只出现在可变写回调中。因此将其 clone 延迟到首次写不改变现用数组内存语义。
- 仓库内唯一 `CustomRegion` 实现是 [page_table.rs:909](../../isla-axiomatic/src/page_table.rs#L909) 的 `ImmutablePageTables`。其页表已经通过 `Arc` 共享，读取只向传入 solver 添加内容，区域自身没有新增内部突变；其符号描述符闭包也在旧 Clone 中共享。没有找到受本轮 clone 时机变化影响的现用实现。

**非阻塞兼容性限制**：[frame.rs:152](../../isla-lib/src/executor/frame.rs#L152)、[frame.rs:212](../../isla-lib/src/executor/frame.rs#L212)、[frame.rs:440](../../isla-lib/src/executor/frame.rs#L440) 改变了 `clone_box` / `clone_dyn` 的调用时机。公开 trait 并未禁止 `&self` 回调使用 `Atomic` 或 `Mutex` 存储路径相关读状态，也未保证自定义 Clone 无可观测副作用。例如一个 `CustomRegion::read(&self)` 使用原子计数器逐次返回设备值，并在 `clone_dyn` 中复制计数值，旧版兄弟帧独立计数，新版只读兄弟帧会共享计数。`Send + Sync` 保证线程访问安全，不保证这种语义等价；写入口的 `make_mut` 也无法隔离这种读取。

因此，等价结论依赖“共享读取不改变路径私有回调状态，Clone 无影响执行结果的副作用”。用户要求保留 `memory(&self)` 并让 Memory 使用 Arc，本次不为任意外部回调添加深拷贝回退。该限制应在交付中明确；若未来支持上述有状态设备回调，需要另定接口或共享策略。

## 性能与最小性

- 只读 `vars()`、`regs()`、`lets()`、`memory()`、回溯和统计遍历通过 `Arc` 解引用访问，未新增锁或容器克隆。独占容器写入的测试检查了指针保持；共享容器首次取得可变访问时仍可能整容器复制。
- 表达式求值保留可变接口，因此即使本次具体表达式仅含常量，也可能在第一次求值时复制整个共享 `LocalState`。这是本方案粒度的限制，不能声称所有概念上的读取都零复制。重复 `Arc::make_mut` 还会增加独占性检查，但没有引入新的哈希表查询包装或锁。
- 九类执行状态容器的冻结与解冻均仅复制 Arc。**整个 freeze/unfreeze 并非严格 O(1)**：[frame.rs:147](../../isla-lib/src/executor/frame.rs#L147)、[frame.rs:207](../../isla-lib/src/executor/frame.rs#L207) 仍保留 `SmtCallStats::clone`，会复制 `sites: Vec<SmtCallSite>`；路径计时快照仍取原有 Mutex。这些成本继承自基线，没有在本轮扩展，也不支持“整个冻结过程完全无锁”的表述。
- 生产改动局限于容器类型、构造、冻结解冻和必要写入点；复用标准 `Arc` / `Arc::make_mut`，没有新增持久化容器、全局锁、包装层或不必要辅助抽象。未发现需要为行数最小化而另改控制流的地方。
- 未运行端到端性能基准，不能从本审查推导整体加速比例或峰值内存改善幅度。

## 测试充分性与局限

新增测试直接区分“冻结/恢复后立即共享”与“写后隔离”，并检查父、兄弟和快照保留原值；内存区域、调用栈 push、独占状态写入、tracetool 分支均有覆盖，测试目标合理，没有大量复制实现细节的专用框架。既有分支预算继承、monomorphize、多 worker 采样一致性、调用恢复与访存事件测试可覆盖必要执行语义；它们属于继承测试，不计为本轮新功能。

剩余边界：本轮新增测试没有直接将 `SeqMemory` 装入 `LocalFrame` 后完成“冻结、兄弟写、兄弟读”的集成链路；其正确性由上述字段与调用链核对支持，原有 `SeqMemory` 测试主要验证 `Memory::clone`。无动态线程分析、Miri、任意第三方回调验证及端到端性能测量。主 agent 已报告库全量测试出现 Z3 枚举排序重名错误并在核对基线，本报告不把该未定原因归因于 COW，也不将未完成排查写成通过。
