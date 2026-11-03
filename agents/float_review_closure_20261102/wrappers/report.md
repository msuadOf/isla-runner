# FP→整数与 ROD wrapper 实施证据

## 固定边界

基线模型：`6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a`。只改 `.worktree/runner-float/sail-riscv/model/extensions/FD/` 下三个 `softfloat_symbolic_f*.sail`；未改根 dirty 模型或其他 owner 文件，未提交、推送或生成 IR。

| 文件 | 基线 SHA-256 | 修改后 SHA-256 |
| --- | --- | --- |
| `softfloat_symbolic_f16.sail` | `715795790c0efb100806c0a82195e137c4de66c4a9614baac9ee2b0b333a0646` | `63c22bc512222b9697a5d7bf544f4260074eb5cbd2b62cbd716e7cd8917a5877` |
| `softfloat_symbolic_f32.sail` | `ce65c868e34c3e5a1d9b1806bef3f48d7bba7b5ff18cd7cfdfe584975b716b65` | `eb9d4883a239700a78f1969c879ac3857f7b8cb2d9290098c4d06ca769d94ac1` |
| `softfloat_symbolic_f64.sail` | `eeb3de73c0bc6de5f07e582db5390b673e28c7c0f3d04a077a85e279695c30b5` | `0cd758949af3ed2b13bc519087aff3fa87cf9c080d79b53efe1bebc7108b14ed` |

## 逐函数结果

| 函数 | invalid NaN（含负 NaN） | invalid 非 NaN 负值 | invalid 非 NaN 正值 | valid |
| --- | --- | --- | --- | --- |
| `riscv_f16ToI32` | `0x7fffffff` | `0x80000000` | `0x7fffffff` | 原 signed32 candidate |
| `riscv_f16ToUi32` | `0xffffffff` | `0x00000000` | `0xffffffff` | 原 unsigned32 candidate |
| `riscv_f16ToI64` | `0x7fffffffffffffff` | `0x8000000000000000` | `0x7fffffffffffffff` | 原 signed64 candidate |
| `riscv_f16ToUi64` | `0xffffffffffffffff` | `0x0000000000000000` | `0xffffffffffffffff` | 原 unsigned64 candidate |
| `riscv_f32ToI32` | `0x7fffffff` | `0x80000000` | `0x7fffffff` | 原 signed32 candidate |
| `riscv_f32ToUi32` | `0xffffffff` | `0x00000000` | `0xffffffff` | 原 unsigned32 candidate |
| `riscv_f32ToI64` | `0x7fffffffffffffff` | `0x8000000000000000` | `0x7fffffffffffffff` | 原 signed64 candidate |
| `riscv_f32ToUi64` | `0xffffffffffffffff` | `0x0000000000000000` | `0xffffffffffffffff` | 原 unsigned64 candidate |
| `riscv_f64ToI32` | `0x7fffffff` | `0x80000000` | `0x7fffffff` | 原 signed32 candidate |
| `riscv_f64ToUi32` | `0xffffffff` | `0x00000000` | `0xffffffff` | 原 unsigned32 candidate |
| `riscv_f64ToI64` | `0x7fffffffffffffff` | `0x8000000000000000` | `0x7fffffffffffffff` | 原 signed64 candidate |
| `riscv_f64ToUi64` | `0xffffffffffffffff` | `0x0000000000000000` | `0xffffffffffffffff` | 原 unsigned64 candidate |

12 项均保留原 RM 解码、`round_to_integral`、`ieee_fp*_to_int_exceptions`、`fp*_to_*` candidate 和 `riscv_pack_ieee_flags`。改动仅将原 ITE 选择变为 `if invalid` 内 `if NaN` 再按符号选择；valid 直接返回原 candidate。NaN 优先，故负 NaN 不会误落负饱和端点。NV/NX 等 flags 仍由原 facts 唯一决定，与所选结果同一次调用返回。

