# agent03 PMA region map

日期：2026-04-27

范围：只抽取当前 `isla/.worktrees/zstore-pma-mmio/rv64d.ir` 中 `register zpma_regions` 与 `sail-riscv/build/config/rv64d_v256_e64.json` 中 `memory.regions`，并推导 `zSTORE` / `zLOAD` 固定 `width=4` 时 `matching_pma_bits_range`、`pmaCheck` 和后续 RAM/MMIO 分派的区域边界。

## 来源与顺序

- Sail JSON 的 `memory.regions` 位于 `sail-riscv/build/config/rv64d_v256_e64.json:103`。
- IR 的 `register zpma_regions` 位于 `isla/.worktrees/zstore-pma-mmio/rv64d.ir:46328`。
- IR 里依次 `cons` RAM、MMIO、ROM；由于 `cons` 头插，最终 list 顺序与 JSON 一致：ROM -> MMIO -> RAM。
- `matching_pma_bits_range` 取第一个满足 `range_subset(base, size, pma.base, pma.size)` 的 PMA region；当前 3 个 region 不重叠。

## 当前 concrete PMA regions

| 顺序 | 名称 | base | size | 起止范围 | attributes | include_in_device_tree |
|---:|---|---:|---:|---|---|---|
| 0 | ROM | `0x0000000000001000` | `0x0000000000001000` | `[0x1000, 0x2000)` | `cacheable=true`, `coherent=true`, `executable=false`, `readable=true`, `writable=false`, `read_idempotent=true`, `write_idempotent=true`, `misaligned_fault=NoFault`, `reservability=RsrvNone`, `supports_cbo_zero=false` | `false` |
| 1 | MMIO PMA | `0x0000000002000000` | `0x0000000002000000` | `[0x02000000, 0x04000000)` | `cacheable=false`, `coherent=true`, `executable=false`, `readable=true`, `writable=true`, `read_idempotent=false`, `write_idempotent=false`, `misaligned_fault=AlignmentFault`, `reservability=RsrvNone`, `supports_cbo_zero=false` | `false` |
| 2 | RAM | `0x0000000080000000` | `0x0000000080000000` | `[0x80000000, 0x100000000)` | `cacheable=true`, `coherent=true`, `executable=true`, `readable=true`, `writable=true`, `read_idempotent=true`, `write_idempotent=true`, `misaligned_fault=NoFault`, `reservability=RsrvEventual`, `supports_cbo_zero=true` | `true` |

说明：

- `include_in_device_tree` 只影响设备树生成，不影响 Sail 执行。
- `cacheable` / `coherent` 当前在 PMA check 中没有执行效果；`read_idempotent` / `write_idempotent` 当前也没有参与 `pmaCheck` 判定。
- `supports_cbo_zero` 只影响 `CacheAccess(CB_zero())`。

## 每个 region 对访问类型的影响

`pmaCheck` 的顺序是：先 `matching_pma`，无匹配则 `accessFaultFromAccessType(access)`；有匹配后先按 `misaligned_fault` 处理 misaligned，再按访问类型检查权限。

以下表格按 aligned 情况描述；若访问落在 MMIO PMA 且 `paddr[1:0] != 0`，`width=4` 时会先返回 access-specific alignment fault。

