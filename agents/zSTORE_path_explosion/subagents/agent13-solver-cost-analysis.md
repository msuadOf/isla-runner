# agent13 solver cost analysis: PMA summary 粒度

日期：2026-04-27

范围：只从 solver 成本角度评估 `matching_pma_bits_range`、`pmaCheck`、`phys_access_check` 三种 PMA 相关 summary 粒度。不改生产代码。

已读取：

- `agents/findings.md`
- `agents/zSTORE_path_explosion/status.md`
- `agents/zSTORE_path_explosion/suggest.md`
- 相关 Sail/IR：`sail-riscv/model/sys/pma.sail`、`sail-riscv/model/sys/mem.sail`、`isla/rv64d.ir`

## 当前 PMA 形态

当前 `rv64d.ir` 中 `pma_regions` 固化为 3 个 region：

1. ROM: base `0x1000`, size `0x1000`, readable, not writable, `misaligned_fault = NoFault`
2. MMIO/CLINT range: base `0x02000000`, size `0x02000000`, readable/writable, `misaligned_fault = AlignmentFault`
3. RAM: base `0x80000000`, size `0x80000000`, readable/writable/executable, `misaligned_fault = NoFault`

`matching_pma_bits_range` 对每个 region 调用一次 `range_subset(base, size, pma.base, pma.size)`。`range_subset` 的语义条件是：

```text
a_begin = base - pma.base
a_end   = (base + size) - pma.base
b_end   = (pma.base + pma.size) - pma.base

a_begin <=u b_end
and a_end <=u b_end
and a_begin <=u a_end
```

因此下面估算里把一个 region match 计为：

- 1 个语义 match condition
- 3 个 BV unsigned comparison
- 若不做常量化/共享，约 3 个 BV add/sub 中间项

## 三种 summary 粒度的 SMT 规模比较

### 1. `matching_pma_bits_range` summary

形态：

```text
ite(match_0, Some(region_0),
  ite(match_1, Some(region_1),
    ...
      ite(match_n, Some(region_n), None)))
```

规模：

- region match 成本为 `O(R)`，`R` 是 PMA region 数。
- 对 `R` 个 region，需要 `R` 个 match condition，也就是约 `3R` 个 unsigned BV comparison。
- first-match 结果需要约 `R` 层 ITE。
- 返回值是 `option(PMA_Region)`，不是小枚举。若实现需要把 `Some(region_i)` 的 payload 作为符号值继续传递，后续读取 `attributes` 时可能把 `PMA_Region` 的每个字段都变成 region ITE 链。
- `PMA_Region` payload 包含 `base`、`size`、`include_in_device_tree` 和 `PMA` 的 10 个属性字段；如果按字段 ITE 表达，3 个 region 就可能额外产生约 `13 * 3 = 39` 个字段选择 ITE，未来 region 增多时线性放大。

判断：

- 它能消掉函数内部递归/IR jump，但 solver 需要保留“命中哪个 region”的符号结果。
- 这个粒度太靠前，仍把 misalignment、read/write/execute 权限、access fault/alignment fault 等判断留给 `pmaCheck` 下游。
- 不建议作为优先默认方向；最多作为显式实验 gate。

### 2. `pmaCheck` summary

形态：

```text
region_match_i = range_subset(...)
region_error_i = f(region_i.attributes, access, aligned)

ite(match_0, region_error_0,
  ite(match_1, region_error_1,
    ...
      ite(match_n, region_error_n, access_fault)))
```

规模：

- region match 部分仍是 `O(R)`：约 `R` 个 match condition、`3R` 个 unsigned BV comparison、`R` 层 first-match ITE。
- 返回值收敛为 `option(ExceptionType)`，当前 store/load/fetch 场景下是很小的返回域：`None`、对应 access fault、对应 alignment fault。
- 如果 `access` 是 concrete ctor，例如当前 `zSTORE` 的 `Store(_)`，`canAccess` 可以按 region 常量折叠：
  - ROM store：writable 为 false，命中即 access fault。
  - MMIO store：writable 为 true，但 misaligned 时 alignment fault。
  - RAM store：writable 为 true，`NoFault`，命中即 `None`。
- 只有在想支持 symbolic/generic `MemoryAccessType` 时，才需要额外表达 `InstructionFetch`、`Load`、`Store`、LR/SC、Atomic、CacheAccess 等 access ctor 选择。第一版应要求 concrete access ctor，否则回退 IR。

当前 3-region、`Store(_)`、concrete width 的估算：

- 3 个 region match condition
- 9 个 unsigned BV comparison
- 3 层 region-result ITE
- 1 个共享 alignment condition
- 约 1 个额外 ITE 用于 MMIO `AlignmentFault if misaligned`
- 无 `PMA_Region` payload 字段 ITE

判断：

- 这是 PMA 侧最合理的第一候选粒度。
- 它保留 first-match、`range_subset` wrap 语义、MMIO alignment fault、ROM/RAM/MMIO 权限差异，但避免把 symbolic `PMA_Region` payload 暴露给下游。
- 相比 `matching_pma_bits_range`，它把 solver 公式直接压到可观察异常结果，表达规模更可控。

