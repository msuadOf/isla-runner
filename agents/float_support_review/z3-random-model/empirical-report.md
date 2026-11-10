# Z3 能否原生返回"随机满足赋值"——CLI 定向实测报告

- 日期：2026-09-28
- 执行方式：只读实验，全部用 SMT2 文件 + z3 CLI（无 z3py、无 pip 安装）
- 证据目录：`isla/target/float-solve-evidence/z3-random-model-experiments-20260928/`（每实验一个子目录，含生成脚本、逐 seed 的 .smt2/.out、summary.txt、distribution.csv）
- 议题背景：isla-lib（z3-sys 0.5.0）逐 case 枚举模型时，自由/弱约束 BitVec 变量（vl、浮点寄存器 payload）在返回模型里几乎恒为 0。用户主张"python 的 z3 solver 就能求出满足约束的随机数"，本报告用实测判定 Z3 是否能不靠 guess-and-check 直接返回随机满足赋值。

## 结论速览

1. **不能。** Z3 4.16 原生 `check-sat`/`get-value`（等价于 python 绑定 `Solver.get_value`，同一 libz3 C API）**不会**对自由/弱约束变量返回随机值：don't-care 变量由模型补全（model completion）恒填 0，与任何 seed/随机化参数无关（E2/E4/E5/E8 共 300+ 次求解全 0）。
2. **seed 无效**：`sat.random_seed`/`smt.random_seed` 跨 20 个 seed 不改变任何上述取值。
3. **搜索随机化仅对"直接参与位级约束"的变量有部分效果且不可控**：`sat.phase=random` 能把弱约束 vl（bvule vl 64）从恒 0 散开到 [0,64] 内 9 个不同值，但分布偏斜（0 和 64 占比最高）、非均匀、对被 UF 洗掉的变量（本项目 pure 函数形态）完全无效。
4. **`sat.phase_stochastic` 在 4.16 不存在**（`unknown parameter 'phase_stochastic' at module 'sat'`），实际机制是 `sat.phase=random`（或 `smt.phase_selection=5`）。
5. **唯一可靠机制是调用方采样 + assumption 注入（guess-and-check）**：`(check-sat-assuming ((= vl K)))` 对可行猜测 100% 命中且模型值即注入值；对不可行猜测诚实返回 UNSAT（域外 0/100），可直接构成重采样循环。用户观察到的"python z3 能求出随机数"只可能是这种（或等式断言后重解的）外部采样机制，而非 Z3 原生行为。

## 环境

| 项 | 值 |
| --- | --- |
| z3 CLI | Z3 version 4.16.0 - 64 bit（/home/linuxbrew/.linuxbrew/bin/z3） |
| isla 实际链接 | `libz3.so.4.16 => /home/linuxbrew/.linuxbrew/opt/z3/lib/libz3.so.4.16`（见 `z3-diagnostic-fc4ce-fvftype-20260927/evidence/ldd.txt`），与 CLI 同一安装 |
| 驱动脚本 | bash / python3 3.13（stdlib，仅生成 SMT2 与汇总，不依赖 z3py） |

## E1 基线确定性

配置：`case_e1.smt2`（弱约束 vl≤64、fp_reg 高 32 位=0、payload 无约束），连跑两遍。
输出（两遍逐位一致，`cmp` 通过）：`vl=payload=fp_reg=0x0`。
结论：z3 默认完全确定；连 fp_reg 这种"一半位被约束"的变量，自由的一半也全 0。

## E2 纯 don't-care（vl 仅出现在恒真式外的声明中）

配置：5 变体（仅变 `sat.random_seed` / 仅变 `smt.random_seed` / `sat.phase=random` / `sat.random_freq=0.05` / 三者组合）× 20 seed = 100 次求解。

| 变体 | vl 分布 |
| --- | --- |
| sat.random_seed 1..20 | `#x0` ×20 |
| smt.random_seed 1..20 | `#x0` ×20 |
| phase=random | `#x0` ×20 |
| random_freq=0.05 | `#x0` ×20 |
| 组合 | `#x0` ×20 |

