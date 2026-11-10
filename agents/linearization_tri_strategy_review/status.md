# 函数线性化三策略评审状态

2026-11-03：静态评审完成；Isla HEAD 为 42000be47596ec088623881d03c0eadc5cf0ba27，保留已有工作树修改。

配置方向可行，但安全资格与成本阈值须分开；full 只能跳过成本门。partial_linearize 保留部分跳转；linearize 会将断言条件改为 true。现有 is_pure 不能作为副作用证明。

当前 executor.rs:1132 越界表示没有 concrete true 且 symbolic 输入为空，不能仅凭 Union 返回确定根因。build_ite 的不同 Union 构造器合并未绑定条件与标签；SymbolicCtor/Ctor 交换也未反转条件，存在语义风险。必须先修底层合并再扩大类型支持。

bounded 改写前不接纳候选属于策略选择；内部不变量错误必须显式失败，不能吞错回退。需检查所有 phi 类型、传递副作用及投机执行安全性，并补条件见证覆盖。

仅静态源码核查；未复现用户崩溃，未新增动态或性能 PASS。实施准备见 [plan.md](plan.md)。


实施方案独立复审发现 self_test 完整性与全局状态证明边界；当前方案须先强化网关并限定封闭纯函数子集。见 [复审](implementation-review.md)。

## 2026-11-03 隔离工作树实现与对比实验（.worktree/isla-linearize-strategy@87bf52f）
- **实现内容**：
  - `executor.rs` 与 `linearize.rs`：新增 `EquivalenceResult` 与 `equivalence_collector`，要求至少 1 条正常路径且所有终态无异常/退出/全死，根除了空真成功漏洞。
  - `linearize_policy.rs`：实现封闭纯标量安全资格门（类型白名单、DAG 拓扑检测、无副作用/无断言/形参不可重赋值/无 Monomorphize）与成本门评估。
  - `config.rs`：解析 TOML `[linearize]` 节点并执行严格字段与阈值检查。
  - `opts.rs`：统一 TOML 与 `-P`/`-L` 调度通道，废弃带断言擦除的旧 `linearize.rs`。
- **独立审查结论（Codex GPT-6.1 Sol）**：
  - 核心架构认可，成功识别并修复了参数赋值崩溃与 Monomorphize 风险。
- **实测验证结果**：
  - `cargo test -p isla-lib`：**287/287 全部通过**。
  - 端到端流水线（`test_pipeline.py`）：**4/4 全部通过**。
  - A/B 对比实验验证：
    - `none`：保持原始 IR（1480 字节），原生分叉；
    - `full`（verify=on）：Z3 严格证明等价并压平成单条 ITE（1714 字节）；
    - `bounded`（<=1）：分支未超标，成功压平（1714 字节，与 full 完全一致）；
    - `bounded`（<=0）：分支超标，在改写前优雅决策保留原 IR（1480 字节，与 baseline 完全一致）；
    - 非纯函数（循环/内存写/断言/复合类型）：安全门 100% 拦截并报错退出（Fail-Fast）。
