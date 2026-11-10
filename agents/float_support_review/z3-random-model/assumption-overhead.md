# 随机值 assumption 注入的求解开销——SMT2 + z3 CLI 定向实测

- 日期：2026-09-28
- 议题背景：[empirical-report.md](empirical-report.md) 已证明 Z3 4.16 原生不返回随机满足赋值（UF 包裹/自由变量恒 0，E4/E5），唯一可靠机制是调用方采样 + `check-sat-assuming ((= vl k))` 注入（E6/E7，域内 100% 命中）。本报告回答后续问题：**在 case 生成循环里每次 check 注入 "= vl k" / "= payload p" 这类随机值 assumption，会拖慢求解多少？**
- 执行方式：只读实验，SMT2 文件 + `z3 -st` 统计（无 z3py）；证据目录 `isla/target/float-solve-evidence/z3-assumption-overhead-20260928/`（脚本、逐次 SMT2、CSV、运行日志）
- 环境：z3 CLI `Z3 version 4.16.0 - 64 bit`（/home/linuxbrew/.linuxbrew/bin/z3），与 isla-lib 实际链接的 `libz3.so.4.16` 同一安装（见 empirical-report.md 环境表）；python3 3.13 仅生成/驱动/聚合

## 结论速览

1. **EC 全循环（最重要）**：模拟 50 case 枚举循环（push + block 前一身份 + check + get-value + pop，30 次独立进程重复，配对统计），50% 拒绝率（k∈[0,128] 均匀、域 vl≤64、UNSAT 重采样≤5 次）下，注入版相对现状 **small +9.6%（t=+11.9）/ medium +3.2%（t=+5.4）/ large +1.9%（t=+3.4）**；0% 拒绝率（k∈[0,64]）对照为 +6.3% / +0.2% / −2.6%（末者为负载漂移噪声，t=−2.6）。**绝对开销每 case 仅 +0.30~0.45ms**，与约束规模基本无关。
2. **EA 单 check 分解**：assumption 本身的开销（V2−V1，同脚本仅差 check 行）为 **+0.18~0.75ms/check**，small/medium 档低于测量分辨率边缘（sem≈0.7-0.9ms），large 档 +0.75±3.2ms——即注入本身近乎免费。
3. **EB UNSAT 代价**：域外 k 的 assuming check **不更贵、反而显著更便宜**（U−S = −2.9 / −6.8 / −25.4ms/check）：`(= vl k>64)` 与守卫 `bvule vl 64` 立即冲突、快速退出。**被拒绝的采样是廉价路径**，拒绝重试不是开销大头。
4. **ED assumption vs push/pop 硬约束**：同值注入用 `(assert (= vl k))` 与用 assumption 差 **−1.0~+0.1ms/check**（噪声级）——两种机制成本等价，assumption 无额外惩罚。
5. **EE FP 理论变体——唯一警示项**：把 UF 换成真 f64 `fp.add/fp.mul`（RNE）后，**assumption 注入出现非平凡惩罚**：冷求解 plain≈1.94s vs assuming 14~87s（7~45×，随 k 混沌）；30 次批内总量 28.76→53.62s（1.86×）。但该族总耗时与 M 无关（成本全在首冷 check、增量轮免费），且幅度随 k 剧烈波动——与校准记录的 CDCL 相位敏感性同源，**不能外推为稳定的每 check 开销**；且 isla 当前 IR 形态是 BV64 payload + UF 包裹（E5），不是原生 FP 理论项，EE 不代表官方负载形态。
6. **外推（合成约束 → 官方负载，方向性）**：每 case 绝对增量 ~0.3-0.45ms，除以锚点 **F_MADD_TYPE_D 79.2ms/case（86.50s/1092 gen）≈ +0.4~0.6%；FVFTYPE 8.2ms/Z3 调用（1800.66s/219605 调用）≈ +4~6%**。对官方求解整体是**个位数百分比以内**的代价，量级上不构成采用障碍。

