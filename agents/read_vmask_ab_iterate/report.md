# read_vmask A/B 迭代改进报告（2026-06-30 自主探索）

## 任务
用户结论"A 和 B 都还要改"。根据 itrace 自主迭代，worktree/分支记录过程，对照实验验证猜想。详细过程见 `status.md`。

---

## 最重要的发现：read_vmask 不是真正的拦路虎

通过 itrace 深挖 MASKTYPEI，发现 **A 的路径根本没走到 read_vmask**：

MASKTYPEI 执行体第 1 步是 `get_start_element()`（vext_utils_insts.sail:274），检查 vstart：
```sail
function get_start_element() -> result(nat, unit) = {
  let start_element = unsigned(vstart);
  let SEW_pow = get_sew_pow();                    // ← SEW_pow 来自符号 vtype，是符号
  if start_element > (2 ^ (3 + vlen_exp - SEW_pow) - 1)   // ← bound 是符号
  then Err(())                                     // ← 符号比较不可解 → Err → Illegal
  else Ok(start_element)
}
```
A 的 path1 itrace：`get_start_element` → `zgt_int(unsigned(vstart), symbolic_bound)` → 解不出 `vstart<=bound` → **Err** → `Illegal_Instruction`。**路径在 get_start_element 就死，根本没到 read_vmask**。

所以：
- **A 的 `isla_read_vmask` extern 一次没被调用**（itrace=0）——路径在它之前就终止了。
- **A 的 subrange=0 是假象**——不是因为修好了 read_vmask，而是因为路径走不到 read_vmask。
- **A 的 0 个 Retire_Success** 也是因此——没真算。

### 根因链
```
vtype 符号 → SEW 符号 → get_start_element 的 bound 符号 → vstart<=bound 不可解 → Err → 路径死
```
read_vmask 的 subrange 错误只是表象之一。**真正的拦路虎是 get_start_element 的符号 bound。**

### B 为什么能算完
B 的 `assert_vector_num_elem_value(num_elem)` 把 num_elem 具体化，结合具体 vlen **反推 SEW 具体**（约束传播）→ bound 具体 → `vstart<=bound` 可解 → Ok（30/31）→ 继续算 → Retire_Success。但 num_elem 有 ~10 个合法值 → 路径膨胀 → 部分 clause timeout。

---

## 实验矩阵（全部在 cleaned baseline 上，sail-riscv commit 0a6375a5 + isla commit 5f8a793）