结论：**model completion 与 seed 及全部随机化参数无关**，don't-care 的 BitVec 恒填 0。

## E3 弱约束 vl ≤ vlmax(64)

形式 u=`(bvule vl 64)`（无符号，vl∈[0,64]）、s=`(bvsle vl 64)`（题目原文有符号形态）。配置 C0 默认仅变 seed / C1 `sat.phase=random` / C2 `sat.random_freq=0.05` / C3 三者组合 / C4 `sat.completion=true`，各 12 seed。

u 形式 vl 分布（值:次数）：

| 配置 | 分布 | 零值占比 |
| --- | --- | --- |
| C0 默认+seed | {0:12} | 12/12 |
| C1 phase=random | {0:3, 3:1, 15:1, 20:1, 23:1, 28:1, 38:1, 42:1, 64:2} | 3/12 |
| C2 freq=0.05 | {0:12} | 12/12 |
| C3 组合 | {0:2, 15:1, 20:1, 28:1, 35:1, 38:1, 39:1, 42:1, 64:3} | 2/12 |
| C4 sat.completion | {0:12} | 12/12 |

s 形式：**5 种配置 60 次求解全部恒 64**（位爆破电路结构决定的退化常数，不是随机）。

结论：默认（含默认 `sat.random_freq=0.01`）下弱约束变量退化为常数；只有 `sat.phase=random`（C1/C3）能让**直接参与位级约束**的 vl 散开，但散开程度/分布由搜索路径决定，偏斜（0、64 权重最高）且对结构敏感（s 形式纹丝不动）；`sat.random_freq` 单独无效（公式太简单、无冲突时随机决策不触发）。

## E4 UF 包裹（本项目 pure 函数形态）

`(declare-fun isla_mask ((_ BitVec 64) (_ BitVec 64)) (_ BitVec 1))`，断言 `mask=isla_mask(vl,64)`、`mask=1`。UF 解释自由 ⇒ vl 对求解器是 don't-care。
结果：C0..C4 × 12 seed = **60/60 次 vl 全 0**（模型给 mask 补一个使 vl=0 成立的解释）。
结论：这正是本项目变量被"洗掉"后的实际形态——**任何 z3 参数都无法让 UF 洗掉的变量取非退化值**。

## E5 载荷变量（payload 只出现在 UF 参数位）

`isla_fp_add(payload_a, payload_b) = 0x3F800000`（f32(1.0) 位模式）。
结果：C0..C3 × 12 seed = 48/48 次 **payload_a、payload_b 同时全 0**。
结论：与 E4 同理，浮点寄存器载荷在 pure 函数包裹下恒 0，seed/phase/freq 无效。

## E6 对照·assumption 注入（vl guess-and-check）

对 E3/E4 约束随机猜 vl，`(check-sat-assuming ((= vl K)))`（注意 SMT-LIB 要求字面量列表，**双括号**；单括号会报 `unknown constant '='`）。每场景 100 采样（固定种子 20260928 可复现）：

| 场景 | 约束 | 猜测域 | SAT 命中 | 理论 |
| --- | --- | --- | --- | --- |
| S1 e3u 域内 | bvule vl 64 | [0,64] | **100/100** | 100% |
| S2 e3s 域内 | bvsle vl 64 | [0,64] | **100/100** | 100% |
| S3 e4 UF 形态 | mask=1(UF) | [0,64] | **100/100** | 100%（UF 吸收任何值） |
| S4 区间冲突 | 32≤vl≤64 | [0,64] | **47/100** | ≈33/65≈50.8% |
| S5 域外 | bvule vl 64 | [65,128] | **0/100** | 0%（全部诚实 UNSAT） |

演示：注入 `vl=37` 后 `get-value` 返回 `((vl #x...25) (mask #b1))`——命中后**模型值即注入值**。
结论：assumption 注入是可靠 oracle：可行即 SAT 且值受控，不可行即 UNSAT，无假阳性。

