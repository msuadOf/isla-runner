# 浮点模型复用既有 Sail 类型的架构审定

日期：2026-09-26。本文记录用户要求“更多复用 Sail-RISC-V 已有类型”后，对当前实现的调整。主 agent 已授权按下述边界实施；实际编译、差分与正式 IR 状态见 [实施记录](implementation.md)和[状态摘要](status.md)。本文中的接口审定不表示正式候选已通过验证。

现行审定采用下文的 C1 方案：复用原有格式结构、原生舍入类型和最终共享 flags，内部保留五个 Bool 的异常事实 record。A/B 将每层事实改为五位位串的尝试因实测耗时回退而放弃；其源码审查和测试结果按对应候选保留，不能用于新候选的动态验收。

## 已核对的现有接口

`sail-riscv/model/prelude/prelude.sail` 已引入 Sail 的 `<float/interface.sail>`，后者提供 `fp_exception_flags`、`float_bits('n)`、`float_decompose` 及分类工具。当前 Sail 版本为 0.20.1。

| 内容 | 复用入口与含义 | 本轮处理 |
| --- | --- | --- |
| RISC-V 原始值 | `sail-riscv/model/core/softfloat_interface.sail` 的 `bits_H/S/D/BF16/W/WU/L/LU` | 三格式包装的现有签名已经使用这些类型，保留 |
| 指令舍入字段 | `bits_rm` 与 `sail-riscv/model/extensions/FD/freg_type.sail` 的 `rounding_mode`，后者包含 `RM_DYN` | 保留已有译码、动态 FRM 选择和合法性检查 |
| Z3 原生舍入值 | Sail 内建 `float_rounding_mode`，实际降低为 Isla 的 RM sort | 删除新增的 `ieee_rounding_mode` 别名，声明和数值辅助直接使用已有内建类型 |
| 共享异常交付 | `<float/common.sail>` 的 `fp_exception_flags = bits(5)` 和既有位序 | C1 在最终出口转换成现有类型；内部 `ieee_fp_exceptions` 保存五个 Bool 事实，避免每层反复打包 |
| ISA 异常布局 | `bits_fflags`，位次为 NV、DZ、OF、UF、NX 从高到低 | 在 `riscv_pack_ieee_flags` 中明确转换共享异常位次 |
| 原始 IEEE 编码拆分 | `float_bits('n)` 与 `float_decompose` | 五个泛型纯分类适配共用该结构，替代 16/32/64 位各自重复切片的十五个函数 |
| 数值运算 | Sail 的 `float16/32/64/128` 与现有 Isla 通用 FP 原语 | 保持由 Z3 计算；不迁移到位串算术实现 |

Sail 的 `<float.sail>` 自身声明 `type rounding_mode = float_rounding_mode`，与当前 RISC-V 枚举重名。因此本轮保留模型的 native 原语声明桥接文件，删除其中多余的 RM 别名，保留全部已接入声明和 Isla 的 82 个注册出口。仅删除未使用声明不能解决类型和格式逻辑重复，也会影响此前的接口承诺。

`<float/common.sail>` 的 `fp_rounding_modes` 是另一套五位编码，且配有 `fp_rounding_global`。当前指令控制继续使用已有 RISC-V 舍入入口，原生数值计算直接使用内建 RM sort；此次复用不增加中间编码转换或全局舍入状态。

## 五个异常事实的布局

五个事实仍分别由已有公式计算。C1 在模型内部以 Bool record 传递，由 `ieee_exception_facts` 构造；通用出口 `ieee_pack_shared_flags` 按下表构造既有共享类型，再由 RISC-V 包装重新排列为架构位次。架构状态累计继续由指令执行函数完成。初始 A 候选曾在每层通过 ITE 选择常量再按位 OR，B 候选改用逐 bit 拼接；两者的回退证据与放弃原因见末节。

| 事实 | Sail 既有常量 | 共享位次 | RISC-V `bits_fflags` 位次 |
| --- | --- | ---: | ---: |
| 无效操作 | `fp_eflag_invalid` | 0 | 4 |
| 除零 | `fp_eflag_divide_by_zero` | 1 | 3 |
| 溢出 | `fp_eflag_oveflow` | 2 | 2 |
| 下溢 | `fp_eflag_underflow` | 3 | 1 |
| 不精确 | `fp_eflag_inexact` | 4 | 0 |

`fp_eflag_oveflow` 的拼写来自当前 Sail 库，不另建同值别名。上表固定当前 Sail 0.20.1 共享位序；C1 只在最终出口按这个位序拼接，而非在异常公式中反复读取位串掩码。共享位串不能直接当作 RISC-V `bits_fflags` 返回。

