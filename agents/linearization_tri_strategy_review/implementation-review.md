# 三策略实施方案独立复审（2026-11-03）

范围：Isla HEAD 42000be47596ec088623881d03c0eadc5cf0ba27 加当前工作树；仅静态核查，无新增动态或性能 PASS。

结论：配置驱动与双门方向可接纳；证明网关和安全检查仍有阻断缺口。

- linearize::self_test 顺序调用两版本，仅比较返回值，采用 Optimistic assertion 初始化；不能证明任意副作用或任意全局状态等价。
- executor::all_unsat_collector 对 Exit/Suspended/非 Bool 只记日志，Dead 不标失败，初始结果 true；存在空真成功风险。Unknown/SAT/执行错误显式置 false。必须强化完整性和结果分类。
- 签名白名单不足，还须检查局部变量、表达式、phi、自由变量、传递调用及提前求值安全性。首版建议限定无全局状态、无递归、无 assume/assert、无异常退出、无未定义值的封闭确定 Bool/固定 BV 子集。
- 当前 IR 没有独立 WriteMem/Assert 变体；效果来自 Call/Extern/Primop、Copy 目标及引用访问。既有 is_pure 不证明传递纯净性。
- partial_linearize 保留 Jump；full 仅跳过成本门。安全检查和实际 pass 必须处理一致的 CFG 范围。
- opts.rs 当前先 -P 后 -L，可重复改写，未知函数仅打印日志。应统一解析、Name 去重、冲突报错，禁止 -L 使用旧 drop_assertions 路径。
- isarch_main 在通用加载后还有 solve-state 断言转换、execution limits 覆盖及 PMP 初态设置；扩大状态支持前须统一证明前提。
- 原始 Sail 名称恰好 zencode 一次；不能凭 z 前缀识别已编码名。精确 IR 名称使用独立字段，验证 Val/Fn 配对及单态化符号。

实施顺序：严格 self_test 及负向回归 → 配置校验与封闭子集安全门 → 统一调度 → 批量验证后安装。bounded 仅允许改写前按资格/成本拒绝；改写或证明故障不得回退。

必测：一臂 Exit、全 Dead、Suspended、Unknown、非 Bool、局部 Union 合流、传递状态写、递归、提前求值错误、不可达环、名称编码、CLI 冲突；正向嵌套菱形、多返回及 Bool/BV 边界。