| 函数 | ROD `rm=0b110` | 普通 RM `0..4` | NaN 出口 |
| --- | --- | --- | --- |
| `riscv_f32ToF16` | 只执行 `ieee_rod32_to_16`，其 flags 与 bits 同臂返回 | 只解码合法 RM、执行 `fp32_to_fp16` 与原 exceptions | ROD 用原 `ieee_is_nan(a)`，普通用原 `fp16_is_nan(result)`，均返回 canonical NaN |
| `riscv_f64ToF32` | 只执行 `ieee_rod64_to_32`，其 flags 与 bits 同臂返回 | 只解码合法 RM、执行 `fp64_to_fp32` 与原 exceptions | 两臂保留原 `ieee_is_nan(a)` canonical NaN 判断 |

旧 f32 普通候选在 ROD 模式下为避免 native 非法 RM 而替换为 RTZ；现 ROD 臂不计算普通候选，`riscv_f32_to_f16_normal_rm_bits` 保留供既有 `test/symbolic_fp/f32_c.sail` 探针使用。该 helper 的表达式未变，只更新注释。没有新增跨 owner 接口或更改函数签名。

## 源码与选择证明

`python3 agents/float_review_closure_20261102/wrappers/prove_selection.py`：退出 0，12 个整数 wrapper 和两处 ROD 模式共 13260 个控制选择组合。脚本从固定基线 `git show 6202e23:<path>` 核对每项原 rounded/candidate/facts 表达式及原选择结构，再检查新分支结构；穷举 invalid、NaN、符号、候选及 5 位 flags 的结果等价。ROD 核对普通与 ROD 分支的 helper、RM decoder 和同臂 flags/bits；模式选择对合法 `RM=0..4,6` 逐项等价。`git diff --check` 退出 0。独立审查证据见 `../review/model/wrappers-source-review.json`，签的是源码语义，不含 IR/动态。

从 `.worktree/runner-float/sail-riscv/model/` 运行 Sail 0.20.1：`sail [可选 -D SYMBOLIC] --strict-var --strict-bitvector --strict-exponentials --require-version 0.20.1 --memo-z3-path ../../../../agents/float_review_closure_20261102/wrappers/sail_smt_cache --all-modules --just-check riscv.sail_project`。最终三文件哈希下，SYMBOLIC 和普通两模式各退出 0；日志分别为 `typecheck-symbolic-final.log`（SHA-256 `8d76d256e99329fd5d1bd42efc2eb8996e738b8d2cf881fa33bb1aa0f3d244b7`）与 `typecheck-ordinary-final.log`（`c0f4da7bbe623179c2ec7156a490776f85361e0262038e4e5c996907bbe76df1`）。这是无单独 config 的全模块类型检查，其他 owner 同时编辑共享工作树；不把它算作四配置冻结源严格生成或 IR 验收。

## 后续实际见证

待完整 IR 与动态阶段使用真实输入：f16 `0x7c00/0xfc00`（±Inf）、`0x7e00/0xfe00`（±qNaN）和最大有限 `0x7bff=65504`。f16 有限数不可能越过 i64 范围；其 i64 invalid 两端以 NaN/Inf 见证，不虚构有限越界。f32 可用 `0x4f000000`（+2³¹）、`0xcf000001`（小于 −2³¹）、`0x5f800000`（+2⁶⁴）；f64 可用 `0x43e0000000000000`（+2⁶³）、`0xc3e0000000000001`（小于 −2⁶³）、`0x43f0000000000000`（+2⁶⁴）。ROD 可用 f32 `0x3f800001`、f64 `0x3ff0000000000001` 对照相应 1.0 精确输入，另需 NaN/Inf/零/溢出/次正规及五 RM 的 flags/bits 配对。

上述有限边界位串用 Python `struct.pack('>e'/'f'/'d', value).hex()` 核对编码；尚未执行 SoftFloat oracle。本报告未将准备值记为动态 PASS；IR CFG、四配置严格生成、完整 Clause 与动态结果均待主任务后续验证。
