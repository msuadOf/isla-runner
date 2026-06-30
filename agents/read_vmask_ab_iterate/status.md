# read_vmask A/B 方案迭代改进 — 状态记录（2026-06-30 自主迭代）

## 用户要求
A 和 B 都还要改。根据 itrace 自己迭代改进，worktree/分支记录，设计对照实验验证各种猜想。

---

## 关键发现（itrace 深挖）

### 发现 1：A 的路径根本没走到 read_vmask
MASKTYPEI 执行体第 1 步是 `get_start_element()`（检查 vstart）。A 的路径在这里就死：
`get_start_element` → `zgt_int(unsigned(vstart), bound)`，bound = `2^(3+vlen_exp-SEW_pow)-1` 是**符号**（SEW_pow 来自符号 vtype）→ 解不出 vstart<=bound → Err → Illegal。
**A 的 `isla_read_vmask` extern 一次没被调用**——路径在它之前就终止了。A 的 subrange=0 是因为路径走不到 read_vmask，**不是因为修好了**。A 的 0 个 Retire_Success 也因此——没真算。

### 发现 2：B 能过 get_start_element 是约束传播
B 的 `assert_vector_num_elem_value(num_elem)` 把 num_elem 具体化，结合具体 vlen 反推 SEW 具体 → bound 具体 → vstart<=bound 可解 → Ok（30/31）。但 num_elem 有 ~10 个合法值 → 路径膨胀 → VITYPE/VIMTYPE timeout。

### 发现 3：根因不是 read_vmask 切片，是 SEW/vstart 符号约束链
```
vtype 符号 → SEW 符号 → get_start_element bound 符号 → vstart<=bound 不可解 → Err → 路径死
```
read_vmask 的 subrange 错误是次要表象。**真正的拦路虎是 get_start_element 的符号 bound。**

---

## 实验矩阵

### 单 clause（MASKTYPEI / VITYPE / VIMTYPE）
| 方案 | MASKTYPEI | VITYPE | VIMTYPE |
|---|---|---|---|
| baseline | 21path | 22path/1subr | timeout |
| A (isla_read_vmask extern) | 9.2s/21/**0✓** | 48s/22/**0✓** | 7s/17/**0✓** |
| B (具体化 num_elem, 4-clause) | 14.8s/31/**10✓** | timeout | timeout |
| **B1-clean (get_sew_pow 全局具体化 SEW)** | **6.4s/31/10✓** | **9.5s/30/6✓** | **31s/27/8✓** |
| B2 (get_start_element 局部具体化) | 7.7s/31/10✓ | 49s/22/0( subrange=1 没修) | timeout |

### 全量 solve timeout
| 方案 | 总 timeout | 说明 |
|---|---|---|
| baseline | 24 | — |
| A | 11 | 路径浅(get_start_element 死)→快但 0 算完 |
| B (4-clause) | 38 | 路径膨胀 |
| **B1-clean** | 26 | 单 clause 最优，但 crypto clause 回归 |

### B1-clean 的 trade-off（关键）
- **解决 15 个 baseline timeout**（VANDN_*/VBREV/VCLZ/VCTZ/VICMPTYPE/VIM*/VMVRTYPE/VROL_*/VROR_*/RIVVTYPE）= 一般算术 clause。
- **新增 17 个 timeout**（VAES*/VCLMUL*/VSM3/4/VGHSH/VGMUL/VCPOP_M/MVVTYPE/VV*/ZVK*）= **crypto + SEW 敏感 clause**。
- 原因：crypto clause 的内部 foreach 循环对 SEW 敏感，全局具体化 SEW 让它们 fork 膨胀。

---

## 结论：没有单一方案全局最优

- **A**：快、全量 timeout 最少(11)，但**所有路径算不完(0 Retire_Success)**——因为 get_start_element 符号 bound 挡住，路径根本没进入计算。subrange=0 是假象。
- **B**：能算完但路径膨胀 timeout。
- **B1-clean**：单 clause 最优(算完+快)，但全局 SEW 具体化伤 crypto。
- **B2**：局部具体化不完整(VITYPE 的 read_vmask 切片没修)。

**根本矛盾**：要让一般算术 clause 算完，需要 SEW 具体(过 get_start_element)；但 SEW 全局具体化会伤 crypto clause 的 SEW 敏感循环。

---

## 下一步方向（未完成，供后续）
1. **B1-clean + crypto 豁免**：全局具体化 SEW，但 crypto clause(VAES/VCLMUL/VSM3/4/VGHSH/VGMUL) 走另一条不具体化 SEW 的路径。难（get_sew_pow 是公共的）。
2. **A + B1-clean 结合**：A 的 isla_read_vmask(修切片) + B1-clean 的 SEW 具体化。可能让算术 clause 既过 get_start_element 又不报 subrange。但 crypto 回归仍在。
3. **约束 vstart 而非 SEW**：vstart<=num_elem 是真语义(超出 reserved)。加这个约束可能让 get_start_element 可解而不用全局具体化 SEW。最 promising 但需验证不违反 guides。
4. **get_start_element 用 assume/不同语义**：把 vstart 越界当 Ok(返回 0)而非 Err，避免路径死。

---

## worktree/分支索引（全部保留）
| 方案 | sail-riscv 分支 | isla 分支 | 说明 |
|---|---|---|---|
| A | read-vmask-extern-A (e46521a) | read-vmask-extern-A (5c11c37) | isla_read_vmask extern + sail SYMBOLIC 分支 |
| B | read-vmask-sail-B (9ee899e) | read-vmask-sail-B (cleaned) | 具体化 num_elem, 4-clause |
| B1-clean | read-vmask-sail-B1-sew (3e671a0) | read-vmask-sail-B1 (cleaned) | get_sew_pow 全局具体化 SEW |
| B2 | read-vmask-sail-B2-gse (660077e) | — | get_start_element 局部具体化 |
| AB(待用) | read-vmask-sail-AB | read-vmask-AB (=A的isla) | A+B 结合(未实现) |

worktree 路径：`.worktrees/{sail-A,sail-B,sail-B1,sail-B2,sail-AB,isla-A,isla-B,isla-B1,isla-AB}`
