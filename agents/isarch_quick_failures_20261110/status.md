# isarch 快速失败修复：状态摘要

| 项 | 状态 |
| --- | --- |
| 阶段 | 四类修复已提交（isla `fix/isarch-quick-failures` 9a4f5c91）；剩 CPOP/CPOPW 超时、LOAD_FP（需改 IR 生成）、浮点 helper（待用户定方向） |
| 方案 | [plan.md](plan.md)；诊断报告 [diagnosis-20261110.md](diagnosis-20261110.md) |
| 工作树 | `.worktree/isla-quickfail-20261110`，分支 `fix/isarch-quick-failures` |
| 验证 | 逐 clause 结果见 [after-fix-20261110.md](after-fix-20261110.md)：原 Poison 类 37/39（34 finished、3 不适用）、无编码类 10/10 不适用、未完成路径类 22/22 finished；Claude 复跑 isla-lib 单元测试 815 通过；`make solve-MRET` 退出 0 |

## Z3 升级（2026-11-10）

- 官方最新提交 `d6c9b4fbb31cb76e35cc325dd7e64b7c26c7d70f`（2026-11-09），版本号 5.4.0.0。源码与构建在 `/data1/baiyifan/build/z3-latest`，Release + Ninja，安装到 `~/.local/opt/z3-official-d6c9b4fbb`。`z3 --version` 输出 `5.4.0 … build hashcode d6c9b4fbb…`。
- 旧库为 `~/.local/opt/z3-official-1fd1d3613`（5.3.4）。

## 新 Z3 对 Poison 的初步复现

isarch 取 daf61c04 源码，链接 Z3 5.4.0（构建目录 `/data1/baiyifan/build/isarch-z3-540-target`）；IR、配置同全量实测；参数为 `--path-merging -T 32 --smt-timeout 1m`；输出在 `/data1/baiyifan/build/z3-540-poison-check/`。

| clause | `--tastic qfaufbv` | `--tastic default` |
| --- | --- | --- |
| ADDIW | Poison，exit 1（4.9 s） | finished，exit 0，生成用例 |
| CLZ | Poison，exit 1（6.0 s） | finished，exit 0 |
| RTYPE | Poison，exit 1（44.7 s） | 未试 |

结论：换新 Z3 不能消除 Poison。它跟 qfaufbv tactic 有关：`src/isarch/exec.rs:315` 的译码回环对求解结果取值，拿到的不是具体值。根因由 Codex 诊断确认。

## 诊断结论（Codex，2026-11-10）

| 类 | 根因 | 修法（已派） |
| --- | --- | --- |
| Poison 39 项 + 未完成路径 22 项 | 前态没有用架构合法域：不支持 H 时仍可取虚拟特权，SXL/UXL 可取 00/11，MPRV 下 MPP 可取保留值 2。Sail 抛内部异常后经 `arbitrary` 返回 Poison。与 Z3 版本和 tactic 无关；default 能成功只是选了别的见证值 | isarch 默认启用现有 `Rv64Domain`，域值取自模型静态能力；Poison 带上异常出处 |
| 无合法编码 10 项 | AES32 四项、Zcf 四项、C_JAL 只在 RV32 合法；BITYPE 依赖 Zibi，本配置关闭了实验扩展 | 编码域为空时报告“本配置不适用”，退出 0 |
| LOAD_FP panic | `word_width={1,2,4,8}` 在 IR 里退化为无范围的 `%i64`，负宽度进入 `zeros(8*width)` | 执行前带入编码域约束，保留 nat 断言 |
| 浮点 helper 缺失 31 项 | 当前 IR 来自官方 sail-riscv `cbb4766f`，67 个 `riscv_f*` helper 只有声明。旧 Rust 分发器已被 `e4e6835b` 删除，且有舍入和 flags 错误，不能原样恢复。精确的 Sail 函数体在模型提交 `d79d8b32` 里 | 待用户定方向 |

另外，诊断确认 V 浮点也走同一批缺失 helper：定向 `vfadd.vf` 40 秒就报 `riscv_f32Add does not exist`。原 2h 超时没有暴露这一点，是因为最终错误汇总被超时遮住了。

## 第一轮修复（Codex，2026-11-10，未提交）

- Z3：`isla-lib/src/smt.rs` 一次性检测运行时版本，最低 5.4.0.0；`scripts/run.mk` 默认前缀和 README 已更新。
- 前态：isarch 默认启用现有 RV64 合法初态域。抽测 RTYPE（10 条用例）、ADDIW（1 条）、AMO（1424 条）均完整完成，未完成路径 0。CSRReg 不再 Poison，但缺少 `get_16_random_bits`（`zkr_control.sail:35`）。
- 回归：C_ADD、C_BEQZ、FMAXM_D、FLI_S 的用例数与原批次相同。
- 不适用状态：单元测试通过，批量未测。
- LOAD_FP：仍 panic。原因是 IR 里 `width_enc_forwards`、`float_load_store_width_supported` 把最后一个 `width=8` 分支编成了默认分支，`{1,2,4,8}` 的类型约束在 IR 里丢了，执行前的编码检查也补不回来。要修只能改 IR 生成（isla-sail），待用户决定。

## 第二轮与提交（2026-11-10，isla `9a4f5c91`）

- `get_16_random_bits`：复用 `undefined_bitvector(16)`，每次返回新的自由值。CSRReg、CSRImm 各生成 859 条用例，没有错误，也没有未完成路径。
- 不适用共 13 项：AES32 四项、Zcf 四项、C_JAL、BITYPE（本配置关闭实验扩展）、FMVH_X_D、FMVP_D_X（要求 32 位模式）、LPAD（`Ext_Zicfilp` 在当前配置下未启用）。全部由编码映射判空得出，没有 clause 白名单。
- 仍未通过：CPOP、CPOPW 在 10 分钟外限内超时（卡在 `count_ones` 结果的 `%i → %i64` 附近，原因未查明，正式口径是 2h，未测）；LOAD_FP 仍 panic。
- 诊断输出 `diag/` 约 19G，留在工作树里，未提交。


## 合并前审查补记（2026-11-10）

本轮已在对应工作树完成未提交修复，原提交的历史验证不自动覆盖修复后源码。限定审查、TDD、测试前后对比和合并取舍见 [两分支审查](../isla_premerge_review_20261110/review.md)。无新增测试失败，顶层仍有原有缺 IR 七项失败；未跑 isarch 长时实测。
