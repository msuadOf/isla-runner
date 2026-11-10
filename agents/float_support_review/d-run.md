# D 隔离候选阶段性运行记录（2026-09-26）

## 边界与输入

- 外部目录：调用者设置的 `D_ROOT`（仓库外）。所有候选 worktree、构建、IR、测试程序及日志均在这里；主 `isla/`、`sail-riscv/` 工作树未写入，正式 `isla/rv64d.ir`、配置和 `run.mk` 未改。
- `snapshot/manifest.json` 锁定 Isla HEAD `f4f8e4584a70588c66c9e7a6286cc20211618f18`、Sail-RISC-V HEAD `f8ce8490981eac6396a31013180a2e718615757d`，两仓 tracked binary diff 与白名单 untracked 文件的 SHA-256。候选 worktree 分别为 `isla-candidate/`、`sail-riscv-candidate/`，均 detached，并逐文件核对到快照哈希。完成时再次核对主工作树快照文件哈希，无漂移。
- Isla A 补丁 SHA-256 `f9e8aae3c9ff9c3182c91aaafcfbabe7b3741c6be7f5df4d7f4c489bf9c83cd8`；Sail 补丁 `c290562890f14d7bdb0e332d09a28056f6b697da9b9cf0d8159ce91a2008be42`。候选 executor 删除旧分发的独立补丁为 `d_executor_delete.patch`，SHA-256 `7d00b19e3b63891c95ae7be7833b5150c87aff193128c0f6b42f514fa497e28a`，只删除 `executor.rs` 34 行。
- 工具：Sail 0.20.1 (`446fb477`)、Cargo 1.93.1、Z3 4.16.0。候选插件 SHA-256 `c4eccb06af9f85820c28bd67556ae0f191361c93cbe1afb334900f9e1f0e22f6`。独立 SoftFloat oracle SHA-256 `0bb63bc72889502ef6a36cb739589745987a0788eb73d57e0570815a3c228bc6`。

## 关键命令与结论

