# F1 内存初态与数组一致性修复

基线：Isla `bdd047bc67c357f3c6e9c4d34b5ec9daaf81ab57`。只修改 `isla-lib/src/memory.rs`、`src/isarch/memory_model.rs`（含同文件单测）；原有 `README.md`、`scripts/run.mk` 和其他 agent 修改未处理。

## 问题与 RED

原实现中 `Concrete` 具体地址读走区域快照，符号地址读走未初始化的 SMT 数组，写入仅更新数组。同一 `0x80000000` 零内存，AMOMAX 的符号地址成功见证可读出全一。完整 IR 的未重编译基线 RED 见 [checks.json](../red-integration/checks.json)：`amo-concrete-symbolic:all-concrete-reads-zero` 为 false，固定地址对照为 true。新增单测首次执行时被共享工作树其他 agent 尚未完成的 `exec.rs` 测试编译阻断，因此不把编译错误当作 F1 的单测 RED。

## 实施

- `SeqMemory` 保存初始数组与当前数组。将 `Concrete` 区域显式非零字节以每 64 个 `Store` 为一组定义到初始数组；零缺省字节在读取涉及该区域时按地址逐字节约束初始数组。大范围零 RAM/CLINT 无逐字节初始化；未配置区域仍为自由初值。
- 数组回调声明普通 RAM 的具体读也通过同一数组，因而具体/符号地址同址读取及写后读使用相同状态。跨 `Concrete` 与普通内存边界逐字节取各侧初态，普通 RAM 保留原有位向量地址回绕语义。
- `Custom` 与 `Constrained` 保留专属分派：可能触及它们的符号地址先向求解器查询；地址唯一时转入具体分派，否则明确返回 `BadRead`/`BadWrite`。具体访问逐字节检查专属区域边界，包括地址顶端回绕，避免通用数组代读或把跨界访问整体交给设备。没有专属区域时不新增该查询。
- 回调的既有 `constrains_symbolic_reads/writes`、判死区域约束和独占写语义保留。`Concrete` 初态按需约束只追加 SMT 断言，不额外触发每次 `check_sat`；判死区域仍按原机制即时检查。存在 `Custom`/`Constrained` 时的符号地址会额外触发重叠查询，唯一地址再触发唯一性查询。

## 验证

共同环境：`CARGO_BUILD_JOBS=4`，`RUSTFLAGS` 指向用户指定的官方 Z3 `~/.local/opt/z3-official-1fd1d3613/lib`，设置如下（`$HOME` 展开后与运行时绝对路径相同）：

```text
export CARGO_BUILD_JOBS=4
export RUSTFLAGS="-L native=$HOME/.local/opt/z3-official-1fd1d3613/lib -C link-arg=-Wl,-rpath,$HOME/.local/opt/z3-official-1fd1d3613/lib"
cargo check --lib
cargo test -p isla-lib memory -- --test-threads=1
cargo test --lib isarch::memory_model::tests -- --test-threads=1
rustfmt --edition 2021 isla-lib/src/memory.rs src/isarch/memory_model.rs
git diff --check -- isla-lib/src/memory.rs src/isarch/memory_model.rs
```

`cargo check --lib` 通过；`isla-lib` memory 相关 4 项通过；最终内存模型 38 项通过、0 失败（含快照、页表、设备与 `Constrained` 边界、普通 RAM 顶端回绕）。原未分块页表初态曾触发 stack overflow；改成每 64 个非零字节一个 `DefineConst` 后，页表定向测试和最终 38 项均通过。完整 IR 的 GREEN 由主 agent 用同一集成脚本复验，不在此提前标为通过。

## 剩余限制与复审点

符号地址若在当前约束下既可触及专属后端又可访问普通 RAM，现接口无法在一次回调中保留两种后端行为，明确返回错误，不静默使用数组。大规模稀疏初态仍会按非零字节数量产生 `Store`，页表单测已覆盖 8 KiB 预置页表；实际大页表性能需在完整 IR 运行中观察。初始化后再次调用 `Memory::write_byte` 不会同步已安装数组；当前 `MemoryBuilder` 在安装回调前完成预置。
