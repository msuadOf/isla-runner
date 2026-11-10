# Sail-RISC-V 按模型功能类别重组提交（2026-10-19）

用户授权基于 `4f2ac293654a02db26dac5055be7f93fd6e3141e` 另建提交链，以 `model/` 的功能种类为边界，不按测试目录或单条指令拆分。

- 分支：`feat/sail-riscv-by-category-20261019`。
- 工作树：`.worktree/sail-riscv-by-category-20261019`。
- HEAD：`3ea3cbaf599b0b210a365eac50736f097b4b2337`。
- 来源：`595c1a0bc43d49bc97e3d959f99fc351ffc33f6b` 至 `755fea6ed7ded07013ebc7f333f5afa3f831320c`，包含起点，共23提交。
- 结果：11个模型功能提交，加1个忽略规则提交，共12个提交。配套C++、构建及测试文件随功能保留，不删除测试，也不以其目录作为分类边界。
- 最终完整tree：`6fafcbc406156ee275bcf301e6db1743eb417a0f`，与 `755fea6e` 完全相同；相对基线151个变动路径完整保留。没有额外语义修改或源码修复。
- 原 `sail-riscv/` 和10-16拆分工作树的HEAD、分支、索引原始字节、两层补丁、修改文件及未跟踪集合均保持；旧分支全部保留，父仓索引及gitlink保持。新工作树干净，未push。

## 提交索引

| 序号 | Commit | 功能 | 原提交来源 |
| --- | --- | --- | --- |
| 01 | `f4073409` | chore(gitignore): 明确构建产物和缓存的忽略范围 | `595c1a0b` |
| 02 | `d9db8dae` | fix(assembly): 修正FLI常量和BF16指令的汇编文本 | `a07322ea` |
| 03 | `942062de` | perf(symbolic): 用公共条件选择接口减少标量浮点分叉 | `a3e7ee65`、`b4b3ddce`、`0b4ad59f` |
| 04 | `31b76d99` | fix(registers): 补齐快速浮点和向量寄存器访问的状态副作用 | `78ff5e0c`、`b3d3fe2d` |
| 05 | `bfa54ad6` | perf(decode): 合并编码匹配条件以减少符号译码分叉 | `099c7c37`、`11c27ceb`、`0063f07c` |
| 06 | `70e3890b` | refactor(float): 统一Sail浮点数值接口和IEEE异常实现 | `fff56db2`、`9206c494`、`d38681d3`、`738cd8bc` |
| 07 | `795bfdf1` | fix(V): 统一普通浮点与BF16指令的SEW合法性检查 | `c348bbb1`、`82a2bc4c:加宽归约SEW8拒绝`、`755fea6e:两条BF16转换SEW16检查` |
| 08 | `c3f80279` | perf(V): 统一不分叉的辅助判断、源掩码和纯浮点工具 | `82a2bc4c`、`73882f0b` |
| 09 | `8b5d6844` | perf(V): 用纯计算和掩码选择统一浮点逐元素执行 | `09846e41`、`7b82be2f`、`c1c79b1d` |
| 10 | `6f5ba4bd` | perf(V): 保持归约顺序并用条件选择合并浮点结果与异常 | `ed2217c1` |
| 11 | `d2c6dcd3` | fix(bfloat16): 无活动元素时不累计标量转换异常 | `83af2352` |
| 12 | `3ea3cbaf` | perf(bfloat16): 用纯转换和掩码选择执行BF16向量指令 | `755fea6e` |

## 两处跨原提交的修复归组

第07提交除了原 `c348bbb1`，还提前纳入两项合法性变化：

1. `82a2bc4c` 原本在改写 `illegal_fp_widening_reduction` 时才通过 `illegal_fp_reduction` 间接拒绝SEW8。现在第07提交先将旧表达式中的 `valid_fp_op` 改为 `valid_fp_standard_op`，第08提交再进行等价的辅助函数复用和Bool表达式优化。
2. `755fea6e` 原本在增加BF16符号执行实现的同时，给两条转换的普通路径补上 `SEW != 16` 拒绝。现在第07提交先补普通路径检查，第12提交只在其上增加SYMBOLIC实现和数据选择优化。

后续原补丁的父树相应调整，避免重复引入这些合法性变化；最终tree逐字相同。FPR/VPR状态修复合为一类，三个译码优化合为一类，共用浮点接口/异常公式/包装/minmax合为一类，普通向量逐元素执行合为一类。归约的顺序依赖、BF16无活动元素语义修复和BF16优化仍分别可审阅。

