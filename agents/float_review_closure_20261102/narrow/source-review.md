# 六个窄整数适配器：源码阶段记录

基线模型提交 `6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a`。本轮只修改 `.worktree/runner-float/sail-riscv/model/extensions/V/vext_fp_utils_insts.sail` 的六个 SYMBOLIC `_pure` helper；同一模型子模块另有 `FD/fdext_regs.sail` 的其他 owner 修改，本记录不评价该文件。没有提交、推送或生成 IR。

目标文件基线 SHA-256 为 `34191de93086708b44f552606b39878e1ad68be07c67fb2321eb7bec1b1172e1`，修改后为 `2c6042a67c1798e746178725ab42a3cf2ff9c1df5b4552a18bcb1e1757ec3564`；[单文件差异](source.patch) SHA-256 为 `a49ee464cdca06dc2f62f655d2831f973e50357785b3cd92abe3025395881867`。该文件 `git diff --check` 退出 0。

三个有符号 helper 在 overflow 真臂按 `sig32[31]` 分到负饱和与正饱和，正常臂原样返回上游 `flag` 和低位。三个无符号 helper 在 overflow 真臂返回全 1 和仅 NV；正常臂同样原样返回上游值。饱和臂替换 flags 为 `0b10000`，没有与上游 flags 做 OR。普通 Sail helper 未改。`VFUNARY0`/`VFNUNARY0` 调用点均在既有 `if mask[i] == 0b1` 内，新增控制仍由该活动 lane 门控；没有改 caller、lane OR 或上游转换接口。

## 位向量证明

运行 `python3 agents/float_review_closure_20261102/narrow/prove_equivalence.py`，调用 `.tmp/z3-official-20261102/install/bin/z3`（官方 `1fd1d3613c1f34c4dff36cba3209b2234f6c6d2b`）。[结果](equivalence.json)与每个 helper 的 `.smt2` 保存于本目录。六个 helper 共 33 个检查均符合期望：每项旧双 ITE 返回式与新分支成对返回式不等的查询为 `unsat`；新式与普通 helper 的有符号上下界／无符号上界表达式不等的查询亦为 `unsat`。符号变量为任意 `sig32:bits(32)` 和任意上游 `flags:bits(5)`，包括含 NX/OF/UF/DZ/NV 的所有旧 flags；另用 `sat` 查询确认各方向和边界可达于该位向量层。

证明的边界是下游窄适配器：它不证明某个浮点位模式一定产生指定的 `sig32`，也不代替编译、IR CFG 或动态 oracle。源码核对 `softfloat_symbolic_f16.sail`/`softfloat_symbolic_f32.sail` 的 I32/Ui32 包装：invalid 时先判断 NaN，负 NaN 仍选正端点，因此本 helper 的符号饱和不会把负 NaN 误判为负端点。上游包装的单独控制及完整测试由其 owner 验收。

一次非冻结源码的严格 SYMBOLIC `--just-check` 使用 Sail 0.20.1、`-D SYMBOLIC --strict-var --strict-bitvector --strict-exponentials --require-version 0.20.1 --all-modules --just-check --config isla/ir/provenance/rv64d.json riscv.sail_project`，退出码 0；[日志](symbolic-check.log)保留。运行时其他 owner 同时修改 `core/ieee_fp_exceptions.sail`、`FD/fdext_regs.sail` 与三个 `FD/softfloat_symbolic_f*.sail`，所以它不是最终提交源的正式 strict PASS。主 agent 将在冻结集成提交后统一检查，不复用本轮退出码签 IR 或动态。

## 待逐项验证的实际输入边界

| helper | 有效边界与特殊输入 | 期望出口 |
| --- | --- | --- |
| f16→i8 | `127`、`-128`；`128`、`-129` | 前二正常；后二各自正/负 NV 饱和 |
| f16→i16 | `32752`、`-32768`；`32768`、`-32800` | 前二正常；后二各自正/负 NV 饱和。f16 在该量级的相邻有限值间距为 32 |
| f32→i16 | `32767`、`-32768`；`32768`、`-32769` | 前二正常；后二各自正/负 NV 饱和 |
| f16→ui8 | `255`、`256`；`-1`、`±Inf`、正/负 NaN | 正越界 NV→`0xff`；负输入经上游饱和 0，NaN 与正 Inf 经上游饱和最大值 |
| f16→ui16 | 最大有限 `65504`；`+Inf`、正/负 NaN、`-Inf`、`-1` | `65504` 正常；真溢出臂由上游 NaN/+Inf 饱和触发。f16 无正有限数超过 `65535` |
| f32→ui16 | `65535`、`65536`；`-1`、`±Inf`、正/负 NaN | 上界两侧、负输入上游饱和及特殊值分别验证 |

每项还需按实际 opcode 验五种普通 RM 与固定 RTZ、范围内非精确结果及原 flags、溢出时仅 NV、活动/屏蔽 lane、`vl=0`、多 lane flags OR 和目标位。IR 阶段必须核新增 Jump 对饱和出口的真实支配关系；动态阶段需固定模型/IR/配置/官方 Z3 与完整 Clause 预算。当前这些仍为待验证，不能写 PASS。
