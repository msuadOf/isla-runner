# sail-riscv 符号执行改进空间研究报告

> 议题:在 **sail-riscv 源码层面**还有哪些改进空间,能让 isla 符号执行(`make solve`)从超时转为收敛。
> 方法:3 维度并行深挖(V扩展/FD浮点/MEMORY访存)→ 逐改进点对抗式验证 → 综合;主 agent 对最关键的 V 扩展维度独立做了源码级交叉验证。
> 日期:2026-06-24

---

## 0. 结论先行

### 0.1 真实超时集(实测 + make 求值确认)

`make solve`(默认跑 `ACTIVE_ALL`)当前真实超时只有 **3 个 clause,全是 V 扩展**:

```
{VITYPE, VVTYPE, VXTYPE}   # output/status.timeout.log,均已确认在 ACTIVE_ALL 内
```

> **注意 LOAD 的口径(已纠正)**:`status.timeout.log` 里有一条 `LOAD timeout`,但 LOAD 在 `MEMORY` 组里(`run.mk:71`),而 `ACTIVE_ALL = $(filter-out $(FD_FLOAT) $(MEMORY), $(ALL))` 把整个 MEMORY 组排除了。用 `make` 实际求值 ACTIVE_ALL,`LOAD-in-active: 0` —— **LOAD 根本不在默认 `make solve` 范围**。那条 `LOAD timeout` 是旧 run 的残留(日志时间戳 22:09 早于当前 run.mk 配置)。LOAD/STORE/AMO 等访存指令属于 `make solve-memory` 单独子目标的范畴。
>
> 同理,`FD_FLOAT` 组的所有浮点指令也被排除,对默认 `make solve` 零增益。

其余 clause 要么 intime、要么不在默认验收范围。**所有改进点必须对着这 3 个 V 扩展超时目标评估收益**,凡是不在这 3 个 clause 路径上的改进对默认 `make solve` 都是零增益(MEMORY/FD 改进只能让 `solve-memory`/`solve-fd-float` 受益)。

### 0.2 已有改造基线(sail-riscv 分支 `isla/symbol-excution_6_14` 已经做了什么)

sail-riscv 已经建立了一套**系统的符号执行优化机制**,改进必须基于"已有这些,还剩什么":

| 机制 | 作用 | 证据 |
|------|------|------|
| `$ifndef SYMBOLIC ... $else ... $endif` 条件编译 | 仿真器(C/Lean)走原始语义,isla 符号执行走改造版 | `grep '$ifndef SYMBOLIC'` 遍布 V/M/K/vector_crypto/FD |
| `isla_mux2(cond, a, b)` / `isla_bool_to_bit_or_default(b)` | 用 SMT ITE 代替 `if-then-else` 的控制流 fork | `vext_vset_insts.sail:94` 等 |
| `pure "isla_*"` extern + isla 侧 `primop.rs` 实现 | 把循环/选择整体下沉成单 SMT 表达式 | `isla_read_vreg`/`isla_init_mask`/`isla_vector_select` 等 40+ 个 |
| `valid_*` / `illegal_*` / `assert_sew` / `checked_sew_value` / `checked_lmul_group_size` helper | 在 fork 点前用有限枚举收窄符号值 | `vext_utils_insts.sail:23-228` |
| `match width { 1=>.., 2=>.., 4=>.., 8=>.. }` | 把符号 width 在合法域枚举,让后续 slice 索引 concrete | `isla-changelog.md` STORE/STORECON/STORE_FP |

**关键事实(主 agent 验证):SYMBOLIC 开关已启用。** rv64d.ir 里 `zisla_init_mask`(SYMBOLIC 路径独有)有 4 处调用;VITYPE 的 IR 函数体引用的是 sail 源 1763-1898 行(`$else` SYMBOLIC 分支),而非 1692-1761 行(`$ifndef` 分支)。所以 isla 执行的就是 SYMBOLIC 改造后的代码。

### 0.3 最小可行改进集

**对默认 `make solve`,只有一项高优先改进:**

1. **V-ALU-MUX(深化版)** —— 解决 V 扩展算术指令里 `foreach (i from 0 to num_elem-1)` 的**符号循环边界**问题。这是唯一覆盖全部 3 个默认超时 clause(VITYPE/VVTYPE/VXTYPE)的改进,优先级最高。

**对 `make solve-memory`(访存子目标,非默认 solve)的辅助改进:**

2. **MEM-01** —— 在 sail 源码侧把 `pmpCheck` 的 PMP 循环短路。effort low,confidence high,对抗验证通过 `is_sound=true`。**注意:LOAD 不在默认 `make solve` 范围**,此项只让 `solve-memory` 受益。

---

## 1. V 扩展改进点(默认 `make solve` 的全部超时瓶颈)