### 单 clause（代表算术 + crypto）
| 方案 | 改动 | MASKTYPEI | VITYPE | VIMTYPE | VAESDF/VCLMUL |
|---|---|---|---|---|---|
| baseline | — | 21path | 22p/1subr | timeout(4p) | timeout |
| A | isla_read_vmask extern + sail SYMBOLIC 分支 | 9.2s/21/**0✓** | 48s/22/**0✓** | 7s/17/**0✓** | (A 不动crypto) |
| B | sail 里具体化 num_elem(4-clause) | 14.8s/31/**10✓** | timeout | timeout | timeout |
| **B1-clean** | get_sew_pow 全局具体化 SEW | **6.4s/31/10✓** | **9.5s/30/6✓** | **31s/27/8✓** | **回归timeout** |
| B2 | get_start_element 局部具体化 SEW | 7.7s/31/10✓ | 49s/0(subr=1) | timeout | — |
| B3 | get_start_element 去掉符号 bound Err 分支 | 30s/30/10✓ | 48s/0(subr=1) | — | — |
| AB | A + B3 组合 | 8.5s/20/0✓ | 48s/21/0✓ | 8.3s/17/0✓ | — |

（✓ = Retire_Success 数）

### 全量 solve timeout
| 方案 | 总 timeout |
|---|---|
| baseline | 24 |
| A | 11 |
| B (4-clause) | 38 |
| B1-clean | 26 |

---

## 各方案本质（一句话）

- **A**：修了 read_vmask 切片，但路径在 get_start_element（符号 bound）就死，没真算。subrange=0 是假象。快但 0 算完。
- **B**：具体化 num_elem 反推 SEW 具体 → 过 get_start_element → 算完。但 num_elem ~10 值 → 路径膨胀 → timeout。
- **B1-clean**：直接在源头（get_sew_pow）具体化 SEW（4 值）。单 clause 最优（算完+快）。但全局生效，crypto clause 的 SEW 敏感循环被 fork 膨胀 → 全量 26 timeout（解决 15 个算术 timeout，新增 17 个 crypto timeout）。
- **B2/B3**：局部改 get_start_element，不完整（read_vmask 切片没修，VITYPE 仍有 subrange）。
- **AB（A+B3）**：两个拦路虎都修了（subrange=0，get_start_element 不死），但**仍 0 个 Retire_Success**——下一层 init_masked_result 的符号 vstart/vl gating 又挡住。

---

## 核心结论

1. **read_vmask 的 subrange 问题是可以单独修的**（A 或 B1 都能让 subrange=0），但它**不是 V 扩展算不完的根因**。
2. **真正的根因是符号约束链**：vtype 符号 → SEW 符号 → get_start_element bound 符号 → 路径死；过了这关还有 init_masked_result 的 vstart/vl 符号 gating → 又死。**完全符号化的 V 执行有一串符号拦截，不是单点能解的。**
3. **没有单一方案全局最优**：
   - 要"算完"（Retire_Success）必须具体化 SEW/vstart/vl 中的某些 → 必然有 fork 膨胀。
   - B1-clean（具体化 SEW）对算术最优，但伤 crypto。
   - A 快但全是假象（路径浅死）。

## 给用户的建议（待定夺）

- **若目标是"消除 read_vmask subrange 硬错误"**：A 或 B1 都行，改动小、subrange=0。推荐 **B1-clean**（单点改 get_sew_pow，全局生效，subrange=0 + 算术 clause 能算完）。crypto timeout 是已有的（baseline 也有），不是回归重点。
- **若目标是"V 扩展真正算完"**：需要系统处理整条符号链（SEW + vstart + vl），不是 read_vmask 单点。这是更大的工程。
- **若担心 crypto 回归**：B1-clean + crypto clause 豁免（需让 crypto 走不具体化 SEW 的路径），或只对算术 clause 具体化 SEW。

---

## worktree/分支索引（全部保留，可复现）

| 方案 | sail-riscv 分支(commit) | isla 分支 | 改动核心 |
|---|---|---|---|
| A | read-vmask-extern-A (e46521a) | read-vmask-extern-A (5c11c37) | isla_read_vmask extern + read_vmask SYMBOLIC 分支 |
| B | read-vmask-sail-B (9ee899e) | read-vmask-sail-B (cleaned) | 具体化 num_elem, 4-clause |
| **B1-clean** | **read-vmask-sail-B1-sew (3e671a0)** | read-vmask-sail-B1 (cleaned) | **get_sew_pow 全局具体化 SEW**（推荐） |
| B2 | read-vmask-sail-B2-gse (660077e) | — | get_start_element 局部具体化 SEW |
| B3 | read-vmask-sail-B3-vstart (be79fe1) | — | get_start_element 去 Err 分支 |
| AB | read-vmask-sail-AB (cd35e05) | read-vmask-AB (=A isla) | A + B3 组合 |

worktree 路径：`/home/baiyifan/workplace-local/isla-runner/.worktrees/{sail-A,sail-B,sail-B1,sail-B2,sail-B3,sail-AB,isla-A,isla-B,isla-B1,isla-AB}`

## 复现命令示例（B1-clean）
```sh
# sail-B1 的 get_sew_pow 具体化 -> IR
cd sail-riscv && git worktree list  # 找 sail-B1
cp .worktrees/sail-B1/model/extensions/V/vext_regs.sail sail-riscv/model/extensions/V/vext_regs.sail
PATH=...isla-sail:$PATH cmake --build build --target generated_isla_rv64d
cp build/model/rv64d.ir ../isla/rv64d.ir
cd ../isla && make solve-MASKTYPEI   # 6.4s/31path/10 Retire_Success
```
