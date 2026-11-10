# 浮点类型复用的性能复核（2026-09-26）

本文记录 `fp_exception_flags` / `float_bits` 类型复用后的独立性能调查。当前已核实：同形小 IR 的未知输入 f16Add RM3 在中间异常值使用 BV5 时耗时 48–67 秒，改为内部五 Bool、仅出口共享 flags 后为 0.05 秒；该单项回退可定位到中间 flags 表示和转换。具体 Z3 内部耗时来源尚未 profiling。当前候选与实施状态由[议题摘要](status.md)汇总；本文不宣布 E 阶段通过。

## 已完成的旧版单项对照

主 agent 报告类型复用候选 IR `361980eac11c52d06d940a552b0b6144777461f47d104315ea7df86e088f67cd` 的未知输入 f16Add 前五种 RM 耗时约 325 秒。本轮独立使用**同一台机器、同一个 runner 二进制**复跑旧版 f16Add RM3，确认旧版此项在当前环境仍能较快完成。

| 项目 | 独立对照结果 |
| --- | --- |
| 原始旧版 IR SHA-256 | `c9e1bfe29e75452568d61fc3b3407e707eb1bd7e48193e212495ec21b885bc75`；与当时主 `isla/rv64d.ir` 及旧 D 原始 IR 一致 |
| 实际受测旧版 wrapped IR SHA-256 | `08b15853621e2dbb8bbe33a12897e539177e3da0fd583ec6c2177008d559198d` |
| runner SHA-256 | `67eb9e5117bc208e5ad3f0c7d1352388f9eeb1bed8bcbbfae626e8110ab4804c`；使用 IR refresh 候选目录中的同一个二进制 |
| 唯一入口 | `d_unknown_riscv_f16Add_rm3` |
| 输入与检查 | 两个浮点操作数保持未知；保留普通 helper 进入追踪、完整执行、最终 SAT 和单路径断言 |
| 外限与退出码 | `timeout 60s`；退出 0 |
| runner 输出 | `PASS d_unknown_riscv_f16Add_rm3 paths=1 sat=1 trace=1` |
| `/usr/bin/time -p` | `real 5.04`、`user 4.91`、`sys 0.11` 秒，包含整个 IR 的解析和初始化 |

外部证据目录以 `RUN_DIR` 表示，目录标识为 `isla-float-perf-old-rm3-20260926-9dp8v2ra`；其中 `one.txt` 为唯一输入清单，`run.log` 保存原始输出，`report.json` 保存实际完整命令、退出码及二进制/IR 哈希。复跑时为 `RUN_DIR` 选择新的证据目录，`REFRESH_DIR` 指向候选产物目录，`BASELINE_DIR` 指向旧 D 产物目录：

```sh
printf '%s\n' d_unknown_riscv_f16Add_rm3 > "$RUN_DIR/one.txt"
timeout 60s /usr/bin/time -p "$REFRESH_DIR/isla-float-d-unknown-runner" \
  "$BASELINE_DIR/ir/rv64d_d_wrapped_all.ir" "$RUN_DIR/one.txt" \
  > "$RUN_DIR/run.log" 2>&1
```

这次独立实验只证明旧版单项在当前环境的表现。325 秒来自另一代理的五项候选观察，不能与包含初始化的单项 5.04 秒直接相除，声称精确速度差。完整新旧 A/B 结果需另行记录。

## 已核实的源码事实

1. 新 generic 分类中的 `float_decompose` 按 `bitvector_length` 分派格式。`isla/isla-lib/src/primop.rs::length` 对符号位串通过 `Solver::length` 读取 Z3 sort 宽度，返回具体 `Val::I128`；格式分派不依赖输入数值，固定 f16/f32/f64 输入不会由此新增符号路径。
2. `float_decompose` 在选中的格式分支提取 sign、exponent、mantissa；`is_all_ones`、`is_all_zeros` 和最高位检查使用已知宽度构造常量或固定索引。它们没有引入新的浮点值域约束。重复调用会增加提取与解释执行工作，例如 `ieee_is_snan` 内又调用 `ieee_is_nan`，二者均执行分解；当前没有证据把严重回退归因于这些额外操作。
3. `isla/isla-lib/src/smt.rs::Solver::add_internal` 对 `Def::DefineConst` 执行 `translate_exp`、`ast.simplify()`，再把 AST 存入 `self.decls`。这个步骤不生成“新 SMT 常量等于表达式”的断言；后续使用会取得已保存的表达式 AST。`subrange_internal` 的固定区间提取也走这条定义路径。
4. `361980ea…` 的 flags 构造使用五个 BV5 ITE 和四次按位 OR；读取 flags 使用 BV5 AND 与非零比较。旧版五 Bool record 的字段读取无需这些打包/拆包表达式。通用类型复用与表达式构造方式是可独立比较的两个选择。

## 待验证的性能解释与实施边界

**目前仅是假说，尚未做 profiling：**反复打包、读取和重新打包 BV5 flags，会让包含 FP 运算的 AST 多次参与 `Z3_simplify`。因此回退可能发生在符号表达式构造阶段，而非最终 `check_sat`。仅凭 runner 在输出 PASS 前耗时较久，不能区分这两者。

Astra 审定的单因素 B 候选保留 `fp_exception_flags` 和 generic `float_decompose`：以五次 `isla_bool_to_bit` 直接拼接共享 flags，以固定 bit getter 读取，RISC-V 层直接按反向位序拼接。共享位序仍为 NV bit 0、DZ bit 1、OF bit 2、UF bit 3、NX bit 4；ISA 包装负责转成 RISC-V 位序。