### 1.1 核心根因:符号 `num_elem` 进入 `foreach` 循环

**完整因果链(主 agent 源码级验证):**

```
vtype (CSR, solve-state 时是符号值,config 未固定)
  → get_sew()      = 2 ^ (unsigned(vtype[vsew]) + 3)      [vext_regs.sail:349]  符号
  → get_lmul_pow() = signed(vtype[vlmul])                  [vext_regs.sail:358]  符号
  → get_num_elem(LMUL_pow, SEW)                            [vext_control.sail:437] 符号
       (虽是 match SEW{8=>..16=>..},但 SEW 符号 → 按 4×7 组合 fork)
  → num_elem 符号化
  → foreach (i from 0 to num_elem-1) { body_result[i] = ... }   符号循环边界
```

**实测铁证(VITYPE.log):**
- `612` 个 FORK 直接 `taints: ["vtype"]`,`42` 个 `taints: ["vstart"]`,`528` 个 `[]`。
- 主 fork 簇 `vext_arith_insts.sail:1689` 计 **586 次**(注:1689:7 是 encdec pragma 行的 source map 引用,实际执行体是 1763+ 行的 SYMBOLIC 分支)。

**为什么现有 SYMBOLIC 改造没解决它:** VITYPE 的 SYMBOLIC 分支已经做了两件事——用 `isla_vector_select(mask, initial_result, body_result)` 把 mask 选择压平成 SMT ITE,用 `isla_unsigned_saturation_narrow1_result` 等 extern 把单个元素的算术下沉。**但 `foreach (i from 0 to num_elem-1)` 的循环边界 num_elem 仍然是符号的**,isla 无法确定展开次数,在符号条件上 fork。

**规模:** vext_arith_insts.sail 有 **115 个** `foreach (i from 0 to (num_elem-1))`,VLEN=256(zvlen_exp=8),所以最坏单次循环最多迭代 256 次(SEW=8,LMUL_pow=3)。

### 1.2 改进点 V-ALU-MUX(深化版):符号循环边界收窄

**改法(参照已有 `match width` 和 `assert_sew` 模式):**

在 SYMBOLIC 分支里,把依赖符号 `num_elem`/`SEW` 的 `foreach`,改造成在有限合法域上枚举 —— 即用 `match SEW { 8 => <SEW=8 专用体>, 16 => ..., 32 => ..., 64 => ... }`(必要时再嵌套 LMUL_pow),让每个分支内的 `num_elem` 成为编译期可计算的 concrete 值。这正是 `isla-changelog.md` 里 STORE 解决 `subrange_internal` 符号宽度的同款思路。

由于 `assert_sew(SEW)` 已经把 SEW 约束到 {8,16,32,64}(有限集合),这种 match 是完全覆盖的,不丢失语义。每个 match 分支里,`'n = num_elem`、`'m = SEW` 都是 concrete,Sail 的 dependent type 和 `foreach` 都能正常展开。

**关键约束合规性(guides.md):**
- ✅ SEW ∈ {8,16,32,64}、LMUL_pow ∈ {-3..3} 排除保留编码 —— 这是 guides.md 明确允许"加强已有但表达过松的约束"。
- ✅ num_elem 落在 vlen 与合法 SEW/LMUL 推导的有限集合 —— guides.md 允许。
- ❌ **不**固定 vtype/vl/vstart 本身的值(运行上下文仍符号),只切断符号传播链。
- ✅ 仅新增 SYMBOLIC 分支,C/Lean 仿真器走 `$ifndef` 完全不变。

**收益:** VITYPE/VVTYPE/VXTYPE 的 612/同步量级 vtype-taint fork 大幅削减,3 个 V clause 预期转 intime。这是当前唯一规模性爆炸点。

**effort:** medium-high。算术指令面广(vext_arith 115 个 foreach),但模式统一(都是 `foreach over num_elem`),可批量化。建议先在一个 clause(如 VITYPE)上跑通模式,再推广。

**confidence:** high(根因由 612 个 vtype-taint 直接证实,改法与已验证的 STORE `match width` 同构)。

### 1.3 次要 V 扩展改进点(配套,V-ALU-MUX 之后)

- **`vstart` 符号化(42 个 taint):** `foreach` 的起点 `get_start_element()` 读符号 vstart。同源问题,但规模小,随 V-ALU-MUX 的有限域收窄一并处理。
- **vector_crypto 完成度核查:** zvbb/zvkned/zvksed/zvkg/zvknhab 已有 `$ifndef SYMBOLIC`,需核查 EGW(element-group width)/寄存器组不重叠约束是否像 `valid_reg_overlap` 一样够紧。

---

## 2. MEMORY 改进点(服务于 `make solve-memory`,非默认 `make solve`)

