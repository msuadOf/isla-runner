# 浮点类型复用审查（2026-09-26）

> 当前采用 C1：泛型格式/内建RM复用保持，内部保留局部五Bool事实，仅出口复用 `fp_exception_flags`。本文下方“删除record”是最初A方案的接口可行性审查；完整未知输入性能门槛使其未获采用。现行取舍与证据见[架构审定](type-reuse-architecture.md)、[性能对照](type-reuse-performance.md)和[实施记录](implementation.md)。

本审查回应用户关于复用已有 Sail 类型、减少平行实现体系的要求。结论由 Astra xhigh 对当前源码与安装的 Sail 0.20.1 库独立核对，并以外部最小模型验证。这里批准的是类型和分类适配的收敛边界；完整实现、差分与正式 IR 的状态由 [实施记录](implementation.md) 和 [议题摘要](status.md) 记账。

## 类型和接口映射

| 当前接口 | 收敛后的接口 | 必须保持的语义 |
| --- | --- | --- |
| `ieee_rounding_mode = float_rounding_mode` | 直接使用 Sail 内建 `float_rounding_mode` | 原生 Z3 RM 的五种值；不使用 RISC-V 指令枚举或位编码充当原生 RM |
| `struct ieee_fp_exceptions` 的五个 Bool 字段 | 已经由 `<float/interface.sail>` 引入的 `fp_exception_flags` | 仍独立计算五种异常事实；共享编码依次为 NV=bit0、DZ=bit1、OF=bit2、UF=bit3、NX=bit4 |
| `riscv_pack_ieee_flags` | 接受 `fp_exception_flags`，显式转成已有 `bits_fflags` | RISC-V 顺序为 NV=bit4、DZ=bit3、OF=bit2、UF=bit1、NX=bit0；可用 `e[0] @ e[1] @ e[2] @ e[3] @ e[4]` 完成一次边界转换 |
| f16/f32/f64 各自重复的 NaN、sNaN、inf、zero、finite 位切片 | 五个以 `float_bits('n)`、`float_decompose` 为基础的泛型 strict Bool 适配函数 | 复用库的格式分解和字段宽度；原始 sNaN/payload 信息仍从位串获得 |
| `bits_H`、`bits_S`、`bits_D`、`bits_BF16`、`bits_rm`、`bits_fflags` | 保持现有 RISC-V 接口 | 原有 SoftFloat extern、指令调用和 C++ 后端契约保持一致 |
| 内建 `float16/32/64/128` | 保持现有 Sail 原生类型 | 数值运算继续调用 Isla/Z3 通用 primop，无第二套位串算术实现 |

安装库 `float/common.sail` 已有 `fp_exception_flags = bits(5)`、五个异常常量、`is_fp_bits`、`fp_bits`、`float_bits('n)` 和 `float_decompose`。其中 overflow 常量的实际名称是 `fp_eflag_oveflow`，实现须使用真实导出名。共享标志不能直接返回为 RISC-V flags：同为五位不代表位序相同。

库里的 `fp_rounding_modes = bits(5)` 使用 1–5 编码，且配有全局 `fp_rounding_global`；它既不是 RISC-V 的三位 RM，也不是 solver 的 `float_rounding_mode`。本次不引入这套全局状态。RISC-V 的 `rounding_mode` 枚举包含 `RM_DYN`，继续用于译码及动态舍入合法性；现有 `riscv_valid_rm_to_ieee` 保留职责。ROD=6 仍只由两种窄化包装处理。

## 分类复用和控制流边界

`prelude/prelude.sail` 已包含 `<float/interface.sail>`。但直接调用库的 `float_is_nan`、`float_is_snan`、`float_is_inf` 会把其中的短路 `&` 带入新 helper：当前正式 IR 的这些函数已有依赖浮点数据的 `Jump`。旧 `f_is_NaN_H/S/D` 等也使用短路布尔表达式，并位于 FD 指令文件中，不宜让 core 反向依赖它们。

可执行的最小适配如下；其余分类同样只使用分解字段和 strict Bool：

```sail
val ieee_is_nan : forall 'n, is_fp_bits('n). bits('n) -> bool
function ieee_is_nan(raw) = {
  let fp : float_bits('n) = float_decompose(raw);
  strict_and_bool(is_all_ones(fp.exp), not_bool(is_all_zeros(fp.mantissa)))
}
```

`float_decompose` 在当前插件生成的 IR 中仍含按 `bitvector_length` 判断 16/32/64 的分支，并未全部静态展开。这些条件由调用实参的具体位宽确定。验收应检查未知浮点数据不增加执行路径，同时允许已核实的位宽分支；不能继续把整个调用闭包“文本中没有任何 Jump”作为必要条件。不得通过全局 linearize 删除架构断言。

BF16 不能直接传给按宽度判格式的上述接口：其 16 位编码是 exp8/fraction7，标准 16 位格式是 exp5/fraction10。现有 BF16 转换使用 f32 原始源判断 sNaN，将结果拼接 16 个零重建为 f32，继续按这一入口调用标准分类和异常算法。

## 文件边界和回归要求

实施包涉及 `model/prelude/ieee_fp_primops.sail`、`model/core/ieee_fp_exceptions.sail`、`model/extensions/FD/softfloat_symbolic*.sail`，以及直接依赖旧类型的 `test/ieee_exceptions/ieee_exceptions.sail`。后者第 4 行使用旧 RM 别名，第 10–15 行使用旧异常结构和全部五个字段，必须同步。包装中的整数无效返回选择、共享库中的域屏蔽和 ROD NX 判断，也必须由 record 字段访问改为对应库标志位的布尔测试。