1. 在父仓根运行 `python3 agents/float_support_review/tools/snapshot_d.py --output ${D_ROOT}/snapshot`，退出 0。按 manifest HEAD 对两个子仓分别执行 `git worktree add --detach <candidate> <HEAD>`、`git apply --check`、`git apply` 各自 `tracked.patch`，复制 `snapshot/sail-riscv/untracked/` 的白名单文件；应用后 2 个 Isla、49 个 Sail 受改/新增文件哈希与 manifest 相等。
2. 从候选 Isla 的 `isla-sail/` 拷贝 `dune`、`dune-project`、`sail_plugin_isla.ml`、`jib_ir.ml` 到 `plugin/`，运行 `dune build --release`，退出 0。运行 `cmake -S sail-riscv-candidate -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF`，退出 0；V128 JSON SHA-256 `89923ebff21718bb382df38bf246207cbb1eb5ae0cd314d078d87c0ab2b9f625`。
3. 从 `sail-riscv-candidate/model/` 运行 `sail -plugin ${D_ROOT}/plugin/_build/default/sail_plugin_isla.cmxs -isla -D SYMBOLIC --strict-var --strict-bitvector --strict-exponentials --require-version 0.20.1 --memo-z3-path ${D_ROOT}/memo/sail_smt_cache --all-modules --isla-preserve encdec_compressed_forwards --isla-preserve encdec_compressed_forwards_matches --isla-preserve encdec_compressed_backwards --isla-preserve encdec_compressed_backwards_matches --isla-output-dir ${D_ROOT}/ir --config ${D_ROOT}/build/config/rv64d_v128_e64.json -o rv64d_d riscv.sail_project`。日志 `ir/generate_retry.log`，退出 0；IR SHA-256 `c9e1bfe29e75452568d61fc3b3407e707eb1bd7e48193e212495ec21b885bc75`。
4. 第一次相同 Sail 命令误把 `--memo-z3-path` 指向已存在目录，约 7 分钟后退出 2，日志 `ir/generate.log` 报 `Is a directory`；其约 15 MiB IR 文件不计通过。已把缓存路径修正为父目录内的文件，并更新仓库内 `tools/README.md`。
5. `python3 agents/float_support_review/tools/check_d_ir.py --baseline isla-candidate/rv64d.ir --candidate ir/rv64d_d.ir --config build/config/rv64d_v128_e64.json --sail-interface sail-riscv-candidate/model/core/softfloat_interface.sail --report ir/check_d_ir.json`，退出 0。旧 IR 为 79 声明/12 函数体/67 缺体；候选 IR 为 88 声明/88 函数体（原 79 均有体，另 9 个已审定纯辅助），同名模型依赖静态检查通过。此结论只涉及 IR 结构。
6. 在隔离 `executor.rs` 对旧分发命中加入 `panic!` 探针，`cargo fmt --package isla-lib`、外部 runner 重构建后，完整 IR 测试副本的 67 项调用仍退出 0。旧正式 IR 加 `f32Add` 包装器的负例退出 101，`d_runner/old_fallback_with_trap.log` 明确显示旧分发 panic。随后仅在隔离候选删除 executor 旧分发入口，再次 `cargo fmt --package isla-lib`、重构建、重跑全 67，退出 0；旧 IR 负例退出 101，`d_runner/old_fallback_after_delete.log` 为 `NoFunction("riscv_f32Add")`。候选 `float.rs` 中旧 `SfOp`/dispatch/计算实现仍存在但已无执行器调用；清理该 A 包文件属于 E 交接。
7. `sail-riscv-candidate/test/symbolic_fp/d_probe.sail` 有 67 个 concrete 包装器及 277 个未知输入包装器，`d_probe.sail_project` strict 类型检查退出 0；`generate_probe_ir.py` 可重建 `probe_unknown_ir/d_probe_unknown.ir`。`make_wrapped_ir.py` 将包装器附到**全模型候选 IR 的外部测试副本**；原候选 IR 哈希不变。`ir/rv64d_d_reproduced.ir` SHA-256 `74e3bc71fcf0d2e6b70aff3b005af780317b6eb8b8f6fc21b4ae21e5dd52a934`。两个 runner 的 Rust 源码、Cargo manifest 和输入 TSV 在 `d_runner/`、`d_unknown_runner/`，`cargo fmt` 与 `cargo build` 退出 0。
8. `d_runner/target/debug/isla-float-d-runner ir/rv64d_d_reproduced.ir d_runner/cases.tsv`：67/67 helper 各有一组独立 SoftFloat RNE 预期，结果位、五 flags、SAT、一条完成路径和普通函数进入事件全部通过。日志 `d_runner/full_no_dispatch_timed.log`，退出 0，耗时 5.04 秒，最大 RSS 131784 KiB。输入 SHA-256 `d7c2f633e066bff78a39b766f4b1834a748778fd61b50c099e5df5650f02408c`。本组具体样例不代表边界全覆盖；格式包此前有更广差分证据。
9. `d_unknown_runner/target/debug/isla-float-d-unknown-runner ir/rv64d_d_reproduced.ir d_unknown_runner/{f16,f32,f64}.txt`：90+96+91=277 项逐名未知位串调用，包含有 RM 签名的五种普通编码及 `f32ToF16`/`f64ToF32` 的 RM6 ROD；每项 `Run::Finished`、SAT、恰好一条完成路径、普通函数进入事件。三个日志 `{f16,f32,f64}_timed.log` 均退出 0，耗时分别 5.47/5.34/5.64 秒，最大 RSS 132396/132256/128860 KiB。此项只验证不新增执行路径，不对全部未知输入证明数值等价。
10. 原有 12 个函数体：`d_runner/old12_cases.tsv` 39 个特殊值/窄整数样例，`d_runner/old12_narrow_boundaries.tsv` 另 24 个整数范围边界，均在禁旧分发的完整 IR 测试副本上核对 bits、五 flags、一条完成路径及进入事件；日志 `d_runner/{old12,narrow}_timed.log`，均退出 0，耗时 5.13/5.18 秒，最大 RSS 130324/129100 KiB。窄整数预期来自 RISC-V 指令规定的有符号/无符号目标范围、越界饱和值和 NV，以及精确端点与 1.5 舍入的 NX；f16 无法表示 32767/65535 时分别用可表示的 32752/65504，并测下一越界值或无穷。Recip7/Rsqrte7 仅对规范明确的零、无穷、qNaN、sNaN、负数特殊分支设预期；**有限正值查表输出尚无独立规范表对照，不能宣称六个估算体完整正确性 PASS**。`old12_cases.tsv` SHA-256 `f0db644d9a61721b5a4b12828bdf0aacf47bf23f61cfcf685d5e1f1eb3a69098`。
11. 隔离 Isla 的 `cargo test -q -p isla-lib --lib primop::float` 为 31/31 PASS，`cargo fmt --package isla-lib --check`、两候选 `git diff --check` 退出 0。日志 `isla_float_tests.log`。