> **适用范围提醒**:本节所有改进的目标 clause(LOAD/STORE/AMO/C_LB*/C_SB* 等)都在 `MEMORY` 组里,被 `ACTIVE_ALL = $(filter-out $(MEMORY), ...)` 排除,**不在默认 `make solve` 范围**。它们只对 `make solve-memory` 这个单独子目标有意义。如果当前验收只看默认 `make solve`,本节可整体跳过,直接做第 1 节的 V-ALU-MUX。

### 2.1 MEM-01 —— PMP 循环短路(✅ 对抗验证 is_sound=true)

**根因:** `sys_pmp_count` 在 rv64d.ir 中被固化为 **16**(IR:24247),而 `pmp_control.sail:106` 的 `if sys_pmp_count == 0 then return None()` 因固化值非 0 **永不命中**;`foreach (i from 0 to sys_pmp_count - 1)`(:118)对 16 个 pmpaddr/pmpcfg 寄存器全展开,每个 entry 的 `range_subset`(`pmp_control.sail:50` + `range_util.sail:22`)在符号物理地址上 fork NoMatch/PartialMatch/Match。

LOAD.log 实测:PMP 相关簇约 **64-76 个 fork(占 ~37%)**,是 LOAD 唯一大簇。

**改法:** 在 `pmp_control.sail` 的 `pmpCheck` 加 `$ifndef SYMBOLIC ... $else: return None()`(等价 difftest PMP-off);零风险替代用 `isla_mux2` 把 foreach 三路 match 合成单路径 ITE。唯一调用点 `mem.sail:178`,隔离良好。

**风险:** `sys_pmp_count` 来自 config `memory.pmp.count`(平台编译期参数),非运行上下文,不违反 guides.md 硬约束。C/Lean 走 `$ifndef` 完整保留 PMP。

**收益(验证下调后):** LOAD fork 约 206→~130(PMP 簇归零),是 LOAD 唯一大簇,大概率从 timeout 转 intime(剩余非 PMP fork 约 130 可能仍偏多,属有限规模,可配合调 timeout)。注意:裁决提示并非所有 MEMORY clause 都能仅靠 PMP 解决。

**effort:** low。**confidence:** high。

### 2.2 MEM-03 —— translateMode 短路(✅ is_sound=true,但收益小)

`vmem.sail:196` 的 `translationMode` 在符号 `cur_privilege` 上 fork。satp=0(difftest 配置)使两路都返回 Bare(物理直通),但 executor 仍按 cur_privilege fork。

**改法:** translateAddr 顶部加 `$ifndef SYMBOLIC ... $else: let mode = Bare`(satp=0 是 difftest 真实不变配置)。技术正确、对仿真器透明。

**收益(验证下调):** 每访mem只省 **1 个** fork(非提案原称 2-4),**不能单独**让任何 clause 跨越 timeout 边界。仅作 MEM-01 之后的"顺手清扫"项。effort low。

### 2.3 MEM-02 / MEM-05(❌ 验证否决,不要做)

- **MEM-02(split_misaligned 短路):** 实测 `vmem_utils.sail:84` 在 LOAD.log 全程只 **1 次** fork,`SymbolicLength`/`subrange_internal` 全日志 **0 命中**(机制杜撰);itrace 证明 split_misaligned 走 (1,width) 早返回,repeat 只 1 次。且实际 config `misaligned.supported=true`(rv64d_v256_e32.json),强制 (1,width) 会改语义,逼近 guides.md 红线。
- **MEM-05(ZICBOZ cache_block_size 固化):** 自我证伪 —— rv64d.ir:10902 显示 `plat_cache_block_size_exp` 已固化为常量 6(cache_block_size=64),无符号化对象可消除;且 ZICB* 不在超时集。

### 2.4 MEM-04 —— pmaCheck SYMBOLIC 区段判定(需谨慎)

PMP 解决后的残留热点(`matching_pma_bits_range`/`range_subset`、`within_mmio_*`)。pmaCheck 决定 access fault 与 RAM/MMIO 分派,**SYMBOLIC 分支必须保留完整可观察语义**(findings.md L99 警示:phys_access_check 通过后仍要 within_mmio 决定 RAM/MMIO)。建议只做"区间匹配合并为 ITE"而非"假设总命中"。effort high。优先级最低:应在 MEM-01 后实测 LOAD 是否仍超时再决定。

### 2.5 MEM-06(路标):区分源码可改 vs executor/difftest 必做

避免重复造轮子(findings.md 已记录大量 isla executor 侧 builtin):
- ① **源码可改**:MEM-01、V-ALU-MUX、(MEM-03/04)
- ② **必须靠 executor builtin**:已有 `pmpCheck`/`pmaCheck`/`within_mmio` summary(findings.md L96-100),默认关闭,需在 solve 配置显式开启(`ISLA_RISCV_BUILTIN_PMP_CHECK=1` 等)
- ③ **必须靠 difftest 配置**:修正 IR 固化常量、symbolic_addrs 区间、确认 misaligned/pmp 配置与 SYMBOLIC 分支一致