### 3. `phys_access_check` summary

形态：

```text
pmp_error = pmpCheck(...)
pma_error = pmaCheck(...)
combine(pmp_error, pma_error)
```

规模：

- PMA 部分至少等于 `pmaCheck` summary。
- PMP 部分若内联现有 exact `pmpCheck` summary，成本由 `sys_pmp_count` 主导；当前 IR 中 `sys_pmp_count = 16`，远大于 3 个 PMA region 的成本。
- wrapper 组合本身不大：`(None,None)`、`(Some,None)`、`(None,Some)`、`(Some,Some)` 约 3 到 5 个 option/tag condition；`Some,Some` 时再做 access/alignment fault priority。
- 但作为单个大 summary，会把 PMP exact formula、PMA formula 和 priority combine 全塞进一个 solver expression，profile 上更难区分 PMP 成本和 PMA 成本。

判断：

- 如果只是为了消掉 `phys_access_check` 自身少量 option-match fork，收益可能小于公式膨胀风险。
- 如果它内联 PMP，则很容易重演“大 summary 降低 executor fork、但 solver 吞吐下降”的问题。
- 不建议作为 PMA 默认入口。应先评估 `pmaCheck`；`phys_access_check` 只适合作为后续 profile/实验 gate。

## 当前 region 数为 3 时的 ITE / condition 估算

以当前 `zSTORE` 关注的 concrete `Store(_)`、concrete width、symbolic paddr 为例：

| 粒度 | region match condition | BV comparison | 结果 ITE | 额外 condition | 主要风险 |
| --- | ---: | ---: | ---: | ---: | --- |
| `matching_pma_bits_range` | 3 | 9 | 3 | payload 字段选择可能约 39 个字段 ITE | symbolic `PMA_Region` payload 继续污染下游 |
| `pmaCheck` | 3 | 9 | 3 | 1 个 alignment condition，约 1 个 alignment/result ITE | generic access ctor 支持过宽时会膨胀 |
| `phys_access_check` | PMA 3 + PMP 16-entry 公式 | PMA 9 + PMP 大量比较 | PMA 约 4 + PMP loop/priority ITE + option combine | option combine 约 3 到 5 个 condition | PMP/PMA 混合成大公式，profile 和默认 gate 风险高 |

补充：

- 这里的 `condition` 是语义 guard，不等同于所有 AST 节点数。
- `range_subset` 的 1 个 match condition 内部包含 3 个 unsigned BV comparison。
- 如果实现能强力常量折叠 `pma.base + pma.size - pma.base` 为 `pma.size`，每个 region 的 BV add/sub 会减少；但 3 个 comparison 仍然存在。

## Region 增多时的风险

PMA region 增多后，三种粒度都会至少线性增长：

- `matching_pma_bits_range`: `R` 个 match condition、`3R` 个 comparison、`R` 层 first-match ITE；如果 payload 字段 ITE 化，约 `13R` 个字段选择 ITE。设备平台把 MMIO 拆成多个窗口时，这个 payload 风险会很快变成主要成本。
- `pmaCheck`: 同样有 `R` 个 match condition 和 `3R` 个 comparison，但输出域固定为 `option(ExceptionType)`，不会随 PMA 字段数扩散。region 增多时仍有 ITE 深度风险，但比 symbolic region payload 可控。
- `phys_access_check`: PMA 的 `O(R)` 会叠加 PMP 的 `O(P)`。当前 `P=16` 已经明显大于 `R=3`；如果未来 `R` 增大，同时默认内联 PMP/PMA，solver 将承受一个更宽的组合公式。

因此，未来 region 增多时应避免默认启用 `matching_pma_bits_range` 和 `phys_access_check` 这种“把选择空间提前暴露给 solver”的大粒度 summary。`pmaCheck` 即使要默认开启，也需要 region-count guard 或 profile gate。

## 与 `pmpMatchAddr` 大 summary 负结果的类比

`pmpMatchAddr` 的经验很直接：

- 早期显式开启 `ISLA_RISCV_BUILTIN_PMP_MATCH_ADDR=1` 后，75 秒内没有完成任何 `fork_profile` path。
- enum sort 修复和小粒度 PMP summary 后，45 秒能完成 142 条 profile path，`max_fork_events=12`，但吞吐仍低于默认路线。
- 结论是：大 summary 可以降低 executor fork 深度，但会把路径选择压进一个复杂 SMT ITE/bitvector 公式，导致 solver 成本过高。

PMA 这里的对应风险是：

- `matching_pma_bits_range` 看起来只是在 3 个 region 里选择一个，但返回的是带大量属性字段的 `PMA_Region` payload。
- `phys_access_check` 看起来只是在合并 PMP/PMA 异常，但如果内联 `pmpCheck`，会把 16-entry PMP exact formula 和 PMA formula 绑在一起。
- 这两种都可能重复 `pmpMatchAddr` 的问题：profile 上 fork 变少，但 completed paths/sec 下降，甚至没有完成路径。

应吸取的原则：

