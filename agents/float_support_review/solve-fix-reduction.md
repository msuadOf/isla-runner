# 顺序浮点归约与共享源掩码

本包实施已批准的 `RFVVTYPE`、`RFWVVTYPE` lane ITE 方案，只改 `sail-riscv/model/extensions/V/vext_fp_red_insts.sail` 两个 execute clause，以及 `vext_utils_insts.sail` 的 `init_masked_source`。纯 tuple 接口复用 `fp_add_pure`、`fp_min_pure`、`fp_max_pure`、`fp_widen_pure`，由普通向量 lane 包维护。本包测试程序位于 `sail-riscv/test/symbolic_fp/solve_vector_reduction/`，证据目录在下文记为 `$RED_STAGE`。

## 实施与语义

- `vl==0` 早退仍在原处：不读 seed、不写目标、不清 `vstart`。非法编码检查仍在它之前。
- `vl>0` 时按 `i=0..num_elem_vs-1` 顺序，以已经选择的 `sum` 调用纯 FP helper，`sum=ite(mask[i]==1,candidate,sum)`。ordered/unordered sum 保持原有顺序实现，不重排。每 lane 的 flags 仅在 active 时 OR 入累计值；widening 先 OR 转换 flags 与加法 flags。循环后一次 `accrue_fflags`，再执行原 `write_single_element` 和 `set_vstart`。无活动 lane 仍写原 seed；sNaN seed payload 不经过未选中的 candidate。
- 共享 `init_masked_source` 在原断言、`get_start_element` Err、end、fractional `real_num_elem` 计算及断言之后，仅 `SYMBOLIC && __isla_use_extra_ops` 返回 `isla_init_mask`。Sail 预处理器要求 `$ifdef` 位于顶层，因此分别保留 SYMBOLIC 与普通函数体；把 fast return 从 SYMBOLIC 体移除后，两函数体逐字节相同。`extra_ops=false` 仍执行原循环，非 SYMBOLIC 函数原样保留。

## 红绿与验证状态

