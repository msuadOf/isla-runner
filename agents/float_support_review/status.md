# Isla 浮点分支审查状态（2026-09-25）

审查对象：`isla` 的 `origin/feat/float-support`，头提交 `1a1910e`，基线 `0008fae`。当前工作树仍在基线，本轮仅静态审查，不切换分支。

## 已确认

- 新增 5 个提交、8 个文件。浮点 helper 绑定在 `isla-lib/src/primop/float.rs`，执行入口在 `isla-lib/src/executor.rs:1196-1229`，SMT 转换在 `isla-lib/src/smt.rs` 与 `isla-lib/src/smt/smtlib.rs`。运行配置见分支 `configs/riscv64_difftest_fd.toml`、`scripts/run.mk`。
- `rv64d.ir` 中 79 个 `zriscv_*` val：12 个有 IR 函数体；67 个无函数体，均在分支 helper 名称解码覆盖范围内。12 个带函数体的名称是 `Recip7`/`Rsqrte7`（各 f16/f32/f64）和窄整数转换（f16 的 I8/Ui8/I16/Ui16、f32 的 I16/Ui16）。
- 分支覆盖 f16/f32/f64 的加减乘除、FMA、开方、比较、roundToInt、32/64 位整数双向转换、格式转换，以及 f32→BF16。结果通过 SMT FP 运算后转为 IEEE 位向量；fflags 在位向量表达式中单独计算。
- 已知语义近似：除法/FMA NX、一般下溢 UF、定向舍入下的 OF。性能方面，分支文档报告复杂 FP clause 求解很慢，可能超时或 OOM；这些是分支作者的报告，本轮未复测。

## 发现的问题

1. `float.rs:745-758`：符号 rm 的 ite 链始终返回 RNE。影响 rm/frm 符号化时的结果和依赖结果的标志。需增加符号 rm 测试，修正各分支舍入模式选择。
2. `float.rs:1162`：`Eq` 使用 signaling 比较的 NaN→NV 规则；SoftFloat `f32_eq` 对 qNaN 不置 invalid。需区分 Eq 与 Lt/Le，并覆盖 qNaN、sNaN。
3. `float.rs:1116-1124`：FMA 未检测无穷大乘积加反号无穷大；NV 漏报且 NaN 位模式不受规范化保护。需加入该无效情形测试。
4. 分支的精确度矩阵本身已承认 OF/UF/NX 的近似；若目标是与 RISC-V SoftFloat 逐位一致，还需精确编码这些异常条件。当前 21 个测试覆盖边界样本，未提供随机差分或全面精确度证明。

## 后续验证

在隔离的分支检出中先添加上述三类失败测试，再修正实现；随后运行 `cargo test -p isla-lib --lib softfloat` 和代表性 `make solve-FLEQ_S`/大路径浮点 clause，最后与 Sail SoftFloat 对数值结果及 fflags 做差分。此处记录为建议，未在本轮执行。