## E7 载荷类别命中（64 位随机位串注入）

| 场景 | 约束 | 命中 | 理论 |
| --- | --- | --- | --- |
| P1 仅 UF 参数位（E5 形态） | 无真实位约束 | **100/100** | 100% |
| P2 对照：最高位须为 1 | extract(63,63)=1 | **47/100** | ≈50% |

演示：注入 `payload_a=0xed12a4d9bd915a5c` → 模型原样返回该位串（payload_b 仍 0）。
结论：对全域随机 64 位位串，don't-care 载荷命中率 100%；真实位约束下命中率等于可行测度，可作为按目标分布采样的滤波器。

## E8 参数面（`z3 -pd` 抽取）

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `sat.phase` | caching | 取值含 `random`（4.16 的随机相位机制） |
| `sat.phase_selection`(smt) | 3 | 5=random（另一入口） |
| `sat.random_freq` | **0.01** | 随机 case-split 频率（默认非 0！） |
| `sat.random_seed` / `smt.random_seed` | 0 | seed；实测对模型取值无影响 |
| `sat.phase_stochastic` | **不存在** | 报错证据：`unknown parameter 'phase_stochastic' at module 'sat'` |
| `sat.completion` | false | 置 true + phase=random 跨 5 seed，don't-care 仍全 0 |
| `model.completion` / `model_evaluator.completion` | false | 置 true 后 don't-care 变量 get-value 仍 `#x0` |
| `nlsat.randomize` | true | 仅非线性 nlsat 通道，与 BV 无关 |
| `tactic.randomizer.seed`、`sls.random_seed`、`fp.spacer.random_seed` | 0 | 其它模块的 seed，不影响本场景 |

## libz3 版本注记

isla 链接的 `libz3.so.4.16` 与本实验 CLI 4.16.0 为**同一安装**，结论无迁移风险、直接适用。若未来更换 libz3 版本需注意：(a) 参数名漂移（`sat.phase_stochastic` 这类名字在不同版本间不存在/更名）；(b) 弱约束变量的退化常数由位爆破预处理结构决定（E3 s 形式恒 64），版本变化可能换成别的常数；(c) model completion 对 BV 填 0 的行为在 4.x 系列稳定，但建议用本目录脚本重跑复验。

## 总结论

- **"z3 能否原生返回随机满足赋值"——不能。** 自由/被 UF 洗掉的变量恒 0（model completion，seed/参数无关）；弱约束变量退化为电路结构决定的常数；`sat.phase=random` 只能让直接参与约束的变量散开，且分布不可控、对本项目实际形态（E4/E5）完全无效。
- **"python 的 z3 solver 就能求出满足约束的随机数"——判定不成立**：python 绑定走同一 libz3 C API、同一模型补全行为；能"求出随机数"的唯一途径是 python 侧自己先采样、再把样本作为等式约束/assumption 注入后求解——即 E6/E7 的 guess-and-check，随机性来自调用方而非 Z3。
- **对 isla-lib 的含义**：不要试图用 z3 参数（seed/phase/freq/completion）解决 vl/payload 恒 0；可行机制是外部采样 + `Z3_solver_check_assumptions`（z3-sys 有该绑定，C API 不受 SMT2 双括号语法细节影响）注入候选值：命中（SAT）即取注入值为模型值，UNSAT 则重采样，域外/冲突场景被诚实拒绝（E6 S5 0/100、S4 47/100）。

## 复现

```bash
cd isla/target/float-solve-evidence/z3-random-model-experiments-20260928
bash  e1_determinism/run_e1.sh
python3 e2_dontcare/run_e2.py
python3 e3_weak/run_e3.py
python3 e4_uf/run_e4.py
python3 e5_payload/run_e5.py
python3 e6_assume_vl/run_e6.py
python3 e7_assume_payload/run_e7.py
bash  e8_param_dump/run_e8.sh
```