## 阶段性初版结论（独立估算参考接入前）

- D 候选已证明：新 V128 IR 的原 67+12 个普通函数体完整、执行器旧分发入口删除后 67 个 concrete 对照与 277 个未知输入路径检查通过；旧 12 个函数体的特殊值及窄整数边界回归通过。E 的指令、访存、RV32、严格配置和正式入口未测。
- 仍需等待独立 RISC-V Recip7/Rsqrte7 有限正值查表参考，经 Astra 审定后补六个估算体的有限输入/flags 定向测试。没有参考前标“旧 12 有限估算待验证”，不把 D 全阶段写成 PASS。
- E 前如需清理 `float.rs` 中未调用的旧专用实现，须由主 agent 将该文件从 A 包移交；当前仅删除隔离 executor 的旧入口，未改主 `float.rs`。正式 IR、严格配置、`run.mk` 保持旧版本。

## 独立估算参考接入与 SAT→差异 UNSAT 补强

本节是上面“待验证”项之后的新增证据，取代初版关于六个估算体有限输入尚未验证的现状判断，保留初版历史以说明门槛如何关闭。仍不把这些样本外推为对全部输入的证明。

### 来源与快照

- RISC-V V v1.0 规范固定 commit `3570f998903f00352552b670f1f7b7334f0a144a` 的 `v-spec.adoc` §13.9/§13.10（`vfrsqrt7`/`vfrec7`），存为 `reference/v-spec-v1.0.adoc`，SHA-256 `bfe42bd33dc6abeef5362f475605dda3d229e722257a613b0691cee760f04a19`。该文件的特殊类别规则及 f32 示例独立于本项目 Sail 源码。
- 参考实现使用 Ara 子模块 `toolchain/riscv-isa-sim` HEAD `204b88deda9bcb7537bc09ae5c320f691e8839ef` 的 Spike SoftFloat API。工作树另有 `riscv/` 改动，`softfloat/` 源文件无本轮修改。`reference/spike-estimate-oracle.c`（SHA-256 `7a7e874b8d5f62c6583e733b120b30ce76c63bae06d593d64a042d7236b9de94`）只重置 flags、设置 RM 并调用固定库的 `f16/f32/f64_recip7` 与 `f16/f32/f64_rsqrte7`，不复制待测 Sail 查表公式。二进制 `reference/spike-estimate-oracle` SHA-256 `5df09858c896ffeff02fb170dd07372114071a93bafe604cba23c95c2cfe6833`；其依赖的 `reference/libsoftfloat.so` 已一同保存，SHA-256 `f1592214d4845ba004aaa487f3f3285e6cbd0909597e126e5438c2f4ae614b41`。复现时设 `LD_LIBRARY_PATH=${D_ROOT}/reference`。Astra 另核规范给出的四个 f32 数值例子与该 Spike API 的五 RM 20 个结果一致。
- 第一批独立向量 `reference/spike-estimate-cases.tsv` 350 行，SHA-256 `92e0e300bb322fad9a27db79ceb9661971a115ebb6dbe89b0daba67360d98236`。此组为各格式有限正值、极小次正规溢出门槛两侧、最大次正规、最小正规、1/1.5/2、最大正规及五 RM 的定向样本。
- `reference/generate_estimate_sweep.py` 只按规范索引选择输入，期望值全部取固定 Spike API；`reference/estimate_sweep.tsv` 1618 行 SHA-256 `3cd9c03ec220a7f7810dc3294c2750178f55a6673ac214b3882b1c42eeca08ad`。每个格式的 Recip7 正规尾数高 7 位索引 0–127、Rsqrte7 指数奇偶加尾数高 6 位索引 0–127 各用 RM0 覆盖；次正规尾数的每个可能最高 1 位置（f16 10、f32 23、f64 52）在两操作上均覆盖 RM0–4。生成器 SHA-256 `63ff893759aabb21d02ad09b0bc37b6069f6318aa903e0a29b305b60bad9d3de`，逐行覆盖元数据 `estimate_sweep.json` SHA-256 `41f07c4c5275c2fc1c1506d8d105b3f56622cde8338ae72044846c3ddc67391e`。
- `reference/generate_estimate_special.py` 只构造输入类别，期望值由同一固定 Spike API 返回；`reference/estimate_special.tsv` 420 行 SHA-256 `ad4da3fc89b9be734f5fde80766e5eae69fd6f55b67613cb13a3a5b81928cfe9`。每格式/操作/五 RM 覆盖正负零、正负无穷、正负最小与最大次正规、正负 1、正负 qNaN/sNaN。生成器 SHA-256 `89e574535ec2ff04a6ddbb5fc6536553209bf34882feb70532f533df38c9a6ac`。

