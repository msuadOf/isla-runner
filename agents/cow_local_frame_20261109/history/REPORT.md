> 2026-11-03 旧候选历史记录。仅归档 Markdown，文中的日志路径属于原工作树；不能代签 2026-11-09 候选测试。当前结果见 [议题状态](../status.md)。

# 任务分叉 COW 交付报告

2026-11-03。工作树 `isla-cow-fork`，基线 `bdd047bc67c357f3c6e9c4d34b5ec9daaf81ab57`，初始无未提交改动。本次修改保留在工作树，未提交、未推送、未移动父仓 gitlink。

## 实现结果

`LocalFrame` 与 `Frame` 共享九类 `Arc` 状态容器：局部状态、内存、调用栈变量、回溯、函数假设、PC计数、已处理interrupt、执行限制状态，以及可选trace路径。冻结、解冻对这些容器只增加引用计数；真正取得可变访问权时由 `Arc::make_mut` 分离。公共方法签名和执行器控制流保持。

生产修改限于 `isla-lib/src/executor/frame.rs` 与 `isla-lib/src/executor.rs`。新增两项单元测试验证父帧、快照和兄弟帧指针共享、局部变量与内存写入隔离、栈压入隔离、独占写指针保持及 `Send + Sync`；原trace测试增加共享和分离断言。先写测试产生编译红例，再实施，见[实施记录](IMPLEMENTATION.md)及[红例](red-test.log)。

## 验证结论

| 验证 | 结果 | 证据 |
| --- | --- | --- |
| 用户指定 `cargo test -p isla --lib` | **149/149 PASS**；该基线实际只有149项，不能宣称163项 | [运行](isla-root-lib.log)、[基线清单](baseline-isla-list.log) |
| 执行器库默认测试 | **275/275 PASS，过滤3项** | [日志](isla-lib-default-skip-replay.log) |
| 执行器库tracetool测试 | **332/332 PASS，过滤3项** | [日志](isla-lib-tracetool-skip-replay.log) |
| 不过滤的库全量 | **FAIL**：Z3枚举排序重名导致进程退出 | [默认](isla-lib-default.log)、[tracetool](tracetool-test.log) |
| 原版基线定向复现 | 同一 `get_multi_member_enum_const_after_checkpoint_replay`、同一Z3环境，出现相同错误 | [基线日志](baseline-enum-replay.log) |
| `cargo fmt --all`、`git diff --check` | PASS | 实施记录与最终检查 |
| `make solve-MRET` | **PASS**，退出0，生成4条用例 | [构建与命令日志](make-solve-MRET.log)、[运行日志](MRET-runtime.log) |

三个过滤项均为名称含 `_after_checkpoint_replay` 的SMT测试，完整名称与命令见[实施记录](IMPLEMENTATION.md)。基线复现证明已观察到的重放失败在COW修改前存在；没有为通过测试而修改求解器。本轮不宣称未过滤的库全量通过。

测试复用用户指定的共享target、官方Z3链接目录与RPATH。可复现的环境变量与cargo命令见实施记录。功能smoke命令为：

```sh
make solve-MRET THREADS=2 OUTER_TIMEOUT=60s SOLVE_TIMEOUT=55s
```

同样使用上述cargo环境。工作树新增被忽略的 `target` 符号链接，指向该共享缓存，适配Make中固定的 `./target/release/isarch` 路径。未删除已有输出；本树原无output目录，运行副本保存在 `output/`，交付日志另存本目录。

受测输入：

- `rv64d.ir` SHA-256：`c65b26c8518042c67bfcb48c9feaf2a13a6eb7d741bc01ae8688d78c4370e5d9`。
- `configs/riscv64_difftest.toml` SHA-256：`9a315cbcc83837a4a245a03a5f8d4c9c88d69622ffe1abb47777cb761b909fc2`。
- 两份受测Rust文件哈希与独审报告一致，详见独审的版本段。

## 独立审查

实现完成后，由独立 **GPT-6.1 Sol high** 逐行审查全部Rust增量并追踪相关实现。未发现现用实现中的P0/P1/P2阻塞缺陷。审查覆盖线程安全、生命周期、写入隔离、函数调用栈、内存回调、特性编译分支和性能边界。完整报告：[REVIEW.md](REVIEW.md)。审查agent没有修改生产代码，也没有代签测试结果。

## 适用边界

- 这是容器级COW，首次可变访问仍可能复制整个对应容器。表达式求值含延迟初始化，即使某次求值只读，也可能触发局部状态分离。
- 九类容器冻结、解冻为O(1)引用操作；整个函数仍有原有SMT统计向量复制和计时Mutex，不能称为整函数严格O(1)或完全无锁。只读访问未新增锁。
- 当前 `SeqMemory` 和 `ImmutablePageTables` 的读取不改变自身路径状态。外部自定义回调若在 `&self` 读取中通过Atomic/Mutex改变路径私有状态，或Clone有执行副作用，不保证旧版语义；标准COW不能自动识别这种内部突变，详见独审。
- 未测端到端性能、峰值堆分配或大规模路径负载，不承诺具体加速比例。MRET仅为限定功能smoke，不代表全部Clause验收。
