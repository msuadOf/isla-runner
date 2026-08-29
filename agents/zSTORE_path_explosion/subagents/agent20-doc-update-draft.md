# agent20 PMA/MMIO 文档收敛草稿

日期：2026-04-27

范围：只为 main agent 准备文档收敛草稿；本文件不是权威状态文件。已阅读：

- `agents/findings.md`
- `agents/zSTORE_path_explosion/plan.md`
- `agents/zSTORE_path_explosion/status.md`
- `agents/zSTORE_path_explosion/suggest.md`
- `agents/zSTORE_path_explosion/principles.md`
- `agents/zSTORE_path_explosion/review.md`
- `agents/zSTORE_path_explosion/audit.md`

## 1. `status.md` 下一步如何从 PMP 转 PMA/MMIO

建议把 `status.md` 的“下一步”收敛为下面这条路线：

PMP 阶段先冻结为当前局部成果：保留 `range_subset`、`split_misaligned` alignment guard、`pmpRangeMatch`、小粒度 PMP summaries，以及显式 `ISLA_RISCV_BUILTIN_PMP_CHECK=1` 的 exact summary。`ISLA_RISCV_ASSUME_PMP_OFF=1` 只保留为诊断/保底假设；`ISLA_RISCV_BUILTIN_PMP_MATCH_ADDR` 继续默认关闭。

PMA/MMIO 阶段的起点应使用 `pmpCheck` exact summary 后的 profile，而不是 PMP-off 结果作为语义基线。当前可引用的基线是 `/tmp/isla-pmpcheck-profile-vmem-off-20260427-postfix`：exit `0`，生成 `zSTORE` 46 条、`zLOAD` 40 条 JSON path，`total_fork_events=618`、`max_fork_events=12`，热点为 `matching_pma_bits_range=150`、`get_X=120`、`clint_store=80`、`phys_access_check=76`、`clint_load=65`、`within_mmio_writable=26`、`clint_dispatch=24`、`within_mmio_readable=21`。

下一步优先做 `pmaCheck` 层 summary，而不是直接把 `matching_pma_bits_range` 做成外部可见 summary。理由是 `matching_pma_bits_range` 返回 `option(PMA_Region)`，符号地址跨多个 region 时 payload 会复杂化；`pmaCheck` 的可观察返回是 `option(ExceptionType)`，更接近上层需要的结果，也可以保留 first-match、misaligned fault、权限判断和 access fault 语义。

建议新增的执行顺序：

1. 在 `pmpCheck` exact summary 开启、VMEM off、fixed `zSTORE` / `zLOAD` width、显式 aligned 前提下，重跑 PMA/MMIO profile，确认 `postfix` 结果仍稳定。
2. 增加显式 gate `ISLA_RISCV_BUILTIN_PMA_CHECK=1`，默认先关闭；支持边界先收紧到 `pma_regions` concrete list、64-bit paddr/region base/size、concrete width、支持的 access ctor、可构造对应 `ExceptionType`。
3. `pmaCheck` summary 只返回 `None()` 或 `Some(ExceptionType)`，不得提前产生 RAM memory event、MMIO event、callback，且不得决定 non-MMIO/plain-RAM。
4. 对 `pmaCheck` on/off 比较 `ret_val`、memory events、fault 类型、path/fork profile；若 PMA 不再是热点，再评估 `within_mmio_readable/writable`。
5. `within_mmio_*` 之后才看 CLINT；`clint_load` 优先于 `clint_store`，`clint_store` 第一版只应考虑 concrete addr/width 精确命中，因为它会写 `mip` / `mtimecmp` / `mtime` 并调用 `clint_dispatch`。

必须保留的边界：

- 不能隐式把 unknown PMA 当普通 RAM。
- 不能隐式关闭 MMIO。
- `pmaCheck` 返回 `None()` 后仍要让 `checked_mem_read/write` 按 `within_mmio_*` 决定 RAM/MMIO 分派。
- access fault、alignment fault、MMIO callback、memory event 分界都必须保留。

## 2. `suggest.md` 优先级是否需要调整

建议调整，但不是推翻现有排序，而是在 PMA/MMIO 条目内部细化优先级。

建议排序：