## 本轮验证和限制

- 11个精确模型中间tree各执行普通及SYMBOLIC全模型严格类型检查，共22次退出0。使用既有补丁版Sail 0.20.1；实际命令、每层tree、耗时和日志SHA-256见 [commits.json](regroup-20261019/commits.json)，工具版本见 [toolchain.json](regroup-20261019/toolchain.json)。类型检查期间当前工作树与暂存树一致，没有提前放入后续代码。
- 命令均在对应精确工作树的 `model/` 执行：`sail --no-warn --no-color --strict-var --strict-bitvector --strict-exponentials --require-version 0.20.1 --memo-z3-path <本轮普通或SYMBOLIC缓存> --all-modules --just-check [-D SYMBOLIC] riscv.sail_project`。
- 最初两个冷缓存检查在约135秒时主动中断，退出-15，不记PASS；核对暂存tree后，复制此前同工具链约束缓存到本轮独立文件再执行。原中断记录及日志保留在 [interrupted-cold-cache.json](regroup-20261019/interrupted-cold-cache.json) 和 `logs/02-cold-cache-*.log`；缓存来源/哈希见 [memo-seed.json](regroup-20261019/memo-seed.json)。
- 最终完整tree与来源tree相等，提交数、准确基线、所有旧分支、两个旧工作树、原索引/文件和父gitlink检查通过。逐项结果见 [final-audit.json](regroup-20261019/final-audit.json)。
- 空白检查仍报告原有Sail文件EOF空行和冻结patch上下文空白；为保持完整tree一致未改写。相应非零退出和日志均保留，不声称空白检查通过。
- 本轮未重新生成完整IR，未执行数值差分、C++构建、全指令求解或硬件验证。来源最终tree与10-16最终tree相同，但历史结果仍按 [10-16交付](commits-20261016.md) 的工具链/配置和范围理解；新的中间tree只获得本轮22次类型检查结论，不能自动继承旧21层的全部验证。

## 查看命令

从根仓库执行：

```sh
git -C .worktree/sail-riscv-by-category-20261019 log --reverse --oneline 4f2ac293..HEAD
git -C .worktree/sail-riscv-by-category-20261019 log --reverse --stat 4f2ac293..HEAD -- model/
git -C .worktree/sail-riscv-by-category-20261019 diff 755fea6e HEAD
```

最后一条应无输出。具体模型文件清单见下文，配套文件的完整清单保存在 `commits.json`。

## 每类模型文件

### 02 `d9db8dae` fix(assembly): 修正FLI常量和BF16指令的汇编文本

修正FLI.H/S/D立即数的文本表示，以及四条BF16指令的寄存器分隔；保持编码索引。

- `model/extensions/FD/zfa_insts.sail`
- `model/extensions/bfloat16/zvfbfmin_insts.sail`
- `model/extensions/bfloat16/zvfbfwma_insts.sail`

### 03 `942062de` perf(symbolic): 用公共条件选择接口减少标量浮点分叉

提供公共ite及不短路Bool接口，并集中接入标量浮点的数据选择：异常累计用完整mstatus的ITE，changed用通用等值表达式，NaN拆箱用ITE，取负翻转符号位。保持原条件更新的架构状态关系和普通异常累计实现。

- `model/extensions/FD/dext_insts.sail`
- `model/extensions/FD/fdext_regs.sail`
- `model/extensions/FD/fext_insts.sail`
- `model/extensions/FD/zfh_insts.sail`
- `model/prelude/ieee_fp_primops.sail`
- `model/riscv.sail_project`

### 04 `31b76d99` fix(registers): 补齐快速浮点和向量寄存器访问的状态副作用

集中修复快速FPR/VPR访问遗漏的检查、表示转换、Dirty状态和写回调，保持与普通访问路径一致。依赖前面的公共符号接口。

- `model/extensions/FD/fdext_regs.sail`
- `model/extensions/V/vext_regs.sail`

### 05 `bfa54ad6` perf(decode): 合并编码匹配条件以减少符号译码分叉

将AMO、向量整寄存器移动/扩展和浮点一元子字段匹配作为一类译码优化，保留各自的完整编码与合法性守卫。依赖公共符号接口。

