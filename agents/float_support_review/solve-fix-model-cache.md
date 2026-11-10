# Model 局部具体值缓存

## 范围与版本

本候选只修改 `isla/isla-lib/src/smt.rs` 中的 `Model`：每个 `Model` 自有 `HashMap<Sym, ModelVal>`，`get_var` 命中时返回 typed clone；首次求值仅在成功得到 `ModelVal::Exp(Bits | Bits64 | Bool | Enum)` 时插入。`Arbitrary`、未绑定变量、其它 sort 错误均不插入。`set_complete_model` 的布尔值发生切换时清空缓存。`get_exp`、底层 Z3 求值、watchdog 与超时机制保持原有路径。

开始前保存的 `smt.rs` SHA256 为 `968101d2aabab1ec160499c57b0ddf01e784982abbe770c3a89c68c1887fdea4`；该源码已经包含浮点原语所用的 `scalar_sort` 既有未提交改动，本包保留它。TDD 测试写入后、缓存实施前的源码 SHA256 为 `9cd07a4f0c40a4befecf84f3ec28517e1006646a1f70514116031d6a7847f6bc`。格式化后的候选 `smt.rs` SHA256 为 `3ce7310d87a71cdd29381966f495450bfb8baab35f1a52e6638bebbaaa2d122f`。

## 验证

证据目录为 `isla/target/float-solve-evidence/model-cache-20260926/`，含开始前的源码副本、红绿日志和 `manifest.json`。先写的三项测试在无缓存实现上全部失败（`tdd-red.log`，退出 101）；候选上 debug、release 和 `smt-thread-interrupt` 特性构建均为 **3/3 PASS**，`FmtVal` 的 2 项测试也通过。`cargo fmt -p isla-lib -- --check` 与 `git diff --check -- isla-lib/src/smt.rs` 均退出 0。

三项定向测试覆盖：B64、129 位 Bits（包括第 128 位）、Bool、Enum 的实际值及同一 `Model` 重复读取不再产生 ModelEval；`MixedBits` 消费缓存的宽段；`get_exp` 仍触发原有求值；complete false→true→false 每次切换重新求值；新 `Model` 不继承旧缓存；Arbitrary 重读仍求值，在 model completion 后可成为具体值；未绑定符号和 unsupported Array sort 的错误均不缓存。后两类错误是动态测试；**Timeout 未做动态触发测试**，只由 `get_ast(...)?` 位于插入语句之前的控制流保证不会缓存。该结论不等于动态 Timeout PASS。

全量 `cargo test -p isla-lib --lib` 在现有 `get_multi_member_enum_const_after_checkpoint_replay` 等 enum checkpoint 用例处触发 Z3 `enumeration sort name is already declared` 并使进程退出；该测试单独执行亦失败。串行运行并仅跳过三项现有 enum checkpoint 测试后，其余 **260/260 PASS**，记录在 `all-debug-skip-enum-replay.log`。这一过滤结果不构成未过滤全库 PASS，也不将该 Z3 错误归因于本缓存改动。

架构独审对源码 SHA `3ce7310d…` 放行局部补丁，并独立重跑 debug/release/thread 三种定向测试各 3/3。额外独立探针验证：两个 `Model` 共享底层模型时，第二实例补全解释后第一实例原 Arbitrary 可变为具体值；已缓存的 BV64、BV129、Enum 保持原值；`get_finite_domain_var` 与 `get_exp` 仍逐次调用 FFI；返回宽位 Vec 的 clone 经调用方修改不污染缓存。均通过，外部临时证据标识为 `model-cache-independent-review-qubcd7gr`。审查同意 Timeout 只作插入前 `?` 的结构证明，不写动态 PASS。

## 性能诊断与验收边界

性能专题在独立诊断 stage 上用环境开关与每次 cache hit 的旧 `get_var` 复算做同一 `Model` typed 相等检查；VFMVFS 的 255 个完整终态全部退出 0。该 stage 的单轮 A/B 记录：`execute_all` 17.934→13.771 秒，ModelEval 157648→73100 次，`complete_pre` 4.154→0.025 秒、`complete_post` 4.083→0.241 秒。跨进程有不同的合法 witness 选值，不能逐字比较两次 JSON。该诊断数据支持最小候选的性能方向，但与本生产源码哈希不同，最终官方 77 项及新冻结运行时仍须独立复验。