建议先做①(源码侧收窄,最高 ROI),再用②③兜底。

---

## 3. FD 浮点改进点(全部不在当前验收范围)

### 3.1 统一结论:FD-1 ~ FD-6 全部对当前 `make solve` 零增益

`FD_FLOAT` 组被 `run.mk:78` 的 `ACTIVE_ALL = $(filter-out $(FD_FLOAT) $(MEMORY),$(ALL))` 排除。所有 FD clause(FCLASS/FMINM/FMAXM/FCVTMOD/FLEQ/FLTQ/FCVT/FROUND/FMADD...)**默认根本不参与 make solve**,也从未超时(status.timeout.log 无任何 FD clause)。

因此 FD-1~FD-6 技术分析虽扎实(行号精确),但与项目当前真实瓶颈完全错位,**不应在本迭代采纳**。

### 3.2 FD 的一个隐藏前置问题(仅未来启用 solve-fd-float 时相关)

对抗验证推翻了 FD-5 原版的核心前提:FLEQ_S/F_BIN_RM_TYPE_S/FROUND_S 实测全部因 `ExecError::NoFunction(riscv_f32Le_quiet/riscv_f32Div/riscv_f32roundToInt)` **确定性崩溃**(rv64d.ir 中 softfloat 声明为 `val` extern,`is_abstract=false`,ir.rs:1358-1360 注释自承"as long as we never actually try to call it",而 FLEQ 恰恰会调用)。

**修正版 FD-5-ABSTRACT:** 在 IR/调用点把 `riscv_f32*`/`riscv_f64*` softfloat extern 批量标记为 abstract,走 executor.rs:933-955 的 ABSTRACT_CALL→无约束符号返回。这是独立工作量(effort medium),纯新增对仿真器透明的符号语义。**仅当未来启用 solve-fd-float 时才是前置条件**,优先级远低于 V 扩展。

---

## 4. 推荐执行顺序

**对默认 `make solve`(验收主体):**

| 序 | 改进 | 攻击目标 | effort | confidence | 说明 |
|----|------|----------|--------|------------|------|
| 1 | **V-ALU-MUX** (符号循环收窄) | VITYPE/VVTYPE/VXTYPE | medium-high | high | **唯一覆盖默认 solve 全部 3 个超时 clause 的改进**;先在 VITYPE 跑通模式再推广 |

**对 `make solve-memory`(访存子目标,非默认 solve):**

| 序 | 改进 | 攻击目标 | effort | confidence | 说明 |
|----|------|----------|--------|------------|------|
| 2 | **MEM-01** (PMP 短路) | LOAD 等 MEMORY 组 | low | high | LOAD PMP 簇归零;仅在启用 solve-memory 时有意义 |
| 3 | 实测后:若 LOAD 仍超时 → MEM-04 (PMA);顺手 MEM-03 | LOAD 残留 | low/high | medium | 每访存省 1 fork |
| 4 | 未来启用 solve-fd-float 前 → FD-5-ABSTRACT | FD_FLOAT 组 | medium | medium | softfloat abstract 标记 |

**预期(默认 make solve):** V-ALU-MUX 一项即可让 3 个超时 clause 全部转 intime,是默认验收唯一需要做的改进。若验收范围扩到 solve-memory,再补 MEM-01。

---

## 5. 跨维度共性根因

> 「平台不可变参数/配置的符号化,在全执行链上被当作开放符号自由传播、放大成 fork。」

- **V 扩展**:`vtype` 合法编码集合 → SEW/LMUL/num_elem 符号传播到 `foreach` 循环。
- **MEMORY**:`sys_pmp_count` 实际取值 → IR 固化为 16 → foreach 16 次全展开。

共性解法(guides.md 允许):在源头用 SYMBOLIC 分支 + 有限域枚举(`match SEW`/`isla_mux2`/`return None()`),把符号传播链切断,**而非**固定运行上下文单点(vl/vstart/vtype 本身/寄存器选择)。

---

## 附录:本报告的验证方法与可信度

- **V 扩展**:workflow 的 dive:vector agent 因 429 限流失败,本维度结论由主 agent 独立源码级验证补全(确认 SYMBOLIC 已启用、定位 foreach 符号循环为真正瓶颈、验证改法与 STORE `match width` 同构)。可信度高。
- **MEMORY**:dive + 对抗验证均成功,MEM-01 经 is_sound=true 确认,MEM-02/05 被实测数据否决。可信度高。
- **FD**:dive + 对抗验证成功,推翻了原版多个高估收益主张,确认全部不在验收范围。可信度高。
- 每个 evidence 标注了 `文件:行号`,可逐项核查。
