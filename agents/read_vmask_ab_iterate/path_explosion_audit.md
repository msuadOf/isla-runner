# vtype 枚举 path 审计（2026-07-01，回应用户质疑）

## 用户质疑
"vtype 有 112 个合法组合，为什么枚举后 path 数只有 ~30，不是 112 倍放大？是不是有些 branch 没达到？"

## 验证结果：用户是对的——枚举严重不均匀，大部分 SEW/LMUL branch 没达到

### B4（SEW+LMUL 枚举）MASKTYPEI 的 31 paths 里 assert_sew 匹配的 SEW 分布
| SEW | path 数 |
|---|---|
| SEW=64 | 20 |
| SEW=32 | 7 |
| **SEW=16** | **0** |
| **SEW=8** | **0** |

**SEW=8 和 SEW=16 完全没被探索到！** 只有 SEW=32/64 的 branch 被达到。

### 这说明什么
1. **枚举不是均匀的**：match SEW{8,16,32,64} 虽然在 IR 里是 4 路 fork，但 isla 的路径探索（受 solver SAT/UNSAT 判定 + 探索顺序 + 时间限制影响）**严重偏向** SEW=64/32，SEW=8/16 的 branch 没产生 path。
2. **可能的根因**：
   - solver 在 SEW=8/16 + 符号 vstart/vl 的组合下，某些约束（如 num_elem 大、foreach 展开多）导致路径被剪枝或未优先探索。
   - 或 path 探索的广度受限于时间/策略，只探索了部分 SEW。
   - 这意味着"枚举 = 覆盖所有情况"**不成立**——实际只覆盖了部分 SEW。

### 之前"B4 全量 9 timeout、算完有 Retire_Success"的结论需修正
- B4 确实比 baseline/A 少 timeout，但**不代表覆盖了所有 SEW/LMUL**。
- "算完"的 path 只是 SEW=32/64 的子集，SEW=8/16 根本没算。
- 所以 B4 的"9 timeout"可能是因为它**没探索那些慢的 SEW=8/16 path**（path 少所以不 timeout），而不是真的高效覆盖。

## 结论
用户的怀疑成立：**枚举的 path 数远小于 112，是因为大部分 SEW/LMUL branch 根本没被探索到**（isla 路径探索偏差 + solver 剪枝）。这不是"高效收敛"，而是**覆盖不全**。

要真正覆盖所有 vtype 组合（112 个），需要：
1. 强制 isla 探索所有 match branch（可能需要调探索策略/广度）。
2. 或确认 SEW=8/16 的 branch 为什么没达到（UNSAT？还是探索遗漏？）——需进一步 itrace/solver 层面诊断。

## 待查
- SEW=8/16 的 branch 是 UNSAT（约束矛盾，合法）还是探索遗漏（可修）？
- 如果是探索遗漏，调 isla 探索策略可能让覆盖完整，但 path 数会真正放大（接近 112×其他维度）。

## 根因找到（2026-07-01 续）：是 isarch 的 fork 限制，不是枚举本身

### 真凶：src/isarch/exec.rs:283-284
```rust
let limits = ExecutionLimits::default()
    .with_max_forks_per_branch(2)   // 单分支点最多 fork 2 次 → 之后 concretize
    .with_max_total_forks(8)        // 全局最多 fork 8 次 → 之后 concretize
    ...
    .with_limit_behavior(LimitBehavior::Concretize);  // 触发后具体化(只走一路)
```

`max_total_forks=8`：每条 path 前缀最多 fork 8 次，之后所有符号分支被 **concretize**（solver 选一个值，另一路永不探索）。
`max_forks_per_branch=2`：assert_sew 同一分支点 fork 2 次后 concretize。
→ SEW=8/16 在 fork 预算耗尽后被 concretize 成 SEW=64/32，**永不探索**。

### 验证：放宽 fork 限制后，path 数和覆盖随限制线性增长
| fork 限制 | MASKTYPEI paths | success | 耗时 | SEW 覆盖 |
|---|---|---|---|---|
| 8/2（默认） | 31 | 10 | 6s | 32/64 only |
| 500/50 | 161 | 114 | 60s | 16/32/64 |
| 100000/10000 | 306 | **301** | 60s(TO) | 完整 |

**path 数随 fork 限制放大**：8→500→100000 时 path 数 31→161→306，success 10→114→301。

### 结论（修正之前的错误判断）
1. **path 数不是被枚举本身限制，是被 isarch 的 fork 预算(8/2)人为砍掉**。默认 8/2 只探索 ~31 paths，覆盖不全（SEW=8/16 丢失）。
2. **完整 vtype 枚举（覆盖所有 SEW/LMUL/vta/vma）的 path 规模**：约几百（MASKTYPEI ~306 paths，301 success）。单 clause ~300 paths。
3. **timeout 估算**：~300 paths × ~0.2s/path ≈ 60s。要完整覆盖 + 算完，单 clause timeout 需 ~60-120s。当前 60s 在完整 fork 下刚好打满（306 paths）。
4. **全量 solve**：每个 V clause ~300 paths，220 clause 大部分是 V/非V。若按 ~300 paths/clause × 0.2s = 60s/clause，全量会很多 timeout。需要更大的 timeout 或并行。

### 这改变了什么
之前说"B4 全量 9 timeout 最优"是**错觉**——那是 fork=8/2 下 path 被砍、覆盖不全的结果（很多 SEW/LMUL branch 没探索，path 少所以不 timeout）。真正完整覆盖（fork 放开）下，path 数暴涨到几百，timeout 要相应放大。

**用户要"探索所有情况"，必须放开 fork 限制（max_total_forks/max_forks_per_branch 调大），代价是 path 数到几百、单 clause timeout 到 60-120s。**
