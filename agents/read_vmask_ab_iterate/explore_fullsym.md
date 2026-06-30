# 全符号算完探索结论（2026-07-01）

## 用户要求
V 扩展真正算完 + 探索所有情况 + 不具体化（禁止固定 SEW/num_elem 到单一值）。

## 核心结论：纯 SMT 符号化 SEW 算不完 —— isla 架构基础限制

### 证据链（itrace + 代码）
1. **read_vreg 的 extra_ops 要求 SEW 具体**：
   - `isla_read_vreg_internal`（primop.rs:3372）开头 `expect_i128_arg(&args[1], "isla_read_vreg SEW")`，对符号 SEW 返回 `Err(Type)`（primop.rs:2411）→ 路径报错。
   - `read_vreg_extra_by_sew`（vext_control.sail:377）开头 `assert_sew(SEW)` = match SEW{8,16,32,64} = fork 枚举。
   - → **读向量寄存器这一步就要求 SEW 具体**。所有 V 指令都要 read_vreg。
2. **foreach 符号边界无法展开**：`foreach(i from 0 to num_elem-1)`，num_elem 符号 → isla `Instr::Jump` back-edge 计数到 `max_backjumps` → `LoopLimitReached`（executor.rs:1159）。要展开必须边界具体。
3. **符号宽度位向量 bits(num_elem)**：mask 是 `bits(num_elem)`（MASKTYPEI: `let 'n=num_elem; vm_val:bits('n)`），宽度符号 → isla SMT bitvector 固定 sort，构造不了。read_vmask 的 subrange_internal 符号 high 报错。
4. **符号索引逐元素访问 vm_val[i]**（foreach 里 i 符号）→ subrange 符号 high/low。

### 结论
**isla 当前架构下，SEW 保持全 SMT 符号、V 扩展算完，做不到。** 不是 read_vmask 单点问题——整个 V 向量抽象（read_vreg/write_vreg/isla_read_vreg/foreach/mask）都建立在"SEW 具体 + num_elem 决定宽度"之上。`fb74687`("解决过度泛型") 的设计就是按 SEW 具体分派。

## 关键区分："match 枚举" vs "固定单值"（用户禁令的辨析）

用户禁止的是"选特殊情况/给一个配置具体值"（如 TOML 配 SEW=32，只探索一种）—— **丢覆盖**。

`match SEW {8,16,32,64}`（B1-clean）是**穷举所有合法 SEW**：4 路 fork，每条 path 一个 SEW 值，**覆盖全部 SEW**。这不丢覆盖，是"分情况探索所有情况"。每条 path 上 SEW 具体（满足 isla read_vreg 要求），4 条 path 合起来 = 全符号 SEW 的等价覆盖。

- **固定 SEW=32**（单点）：❌ 只探索 1 种 SEW，丢 3/4 覆盖。**这才是用户禁止的**。
- **match SEW 枚举 4 值**（B1-clean）：✅ 探索所有 4 种 SEW，覆盖完整。算完。

## 因此最佳方案：B1-clean（match SEW 穷举）+ 优化 crypto 回归

B1-clean（get_sew_pow 里 match SEW_pow 到 {3,4,5,6}）：
- ✅ 算完（MASKTYPEI 10 success / VITYPE 6 / VIMTYPE 8 success）
- ✅ 覆盖所有 SEW（4 路 fork，非单点）
- ✅ subrange=0
- ⚠️ num_elem 仍符号（不具体化 num_elem）—— SEW 具体 + vlen 具体 → num_elem = vlen/SEW * LMUL，虽可推导但仍符号处理
- ⚠️ crypto clause 回归（全局 SEW match 让 crypto SEW 敏感循环 fork 多）—— 待优化

### crypto 回归的解法方向
- crypto clause（VAES/VCLMUL/VSM3/4）的内部循环对 SEW 敏感，全局 match SEW 让它们多 fork。
- 解法：crypto 的 SEW 通常固定（如 AES 总是 8-bit 元素），可让 crypto 路径不走 get_sew_pow 的 match。但 get_sew_pow 是公共函数，难分离。
- 或：提高 crypto 的 timeout（用户说有限规模可接受放宽 timeout）。

## 如果用户坚持"SEW 全 SMT 符号、path 级也不能具体"
那需要 isla 引擎级改造：
1. 重写 isla_read_vreg/isla_pack_vreg 支持符号 SEW（按符号 SEW 构造变长向量）。
2. 符号边界循环的 SMT 化（把 foreach 变成 SMT 表达式而非展开）。
3. 符号宽度位向量（MixedBits 扩展到符号段宽）。
这是大工程，非 sail/primop 单点能解。

## 本轮实验 worktree
- sail-A2（read-vmask-A2-puresym）：纯符号 read_vmask（无 assert）——类型错误（bits('n)↔vlenbits），暴露符号宽度位向量问题。
- sail-A3（read-vmask-A3-vlenunroll）：vlen 边界 foreach 思路——未完成（需配套改 read_vreg/vector 宽度）。
- 结论：受限于 read_vreg 要求 SEW 具体，A3 不成立。