| Region | Load(Data) | Store(Data) | Misaligned | LR/SC | Atomic | Cache access |
|---|---|---|---|---|---|---|
| ROM | 允许，后续进入非-MMIO RAM read 分派 | `E_SAMO_Access_Fault`，因为 `writable=false` | `NoFault`，PMA 不因 misaligned 报错 | LR: `E_Load_Access_Fault`；SC: `E_SAMO_Access_Fault`，因为 `reservability=RsrvNone` 且 store 不可写 | `E_SAMO_Access_Fault`，因为 atomic 要求 readable & writable | `CB_zero` fault；`CB_manage` 允许；`PREFETCH_R` 允许，`PREFETCH_W/I` fault |
| MMIO PMA | aligned 时允许 | aligned 时允许 | `AlignmentFault`，Load -> `E_Load_Addr_Align`，Store/AMO/CB_zero/CB_manage -> `E_SAMO_Addr_Align` | aligned LR/SC 仍 fault，因为 `reservability=RsrvNone` | aligned atomic 允许，因为 PMA 只要求 readable & writable | `CB_zero` fault；`CB_manage` 允许；`PREFETCH_R/W` 允许，`PREFETCH_I` fault |
| RAM | 允许 | 允许 | `NoFault`，PMA 不因 misaligned 报错 | LR/SC 允许，`reservability=RsrvEventual` | 允许 | `CB_zero`、`CB_manage`、`PREFETCH_R/W/I` 均允许 |

额外边界：

- 普通 `zLOAD` / `zSTORE` 的 Data access 对应 `Load(_)` / `Store(_)`，通常 `res_or_con=false`。
- LR/SC 还会受外层 `mem_read_priv_meta` / `mem_write_value_priv_meta` 的对齐检查影响：`res=true` 或 `con=true` 且 misaligned 时，可能在进入 `checked_mem_*` / `pmaCheck` 前先得到 alignment fault。
- 当前 Sail 模型注释说明 atomic PMA 尚未细分 AMO 类型；`pmaCheck` 对 `Atomic(_,_,_)` 只要求 readable & writable。

## width=4 时 matching_pma_bits_range 的互斥地址分区

`matching_pma_bits_range(pma_regions, paddr, 4)` 要求 `[paddr, paddr + 4)` 完全包含在某个 PMA region 内。当前 region 都不 wrap，因此每个匹配区间的起始地址上界是 `region_end - 4`。

| paddr 起始地址区间，闭区间 | matching result | 说明 |
|---|---|---|
| `0x0000000000000000..0x0000000000000fff` | `None()` | ROM 前空洞 |
| `0x0000000000001000..0x0000000000001ffc` | ROM | `[paddr,paddr+4)` 完整落在 ROM |
| `0x0000000000001ffd..0x0000000001ffffff` | `None()` | ROM 尾部跨界与 MMIO 前空洞 |
| `0x0000000002000000..0x0000000003fffffc` | MMIO PMA | `[paddr,paddr+4)` 完整落在 MMIO PMA |
| `0x0000000003fffffd..0x000000007fffffff` | `None()` | MMIO 尾部跨界与 RAM 前空洞 |
| `0x0000000080000000..0x00000000fffffffc` | RAM | `[paddr,paddr+4)` 完整落在 RAM |
| `0x00000000fffffffd..0xffffffffffffffff` | `None()` | RAM 尾部跨界与高地址空洞 |

这些是 `matching_pma_bits_range` 的 region 边界。对 `pmaCheck` 还需要在 MMIO PMA 匹配区间内继续按 `paddr[1:0] == 0` 划分 aligned / misaligned。

## access fault 与 RAM/MMIO 分派

### zLOAD, width=4, Load(Data)

| 条件 | pmaCheck 结果 | 后续分派 |
|---|---|---|
| `matching_pma_bits_range == None()` | `E_Load_Access_Fault` | 不分派 |
| ROM 匹配 | `None()` | `within_mmio_readable=false`，进入 `read_ram` |
| MMIO PMA 匹配且 `paddr[1:0] != 0` | `E_Load_Addr_Align` | 不分派 |
| MMIO PMA 匹配且 `paddr[1:0] == 0` | `None()` | 再由 `within_mmio_readable` 决定 CLINT/HTIF MMIO 还是 `read_ram` |
| RAM 匹配 | `None()` | `within_mmio_readable=false`，进入 `read_ram` |

### zSTORE, width=4, Store(Data)