## 约束族（模拟 Isla 路径条件形态）

生成器 `gen_family.py`，形态与 E4/E5 退化形态一致：

- 32 位指令 word 固定位域（OP-V 浮点：opcode/funct3/funct6/vd 固定，vs1/vs2 各 5 位自由）；
- BV64 状态变量 `vl/vtype/fcsr/frm/sew/vlmax`，守卫 `bvule vl vlmax(64)`；
- **UF 包裹**：`isla_mask`、`vector_select`、`isla_fp_add`、`fp_classify` 均 declare-fun，vl/payload 只出现在 UF 实参与守卫里（UF 吸收一切位约束，求解器视其为 don't-care——正是实测恒 0 的形态）；
- 纯 BV 工作块：w=f(vs1,vs2,nonce) 经 K 步 add/xor/shr 混合链，固定输出最高 1 位（python 预计算保证 SAT）；
- 深层 ite 链（大档，分支被 UF 断言强制、python 同步镜像预计算保证 SAT）。

三档（UF 应用数）：**small 10 / medium 180 / large 700**（链长 20/48/128，ite 深 8/12/48）。校准记录（`calib/`）：CDCL 相位使跨配置耗时**非单调**（无法用旋钮稳定排序，D=2→D=4 可从 30ms 翻到 674ms），但每个固定配置重复方差小（std≈4-6ms），满足差分测量需要；实测耗时见下表，不预设单调。

## 计时方法

- `z3 -st` 的 `:total-time` 分辨率仅 **0.01s（10ms）**，单次 check 无法直接测。EA/EB/ED 采用**批内 M 轮摊薄**：每脚本 M × (push + block_i + [注入] + check_i + [get-value] + pop)，每轮 k_i/block_i 不同（防缓存），per-check 开销 = (T_variant − T_floor)/M；30 次独立进程重复取均值，配对差分的均值标准误见表内 ±（small/medium 档 ~0.7-0.9ms，即该量级以下的开销只能给上界）。
- EC 用**交互式进程**（`z3 -st -in`，python 逐命令驱动、逐轮 wall 计时）模拟 isla-lib 真实使用（单上下文、每 case push/pop、block 前一个 instr 身份）；进程退出时读 `:total-time` 交叉核验（与 wall 一致，见 `ec/ec_run.log`）。
- 增量语义注意：首轮 check 付冷启动（位爆破/预处理）成本，其后轮次复用内部状态——这正是 isla-lib 逐 case 循环的真实成本结构；批内均值把冷成本摊进 M。
- 守门：域内变体断言 SAT、域外断言 UNSAT（`run_batch.py:measure`），EC 每轮断言 sat/unsat 预期，全部通过。

## EA 基本开销（30 reps；单位 ms/check，含批内摊薄）

| 档（UF 数/脚本大小） | plain check (V0−floor) | +get-value (V1−V0) | assume 开销 (V2−V1) | assume vs plain (V2−V0) |
| --- | --- | --- | --- | --- |
| small（10 UF / 10KB） | 2.55 | +0.82 | +0.22±0.89 | +1.03 |
| medium（180 UF / 55KB） | 7.01 | +1.27 | +0.18±0.69 | +1.44 |
| large（700 UF / 201KB） | 26.64 | +5.86 | +0.75±3.17 | +6.61 |

（"assume 开销"列的 ± 为 30 次重复配对差分的均值标准误，其余列为点估计。）**assumption 开销在全部三档都不超过 ~1ms，多数情况低于分辨率**；get-value 与 check 本体随规模增长（0.8→5.9ms、2.6→26.6ms）。

## EB UNSAT 代价（域外 k∈[65,128] 必 UNSAT，无 get-value）