本包保留全部既有通用原语声明。直接包含安装库 `<float.sail>` 会与模型 `freg_type.sail` 的 `rounding_mode` 枚举重名；本次不为删除声明重复而改动整个架构枚举，也不切换到库的比较或算术实现。原始数值算法、阈值、NaN 规范化、整数无效值、CSR 累计及 C++/Lem extern 继续按现有职责分工。

实现后应完成以下相关门槛：

1. 严格 Sail 类型检查和 SYMBOLIC IR 生成；非 SYMBOLIC C++ 仍使用原 SoftFloat extern。
2. 五个独立异常位及组合的库编码、RISC-V 出口位序回归，覆盖全部 32 种布尔组合；避免测试和实现共用同一个错误打包函数。
3. f16/f32/f64 的 NaN、sNaN、inf、正负零、有限数分类差异检查；未知数据逐格式单完成路径。BF16 另用能区分两种 16 位格式的样例。
4. 受影响的完整 helper 结果与五 flags 差分，包括整数无效返回、ROD、BF16 及普通算术特殊域；重新检查全部 67 个 helper 调用闭包和未知输入路径。
5. 正式候选 IR 重生及 79 份严格配置、源码坐标和注释锚点同步，随后执行相关指令回归。类型探针通过不替代这些门槛。

## 最小探针实测

探针位于外部临时目录 `isla-float-type-audit-20260926`，未编辑共享模型。Sail 为 0.20.1；Isla/Sail-RISC-V HEAD 分别为 `f4f8e4584a70588c66c9e7a6286cc20211618f18`、`f8ce8490981eac6396a31013180a2e718615757d`，两者均存在本议题未提交修改。动态 runner 使用已删除旧浮点分发的 D 隔离候选 `isla-lib`，没有使用内存 worktree。

`probe.sail` 定义泛型 NaN、sNaN、finite 分类，引用 `float_bits`/`float_decompose`；另有五 Bool 到 `fp_exception_flags` 的纯 ITE/OR 组合、直接接受 `float_rounding_mode` 的函数及三个未知输入入口。该文件没有 `$sail_internal`，直接引用内建 RM 的编译已通过。探针项目引用当前模型 prelude；原生类型声明中的 `$sail_internal` 已先加载。

令 `TYPE_REUSE_OUTPUT` 指向上述外部证据目录，`ISLA_PLUGIN` 指向 D 隔离构建的插件，实际成功命令为：

```sh
sail --plugin "$ISLA_PLUGIN" --isla \
  --strict-var --strict-bitvector --strict-exponentials \
  --memo-z3-path "$TYPE_REUSE_OUTPUT/sail_smt_cache" --all-modules \
  --isla-preserve audit_unknown16 --isla-preserve audit_unknown32 \
  --isla-preserve audit_unknown64 --isla-preserve audit_flags \
  --isla-preserve audit_rm --isla-output-dir "$TYPE_REUSE_OUTPUT" \
  -o probe "$TYPE_REUSE_OUTPUT/probe.sail_project"
cargo run --quiet --manifest-path "$TYPE_REUSE_OUTPUT/runner/Cargo.toml" \
  -- "$TYPE_REUSE_OUTPUT/probe.ir"
```

Sail 编译退出 0。动态 runner 对每个 `undefined bits(16/32/64)` 分别执行完整泛型分类链，要求返回 `Run::Finished`、SAT 且完成路径数严格等于 1；三项均通过，runner 退出 0：

```text
zaudit_unknown16: SAT, exactly one completed path
zaudit_unknown32: SAT, exactly one completed path
zaudit_unknown64: SAT, exactly one completed path
```

| 证据 | SHA-256 |
| --- | --- |
| `probe.sail` | `115c36bb83dcbc1ff69a4101eff083dcc6f94dac9360e33a4903d5ba0795704a` |
| `probe.ir` | `b0e89daa07ea4d95d569049fc1bcdcc87865396926d827d0986d1f891aeda156` |
| `runner/src/main.rs` | `4ba74f92023ead6a9a6bac5c67d47c7fe55a41fc7125e31af82e8ee6b4e02e83` |
| `run.stdout` | `fe927dc0c23a5510a6948b2390ad0146e8bde844f51dd5ae36bbbd0ea9e95cc2` |
| D 构建 `sail_plugin_isla.cmxs` | `c4eccb06af9f85820c28bd67556ae0f191361c93cbe1afb334900f9e1f0e22f6` |
| 安装库 `float/common.sail` | `7b019ef910e6e6f53c3115ab71fd82ab4f0e349eb9ffb97328904870f9c44dd9` |
| 安装库 `float/nan.sail` | `0b5e8517b3a0ad042c81774b170cb9777c7210d39c651f67cc019281c7ca65d8` |

初次探针生成曾因项目文件绝对路径处理和未引号保护的路径连字符失败；首版 Rust runner 也曾因可变借用和调试格式错误未编译。这些准备失败修正后才取得上述成功产物，未计作模型失败。成功探针仅证明类型接线、三种分类的未知数据单路径与 flags 构造可编译；未对该探针的全部分类输出或五异常组合做数值等价证明，亦未验证最终迁移后的完整模型。