此调整不改变 NV 对 NX 的优先规则、有限输入屏蔽、OF/UF/NX 判据、ROD 的不精确置奇规则或 ISA 的 NaN/无效整数返回策略。审查需逐项核对原 record 字面量的五个表达式与新事实构造函数参数一一对应。

## 分类复用与执行分叉

现有 `float_is_nan/snan/inf` 使用短路布尔表达式，其 IR 含依赖输入数据的条件分支。当前迁移 helper 的纯选值要求仍然适用。因此本轮复用 `float_decompose`、`float_bits`、`is_all_ones`、`is_all_zeros` 和 `is_highest_zero`，并使用已有严格布尔原语组合分类结果。

`float_decompose` 在当前插件生成的 IR 中仍含按位串长度选择格式的分支。已核对 `isla/isla-lib/src/primop.rs` 的 `length`：对于 symbolic BV，从 solver 读取固定 sort 宽度，直接返回具体 `Val::I128`；具体 BV 和 MixedBits 也返回具体长度。因此已知格式、未知数值的调用可以执行一个确定的格式分支。

验收仍是纯计算新增执行分叉为零。IR 文本里存在 `Jump` 本身不等于发生符号分叉；应检查分支所依赖的值，以及各格式未知输入的实际执行路径。小型独立编译实验已确认泛型拆分和消费者直接使用 `float_rounding_mode` 可编译；三个未知输入探针分别以 16/32/64 位调用 NaN、sNaN 和 finite 分类，均 SAT 且只有一条完成路径。这些小实验只支持接口可行性，最终门槛须针对本次实际实现和全部受影响 helper 复验。

## 文件与验证边界

同一实现负责人独占 native 声明、共享异常库、公共 RISC-V 包装和三个格式包装，统一完成接口迁移；依赖旧 record 的隔离 Sail fixture 同步修改。独立测试负责人只新增其专属类型复用测试文件，正式 IR 和严格配置由集成人在模型冻结后处理。

本轮保留四个现有 `riscv_canonical_nan*` 包装。进一步复用 `sail-riscv/model/extensions/FD/fdext_regs.sail` 中的 canonical NaN 定义需要调整早期模型与隔离测试的依赖位置，作为后续单独收敛项登记。

必须提供以下证据：

1. 结构检查确认多余 RM 别名已移除，分类共用既有格式结构，仅保留内部 Bool 事实 record，最终出口使用共享 `fp_exception_flags`；82 个通用注册出口和现有 Sail 绑定完整保留。
2. 五个事实的 32 种组合分别验证共享布局和 RISC-V 布局，独立预期采用上表位次。
3. 分类覆盖 16/32/64 位的 NaN、sNaN、无穷、正负零及普通有限值；未知数据保持单条完成路径。
4. 共享异常和 67 个 helper 复验完整结果位及五 flags，包括整数边界、五种普通舍入和两个 ROD 窄化入口；先确认输入 SAT，再要求差异 UNSAT。原有未知入口的单路径证据须重跑。
5. 正式 V128 IR 由冻结源码重新生成，确认完整退出 0，重新核对函数体、调用依赖、79 份配置的哈希、全部源码区域与锚点。同批切换 IR 和配置后运行受影响的指令状态回归，包含本轮 BF16 LMUL 修复。

初始设计曾预见把 Bool record 改成五位位串会增加中间 SMT 表达式，因此保留未知输入耗时门槛。实测回退后，C1 复用原 Bool record 作为内部事实表示，并只在出口转换共享 flags；这项取舍由下述同形小 IR 对照支持。独立事实的语义、未知域及单路径门槛保持不变。超时或 Unknown 按未通过记录。

## 实施源码的独立复核

2026-09-26 对初始 A 候选的源码进行了逐操作复核。比较基准为 D 阶段冻结的共享异常库，其 SHA-256 为 `e48d120694876f2365bb4a2bb5a8e2b5b31f5b569185bea2099b7f90c5509704`。此节属于 A 候选的历史审查。

- 共享库保留的 58 个函数，经过本节允许的类型替换、分类函数合并、字段读取改为具名 getter、record 构造改为五参数构造后，去除注释和空白的代码完全一致。34 个 record 构造逐个核对旧字段顺序为 invalid、divide_by_zero、overflow、underflow、inexact；表达式与新参数逐项一致。
- 共享库移除十五个按格式分类函数，新增五个泛型分类、五个异常读取函数及一个异常构造函数。新增逻辑已人工核对其拆分字段、sNaN quiet bit、常量位次和严格布尔组合。
- 三个格式包装文件的变化全部属于上述允许变换。公共 `riscv_pack_ieee_flags` 依次读取 NV、DZ、OF、UF、NX 并拼接，保持 RISC-V 从高到低的位序。
- native 桥接文件原有 190 条 Sail `val` 声明，在 RM 类型替换后与新集合完全相等；未删除注册出口或转换声明。