| 档 | SAT check/轮（S） | UNSAT check/轮（U） | U−S |
| --- | --- | --- | --- |
| small | 3.32ms | 0.45ms | **−2.87±0.88ms** |
| medium | 7.24ms | 0.47ms | **−6.78±0.55ms** |
| large | 26.31ms | 0.89ms | **−25.42±1.84ms** |

（S/U 含 floor 摊薄，绝对值按 (T−floor)/M 折算。）UNSAT 拒绝 check 的绝对成本**与规模几乎无关（0.45/0.47/0.89ms）**：注入的 `(= vl k)` 与守卫直接冲突，搜索立即终止。**拒绝对应"廉价快速失败"，不是惩罚项**。

## EC 全循环对照（核心；50 case/循环 × 30 进程；配对统计）

协议——A（现状）：push + block 前一身份 + `check-sat` + `get-value` + pop；B（注入版）：同上但采样 k∈[0,128] 均匀 → `check-sat-assuming ((= vl k))`，UNSAT 重采样≤5 次（6 次皆拒则回退 plain check），B0：k∈[0,64]（0% 拒绝）。

| 档 | A per-case | B per-case | B0 per-case | B−A（配对，t 值） | B0−A |
| --- | --- | --- | --- | --- | --- |
| small | 3.69±5.33ms（loop 184.5±6.0ms） | 4.05±5.92ms | 3.92ms | **+0.36ms / +9.64%（t=+11.9）** | +0.23ms / +6.34%（t=+8.6） |
| medium | 9.36±11.58ms（loop 468.0±14.4ms） | 9.66±11.66ms | 9.37ms | **+0.30ms / +3.19%（t=+5.4）** | +0.02ms / +0.17%（t=+0.3，不显著） |
| large | 23.83±32.28ms（loop 1191.6±21.8ms） | 24.28±31.60ms | 23.22ms | **+0.45ms / +1.88%（t=+3.4）** | −0.61ms / −2.57%（t=−2.6，负载漂移噪声） |

（per-case ±std 大是因为首轮冷启动与相位方差；配对 t 检验按同 rep 序号配对。B 的 checks/case=1.996、rejects=1516/30 循环 ≈ 1.01 次/case，与理论 E[拒绝]=(1−p)/p≈0.98 一致；fallback 22/45000 轮 ≈ 0.05%。）

**解读**：开销百分比随规模递减（9.6%→1.9%）不是因为注入变便宜，而是分母（check 本体耗时）变大；**绝对开销稳定在 ~0.3-0.45ms/case**，其中约一半是 0% 拒绝时也存在的 assumption+模型交互成本（B0：small +0.23ms），另一半是 ~1 次/case 的 UNSAT 拒绝重试。

## ED assumption vs push/pop 硬约束（同值注入，均含 get-value）

| 档 | HD−AS（每 check） |
| --- | --- |
| small | +0.07±0.78ms |
| medium | −0.07±0.75ms |
| large | −1.03±2.46ms |

两种机制等价（差在噪声内）。选 assumption 的理由是**不用重建公式**（k 变化只改字面量）与 UNSAT 后自动回滚，而非速度。

## EE FP 理论变体（选做）

`run_ee.py`：与 small 档同构（instr 位域 + vl 守卫 + add/xor 链），payload 改为真 `(_ FloatingPoint 11 53)`，约束 `(fp.eq (fp.add RNE p0 p1) 1.0)`、`(fp.eq (fp.mul RNE p2 p3) 2.0)`、`fp.gt/fp.lt` 界（0.5+0.5 等预置可行）。30 reps：

| 配置 | total-time / wall |
| --- | --- |
| V1 plain（M=20 轮批） | 28.759±0.680s（与 M 无关，M=3..20 均一致） |
| V2 assuming（M=20 轮批） | 53.617±0.895s（**1.86×**） |
| 单 check plain 冷求解 ×3 | 1.94s（一致） |
| 单 check assuming 冷求解 k=41/64/0/7 | 14.0 / 25.6 / 59.2 / 86.6s（**7~45×**，随 k 混沌） |

