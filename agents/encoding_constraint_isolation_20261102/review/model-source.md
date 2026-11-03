# f16→i16 饱和出口：独立源码签收

结论：源码语义审查通过，无阻断，可提交并开始四配置 IR 生成。该结论不代替生成 IR 或完整 Clause 验收。

受审基线：Sail-RISC-V `a9fd9476fc1bf471070a38e01ee9233d10d742d3`。目标为 `.worktree/runner-float/sail-riscv/model/extensions/V/vext_fp_utils_insts.sail`，受审文件 SHA256 为 `34191de93086708b44f552606b39878e1ad68be07c67fb2321eb7bec1b1172e1`。

实际 diff 只有注释修正及 `riscv_f16ToI16_pure` 最终两个同条件 ITE 改成一个 `if overflow`，调用、溢出条件、截断、限幅方向、flags 和返回类型均未变。`nvFlag()` 是纯常量 0b10000，`limit` 的符号位选择仍为原 ITE，故两臂的数值与异常位逐点相同。

当前 `vext_fp_insts.sail` 的 VFUNARY0 两个调用点都在 `if mask[i] == 0b1` 活动 gate 内；mask 由 `init_masked_result` 生成。不活动 lane 保留该函数准备的初始结果，不会先做该转换。未改其他宽度的转换、flags changed 或异常原因分类。此前“所有窄整数适配器均使用 ITE”的注释已同步修正。

剩余：严格四配置生成、实际 CFG 的 overflow Jump、活动 gate 支配关系以及新 Isla 下完整 Clause 与见证检查。

独立数值检查：`model-equivalence.smt2` 以任意32位 `sig` 与任意5位 `flags` 比较新 overflow/limit 公式和原普通 helper 的有符号上下界饱和。使用官方 `z3-official-1fd1d3613/bin/z3` 返回 `unsat`（见 `model-equivalence.log`），即不存在数值或 flags 反例；该检查不替代 FP16→I32 本体及实际路径覆盖验收。
