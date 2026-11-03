# 编码隔离：独立源码签收

结论：受审两份 Rust 源码无阻断，可正式构建和进行真实 Clause 验证。此处仅签收源码及定向回归，不宣称完整 Clause 性能或见证覆盖完成。文件与测试程序的精确 SHA256 见 [source-manifest.json](source-manifest.json)。

## 语义与结构

- `Checkpoint::without_assertions` 按原序保留除 `Assert` 外全部事件，含 `DefineConst`、声明函数、枚举及非 SMT 事件。原 `next_var` 保持；因此候选仍沿用执行路径上的符号和计算定义。
- `with_suffix_from` 以 Arc 身份确认候选的辅助基点祖先；仅新增节点以原序接到完整执行 checkpoint。每段的 checkpoint 计数重建，最终采用候选的 `next_var`，防止符号重号；错误祖先或编号回退直接失败。
- 普通辅助编码探索扩大域，但每个成功、正常拒绝和异常终态先使用“完整原执行事件＋候选增量”检查。只有 UNSAT 被过滤；UNKNOWN 和 SMT error 被明确返回。原完整域可达的异常保留原错误分类，扩大域中不可达的异常不污染结果。
- 普通拒绝保存辅助候选 checkpoint，并沿用同一辅助基点接续压缩；因此普通拒绝条件不会在第二轮被删除。普通成功域保持优先，全部可达编码终态分别返回，没有提前取单个求解模型。
- 初始配置断言与执行路径断言在辅助阶段都暂时移去，但最终检查和返回 checkpoint 完整恢复二者。随后 collector 仍以同一个最终求解模型具体化指令、前态、后态、返回值及编码。
- `length_bits` 与 `segments_length` 仅读长度，不添加符号或断言；在它们之前获取 candidate 不遗漏求解状态。

本轮审查提出并已落实两个顺序修正：采样完整性检查在 UNSAT 过滤之前，防止已选不可达采样臂掩盖另一可达臂；`Run::Dead` 已在辅助域不满足，完整域是子集，可直接忽略而不增加昂贵完整检查。没有改任务树、实际执行路径、数值算法或最终模型具体化顺序。

## 独立重跑

审查直接运行实施交付的测试二进制，避免并发 Cargo 构建；每次外限60秒：

|回归|结果|证据|
|---|---|---|
|SMT checkpoint 隔离/多段合并/枚举/事件/原断言恢复|1/1通过|[smt-tests.log](smt-tests.log)|
|全部候选、完整域过滤、普通拒绝压缩、不可达辅助断言失败|1/1通过（包含三种场景）|[encoding-tests.log](encoding-tests.log)|
|实际 collector 既有回归，含多编码、压缩域、前后态、FS/VS、可达异常及 ExecuteAs|11/11通过|[collector-tests.log](collector-tests.log)|

`git -C isla diff --check` 无输出且退出0。测试和源码审查未发现约束漏回、单模型取代候选枚举或 normal/compressed 域变化。

剩余签收：四配置新 IR 来源和 CFG、新模型活动 gate 与 overflow 分支、正式 Release 的旧 flags/sat 与新饱和 Clause 完整运行、实际 JSON 及双工具链编码。

另有独立编写的 [checkpoint_probe.rs](checkpoint_probe.rs)，经当前已编译库执行通过：空 checkpoint、函数声明和定义、双原段与双辅助段、两个枚举、完整事件精确顺序、replay 后 fresh 编号、原模型值回读、错误祖先拒绝。结果见 [checkpoint_probe.json](checkpoint_probe.json) 和 [日志](checkpoint_probe.log)。探针初稿错误地复用已声明枚举的同一 Context，触发既有重复枚举名称限制；最终使用与生产相同的独立 Context，不将初稿当作被审代码回归。