### 隔离候选证明命令与结果

`d_runner/src/main.rs` 已在外部目录改为：对每个实际 `Run::Finished` 的 tuple，先 `check_sat` 确认可满足，取完整结果位和五 flags 后，用 `check_sat_with(OR(flags != expected, bits != expected)) == Unsat` 排除任何不同结果；同时检查普通函数进入事件与恰好一条完成路径。Unsat、Unknown、超时或额外路径均不会记为通过。runner 源 SHA-256 `9a9c8e264534540dd51a716d21e1e4206093b5449873ccf39980cf7042df07e2`，`cargo fmt --manifest-path d_runner/Cargo.toml`、`cargo build --manifest-path d_runner/Cargo.toml` 退出 0。所有下列命令使用已删除旧分发的隔离 Isla 候选，IR 为完整 V128 候选加只供调用的包装器 `ir/rv64d_d_reproduced.ir`；原 `ir/rv64d_d.ir` 哈希不变。

```sh
: "${D_ROOT:?set an external work directory}"
D_BIN="$D_ROOT/d_runner/target/debug/isla-float-d-runner"
D_IR="$D_ROOT/ir/rv64d_d_reproduced.ir"
"$D_BIN" "$D_IR" "$D_ROOT/d_runner/cases.tsv"
"$D_BIN" "$D_IR" "$D_ROOT/reference/spike-estimate-cases.tsv"
"$D_BIN" "$D_IR" "$D_ROOT/reference/estimate_sweep.tsv"
"$D_BIN" "$D_IR" "$D_ROOT/reference/estimate_special.tsv"
"$D_BIN" "$D_IR" "$D_ROOT/d_runner/old12_cases.tsv"
"$D_BIN" "$D_IR" "$D_ROOT/d_runner/old12_narrow_boundaries.tsv"
```

| 输入与日志（均在 `d_runner/`） | 通过/总数 | 退出码 | wall time | 最大 RSS |
| --- | ---: | ---: | ---: | ---: |
| `cases.tsv` → `unsat_67.log` | 67/67 | 0 | 5.07 s | 130036 KiB |
| `spike-estimate-cases.tsv` → `unsat_estimate350.log` | 350/350 | 0 | 7.31 s | 130956 KiB |
| `estimate_sweep.tsv` → `unsat_estimate_sweep.log` | 1618/1618 | 0 | 14.72 s | 128500 KiB |
| `estimate_special.tsv` → `unsat_estimate_special.log` | 420/420 | 0 | 7.61 s | 135352 KiB |
| `old12_cases.tsv` → `unsat_old12.log` | 39/39 | 0 | 5.68 s | 128664 KiB |
| `old12_narrow_boundaries.tsv` → `unsat_narrow.log` | 24/24 | 0 | 5.50 s | 131488 KiB |

Recip7 极小次正规 `0x1` 的五 RM 特别复核：三格式均报 `OF|NX=0x05`；RNE/RUP/RMM 返回正无穷，RTZ/RDN 返回最大有限值，全部经上表 SAT→差异 UNSAT。所有 350/1618/420 例同时核完整 NaN 位模式与五 flags，未跳过 NaN。`d_unknown_runner` 的 277 项仍仅证明未知位串入口单路径、SAT 和函数进入；它不证明所有符号输入上的结果等价。

### 最新结论与限制

- 六个 Recip7/Rsqrte7 原函数体的规范特殊类别、代表性有限正值、全部 128 个正规查表索引及次正规各最高位位置已有**独立 Spike 位/flags 参考的定向回归**，且在删除旧分发的候选完整 IR 中逐项 SAT→差异 UNSAT。连同窄整数范围边界和原 67 项，D 阶段要求的隔离候选门槛已有上述证据。
- 这些有限向量仍不是对任意指数、尾数剩余低位、所有负有限值组合或全部输入的形式化证明。全符号输入上的位/flags 等价未在 D 候选上逐项证明；277 项未知输入只检查不新增数据 fork。E 阶段指令译码、CSR/flags 累计、mask/vstart、访存、RV32 条目及正式 IR/严格配置仍未实施。候选 `float.rs` 中无调用旧实现仍待 E 文件边界移交。