此源码审查允许启动隔离候选 IR 生成；动态数值、flags、路径和完整指令门槛仍须分别完成，不能以机械一致性检查替代动态通过。

复核从仓库根目录运行。`TYPE_REUSE_BASELINE` 指向 D 阶段冻结快照的 `sail-riscv/untracked` 目录，`TYPE_REUSE_SOURCE` 指向受审候选的 Sail-RISC-V 源码根目录，`TYPE_REUSE_VARIANT` 必须指定 `a` 或 `c1`。命令先验证基准 SHA，再按对应候选允许的变换比较每个函数，任何不符立即退出；A 模式须使用保留的 A 候选源码，C1 模式用于最终审定源码。

```sh
python3 - "$TYPE_REUSE_BASELINE" "$TYPE_REUSE_SOURCE" "$TYPE_REUSE_VARIANT" <<'PY'
from pathlib import Path
import hashlib
import re
import sys

baseline = Path(sys.argv[1])
current = Path(sys.argv[2])
variant = sys.argv[3]
assert variant in ("a", "c1")
fields = ["invalid", "divide_by_zero", "overflow", "underflow", "inexact"]
record_count = 0

def uncomment(text):
    return re.sub(r"//[^\n]*", "", text)

def normalize(text):
    return re.sub(r"\s+", "", uncomment(text))

def split_fields(text):
    depth, start, result = 0, 0, []
    for index, char in enumerate(text):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            if text[start:index].strip():
                result.append(text[start:index].strip())
            start = index + 1
    if text[start:].strip():
        result.append(text[start:].strip())
    return result

def transform(text):
    text = text.replace("ieee_rounding_mode", "float_rounding_mode")
    if variant == "a":
        text = text.replace("ieee_fp_exceptions", "fp_exception_flags")
    text = re.sub(r"ieee_is_(nan|snan|inf|finite|zero)(?:16|32|64)\b", r"ieee_is_\1", text)
    text = re.sub(r"\b(\w+)\.(invalid|divide_by_zero|overflow|underflow|inexact)\b",
                  lambda m: "ieee_has_" + m[2] + "(" + m[1] + ")", text)
    def record(match):
        global record_count
        entries = [entry.split("=", 1) for entry in split_fields(match[1])]
        assert [key.strip() for key, value in entries] == fields
        record_count += 1
        constructor = "ieee_exception_flags" if variant == "a" else "ieee_exception_facts"
        return constructor + "(" + ",".join(value.strip() for key, value in entries) + ")"
    return re.sub(r"\bstruct\s*\{([^{}]*)\}", record, text)

def functions(text):
    text = uncomment(text)
    starts = list(re.finditer(r"^(?:function|val)\s+(\w+)", text, re.M))
    result = {}
    for index, match in enumerate(starts):
        if match[0].startswith("function "):
            end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
            result[match[1]] = text[match.start():end].split("$endif")[0]
    return result

relative = "model/core/ieee_fp_exceptions.sail"
original = (baseline / relative).read_bytes()
assert hashlib.sha256(original).hexdigest() == "e48d120694876f2365bb4a2bb5a8e2b5b31f5b569185bea2099b7f90c5509704"
old, new = functions(original.decode()), functions((current / relative).read_text())
common = set(old) & set(new)
assert len(common) == 58
for name in sorted(common):
    assert normalize(transform(old[name])) == normalize(new[name]), name
assert record_count == 34
removed = {f"ieee_is_{kind}{width}" for kind in ("nan", "snan", "inf", "zero", "finite") for width in (16, 32, 64)}
assert set(old) - set(new) == removed
for width in (16, 32, 64):
    relative = f"model/extensions/FD/softfloat_symbolic_f{width}.sail"
    assert normalize(transform((baseline / relative).read_text())) == normalize((current / relative).read_text()), relative
relative = "model/prelude/ieee_fp_primops.sail"
old_vals = {normalize(line.replace("ieee_rounding_mode", "float_rounding_mode")) for line in (baseline / relative).read_text().splitlines() if line.startswith("val ")}
new_vals = {normalize(line) for line in (current / relative).read_text().splitlines() if line.startswith("val ")}
assert len(old_vals) == len(new_vals) == 190 and old_vals == new_vals
print("58 个函数、34 个 record、3 个格式包装、190 条声明：预期变换一致")
PY
```