- 优先 summary 小返回域、接近可观察结果的函数。
- 避免把“内部选择了哪个配置 entry/region”作为符号结构值暴露给下游。
- 对大 summary 先显式 gate 和 solver metrics，不因 fork 数下降就默认开启。

## 推荐 gate 策略

### 默认策略

- `matching_pma_bits_range` summary：默认关闭。不建议作为当前默认优化方向。
- `pmaCheck` summary：先默认关闭，作为显式实验 gate。若多组 profile 证明 solver 吞吐和语义回归都稳定，再考虑默认开启。
- `phys_access_check` summary：默认关闭。只在 `pmaCheck` 已证明收益后，再作为更大粒度实验比较。

当前可保留的默认开启对象仍应是已验证的小粒度 summary，例如 `range_subset`、`pmpRangeMatch`、PMP small summaries。PMA 这一层尚无 solver 侧证据，不应直接默认开。

### 实验 gate

建议拆成独立 gate，避免一个开关混合三种粒度：

- `ISLA_RISCV_BUILTIN_MATCHING_PMA_BITS_RANGE=1`
- `ISLA_RISCV_BUILTIN_PMA_CHECK=1`
- `ISLA_RISCV_BUILTIN_PHYS_ACCESS_CHECK=1`

实验 gate 命中条件建议保守：

- `pma_regions` 必须 concrete，且 region 数可读取。
- `paddr`/`base` 必须是可表达的 bitvector，当前先支持 64-bit。
- `width` 必须 concrete 或能稳定转成固定宽 bitvector。
- `access` 第一版必须是 concrete ctor；unsupported access 回退 IR。
- `get_config_print_pma()` 若可能为 true，涉及日志 side effect，应回退 IR 或明确记录 trace/log 边界。

### Profile gate

建议新增或扩展 profile-only 机制，而不是一开始就替换语义：

- `ISLA_RISCV_PROFILE_FORKS=1` 继续记录 fork 热点。
- 增加 solver/profile 侧统计，例如 `ISLA_RISCV_PROFILE_SOLVER=1` 或 `ISLA_RISCV_PROFILE_BUILTINS=1`。
- profile-only 模式可只估算/打印 summary expression 规模和 fallback reason，不改变执行结果。

## 决定默认开启前必须收集的 metrics

只看 fork count 不够，至少需要以下 metrics：

1. end-to-end 吞吐
   - wall time
   - completed paths
   - completed paths/sec
   - 是否在固定 timeout 内生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`

2. executor fork 指标
   - `total_fork_events`
   - `max_fork_events`
   - 按函数聚合的热点排序
   - `matching_pma_bits_range`、`pmaCheck`、`phys_access_check` 各自命中前后的差异

3. solver 指标
   - check-sat 调用次数
   - solver 总耗时、平均耗时、p95/p99 耗时
   - `unknown` / timeout 次数
   - model 构造和求值耗时
   - 当前 path 的 constraint 数、`DefineConst` 数、trace 长度

4. SMT expression 规模
   - 每次 summary 构造的 AST node count
   - ITE node count 和最大 ITE depth
   - BV comparison count
   - BV add/sub/concat/extract/zero-extend count
   - 序列化 SMT-LIB 字节数
   - symbolic enum/union/tag 数量

5. builtin 命中质量
   - hit count
   - fallback count 和 fallback reason
   - 每个 summary 的构造时间
   - `pma_regions` region 数分布
   - `access` ctor 分布
   - width 分布
   - aligned/misaligned 分布

6. 语义回归
   - final result 分布不变
   - exception 类型分布不变，特别是 access fault vs alignment fault priority
   - memory event count 分布不变
   - MMIO read/write callback、CLINT side effect、RAM event 分界不变
   - trace/probe/stop/function-assumption 边界若不同，必须明确接受或回退 IR

7. 配置覆盖
   - 当前 3-region 配置
   - synthetic 8/16/32-region PMA 配置
   - RAM-only、ROM+RAM、多 MMIO window、region 边界访问
   - constrained-to-RAM paddr 与 unconstrained symbolic paddr
   - Load/Store/InstructionFetch/LR/SC/AMO/CacheAccess
   - width 1/2/4/8/cache block
   - aligned 与 misaligned
   - `ISLA_RISCV_BUILTIN_PMP_CHECK=1` 开/关组合，避免 PMA 结论被 PMP 成本掩盖

## 结论

推荐路线：

1. 不优先做 `matching_pma_bits_range` 默认 summary；它返回 symbolic `PMA_Region` payload，solver 字段 ITE 风险高。
2. 优先实验 `pmaCheck` summary；它保留 PMA 语义边界，同时把输出压成小返回域 `option(ExceptionType)`。
3. 暂不默认做 `phys_access_check` summary；它容易把 PMP exact formula 和 PMA formula 合并成一个大 solver 问题。
4. PMA 新 summary 初始都应默认关闭，通过独立实验 gate 和 solver metrics 决定是否升为默认开启。

最终建议：`pmaCheck` 是当前最值得 profile 的 PMA summary 粒度，但默认开启条件尚不满足。