复核 B 时应核对实际 IR 差分只改变上述 flags 构造/读取、固定 runner 和未知输入清单，并保留 SAT 与单路径检查；先验 32 种 Bool 组合与未知 f16Add，再看完整 f16 集合。若 B 改善，只能先归因于这组表达式改写；定位到某次 `simplify` 或某种 Z3 重写规则仍需独立测量。此次调查不授权修改 Isla 核心 simplifier，也不删 SAT 检查或缩小未知输入域。

## A/B 小 IR 结果的独立复核

类型复用实施代理随后提供同 runner、同入口的 A/B 测量。本轮独立读取两份实际 IR 与原始 `rm3.log`，确认以下结果；没有重复运行 A/B。

| 候选 | 实际 IR SHA-256 | real / user / sys（秒） | 结果 |
| --- | --- | --- | --- |
| A：BV5 ITE、OR 与掩码 getter | `0e095c243b2e3893a15e88859c6b6d814931b6fc3c0127933a0637a4d0b0e8a1` | 67.28 / 67.10 / 0.07 | 单路径、SAT、普通 helper 进入追踪通过 |
| B：Bool 转 bit 拼接、bit getter、ISA 位序反转 | `21f30c652e16a87efd2b2e09b393d3438bd06ae45d0e29984b651cf6e9cbf85d` | 48.38 / 48.24 / 0.06 | 单路径、SAT、普通 helper 进入追踪通过 |

两项均使用前述 `67eb9e51…` runner，输入清单为 `d_unknown_riscv_f16Add_rm3`，清单 SHA-256 为 `aab993df9c2161b45f8177e3df480cb09550ac04be85732f5c15f788cdda8820`。外部目录标识分别是 `isla-type-reuse-a`、`isla-type-reuse-b`，各自保存受测小 IR 和 `rm3.log`；路径仍由调用者的运行目录确定。

独立去除源码位置后的函数体对比确认：变化仅涉及 `ieee_exception_flags`、OF/UF/NX getter 及 `riscv_pack_ieee_flags`；NV/DZ getter 因不再使用被编译器删除。generic NaN/sNaN/inf/finite 分类、rounded 异常算法和 add 异常算法逐字相同。因此本轮数据支持 flags 表达式形状影响耗时；B 仍明显慢于旧版，尚不能作为性能恢复的交付。

**B 的剩余耗时不能据此归因于 generic 分类。**generic 分解和分类只对原始输入位串构造固定提取和比较，没有构造浮点算术表达式或附加输入约束。A/B 复核时，主 agent 与 Astra 选择进一步隔离的 C：保留 generic 分类和原生 RM，在内部保留五个 Bool 异常事实，仅在输出边界转为共享 `fp_exception_flags`。当时 C 尚待实际测量，后续结果见下一节。A/B 使用小 IR，旧版对照使用完整 IR，均包含各自解析与初始化，不记录跨两者的精确速度倍数。

## C0/C1：中间 flags 表示的定位与最终复用边界

本轮独立读取 C0/C1 实际小 IR、重新计算哈希并核对原始 `rm3.log`，未重复运行。两者沿用前述 runner 和 RM3 输入清单。

| 候选 | 实际小 IR SHA-256 | real / user / sys（秒） | 结果 |
| --- | --- | --- | --- |
| C0：内部五 Bool，出口直接拼 RISC-V flags | `37578a72703f8a0e93c4043caf0e0795829b571320533295def31dd14020f3f9` | 0.05 / 0.02 / 0.02 | `paths=1 sat=1 trace=1` |
| C1：内部五 Bool，出口先转共享 flags，再反转位序 | `eb1fb6af42dfa566fab588ac5145e72a75542fbc6581769730ec90c4ff6a6cba` | 0.05 / 0.03 / 0.02 | `paths=1 sat=1 trace=1` |

外部目录标识分别为 `isla-type-reuse-c0`、`isla-type-reuse-c1`，对应文件为 `d_probe_c0.ir` / `d_probe_c1.ir` 与各自 `rm3.log`。C1 目录同时有其他候选 IR，不能用目录内其他 IR 的哈希代替本表的实际受测小 IR。

独立 IR 复核确认：

- B、C0、C1 的 `float_decompose`、NaN/sNaN/inf/finite 分类、原生 RM 选择和未知 RM3 wrapper 在去除源码位置后逐字相同。wrapper 仍生成两个 `undefined_bitvector(16)` 并调用普通 `riscv_f16Add`，没有固定操作数或改变 RM3。
- B→C0 把异常构造从 BV5 拼接改为五 Bool record，getter 改为字段读取，并同步中间值类型与输出打包；`add16` 与 `riscv_f16Add` 的其余运算表达式未变。
- C0→C1 只新增 `ieee_pack_shared_flags` 并调整 `riscv_pack_ieee_flags`：将内部事实以 NX/UF/OF/DZ/NV 拼成 Sail 的共享五位类型，再读取 `shared[0]` 到 `shared[4]` 拼成 RISC-V 位序。

因此，在这个完整未知输入的 RM3 单项中，严重回退来自**中间 flags 的位串表示及反复转换**；generic 分类和原生 RM 保持不变仍恢复快速执行。C1 也证明只在输出边界复用共享 flags 没有重现该单项回退。此结论比最初的静态假说更强，但仍不能细分时间究竟耗在 `Z3_simplify`、其他表达式构造或最终 SAT；本文没有做 profiling，也没有修改核心 simplifier。

最终采用的结构为内部异常事实 record、generic `float_bits`/`float_decompose` 分类和原生 `float_rounding_mode`，在输出边界使用 `fp_exception_flags`，最后由 RISC-V 包装处理位序。这次性能定位只覆盖上述 f16Add RM3；其他操作、完整新 IR 的未知输入集合和指令语义回归仍以集成验证记录为准。
