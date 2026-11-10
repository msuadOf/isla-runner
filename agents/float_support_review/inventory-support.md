# 浮点支撑层检查清单（2026-09-26）

本表补充 [实施计划](plan.md) 的参考清单，检查 Sail 类型、IR、SMT 表达式、Z3 接线、输出及测试入口。通用 primop 名称和 RISC-V helper 的逐项清单另列，不在这里重复。

## 1. 版本和检查范围

- Isla：`f4f8e4584a70588c66c9e7a6286cc20211618f18`。
- Sail-RISC-V：`f8ce8490981eac6396a31013180a2e718615757d`。
- 当前根目录没有 `sail/` 源码 checkout。本轮读取的是 `sail --dir` 指向的已安装库；`sail --version` 为 `Sail 0.20.1 (HEAD @ 446fb477c508853595ccc937ed60765aa685ae31)`。下文以 `$(sail --dir)/lib/...` 表示该来源，不能据此声称父仓库固定了这份 Sail 安装。
- 主要做静态检查；另用命令行 Z3 4.16.0 做了两组很小的语法/求解器检查，命令和结果在第 3 节。没有构建 Isla、生成 IR 或运行浮点回归，因此不是完整浮点验收。
- 判断标准：通用 IEEE 数值操作直接使用 Z3；换成 ARM、x86 后含义不变的基础操作可以留在 Isla。异常、ISA 返回值和状态更新由模型组合。
- 本表的 CLI Z3 结果仅证明列出的独立小表达式在命令行 Z3 4.16.0 上得到所记输出；没有经过 Isla 的 Solver、Sail 编译、IR 或完整指令，不记为 Isla 功能 PASS。

## 2. 参考清单

“保留”表示本次没有发现需要改动的接线，并不等于全量语义测试通过。“需补/需改”是具体工作；“待验证”不能提前记为错误或通过。