1. `pmaCheck`：当前 PMA/MMIO 阶段第一优先级。它能把 `matching_pma_bits_range`、misaligned fault、PMA permission 判断收敛到 `option(ExceptionType)`，比直接 summary `matching_pma_bits_range` 更接近可观察语义。
2. `matching_pma` / `matching_pma_bits_range`：保留为 `pmaCheck` 内部子表达式或局部 helper，不建议作为独立默认 summary 的第一目标。原因是返回 `Some(PMA_Region)` payload 会让符号多 region 场景变复杂。
3. `within_mmio_readable` / `within_mmio_writable`：排在 `pmaCheck` 之后。它们决定 RAM 还是 MMIO，对 memory event、callback、device side effect 分界有直接影响，因此不能早于 PMA fault/permission 层做近似。
4. `clint_load`：排在 `within_mmio_*` 之后，且优先于 `clint_store`。读路径主要是 exact addr/width dispatch 和寄存器读取，风险相对低。
5. `clint_store` / `clint_dispatch`：最后处理。它包含 guarded register update、`clint_dispatch`、timer/interrupt 可观察状态，第一版只适合 concrete addr/width 精确命中；符号地址应回退 IR。

因此，`suggest.md` 里 “PMA/MMIO 当前下一优先级” 结论应保留，但建议把 `matching_pma_bits_range` 从“候选函数同级目标”降为 `pmaCheck` 内部机制，把 `pmaCheck` 明确升为 PMA/MMIO 阶段主入口。

## 3. `findings.md` 拟新增事实草稿

以下条目只是草案，等待其它 subagents 结果后再由 main agent 合并，不直接改 `findings.md`。

### 2026-04-27 PMA/MMIO 阶段候选事实

- PMP exact summary 后，完整语义路线的 `zSTORE` / `zLOAD` VMEM off 样例已经从 PMP 转到 PMA/MMIO 热点。证据目录是 `/tmp/isla-pmpcheck-profile-vmem-off-20260427-postfix`：exit `0`，生成 `zSTORE` 46 条、`zLOAD` 40 条 JSON path，`total_fork_events=618`、`max_fork_events=12`；热点排序为 `matching_pma_bits_range`、`get_X`、`clint_store`、`phys_access_check`、`clint_load`、`within_mmio_*`。
- `matching_pma_bits_range` 定义在 `sail-riscv/model/sys/pma.sail:108`，递归返回第一个完全包含 `[base, base+size)` 的 `PMA_Region`；判断使用 `range_subset(base, size, pma.base, pma.size)`，因此必须保留既有 wrap-around bitvector 语义。`matching_pma` 在 `sail-riscv/model/sys/pma.sail:121` 把 `physaddr` zero-extend 并把 `width` 转成 bits 后委托给 `matching_pma_bits_range`。
- IR 中对应函数是 `isla/rv64d.ir:46177` 的 `zmatching_pma_bits_range`、`isla/rv64d.ir:46210` 的 `zmatching_pma`，以及 `isla/rv64d.ir:46860` 的 `zpmaCheck`。`zpmaCheck` 内部先调用 `zmatching_pma`。
- `pmaCheck` 定义在 `sail-riscv/model/sys/mem.sail:75`。当没有匹配 PMA region 时返回 `Some(accessFaultFromAccessType(access))`；匹配后先根据 `attributes.misaligned_fault` 和 `is_aligned_addr` 决定 access fault 或 alignment fault，再按 access ctor 检查 executable/readable/writable/reservability/cache access 等权限，失败时返回 access fault，成功时返回 `None()`。
- `phys_access_check` 定义在 `sail-riscv/model/sys/mem.sail:171`，先分别求 `pmpCheck` 与 `pmaCheck`，若两边都有 fault，则通过 `highestPriorityAlignmentOrAccessFault` 选择优先级更高的异常。因此 PMA summary 不能绕过 PMP/PMA 异常优先级组合。
- `checked_mem_read` / `checked_mem_write` 在 `sail-riscv/model/sys/mem.sail:199` 和 `sail-riscv/model/sys/mem.sail:264` 只在 `phys_access_check` 返回 `None()` 后才调用 `within_mmio_readable/writable`；MMIO 为真时走 `mmio_read/write`，否则走 `read_ram/write_ram`。所以 `pmaCheck` summary 不能提前产生 RAM/MMIO memory event。
- `within_mmio_readable` / `within_mmio_writable` 定义在 `sail-riscv/model/sys/platform.sail:333` 和 `sail-riscv/model/sys/platform.sail:338`。`get_config_rvfi()` 为真时直接 false；否则分别检查 CLINT 与 HTIF 范围。`within_clint` 在 `sail-riscv/model/sys/platform.sail:23` 使用 unbounded integer 边界检查避免地址加法 overflow，不是普通 bitvector wrap 比较。
- `mmio_read` / `mmio_write` 在 `sail-riscv/model/sys/platform.sail:343` 和 `sail-riscv/model/sys/platform.sail:350` 先 dispatch CLINT，再 dispatch HTIF，否则返回对应 access fault。
- `clint_load` 定义在 `sail-riscv/model/sys/platform.sail:72`，只允许 MSIP、MTIMECMP、MTIME 等 exact aligned addr/width 组合，未映射组合返回 `Err(accessFaultFromAccessType(access))`。
- `clint_store` 定义在 `sail-riscv/model/sys/platform.sail:141`，会写 `mip[MSI]`、`mtimecmp` 或 `mtime`，并调用 `clint_dispatch`；未映射组合返回 `Err(E_SAMO_Access_Fault())`。因此 `clint_store` summary 的 side-effect 风险高于 `clint_load`。

