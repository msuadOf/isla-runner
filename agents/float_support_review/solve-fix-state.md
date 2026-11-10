# R1：浮点 solve 状态快照实施记录

2026-09-26。范围仅为 `isla/src/isarch/target.rs`；方案与联调协议见 [运行器设计](solve-fix-runtime-design.md) §3。工作区原有未提交修改保留，未进入 `.worktrees`。

## 实施

- RV64/RV32 的主动符号化寄存器清单增加 `fcsr`。RV64 仍不主动符号化固定 `x0` 或入口 `PC`；旧 `rv64_target_trait` 曾错误要求二者在清单中，已按既有实际行为修正断言。
- 保留 `solve_pre_state` 的稀疏输出规则，但字段格式化失败现在向上传播，避免部分 map 被当成成功 witness。collector 应先在未开启 completion 的同一 model 上取旧字段，再取完整字段；Z3 对先前 completion 已物化的解释没有撤销接口。
- `solve_pre_state_complete` 对 `PreStateCtx` 中实际存在的所有寄存器启用 model completion 并输出具体值。`solve_post_state` 从同一清单及实际末帧 `RegisterBindings::get_last_if_initialized` 取末值；缺失或未初始化寄存器直接判内部不变量错误。两者复用调用者传入的同一个 `Model`，不创建第二个 solver/model。
- 完整输出只表示当前目标清单中 IR 实际存在的寄存器。非访存指令若依赖清单外初态，需由联调复核并扩充清单或在 replay manifest 记录固定初始化来源。

## TDD 与验证

1. 先加入 `fcsr` 清单、完整 pre/post 接口测试；在 `isla/` 以仓库外 `CARGO_TARGET_DIR` 运行 `cargo test --lib complete_pre_state_keeps_arbitrary_fcsr_and_mstatus --no-default-features`，因 `solve_pre_state_complete`/`solve_post_state` 缺失而编译失败（E0599），符合红测试预期。
2. 实现后在相同构建目录运行 `cargo test --lib isarch::target::tests:: --no-default-features`：29/29 PASS。最终 `target.rs` SHA-256 为 `de2658391cf874860b7f7ed522112ddd0c18e949f8af9f5d688657d5080cd4d8`。测试覆盖未约束 `fcsr/mstatus` 的完整输出、两组 `fcsr` FRM/flags 位型 SAT、正式 IR 所用单字段 `Fcsr`/`Mstatus` struct 格式、`Ty::Struct` 初始化与基于符号 pre-state 的 flags OR 写回、同一 model 的前后状态一致/写后变化、旧稀疏兼容、缺少 post 寄存器 panic、不可格式化状态报错、既有向量上下文约束。
3. 仅对 `src/isarch/target.rs` 执行 `rustfmt --edition 2021`，避免共享工作树中其他 agent 的 Rust 文件被全局格式化。

这些是 R1 单元测试结论；尚未在本 lane 执行真实小 IR 的 executor 写回 fixture。完整 solve JSON 与 77 项官方批次须待 R2/R3 接入及整体联调后另行验证。R1 接口签名与字段名按 [运行器设计](solve-fix-runtime-design.md) §3/§4 提供给 collector。

## 追加：RV64 架构合法初态域

独立架构复核指出，正式 IR 的 `cur_privilege` 虽有五个枚举成员，当前 hart 不支持 H 时 VirtualSupervisor/VirtualUser 不可由 reset/合法 CSR 流程到达；`mstatus.SXL/UXL` 是由 `xlen` 与 S/U 静态能力确定的只读字段。此项只修正模型架构可达域，不固定 FS/VS、FRM、flags 或其他运行态位。