| 编号 | 检查项 | 当前情况与证据 | 结论及修改建议 |
| --- | --- | --- | --- |
| S01 | Sail 原生 FP/RM 类型 → IR | `isla/isla-sail/sail_plugin_isla.ml:117` 映射 float16/32/64/128 和 float_rounding_mode；`isla/isla-lib/src/ir_parser.lalrpop:49` 读取 `%f16/%f32/%f64/%f128`，`:76` 读取 `%rounding_mode`。 | **保留，补最小编译测试**。不必重造四种 IEEE 格式和 typed RM 类型。 |
| S02 | FP 格式参数和声明 | `isla/isla-lib/src/ir.rs:151` 定义 (5,11)/(8,24)/(11,53)/(15,113)；`isla/isla-lib/src/primop_util.rs:425` 将 FP/RM 变成符号值；`isla/isla-lib/src/smt.rs:747` 创建对应 Z3 sort。 | **保留，补格式断言测试**。注意 significand 宽度包含隐含位，IEEE 位串宽度为 exponent + significand。 |
| S03 | BF16 | IR/插件仅接受上述四种 float 类型；BF16 需要 (8,8)，与 f16 的 (5,11) 不同。SMT 层 `Ty::Float(u32,u32)` 和原生转换可表达 (8,8)。 | **需补公开路径**。按设计先验证通用 f32→BF16 位串转换；不能把 BF16 当作 `%f16`。是否扩展 IR 类型留待最小接口验证。 |
| S04 | 五种 RM 常量和 NaN/±inf/±0 | `isla/isla-lib/src/smt/smtlib.rs:56`、`:65` 有枚举；`:1105` 推导类型；`isla/isla-lib/src/smt.rs:2222`、`:2230` 逐项调用 Z3 原生构造；`isla/isla-lib/src/simplify.rs:1483`、`:1495` 可打印。 | **保留，补五模式测试**。RM 本身是通用值，RISC-V 3 位编码解释应放模型。 |
| S05 | 从 IEEE 位串建 FP | `isla/isla-lib/src/smt/smtlib.rs:97` 正确推导 `Float(ebits,sbits)`；`isla/isla-lib/src/smt.rs:2252` 调用 `Z3_mk_fpa_to_fp_bv`；`isla/isla-lib/src/simplify.rs:1518` 输出带格式的 `to_fp`。 | **保留合入修复**。具体 BV 输入的 primop 接收问题仍需改，详见通用 primop 清单；不能把底层接线完整当成入口可用。 |
| S06 | FP 转 IEEE 位串 | `isla/isla-lib/src/smt/smtlib.rs:98`、`isla/isla-lib/src/smt.rs:2253` 已有 ToIEEE 类型和 API；通用 Sail primop 未公开。ToIEEE AST 还携带 ebits/sbits，而 Z3 实际由操作数 sort 决定位宽。 | **需补公开入口及参数检查**。确保 AST 标注格式与输入 sort 一致；不让用户通过此入口改变格式。NaN 位串未指定，不承诺 NaN payload 往返。 |
| S07 | ToIEEE 文本输出 | `isla/isla-lib/src/simplify.rs:1519` 输出 `((_ fp.to_ieee_bv) x)`；普通形式为 `(fp.to_ieee_bv x)`。本机 Z3 4.16.0 两种都接受。 | **建议规范输出，非已确认运行错误**。补打印后重新解析的测试；不能说当前 Z3 一定解析失败。 |
| S08 | FP/整数转换类型与 Z3 接线 | `isla/isla-lib/src/smt/smtlib.rs:118` 处理 Convert/FromSigned/FromUnsigned/ToSigned/ToUnsigned；`isla/isla-lib/src/smt.rs:2256` 调用对应 Z3 API；`isla/isla-lib/src/simplify.rs:1524` 已打印这五类。 | **底层保留，公开入口需补**。ToUnsigned 尚未公开；ToSigned 原语虽已注册，已安装 native `float.sail` 未提供相应声明。模型需要的 signed/unsigned 声明都应明确添加。 |
| S09 | 算术、比较、分类及 FMA 接线 | `isla/isla-lib/src/smt.rs:2240` 到 `:2301` 为 FPUnary、FPRoundingUnary、FPBinary、FPRoundingBinary、FPfma 调用原生 Z3；`isla/isla-lib/src/smt/smtlib.rs:1105` 到 `:1129` 有结果类型。 | **保留，补结果/类型测试**。一般 SMT `=` 与 `fp.eq` 不同；架构浮点相等比较应调用后者。min/max 的 ISA 特例由模型处理。 |
| S10 | 表达式遍历、变量替换、引用统计 | `isla/isla-lib/src/smt/smtlib.rs:553`、`:645`、`:766`、`:856`、`:953` 的访问/替换包含 FPUnary、带 RM 的操作和 FMA；`isla/isla-lib/src/simplify.rs:148` 的引用统计也访问 RM 及全部操作数。ToIEEE 使用现有 FPUnary 分支。 | **未发现因增加 ToIEEE 而漏遍历的项，保留**。新增操作时仍需检查变量替换、删除未使用变量和打印后的求解等价性。这里不要求在 Rust 中计算浮点常量。 |
| S11 | 输出多样化与直接读取模型值 | `isla/isla-lib/src/smt.rs:1727` 的 `get_finite_domain_var` 对 FP/RM 在 `:1743` 返回 None，只是跳过该类抽样。直接 `get_var/get_exp/get_val` 经 `get_ast_with_timeout`，FP/RM 在 `:2012` 返回 `unsupported sort kind`。 | **明确接口限制，修正文档**。现方案将 FP/RM 留作内部值，最后输出 BV/Bool，暂不必扩展直接 FP 物化。若以后允许 FP 类型架构输出，则必须补该接口；不能统一描述成“FP/RM 读取返回 None”。 |
| S12 | SMT 条件输入解析器 | `isla/isla-lib/src/smt_parser.lalrpop:66` 到文件末尾支持 Bool/BV/ITE/数组，未列 FP 运算或 RM 常量。它是模型约束/假设入口，不是完整 SMT-LIB 文件解析器。 | **当前计划可不改**，外部输入仍以 BV 约束。若要让用户在配置中直接写 `fp.add/fp.eq`，需另补解析器并测试；不能宣称所有文本入口都支持 FP。 |
| S13 | 现有 native Sail 浮点声明 | 已安装 `$(sail --dir)/lib/float.sail:53` 定义 `rounding_mode = float_rounding_mode`；`:138` 起声明 FromIEEE，`:173` 起声明 FromSigned/Unsigned，但整个文件没有 ToIEEE/ToSigned/ToUnsigned 声明。`sail-riscv/model/extensions/FD/freg_type.sail:49` 已有自己的 rounding_mode 枚举。 | **需新增不冲突的模型声明文件**。不整体 include 旧 `float.sail`；使用 `float_rounding_mode` 或独立别名，声明所需通用原语。安装库读取结果需与正式构建使用的 Sail 版本再次核对。 |
| S14 | Sail 位串浮点库 | `sail-riscv/model/prelude/prelude.sail:21` 已 include `<float/interface.sail>`。已安装 `float/common.sail:23` 到 `:27` 的 flags 为 invalid 最低位、inexact 最高位；`:31` 到 `:39` 的舍入编码及全局状态也是该库自身约定。 | **分类可复用，编码必须转换**。RISC-V 不可直接接收这份 flags，也不能用这份全局 rounding 状态代替 frm。不要为复用算术库把现有 Z3 原生数值计算换成位运算实现。 |
| S15 | Sail SYMBOLIC 与 extern 函数体 | `isla/isla-sail/sail_plugin_isla.ml:348` 自动定义 SYMBOLIC；`:294` 的 `remove_extern_impls` 删除 Jib 中仍带 extern 标注的函数体；`:340` 将该过程用于最终 IR。 | **必须最小编译验证**。增加 SYMBOLIC 函数体后，要检查 IR 中 helper 确实有实现、内部 FP 操作成为 primop。是否保留 cpp/lem extern 而不影响 Isla 必须用实际 IR 确认。 |
| S16 | solver 初始化与 tactic | `isla/isla-lib/src/smt.rs:2065` 要求显式 `configure_tastic`，`:2119` 未初始化直接 panic；默认 Qfaufbv 见 `isla/isla-lib/src/smt/tactic.rs:7`。当前 CLI Z3 的小 FP/BV/RM 公式在 qfaufbv/smt/default 下都返回 sat。 | **初始化按现约定保留，完整混合公式待测**。小公式可接受不代表实际 flags、RVV 和性能已通过，也不保证 CLI Z3 与 Isla 链接库版本相同。 |
| S17 | 现有 softfloat 单元测试初始化 | `isla/isla-lib/src/primop/float.rs:1348` 的 `solve_call` 在 `:1352` 直接 `Solver::new`，本模块没有 `configure_tastic`。筛选本模块单独运行时，不能依赖别的模块碰巧初始化全局状态。 | **需改测试入口**。按现行惯例先调用 configure，再创建 Solver；用单独筛选的测试运行证明不依赖测试顺序。本轮静态确认调用缺失，未运行 cargo 测试。 |
| S18 | 当前测试覆盖范围 | `isla/test/property/` 仅查到三份原生浮点性质测试：加法不结合、NaN 分类、与 max 的比较。`isla/src/isarch/exec.rs:1176` 另测多样化跳过 FP/RM。未查到逐格式 FromIEEE/ToIEEE/ToUnsigned、symbolic RM、打印再解析的专门测试。 | **需补有针对性的回归**。旧性质测试保留；新增通用入口测试、仅对 SoftFloat 有同语义 API 的模型 helper 做结果+flags 差分，Recip7/Rsqrte7、FCVTMOD 和指令状态按规范/模型测试。测试存在不代表本轮已运行。 |