独立真实 Sail→IR 归约原型先记录优化目标的红基线：4 lane 未知 mask、f16 源、seed、旧 flags 的原 if 实现有 16 条 SAT 完成路径；目标为 1 条。顺序 ITE 原型为 1 条，全部旧路径的 sum bits 与 flags 差异 UNSAT；2 lane 对应 4→1 条。原型文件及逐命令/哈希在 `$PROTOTYPE_STAGE/red_report.json`，详见 [性能设计](solve-fix-performance.md#112-顺序归约与共享源-mask)。这一原型不等于生产 IR 验收。

`init_masked_source` 的四组独立 SMT 公式以任意 BV128 start/end/real 与未知 vm 比较原循环活动条件、`isla_init_mask` 位条件：2/4/8/64 lane 均先 SAT、差异 UNSAT。本轮分别重跑 `$PROTOTYPE_STAGE/source-mask-2.smt2`、`-4.smt2`、`-8.smt2`、`-64.smt2`，每组输出 `sat`、`unsat`。非法 start 的实际指令返回另由下方两个输入核对，公式证明不能替代此调用链。

本包源码落盘后，全模型 Sail strict typecheck 两档均退出 0。随后共享工作树的 `vext_fp_utils_insts.sail` 在途修改一度使 SYMBOLIC 检查于该文件第 563 行报 `Cannot re-write sizeof('d)`，本包两个源码哈希未变。普通 lane 包修复该 helper 后，**再次重跑 SYMBOLIC 与非 SYMBOLIC 全模型 strict 检查均退出 0**。命令：

```sh
cd sail-riscv/model
sail --strict-var --strict-bitvector --strict-exponentials --require-version 0.20.1 \
  --memo-z3-path "$RED_STAGE/symbolic-cache" -D SYMBOLIC --all-modules \
  --just-check riscv.sail_project
sail --strict-var --strict-bitvector --strict-exponentials --require-version 0.20.1 \
  --memo-z3-path "$RED_STAGE/default-cache" --all-modules \
  --just-check riscv.sail_project
```

专属测试从既有独立 oracle 及 guard 输入生成 **142 条合法、4 条非法 start**。合法集合包括单宽/加宽的顺序辨识 `2^24+1−2^24`（加宽用相应精度的整数幂）、reverse、mask，min/max NaN/±0，全 mask sNaN seed payload、活动 sNaN 转换 NV、`vl=0`、VS Initial/Clean、fractional LMUL、policy，以及新加的「inactive sNaN 后一 lane 活动精确抵消」两例。非法 start 包含 `vl=1` 与 `vl=0`，核对前置 guard 不因零 VL 跳过。每例观察所有 32 个物理向量寄存器、已有浮点寄存器、`fcsr`、`mstatus`、`vstart`、`vl`、`vtype`、`misa`；runner 对期望差异求 UNSAT 并核对译码/编码、单执行路径、返回类别。原 d012 IR 基线 142/142 合法及 4/4 非法 PASS，作为下节新旧行为对照。

```sh
python3 agents/float_support_review/tools/solve_vector_coverage/numeric.py \
  --output "$RED_STAGE/inputs-caseid.json"
python3 sail-riscv/test/symbolic_fp/solve_vector_reduction/prepare_cases.py \
  --numeric "$RED_STAGE/inputs-caseid.json" \
  --hazards "$VECTOR_STAGE/inputs-reduction-hazards/reduction-hazards.json" \
  --guards "$VECTOR_STAGE/inputs-final" --output "$RED_STAGE/inputs"
python3 sail-riscv/test/symbolic_fp/solve_vector_reduction/run_cases.py \
  --runner "$IR_STAGE/isla-float-e-nonmem-runner" \
  --ir "$IR_STAGE/ir/rv64d_final.ir" --config "$IR_STAGE/rv64-e.toml" \
  --cases "$RED_STAGE/inputs/reduction-cases.json" --output "$RED_STAGE/success"
python3 sail-riscv/test/symbolic_fp/solve_vector_reduction/run_cases.py \
  --runner "$IR_STAGE/isla-float-e-illegal-runner" \
  --ir "$IR_STAGE/ir/rv64d_final.ir" --config "$IR_STAGE/rv64-e.toml" \
  --cases "$RED_STAGE/inputs/reduction-illegal.json" --output "$RED_STAGE/illegal"
```

本轮旧基线输入 SHA-256：合法 `07c8637c63d97e1707fbeff30b003b54c19f78eb5df9b7e1224291a930446733`；非法 `1898fcf24d18a7ecb6df9f97a5385d8546f7994b7d3c82f53a153430f8dac846`。d012 IR SHA-256 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`，E 配置 `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`。合法 runner `bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425`，非法 runner `e265b79839c1e3b6721342b435d1c974574c7424d47b2edda92246d9f41802b3`。对应结果 JSON SHA-256 分别为 `fbf1cf608e51c00afdabadaed73b6bdef75b51a323353bff0355e535b3eb8155`、`4ddc9d7843aff0abab003fb6c4adc46f13d52beb0f835fb0d0eb76e1285cb43b`，两个 runner 均退出 0、逐项无错误。新源码 SHA-256：red `62c066def287a83d49d9ddfd57266e6d4d91c950a2931391aaf37572456bae45`；source mask `993b15a715a8f31a03c11d4519297cdd8176e2bd775383e761fb50fe46c43b4f`。

## P2 新 IR 归约回归

P2 候选 IR `d86655a415441ad17533742b9d0ee726b43b64acaf2c0fc0754d27979c7859a9` 由同批模型快照生成，快照 manifest SHA-256 `128d59a5661c3efdba566682c58ee6733f4799d9afd19fa3c6a542d24d95f346`；其中本包 red/source mask 两文件 SHA 与上文一致。原始输入、候选 IR、E 配置、source manifest、四组原始 runner 输出、逐命令/哈希 manifest 和 [比较报告](../../isla/target/float-solve-evidence/reduction-p2/comparison.json) 均保存于 `isla/target/float-solve-evidence/reduction-p2/`（本机运行产物，不是提交源文件）。

| 配置 | SHA-256 | 合法 Retire | 非法 start | 结果 JSON SHA-256（合法／非法） |
| --- | --- | ---: | ---: | --- |
| E 原配置，`extra_ops=true` | `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987` | 142/142 PASS | 4/4 PASS | `f94a33c2558bd0202df3cf321f7b260432ffc659b1e4d1fddb4c34cf6a8e4436`／`ca341967e4f410842364021846cd459f9512403ef8deb78b112bfd8d728b9c8a` |
| 仅 `__isla_use_extra_ops=false` | `8f7d1d52051712a5202570798ba149cebc29a78664fc3e11cd19186e81e03f62` | 142/142 PASS | 4/4 PASS | `2f9aa590d482e0efb351bef472ecf22ac83636bfa40c2915e033b162e63b97fb`／`a663b30a156416705dbc1b797585c78347456b947a21e55b378aef842bfa3563` |

四组命令都使用上文的 `run_cases.py`，`--ir` 指向证据目录的 `ir/rv64d_p2.ir`，`--config` 分别指向 `configs/rv64-e.toml`、`configs/default-lanes.toml`，`--cases` 指向 `inputs/reduction-cases.json` 或 `inputs/reduction-illegal.json`，`--output` 为 `extra_ops_{true,false}-{success,illegal}/`。每个 manifest 保存完整命令、退出码 0、输入/IR/配置/runner/输出哈希和耗时；每个结果均 SAT、与预期寄存器状态差异 UNSAT、真实译码/重编码一致、唯一执行路径及正确返回类别。逐项比较两种 P2 配置及旧 d012 原始结果的名称、编码、返回类别、全部观察寄存器、解码字段、SAT/UNSAT 与路径数，**142 条合法及 4 条非法均 0 项语义差异**。

这批使用旧 E 预编译 runner，其哈希见上节；该二进制仍链接旧版 Rust 库。因此结论是新 Sail→IR 模型在既有 runner 下的数值及观察状态回归，不能代替 R3 新 runner 的官方初始化、完整终态账本、动态源码分支和 77 项完成性验证。P2 严格 workaround 区域、官方入口仍由 IR 集成和运行包继续验证；上述 PASS 只适用于表中 IR、配置、输入及 runner。