- `model/extensions/A/zaamo_insts.sail`
- `model/extensions/V/vext_arith_insts.sail`
- `model/extensions/V/vext_fp_insts.sail`

### 06 `70e3890b` refactor(float): 统一Sail浮点数值接口和IEEE异常实现

把C++数值适配、IEEE异常/RM公共公式和67个浮点包装切换组织为同一功能；标量与向量min/max复用统一规则。配套构建与历史测试随功能保留。依赖公共符号接口；完整构建仍需既有Sail FP/RM lowering补丁。

- `model/CMakeLists.txt`
- `model/core/ieee_fp_exceptions.sail`
- `model/core/softfloat_interface.sail`
- `model/extensions/FD/dext_insts.sail`
- `model/extensions/FD/fext_insts.sail`
- `model/extensions/FD/fp_minmax.sail`
- `model/extensions/FD/softfloat_symbolic.sail`
- `model/extensions/FD/softfloat_symbolic_f16.sail`
- `model/extensions/FD/softfloat_symbolic_f32.sail`
- `model/extensions/FD/softfloat_symbolic_f64.sail`
- `model/extensions/FD/zfa_insts.sail`
- `model/extensions/FD/zfh_insts.sail`
- `model/extensions/V/vext_fp_utils_insts.sail`
- `model/prelude/ieee_fp_primops.sail`
- `model/riscv.sail_project`

### 07 `795bfdf1` fix(V): 统一普通浮点与BF16指令的SEW合法性检查

区分普通浮点和允许INT8转换的合法域，覆盖加宽算术及归约；BF16乘累加和两条转换仅接受SEW16。把原散落于辅助优化和BF16优化中的合法性修复提前集中，避免后续性能提交夹带此类语义变化。

- `model/extensions/V/vext_fp_insts.sail`
- `model/extensions/V/vext_fp_utils_insts.sail`
- `model/extensions/bfloat16/zvfbfmin_insts.sail`
- `model/extensions/bfloat16/zvfbfwma_insts.sail`

### 08 `c3f80279` perf(V): 统一不分叉的辅助判断、源掩码和纯浮点工具

公共辅助层用通用等值和严格Bool组合表达判断，提供快速源掩码及只返回值/flags的纯浮点工具，供后续逐元素和归约执行复用。加宽归约SEW修复已在前一提交，不在此处引入。依赖公共符号接口、统一浮点实现和SEW修复。

- `model/extensions/V/vext_control.sail`
- `model/extensions/V/vext_fp_utils_insts.sail`
- `model/extensions/V/vext_utils_insts.sail`

### 09 `8b5d6844` perf(V): 用纯计算和掩码选择统一浮点逐元素执行

普通向量浮点算术、FMA、比较、转换、开方、分类及move/merge按同一掩码选择方案组织；纯计算返回候选值和flags，仅活动元素贡献结果与异常，保留prestart/tail/mask规则。依赖前面的纯工具与掩码接口。

- `model/extensions/V/vext_fp_insts.sail`
- `model/extensions/V/vext_fp_vm_insts.sail`

### 10 `6f5ba4bd` perf(V): 保持归约顺序并用条件选择合并浮点结果与异常

归约按原lane顺序计算候选，用ITE选择累加状态并一次提交异常；保留逐步依赖和舍入顺序。因其语义区别于独立逐元素执行而单列。依赖纯浮点工具及源掩码接口。

- `model/extensions/V/vext_fp_red_insts.sail`

### 11 `d2c6dcd3` fix(bfloat16): 无活动元素时不累计标量转换异常

VFWMACCBF16_VF仅在存在活动元素时累计标量转换flags，修复零VL/全掩码/prestart情况下误置NV；独立保留正确性修复及配套文件。依赖BF16合法性检查。

- `model/extensions/bfloat16/zvfbfwma_insts.sail`

### 12 `3ea3cbaf` perf(bfloat16): 用纯转换和掩码选择执行BF16向量指令

BF16宽化转换的数据判断使用ITE，四条向量转换/乘加采用无副作用候选计算、掩码合成和统一异常累计。普通路径保留已有语义修复；两条转换的SEW16检查已提前归入合法性提交。依赖统一浮点实现、掩码接口和BF16无活动元素修复。

- `model/extensions/bfloat16/zfbfmin_utils.sail`
- `model/extensions/bfloat16/zvfbfmin_insts.sail`
- `model/extensions/bfloat16/zvfbfwma_insts.sail`