### 类型检查的补充

`isla/isla-lib/src/smt/smtlib.rs:1048` 明确说明 `infer` 的前提是表达式已合法，因此它不是完整的 sort 校验器。不能因为它给出了一个返回类型，就假定输入 FP 格式、RM 类型、ToIEEE 的 ebits/sbits 都一致。通用 primop 在组装 SMT 前应按现有接口检查参数；不必为了本次迁移重写整个 SMT 类型系统。

`isla/isla-lib/src/smt/smtlib.rs:822` 的 `map_var` 把 FPConstant 参数局部命名为 `sbits, ebits`，但按原顺序取出并按原顺序放回，没有实际交换参数。属于命名容易误读，不应误报为当前格式颠倒错误。

## 3. 小范围命令检查

### 3.1 ToIEEE 打印式

本轮通过 Python `subprocess.run(['z3','-in'], input=source, text=True, capture_output=True)` 将下面输入直接交给命令行 Z3，没有改仓库文件。`z3 --version` 输出 `Z3 version 4.16.0 - 64 bit`。

```smt2
(declare-const x (_ FloatingPoint 8 24))
(assert (= ((_ fp.to_ieee_bv) x) #x3f800000))
(check-sat)
```

结果：标准输出 `sat`，标准错误为空，退出码 0。把第二行改为下面普通形式，结果相同：

```smt2
(assert (= (fp.to_ieee_bv x) #x3f800000))
```

结论只限于这个 Z3 版本的语法接受情况。当前打印形式可以规范化，但没有证据将它列为本机求解阻塞。

### 3.2 tactic 接受 FP/BV/RM 混合小公式

本轮通过 `subprocess.run(['z3','-in','-T:5'], input=source, text=True, capture_output=True)` 输入：

```smt2
(declare-const x (_ FloatingPoint 8 24))
(declare-const y (_ FloatingPoint 8 24))
(declare-const rm RoundingMode)
(assert (= (fp.to_ieee_bv (fp.add rm x y)) #x3f800000))
(assert (fp.isNormal x))
(assert (fp.isNormal y))
(check-sat-using qfaufbv)
(get-info :reason-unknown)
```

分别将 `qfaufbv` 替换为 `smt`、`default`，三次都返回：

```text
sat
(:reason-unknown "")
```

三次退出码均为 0，标准错误为空。此检查只说明 CLI Z3 接受并解出了该公式，不是 Isla 初始化、实际链接库、完整异常公式或性能的验收。

## 4. 建议实施时的顺序

1. 补通用原语公开入口和输入检查，同时修复测试初始化；保留现有正确类型/Z3 接线。
2. 建立不与 RISC-V 枚举冲突的 Sail 原语声明，用一个 FP→BV 返回值验证完整编译和运行。
3. 验证 BF16 路径、类型/打印/变量替换、五种 RM 及具体/符号输入。
4. 模型继续使用原始位串检查 sNaN/payload，FP 只承担数值计算；所有架构返回值在读取模型前变为 BV/Bool。
5. 最后以实际 Isla 所链接 Z3 和正式 IR 做完整浮点回归，记录 tactic、版本、结果、失败和超时。