- `constrain_pre_state` 在 RV64 的 `cur_privilege` 与 `mstatus` 均存在时，从同一 IR 的 `zhartSupports(Ext_S/U/H)` 独立执行探测。输入仅为具体 enum、同一 lets、空寄存器；要求每项唯一 `Finished(Bool)`、无寄存器/内存/抽象事件、无 fork/采样且最终 SAT。异常或非唯一结果直接报内部错误，不猜配置值。仅测试 fixture 两个状态都不存在时跳过；只存在一个状态为内部错误。
- `xlen` 必须为 64。允许的特权态为 Machine，以及能力启用时的 Supervisor/User；H 与相应 S/U 同时启用时才允许虚拟态。`mstatus.SXL[35:34]` 与 `UXL[33:32]` 分别约束为能力启用时的 `2`、否则 `0`。其它位保持符号性。
- `Target::domain_manifest()` 返回可序列化 map，含 status、xlen、S/U/H 静态能力、允许的特权态、两个只读字段及 `zhartSupports`/`sys_regs.sail` 规则来源。IR 版本与配置哈希由运行批次 manifest 另行绑定。

此追加先写三组真实小 IR `zhartSupports` fixture 测试：初始缺 `domain_manifest` 红编译 E0599；实现后 `cargo test --lib isarch::target::tests:: --no-default-features` 得到 32/32 PASS。经架构复核再加入读取空寄存器的负向探测测试，确认 `zhartSupports` 执行失败即 panic、不能猜能力；最终 **33/33 PASS**，`target.rs` SHA-256 为 `ad0a48165a42696c47e73b8287636efb7747551e124c35ef9d4eaf1018723100`。覆盖 S/U/M 三态 SAT、H 关闭时两虚拟态 UNSAT、FS/VS Off 与其他位型 SAT、错误 SXL/UXL UNSAT，以及 S/U 关闭时仅 Machine 与两个字段为零。原阶段 29/29 与首次追加 32/32 结果保留作历史；77 项批次仍待复验。

R2 随后用当前正式 IR 重跑 `zFLI_S`；[结果 JSON](tools/solve_runtime_tests/output/rv64_zFLI_S.json) 的 `summary` 为 `complete=true`、97 个终态（96 Retire、1 encoder non-encodable）、无错误，`state-domain` 实测 S/U=true、H=false、允许 Machine/Supervisor/User、SXL/UXL=2。此前两条 Zicbop Type 终态在该次复验中消失。此为单 clause 联调证据，不能代替 77 项完成或全部源码分支覆盖。

R2 的非 77 项 `zMRET` 诊断又发现 `core/types.sail:78` 的 `Invalid privilege level or virtual mode` Poison。源码复核：`privLevel_bits` 无 MPP=`10` 映射，`legalize_mstatus` 不保留该编码。按架构审定，仅添加 `mstatus.MPP[12:11] != 10`；`00/01/11` 与 FS/VS/MPV 等位保持符号域。测试先在旧约束下证明 `10` 为 SAT（红），新增 SMT 排除后 `cargo test --lib isarch::target::tests:: --no-default-features` 为 **34/34 PASS**，其中三个合法 MPP 值 SAT、`10` UNSAT，且 FS 的 Dirty 仍 SAT。最终 `target.rs` SHA-256 为 `3b7ebaf2180237e5dc6a89a7a12ace9129388f308b759fb29923674a11c4115d`；manifest 新增 `mstatus-mpp=0,1,3` 与 `reserved-mpp=2-excluded`。R2 随后复跑的 [MRET 结果 JSON](tools/solve_runtime_tests/output/rv64_zMRET.json) 为 `complete=true`、4 终态（3 Retire、1 Illegal）、无 Poison；这是诊断 clause 的局部结论。

架构独立复核要求再证明探测返回符号 Bool 时不能用 model completion 猜能力。追加 `Exp::Undefined(Ty::Bool)` 的小 IR 负例，实测 panic 为 `zhartSupports(zExt_S) 非具体 Bool 正常结束`；当前 target 专项 **35/35 PASS**，`target.rs` SHA-256 为 `d9779a183f228da58f536e89491178293542f2cf55efd6574d68d9da4f0b0804`。先前 34/34 及 MRET 局部复验仍保留为对应版本历史。