## 初始 A 候选 IR 的独立结构审查

2026-09-26 初始 A 方案的 V128 候选 SHA-256 为 `361980eac11c52d06d940a552b0b6144777461f47d104315ea7df86e088f67cd`，其模型 manifest SHA-256 为 `678fa776a36c2b8e26bf8c2cbd3e2a9987e10f9583240e06a56da5a4e2552e87`。独立重算确认 manifest 的 165 份模型文件同时匹配生成快照与当时的 `sail-riscv/model/`。完整生成退出码由集成人记录为 0。

与旧 `c9e1bfe2…` IR 比较，函数数从 2052 变为 2048：移除十五个分格式分类函数，增加五个泛型分类、五个 getter 和一个异常构造函数。编译器自动参数 `z3zE` 后的数字随前序函数变化而重新编号；比较每个函数时，先去除 SourceLoc，再对这些参数做保持引用同一性的一一重命名，实际变化只有 120 个 IEEE/RISC-V 浮点函数与 `execute`。其余函数均一致。`execute` 的差异仅为 BF16 VF 指令先返回非法扩宽配置，再检查内部 LMUL 不变量。

非函数部分移除了异常 record 和两个包含该 record 的 tuple 类型，调整了相应 IEEE 声明与 `riscv_pack_ieee_flags` 参数。无其他声明变化；其余类型和全局内容在忽略空白后完全一致。这项检查排除了无关模型逻辑混入的迹象，仍不代替新候选的数值、路径、状态和严格配置门槛。

独立核对[类型复用隔离测试](../../sail-riscv/test/symbolic_fp/type_reuse_README.md)在 A 方案时点的原始日志：32 种共享与 ISA 标志组合、三个格式各 12 个分类特殊值、三个真正未知输入的 SAT 单完成路径均通过。受测隔离 IR SHA-256 为 `b4706cc368e21dfe098e0402d611bd27b4529ec059f2fcecbf8d319e17b7cdb4`；共享异常源 SHA-256 为 `4e4305571ebd137c09031ca9b76fa34fb97f3dc69d530b951abe9203c953ce55`，与 A 候选 manifest 一致。该结论仅覆盖此处列出的类型与分类合同。

## 性能门槛触发的构造调整

上述 `361980ea…` 候选未切入主树。未知 f16 输入批次出现实际耗时回退：D 阶段同一运行器的 90 项入口耗时 5.47 秒；本轮达到 600 秒外限、退出 124，只完成 17/90 项的 SAT 单路径检查，后续 f32/f64 未运行。此结果触发隔离 A/B 诊断，当前不能归结为已经确认的特定根因，也不能以削减未知域或删除 SAT 检查绕过门槛。

主 agent 授权先验证以下单因素候选。保留 `fp_exception_flags`、泛型分类、全部异常公式与普通原语；仅将异常构造改为 `isla_bool_to_bit(inexact) @ isla_bool_to_bit(underflow) @ isla_bool_to_bit(overflow) @ isla_bool_to_bit(divide_by_zero) @ isla_bool_to_bit(invalid)`，五个 getter 分别读取固定 bit 0–4 并比较 `0b1`，ISA 包装直接拼接 `e[0] @ e[1] @ e[2] @ e[3] @ e[4]`。这仍复用 Sail 的异常类型与既有位序；用户要求不强制每次都经 `fp_eflag_*` 常量构造。上文 ITE/OR 和掩码构造适用于第一候选，若本替换获验证，现行实现以本节修订为准。

A/B 首先在仓库外源码副本执行 strict 编译、32 种 flags 组合和分类合同，再由同一运行器、同一真正未知输入比较 Add 单项及整个 f16 批次。保留原候选失败或超时记录；确认构造替换有效后再复验三格式和异常结果，重新冻结模型与生成正式候选。此阶段尚不将 A/B 假设写作性能修复 PASS。

后续同一 D 小模型、同一运行器、同一真正未知 `f16Add` RM3 输入的结果为：A 67.28 秒，B 48.38 秒，C0 0.05 秒，C1 0.05 秒，均 SAT 且仅一条完成路径。C0 保留泛型格式拆分与原生 RM，只恢复内部 Bool record 和旧的最终 ISA 拼接；C1 在 C0 基础上只增加最终一次 `fp_exception_flags` 转换与 ISA 位序映射。C0/C1 的 IR SHA-256 分别为 `37578a72703f8a0e93c4043caf0e0795829b571320533295def31dd14020f3f9`、`eb1fb6af42dfa566fab588ac5145e72a75542fbc6581769730ec90c4ff6a6cba`。源码与原始日志均已独立复核。这个单项对照支持保留泛型拆分并撤销内部反复 Bool/BV 打包；它不是全量性能或数值验收。

