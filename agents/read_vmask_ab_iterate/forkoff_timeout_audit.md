# V 扩展 timeout clause 分类（fork-off + 120s，itrace 审计）

## 任务
通过 itrace 把 V 扩展 88 个 timeout clause 分成两类：
1. **无限 fork / 无法停机**（符号边界循环等，对应特定 sail 代码块）
2. **规模大但有限**（有限 match/if 的组合爆炸，120s 跑不完）

## 核心判据

| 指标 | 含义 |
|---|---|
| `LoopLimitReached` 次数 | >0 说明触发了 backjumps_per_loop(256) 上限 = **符号边界循环**（无限倾向）|
| 同一 FORK 点被重复命中次数 | 多条 path 都过同一分支点 = 有限组合爆炸；单 path 内同一循环体反复 fork = 循环 |
| FORK 热点对应的 sail 代码块 | foreach 体 vs 有限 match/if |

## 结果：绝大多数（85/88）是"规模大但有限"，只有极少数（3）有循环痕迹

### LoopLimitReached 分布（88 个 V timeout clause）
- **LoopLimitReached=0: 85 个**（96.6%）—— foreach 符号边界循环 **没触发** backjumps 上限
- LoopLimitReached>0: 仅 3 个（VBREV8_V=4, VGHSH_VV=1, VGMUL_VV=3）—— 这些有真循环

→ **85/88 的 timeout 不是无限循环**，是 **有限组合爆炸**（fork-off 后每个符号条件都 fork，组合数大但有限，120s 跑不完）。

## 两类具体分类

### 类别 A：规模大但有限（85 个，绝大多数）
**特征**：LoopLimitReached=0；FORK 热点是有限 match/if（encdec when 子句、valid_vtype、assert_sew/assert_lmul_pow、zvk_check_encdec 等），每个分支点 fork 有限次，但组合后 path 数大。

**典型 FORK 热点（有限符号条件）**：
- `currentlyEnabled(Ext_Zve32x) & get_sew()<=32 | ...`（encdec `when`，vext_arith_insts.sail:980/354/45/508 等）—— SEW/扩展使能位的符号比较
- `zvk_check_encdec`（zvk_utils.sail:19）—— vl/vstart/LMUL 的符号比较（VAESDF/VAESEM/VSM3/VSHA2 等）
- `assert_sew`/`assert_lmul_pow`（vext_control.sail:29/39）—— SEW/LMUL match
- `valid_vtype`（vill fork）

**为什么 120s 跑不完**：fork-off 后每个符号条件都 fork，SEW(4)×LMUL(7)×扩展位×vstart×vl×vd×vs2×funct6×... 组合数巨大。虽然每个维度有限，笛卡尔积后 path 数到几千-几万，120s 只能探索几百。

### 类别 B：符号边界循环 / 循环体 fork（3 个明确 + 若干疑似）
**特征**：LoopLimitReached>0 或 FORK 热点在 `foreach(num_elem-1)` 循环体内、且同一循环体 fork 被重复命中很多次。

**明确的循环型（LoopLimitReached>0）**：
- **VBREV8_V**（LoopLimitReached=4）：vector_crypto/zvbb_insts.sail:175-177（vbrev8 的逐字节循环）
- **VGHSH_VV**（LoopLimitReached=1）：zvk_utils.sail:19
- **VGMUL_VV**（LoopLimitReached=3）：zvk_utils.sail:19

**疑似循环体 fork（FORK 热点在 foreach 体内，但 LoopLimitReached=0——可能在 256 backjumps 前就 timeout）**：
- **VCPOP_M**：vext_mask_insts.sail:115（`foreach(i from 0 to num_elem-1) { if (mask & vs2_val)[i]==1 then count=count+1 }`）—— x148 次（popcount 逐元素循环，mask/vs2_val 元素符号 → 每元素 fork）
- **VFIRST_M**：vext_mask_insts.sail:131（类似，找第一个 set bit，逐元素循环）—— x150
- **VMSBF_M/VMSIF_M/VMSOF_M**：vext_mask_insts.sail 198/243/288（mask 前/后缀循环）
- **MASKTYPEV/MASKTYPEI/MASKTYPEX**：vext_arith_insts.sail 386/1011（foreach 循环体 `if vm_val[i]==1`）

这些 mask-reduction/merge 类指令的 **foreach(num_elem-1) 循环体内部有符号条件 fork**（`mask[i]==1`、`vs2_val[i]` 等），每条 path 上循环每迭代 fork 一次，num_elem 大（SEW=8 时 256）时 fork 数 ~256/path —— 这是 **"循环体每迭代 fork"，边缘无限**（只要 num_elem 能取大值，循环 fork 数无上界）。

## 结论

| 类别 | 数量 | 性质 | 对应 sail 代码块 |
|---|---|---|---|
| **A. 规模大但有限** | ~80+ | 有限 match/if 组合爆炸 | encdec when、valid_vtype、assert_sew/lmul、zvk_check_encdec |
| **B. 循环体 fork / 无限倾向** | ~8 | foreach(num_elem-1) 体内核符号条件，每迭代 fork | vext_mask_insts.sail foreach 体(VCPOP_M/VFIRST_M/VMS*)、vext_arith foreach 体(MASKTYPE*)、zvk_utils(VAES/VGMUL/VGHSH/VBREV8) |

**绝大多数（~80/88）是"规模大但有限"，不是无限停机**。只有 mask-reduction/merge（VCPOP/VFIRST/VMSBF/VMSIF/VMSOF/MASKTYPE*）和 vector-crypto 循环（VBREV8/VGMUL/VGHSH）这 ~8-10 个有"循环体每迭代 fork"的无限倾向——它们的 foreach(num_elem-1) 循环体内部对符号元素值 fork，num_elem 越大 fork 越多，没有自然上界。

## 区分两者的实用方法（已验证）
- `grep LoopLimitReached $c.log`：>0 = 循环型（无限倾向）；=0 = 有限组合型。
- FORK 热点行号在 `foreach` 体内（如 vext_mask_insts 115/131/198/243/288，vext_arith 386/1011）= 循环体 fork；在 encdec `when`/`valid_vtype`/`zvk_check_encdec` = 有限组合。