## 4. 历史结论保留/过期标记建议

建议保留：

- `principles.md` 中的最高原则：语义等价、fail closed、显式外部前提、不能静默近似成功。
- `plain-ram` VMEM builtin 只能作为显式 identity translation、PMP permits、plain RAM、non-MMIO、aligned 前提下的快速路径；不能作为最终完整语义。
- `range_subset` summary 是正结果，但只提供局部收益。
- `split_misaligned` alignment guard 是正结果，但不是完整 misaligned split；concrete misaligned 和允许 misaligned split 的多段 memory event 仍不能近似。
- `pmpRangeMatch` summary、小粒度 PMP summaries、显式 `pmpCheck` exact summary 的结论应保留。
- `pmpMatchAddr` 单函数 summary 保留为实验 gate、默认关闭。
- `ISLA_RISCV_ASSUME_PMP_OFF=1` 只保留为诊断/显式 init 前提。
- 当前 `rv64d.ir` 的 `plat_enable_misaligned_access` 来自生成期 JSON，运行时 TOML 不能覆盖 top-level `let` 的结论仍需保留。

建议标记为过期或降级：

- “下一步主要处理 PMP 配置/循环层”已经过期；在 `ISLA_RISCV_BUILTIN_PMP_CHECK=1` 后，下一步应转 PMA/MMIO。
- 早期 `pmpRangeMatch` profile 中带 enum sort panic 的数据只能作为趋势证据；应以 enum sort 修正后的记录和 `postfix` profile 为准。
- 早期 `pmpMatchAddr` “75 秒 0 条 profile path”不是唯一判断依据；enum sort 修复后它能完成路径，但吞吐仍差，因此当前理由应改成“solver 成本/吞吐不适合默认开启”。
- 把 `matching_pma_bits_range` 作为独立首要 summary 的倾向应降级；当前更合适的是 `pmaCheck` 层 summary。
- 继续扩大 `subrange_internal` 处理动态 bitvector 结果宽度的方向应标记过期；`split_misaligned` guard 已移开显式 aligned 场景的诊断阻断。
- 大而全的 `vmem_read_addr` / `vmem_write_addr` 粗粒度 builtin 作为最终路线应标记过期；它们只适合作为性能基线或显式 plain-RAM 快速路径。
- concrete misaligned 在 plain-RAM 前提校验前直接返回 alignment exception 的早期逻辑已过期；当前必须通过显式 gate 和前提校验。

## 5. main agent 最终汇报模板

```text
DONE

已完成 PMA/MMIO 阶段文档收敛草稿，未修改现有权威文档。

写入：
- agents/zSTORE_path_explosion/subagents/agent20-doc-update-draft.md

草稿结论：
- status.md 下一步建议从 PMP exact summary 的正结果切到 PMA/MMIO；以 pmpCheck exact summary 后的 profile 为语义基线，不用 PMP-off 代替。
- suggest.md 建议把 PMA/MMIO 内部优先级细化为 pmaCheck -> matching_pma 内部子表达式 -> within_mmio_* -> clint_load -> clint_store/clint_dispatch。
- findings.md 拟新增 PMA/MMIO source/IR 事实、profile 证据和 side-effect 边界；当前只写草案，等待其它 subagents 结果后再合并。
- 历史结论中保留语义原则、range_subset/split/pmpRange/pmpCheck 结果；标记“下一步 PMP”、大 VMEM builtin 终局路线、matching_pma_bits_range 独立首要目标等为过期或降级。
```