C1 被审定为最终实现方向：内部类型沿用 `ieee_fp_exceptions`，构造名称改为 `ieee_exception_facts`；`ieee_pack_shared_flags` 位于 `sail-riscv/model/core/ieee_fp_exceptions.sail`，RISC-V 包装只调用该通用转换并按 ISA 位序排列。命名与位置调整后须重新冻结源码、完成完整动态门槛，再生成最终 V128 IR；A/B 原候选均不切入主树。

## C1 最终源码冻结审查

最终命名与位置已落实。独立逐字核对确认主源码与 C1 快照一致：共享库 SHA-256 为 `d80c4aabcc40f6c0de5aad439aab24a012de51a98ec1a3669ff4a52a781c9bf6`，公共 RISC-V 包装 SHA-256 为 `ee9ba560fb4acb70ed664593da95a52657dfef9bd6643ed830a1d4a4d5b0a881`。

以上归一化脚本以 `TYPE_REUSE_SOURCE=sail-riscv`、`TYPE_REUSE_VARIANT=c1` 运行，确认 58 个原有异常函数、34 个 record 的五参数表达式、三个格式包装和 190 条 native 声明均只有预期变换。泛型分类、record 构造与 getter、共享 flags 出口及 RISC-V 反序已人工复核。允许集成人冻结该源码并生成最终 V128 IR；完整数值、未知输入和指令回归仍须针对最终候选分别验收。

命名调整后的隔离类型 IR SHA-256 为 `66f5cda3f7d3823703627be9562e46a70186f723276861511e8b0cdfe6461d04`，32 种 flags 组合、36 个分类特殊值和 3 个未知分类入口的原始通过日志已复核。f16 小模型 IR SHA-256 为 `e797c9e4e8fb3832068833936c1dbc51ba1dbaea62a9099c16fc998b8baac344`，90 条未知输入逐项满足单完成路径、SAT 与普通函数进入，耗时 0.61 秒。该数据确认已审命名版本的 f16 小模型门槛，完整 V128 候选的 277 项仍须独立重跑。

## 最终 C1 V128 候选复核

最终 V128 IR SHA-256 为 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`，完整生成退出 0；模型 manifest SHA-256 为 `1458881ee1154470f33c7c5d1f4ec103fea60c4cddf7cf72e76ea56509700450`，165 份模型文件已独立核对为冻结源与当前主源码一致。相对旧 `c9e1bfe2…`，新增 12 个、移除 15 个函数均为预期分类与事实接口变化；归一化后 71 个现存函数变化仅含 70 个浮点函数及 BF16 所在 `execute`。全部保留函数声明的签名、其余类型与全局内容不变。

该最终 IR 的完整 277 项未知入口已重跑，输入清单与每条结果逐项、逐名、逐序一致：f16/f32/f64 分别 90/96/91 项，全为一条完成路径、SAT、普通函数进入，耗时分别 5.25/5.31/5.25 秒。67 个 helper 的具体样例、估算体 350+1618+420 例、旧函数体 39+24 例及 Legacy 35 例的输入数量、通过日志和 20 项来源哈希均已独立复核。测试包装 IR 保留最终候选的完整字节前缀，未替换其函数体。

最终候选的 BF16 LMUL 十例均通过真实编码及状态差异 UNSAT 检查；79 份严格配置除预期 IR 哈希外无结构变化，132 个 region 与 22 个锚点校验通过。上述结论仅覆盖列出的检查：277 项证明执行路径性质，具体差分与指令样例证明其受测输入；不能宣称任意浮点输入等价或 E 全阶段通过。指令矩阵、正式切换和官方入口的最新结论由[状态摘要](status.md)与[实施记录](implementation.md)维护。

最终非访存矩阵亦完成独立复核：摘要 SHA-256 为 `9f4fccb7c3fb973afbee2dd491e4c56f2135d556b35f6ad590f957628d7396f5`，24 组输入与输出各自哈希、实际 IR/运行器/配置绑定均匹配。1509 行结果逐项对应原输入的名称、clause、编码及预期状态；全为单执行路径、SAT、差异 UNSAT、结构检查通过与 `Retire_Success`，clause 集合恰为所列 77 项。由此放行最终 IR 与 79 份严格配置同批切换；官方旧 IR 的完整入口批次和普通 `make solve` 的未完成结果保持独立，不借此改成通过。