诊断结论：FP 族总耗时**与 M 无关**——成本集中在首个冷 check，后续增量轮近乎免费，因此不能按 (V2−V1)/M 折算每 check 开销（首轮报告草稿中的 +1243ms/check 为除法伪影，已修正）。真实信号：**在原生 FP 理论上，assumption 模式改变了求解路径，冷求解系统性变慢但幅度混沌（同族 BV 校准中 D=2→D=4 也有 22× 相位跳变）**。对本项目的适用性：isla 现行 IR 的 payload 是 BV64 + UF 包裹（E5 实测形态），不是原生 FP 项，EA/EB/EC 已证该形态下无此惩罚；若未来把约束直接编译成 z3 FP 理论项，需重做此实验。

## 外推（锚点：官方求解账目）

| 档 | EC 实测 B−A（每 case 绝对增量） | ÷ F_MADD_TYPE_D 79.2ms/case | ÷ FVFTYPE 8.2ms/调用 |
| --- | --- | --- | --- |
| small | +0.36ms | **+0.45%** | **+4.3%** |
| medium | +0.30ms | **+0.38%** | **+3.6%** |
| large | +0.45ms | **+0.57%** | **+5.5%** |

锚点来源：`docs/RESULTS.md`（56cc 官方 D FMA：86.50s、1092 gen 无抑制 → 79.2ms/case）；`agents/float_support_review/status.md`/`docs/RESULTS.md`（fc4 FVFTYPE 诊断：1800.66s、219605 完成调用 → 8.2ms/调用）。

**外推局限（明确标注）**：①合成约束的外推——我们的约束族只模拟形态（UF 包裹 + 位域 + 守卫），未复现官方公式的真实规模分布（FVFTYPE 单调用含数千 UF/位运算、Eq 热点等），绝对增量在更大公式上可能上移（各实验最保守合成上界 ≈1.6ms/case，见下段）；②FVFTYPE 锚点是"每 Z3 调用"均值，注入频率若为每 case 一次则与每 case 锚点同类，若逐调用注入则按比例放大；③官方负载的增量语境（公式持续增长、真 push/pop 深度）与合成循环不同；④B0-large 的 −2.6% 表明 ±3% 以内的百分比已进入环境噪声区，个位数下限不应过度解读。

**量级判断**：对 F_MADD 类（~79ms/case）官方求解，注入版预期减速 **<1%**，不可测；对 FVFTYPE 类（~8.2ms/调用）**约 4-6%**。即使按各实验最保守的绝对增量合成（EA large assume 0.75ms + EB large UNSAT 0.89ms ≈ 1.6ms/case）外推，也只有 F_MADD +2%、FVFTYPE +20%——这是"大公式 + 每次 check 都付最贵路径"的悲观上界，EC 实测不支持。**随机值 assumption 注入在性能上可行，瓶颈不在求解开销而在调用方采样逻辑本身。**

## 复现

```bash
cd isla/target/float-solve-evidence/z3-assumption-overhead-20260928
python3 calib/calibrate.py          # 约束族校准（SAT 守门 + 耗时）
python3 run_batch.py ea             # EA 基本开销（floor/V0/V1/V2 × 3 档 × 30）
python3 run_batch.py eb             # EB UNSAT 代价
python3 run_batch.py ed             # ED assumption vs 硬约束
python3 run_ec.py                   # EC 全循环（交互式，A/B/B0 × 3 档 × 30）
python3 run_ee.py                   # EE FP 变体
python3 aggregate.py                # 汇总 + 外推 -> aggregate_summary.md
```

原始数据：`ea|eb|ed|ee/<exp>_results.csv`（含 30 次逐值）、`ec/ec_results.csv`、逐脚本 `*/smt2/*.smt2`、运行日志 `ea_eb_ed_run.log`、`ec/ec_run.log`。