| 条件 | pmaCheck 结果 | 后续分派 |
|---|---|---|
| `matching_pma_bits_range == None()` | `E_SAMO_Access_Fault` | 不分派 |
| ROM 匹配 | `E_SAMO_Access_Fault` | 不分派 |
| MMIO PMA 匹配且 `paddr[1:0] != 0` | `E_SAMO_Addr_Align` | 不分派 |
| MMIO PMA 匹配且 `paddr[1:0] == 0` | `None()` | 再由 `within_mmio_writable` 决定 CLINT/HTIF MMIO 还是 `write_ram` |
| RAM 匹配 | `None()` | `within_mmio_writable=false`，进入 `write_ram` |

当前平台 MMIO 分派不是直接由 PMA region 名称决定：

- JSON 中 `platform.clint.base = 33554432 = 0x02000000`，`platform.clint.size = 786432 = 0x000c0000`。
- `within_clint(paddr, 4)` 的起始地址区间是 `0x0000000002000000..0x00000000020bfffc`。
- 因此 aligned 且落在这个 CLINT 区间内的 MMIO PMA access 会进入 `clint_load` / `clint_store`；CLINT 内部还只接受少数 exact offsets：`0x0`, `0x4000`, `0x4004`, `0xbff8`, `0xbffc`，其它 offset 会在 `clint_*` 中返回 access fault。
- 默认 `htif_tohost_base=None()`；除非外部 `enable_htif`，HTIF 不贡献当前分派区间。
- MMIO PMA 中 aligned 但不满足 `within_mmio_readable/writable` 的地址，在当前 `checked_mem_*` 结构里会走 `read_ram` / `write_ram`，而不是 `mmio_read` / `mmio_write`。

## exact pmaCheck summary 的循环规模与 solver 负担

当前 exact `pmaCheck` summary 只需要覆盖 3 个 concrete PMA region：

1. ROM subset predicate: `range_subset(paddr, 4, 0x1000, 0x1000)`
2. MMIO subset predicate: `range_subset(paddr, 4, 0x02000000, 0x02000000)`
3. RAM subset predicate: `range_subset(paddr, 4, 0x80000000, 0x80000000)`

预期负担：

- Region 循环规模固定为 3，比 PMP 当前 `sys_pmp_count=16` 小很多。
- 每个 region 的匹配公式是 64-bit bitvector 上的常量边界比较；`width=4` concrete 后没有动态宽度问题。
- 访问类型若限制在 `Load(Data)` / `Store(Data)`，权限判定退化为常量布尔；唯一额外符号条件是 MMIO PMA 内的 `paddr[1:0] != 0` alignment fault。
- 不建议直接 summary `matching_pma_bits_range` 的 `option(PMA_Region)`，因为返回 struct/option 会把 PMA 属性选择带给后续代码；更合适的是在 `pmaCheck` 层直接合成 `option(ExceptionType)`，保留 access fault / alignment fault / success 三类可观察结果。
- 对 `zLOAD`，PMA summary 的最终 outcome 类大致是：no-match access fault、ROM success、MMIO aligned success、MMIO misaligned alignment fault、RAM success。
- 对 `zSTORE`，最终 outcome 类大致是：no-match access fault、ROM access fault、MMIO aligned success、MMIO misaligned alignment fault、RAM success。
- solver 成本预计低于现有 PMP exact summary，也低于把 CLINT/MMIO 子分派一起吞掉的大 summary；PMA summary 应只推进到 `checked_mem_*` 的 RAM/MMIO 分派点，后续 `within_mmio_*` / `clint_*` 可单独评估。

## 结论

当前 concrete PMA 配置非常小：ROM、MMIO PMA、RAM 共 3 项。`width=4` 时 `matching_pma_bits_range` 的互斥边界完全由各 region 的 `base` 和 `end-4` 决定；PMA access fault 主要来自 no-match 和 ROM store，MMIO misaligned 是 alignment fault 而不是 access fault。exact `pmaCheck` summary 的 region 循环规模小、公式简单，适合优先做在 `pmaCheck` 层，并把 CLINT/HTIF MMIO 分派留给后续 summary 或原 IR。
