# agent02: PMA/MMIO IR hotspots

日期：2026-04-27

范围：只分析 `isla/.worktrees/zstore-pma-mmio/rv64d.ir` 中 PMA/MMIO 相关函数。已按要求先读 `agents/findings.md`，再读 `agents/zSTORE_path_explosion/status.md` 和 `agents/zSTORE_path_explosion/suggest.md`。

源位置映射：IR 里的反引号源 ID 在本段相关代码中可读作：

- `60`: `sail-riscv/model/sys/platform.sail`
- `61`: `sail-riscv/model/sys/pma.sail`
- `62`: `sail-riscv/model/sys/mem.sail`

## 背景结论

`pmpCheck` exact summary 后热点转到 PMA/MMIO 是符合调用链的：`checked_mem_read/write -> phys_access_check -> pmpCheck + pmaCheck` 中，PMP 循环和配置位分支被 exact summary 吃掉后，仍然必经 `pmaCheck`。`pmaCheck` 会调用 `matching_pma(pma_regions, paddr, width)`，而 `matching_pma_bits_range` 对每个 PMA region 做一次 `range_subset`。符号地址能同时覆盖 RAM、CLINT/MMIO、ROM 或未覆盖空间时，这些 `range_subset` 命中/未命中就是新的 executor fork 源。

随后 `checked_mem_read/write` 在 `phys_access_check` 返回 `None` 后继续用 `within_mmio_readable/writable` 决定 RAM 还是 MMIO。CLINT PMA region 允许读写但实际 MMIO dispatch 还要过 `within_clint` 和 CLINT 精确寄存器地址匹配，所以热点继续扩散到 `within_mmio_*`、`clint_load`、`clint_store`、`clint_dispatch`。

状态文档中 `pmpCheck` exact summary 的 120 秒 profile 已体现这个转移：`matching_pma_bits_range=150`、`get_X=120`、`clint_store=80`、`phys_access_check=76`、`clint_load=65`、`within_mmio_writable=26`、`clint_dispatch=24`、`within_mmio_readable=21`，PMP 不再是热点。

## 相关 ctor/struct/enum/register

- `struct zPMA`: `rv64d.ir:3281`，字段包括 `zcacheable`、`zcoherent`、`zexecutable`、`zmisaligned_fault`、`zreadable`、`zwritable`、`zreservability`、`zsupports_cbo_zzero` 等。
- `struct zPMA_Region`: `rv64d.ir:3294`，字段为 `zattributes`、`zbase`、`zinclude_in_device_tree`、`zsizze`。
- `union zoptionzIRPMA_RegionzK`: `rv64d.ir:3301`，ctors 为 `zNonezIRPMA_RegionzK` / `zSomezIRPMA_RegionzK`。
- `enum zmisaligned_fault`: `rv64d.ir:671`，成员 `zNoFault`、`zAccessFault`、`zAlignmentFault`。
- `enum zReservability`: `rv64d.ir:3145`，成员 `zRsrvNone`、`zRsrvNonEventual`、`zRsrvEventual`。
- `union zMemoryAccessTypezIEmem_payloadz5zK`: `rv64d.ir:3346`，ctors 包括 `zInstructionFetch...`、`zLoad...`、`zStore...`、`zLoadReserved...`、`zStoreConditional...`、`zAtomic...`、`zCacheAccess...`。
- `enum zPrivilege`: `rv64d.ir:3176`，成员 `zUser`、`zVirtualUser`、`zSupervisor`、`zVirtualSupervisor`、`zMachine`。
- `union zExceptionType`: `rv64d.ir:3462`，本段主要用 `zE_Fetch_Access_Fault`、`zE_Load_Access_Fault`、`zE_SAMO_Access_Fault`、`zE_Fetch_Addr_Align`、`zE_Load_Addr_Align`、`zE_SAMO_Addr_Align`。
- `union zoptionzIUExceptionTypezK`: `rv64d.ir:3534`，ctors 为 `zNonezIUExceptionTypezK` / `zSomezIUExceptionTypezK`。
- CLINT 相关状态：`struct zMinterrupts` 在 `rv64d.ir:3334`，`zmtime` 在 `rv64d.ir:21604`，`zmip` 在 `rv64d.ir:23164`，`zmtimecmp` / `zstimecmp` 在 `rv64d.ir:44047` / `rv64d.ir:44049`。
- CLINT 常量：`zMSIP_BASE` `rv64d.ir:44051`，`zMTIMECMP_BASE` `rv64d.ir:44073`，`zMTIMECMP_BASE_HI` `rv64d.ir:44095`，`zMTIME_BASE` `rv64d.ir:44117`，`zMTIME_BASE_HI` `rv64d.ir:44139`。
- `zpma_regions`: `rv64d.ir:46328`。当前 IR 中可见三段 region：
  - RAM: base `0x0000000080000000`，size `0x0000000080000000`，`readable/writable/executable=true`，`misaligned_fault=zNoFault`，`reservability=zRsrvEventual`。
  - CLINT/MMIO PMA: base `0x0000000002000000`，size `0x0000000002000000`，`readable/writable=true`，`executable=false`，`misaligned_fault=zAlignmentFault`，`reservability=zRsrvNone`。
  - ROM-like region: base `0x0000000000001000`，size `0x0000000000001000`，`readable=true`，`writable=false`，`executable=false`，`misaligned_fault=zNoFault`。

注意：`zplat_clint_base` 为 `0x02000000`，但 `zplat_clint_sizze` 是 `786432` (`0x000c0000`)；PMA 的 CLINT/MMIO region 比 `within_clint` 的实际 CLINT dispatch 范围更大。因此 PMA 命中 CLINT region 后，后续 `within_mmio_*` 仍可能 fork 到 RAM/HTIF/CLINT/AccessFault 分支。

## 函数与 fork 点

### `zmatching_pma_bits_range`

- 起始行：`val` 在 `rv64d.ir:46177`，`fn` 在 `rv64d.ir:46179`。
- 源：`sys/pma.sail:109-116`。
- 关键 IR：
  - `rv64d.ir:46181`: `jump @not(@is_empty(zpmas)) goto 4`，源 `61 110:4-110:8`，对应 `match pmas { [||] => None(), ... }`。当前 `zpma_regions` 是 concrete list 时它本身不应是主要符号 fork，但递归每层都会经过。
  - `rv64d.ir:46201`: 调用 `zrange_subset(base, size, pma.base, pma.size)`，源 `61 112:9-112:53`。
  - `rv64d.ir:46202`: `jump zz43 goto 25`，源 `61 112:6-114:52`，对应 `if range_subset(...) then Some(pma) else ...`。这是 PMA 匹配链的主 fork 点。
  - `rv64d.ir:46203`: 未命中时递归 `zmatching_pma_bits_range(rest, base, size)`，源 `61 114:11-114:52`。
  - `rv64d.ir:46205`: 命中时返回 `zSomezIRPMA_RegionzK(zz41)`，源 `61 113:11-113:20`。
- 判断：主问题是 `range_subset` 的符号布尔被编译成控制流。该函数纯、无副作用，但返回 `option(PMA_Region)`，payload 是结构体 region；直接 summary 它会把多 region 的 `Some(region)` 选择搬到返回值表达式里，收益不如在 `pmaCheck` 层直接合成 `option(ExceptionType)`。

### `zmatching_pma`

- 起始行：`val` 在 `rv64d.ir:46210`，`fn` 在 `rv64d.ir:46212`。
- 源：`sys/pma.sail:122`。
- 关键 IR：
  - `rv64d.ir:46231`: `return = zmatching_pma_bits_range(zpmas, zz40, zz45)`，源 `61 122:2-122:75`。
- 内部无 `jump`。它只把 `physaddr` 转成 64-bit base，把 `width` 转成 64-bit size，再委托 `matching_pma_bits_range`。
- 判断：适合作为 `pmaCheck` summary 的内联 helper，不适合作为单独优先 summary 目标。

### `zpmaCheck`

- 起始行：`val` 在 `rv64d.ir:46860`，`fn` 在 `rv64d.ir:46862`。
- 源：`sys/mem.sail:82-151`。
- 关键 IR：
  - `rv64d.ir:46864`: 调用 `zmatching_pma(zpma_regions, zpaddr, zwidth)`，源 `62 82:8-82:47`。
  - `rv64d.ir:46866`: `jump zz40 is zNonezIRPMA_RegionzK goto 8`，源 `62 83:4-83:10`，对应 PMA miss -> access fault。
  - `rv64d.ir:46882`: `jump @neq(zAccessFault, zz47) goto 31`，源 `62 90:8-90:19`。
  - `rv64d.ir:46885`: `jump @not(zz49) goto 24`，源 `62 89:6-149:7`，对应 `AccessFault if misaligned` 的 guard。
  - `rv64d.ir:46894`: `jump @neq(zAlignmentFault, zz47) goto 43`，源 `62 91:8-91:22`。
  - `rv64d.ir:46897`: `jump @not(zz412) goto 36`，源 `62 89:6-149:7`，对应 `AlignmentFault if misaligned` 的 guard。
  - `rv64d.ir:46908` / `46911` / `46918` / `46921` / `46935` / `46949` / `46961` / `46972`: 对 `MemoryAccessType` ctor 的 match，源分别在 `sys/mem.sail:95`、`96`、`99`、`102`、`103`、`106`、`118`、`130`。
  - `rv64d.ir:46927`、`46941`、`46955`、`46966`、`46977`: `readable/writable/reservability/supports_cbo_zero` 等短路布尔。
  - `rv64d.ir:46986` / `46989`: `CB_prefetch` 的 `PREFETCH_R/W/I` 分支，源 `62 138:14-139:24`。
  - `rv64d.ir:46999` / `47005`: `get_config_print_pma() & not(canAccess)` 的日志分支，源 `62 144:13-145:111`。
  - `rv64d.ir:47023`: `jump zz415 goto 165`，源 `62 147:10-147:79`，对应最终 `if canAccess then None() else Some(accessFault...)`。
- 判断：这是最合适的 PMA summary 层。它返回 `option(ExceptionType)`，可以保留 first-match、region 属性、misaligned fault、权限和 access type 语义，同时避免向外暴露 `option(PMA_Region)` payload。需要保守处理 `get_config_print_pma()`：若开启打印，要么精确建模日志，要么回退 IR。

### `zphys_access_check`

- 起始行：`val` 在 `rv64d.ir:47110`，`fn` 在 `rv64d.ir:47112`。
- 源：`sys/mem.sail:178-185`。
- 关键 IR：
  - `rv64d.ir:47114`: `zpmpCheck(...)`，源 `62 178:41-178:77`。
  - `rv64d.ir:47116`: `zpmaCheck(...)`，源 `62 179:41-179:83`。
  - `rv64d.ir:47118` / `47119`: 匹配 `(None(), None())`，源 `62 181:5-181:19`。
  - `rv64d.ir:47122` / `47123`: 匹配 `(Some(e), None())`，源 `62 182:5-182:20`。
  - `rv64d.ir:47128` / `47129`: 匹配 `(None(), Some(e))`，源 `62 183:5-183:20`。
  - `rv64d.ir:47139`: 两边都是 `Some` 时调用 `zhighestPriorityAlignmentOrAccessFault`，源 `62 184:33-184:78`。
- 判断：`pmpCheck` exact summary 后，这里仍会作为 PMP/PMA 错误合并点出现。若 `pmaCheck` 也 summary 化，`phys_access_check` 可作为轻量 wrapper summary，消掉 option tuple match 的控制流。但不建议先在这里粗暴绕过 `pmaCheck`，否则容易漏掉 PMA alignment/access fault priority。

### `zwithin_mmio_readable`

- 起始行：`val` 在 `rv64d.ir:45992`，`fn` 在 `rv64d.ir:45994`。
- 源：`sys/platform.sail:334-336`。
- 关键 IR：
  - `rv64d.ir:45997`: `jump zz40 goto 29`，源 `60 334:2-336:80`，对应 `if get_config_rvfi() then false`。
  - `rv64d.ir:46001`: `jump zz41 goto 26`，源 `60 336:7-336:80`，对应 `within_clint(addr,width) | ...` 的 CLINT short-circuit。
  - `rv64d.ir:46005`: `jump zz43 goto 13`，源 `60 336:36-336:79`，对应 `within_htif_readable(addr,width) & 1 <= 'n`。
  - `rv64d.ir:46018`: `zlteq_int(1, width)`，源 `60 336:72-336:79`。
- 依赖 helper：
  - `zwithin_clint` 起始 `rv64d.ir:43955`；`rv64d.ir:43973` 对 `clint_base_int <= addr_int` 做 `jump`，源 `60 30:4-31:64`。
  - `zwithin_htif_writable` 中 `rv64d.ir:43999` 匹配 `htif_tohost_base` 的 `None/Some`，源 `60 36:4-36:10`。
- 判断：纯谓词，适合小 summary，但必须保留 `get_config_rvfi`、CLINT 范围、HTIF 是否启用和 width guard。

### `zwithin_mmio_writable`

- 起始行：`val` 在 `rv64d.ir:46028`，`fn` 在 `rv64d.ir:46030`。
- 源：`sys/platform.sail:339-341`。
- 关键 IR：
  - `rv64d.ir:46033`: `jump zz40 goto 29`，源 `60 339:2-341:80`，对应 `if get_config_rvfi() then false`。
  - `rv64d.ir:46037`: `jump zz41 goto 26`，源 `60 341:7-341:80`，对应 `within_clint(addr,width) | ...`。
  - `rv64d.ir:46041`: `jump zz43 goto 13`，源 `60 341:36-341:79`，对应 `within_htif_writable(addr,width) & 'n <= 8`。
  - `rv64d.ir:46054`: `zlteq_int(width, 8)`，源 `60 341:72-341:79`。
- 判断：和 readable 一样适合纯 predicate summary；写路径后续副作用在 `mmio_write/clint_store`，不能在这里直接假设 non-MMIO。

### `zclint_load`

- 起始行：`val` 在 `rv64d.ir:44161`，`fn` 在 `rv64d.ir:44163`。
- 源：`sys/platform.sail:73-125`。
- 关键地址/width ladder：
  - MSIP `addr == MSIP_BASE & (width == 8 | width == 4)`: `rv64d.ir:44182`、`44192`、`44202`，源 `60 76:5-76:44` / `60 76:2-125:3`。
  - MTIMECMP low 4-byte: `rv64d.ir:44211`、`44220`，源 `60 82:10-82:43` / `60 82:7-125:3`。
  - MTIMECMP 8-byte: `rv64d.ir:44229`、`44238`，源 `60 89:10-89:43` / `60 89:7-125:3`。
  - MTIMECMP_HI 4-byte: `rv64d.ir:44247`、`44256`，源 `60 96:10-96:46` / `60 96:7-125:3`。
  - MTIME low 4-byte: `rv64d.ir:44265`、`44274`，源 `60 103:10-103:40` / `60 103:7-125:3`。
  - MTIME 8-byte: `rv64d.ir:44283`、`44292`，源 `60 109:10-109:40` / `60 109:7-125:3`。
  - MTIME_HI 4-byte: `rv64d.ir:44301`、`44310`，源 `60 115:10-115:43` / `60 115:7-125:3`。
  - Not mapped: `rv64d.ir:44328` returns `zErrzIbzCUExceptionTypezK(accessFaultFromAccessType(access))`，源 `60 124:4-124:42`。
- 还有多处 `get_config_print_clint()` 日志分支：例如 `rv64d.ir:44314`、`44333`、`44372`、`44401`、`44440`、`44489`、`44518`、`44567`。
- 判断：load 本身除可选日志外无状态写，可做窄 summary，尤其是 concrete addr/width 精确命中时。对符号 addr/width 做完整 ladder summary 会产生多路 value ITE 和 exception ITE，收益需实测。

### `zclint_dispatch`

- 起始行：`val` 在 `rv64d.ir:44611`，`fn` 在 `rv64d.ir:44613`。
- 源：`sys/platform.sail:129-138`。
- 关键 IR：
  - 更新 `zmip[MTI]`：`mtimecmp <=_u mtime` 在 `rv64d.ir:44622-44641` 一段完成，无直接 `jump`，但写 `zmip`。
  - `rv64d.ir:44647`: `jump have_exception`，源 `60 131:5-131:31`，来自 `currentlyEnabled(Ext_Sstc)`。
  - `rv64d.ir:44651`: `jump zz415 goto 40`，源 `60 131:5-131:54`，Sstc enabled short-circuit。
  - `rv64d.ir:44663`: `jump zz414 goto 52`，源 `60 131:2-133:3`，决定是否更新 `zmip[STI]`。
  - `rv64d.ir:44696`: `get_config_print_clint()` 日志分支，源 `60 134:2-135:50`。
  - `rv64d.ir:44716`: `old_mip != mip.bits` 分支，源 `60 136:5-136:42`。
  - `rv64d.ir:44721`: `old_mip != mip.bits | mip_was_written` 分支，源 `60 136:2-138:3`。
  - `rv64d.ir:44726`: `zcsr_name_write_callback("mip", zz444)`，源 `60 137:4-137:39`。
- 判断：不适合先做宽 summary。它写 `zmip`，可能调用 CSR callback，还依赖 extension/config state。只有在完整建模 `zmip` 更新和 callback/event 语义后才可替代 IR。

### `zclint_store`

- 起始行：`val` 在 `rv64d.ir:44731`，`fn` 在 `rv64d.ir:44733`。
- 源：`sys/platform.sail:143-190`。
- 关键地址/width ladder：
  - MSIP `addr == MSIP_BASE & (width == 8 | width == 4)`: `rv64d.ir:44752`、`44762`、`44772`，源 `60 144:5-144:44` / `60 144:2-190:3`。
  - MTIMECMP 8-byte: `rv64d.ir:44781`、`44790`，源 `60 150:12-150:43` / `60 150:9-190:3`。
  - MTIMECMP low 4-byte: `rv64d.ir:44799`、`44808`，源 `60 156:12-156:43` / `60 156:9-190:3`。
  - MTIMECMP_HI 4-byte: `rv64d.ir:44817`、`44826`，源 `60 162:12-162:46` / `60 162:9-190:3`。
  - MTIME 8-byte: `rv64d.ir:44835`、`44844`，源 `60 168:12-168:40` / `60 168:9-190:3`。
  - MTIME low 4-byte: `rv64d.ir:44853`、`44862`，源 `60 174:12-174:40` / `60 174:9-190:3`。
  - MTIME_HI 4-byte: `rv64d.ir:44871`、`44880`，源 `60 180:12-180:43` / `60 180:9-190:3`。
  - Not mapped: `rv64d.ir:44904` returns `zErrzIozCUExceptionTypezK(zE_SAMO_Access_Fault(()))`，源 `60 189:4-189:30`。
- Side-effect/callback hot points:
  - Calls to `zclint_dispatch(false)`: `rv64d.ir:44939`、`44978`、`45009`、`45056`、`45103`、`45138`。
  - MSIP path calls `zclint_dispatch(true)`: `rv64d.ir:45211`。
  - Writes to `zmtime` / `zmtimecmp` / `zmip` occur in the same case bodies before dispatch.
- 判断：宽 summary 风险高。它有 architectural state writes and callback behavior through `clint_dispatch`。第一版最多处理 concrete addr/width 精确命中的小 case，并且必须显式写寄存器、调用/建模 dispatch 和保留 access fault。

## 最可能造成 fork 的 IR jump

优先级从高到低：

1. `rv64d.ir:46202` (`zmatching_pma_bits_range`): `range_subset` 命中/未命中。符号 `paddr,width` 对三个 PMA region 逐层尝试，这是 `matching_pma_bits_range=150` 的核心来源。
2. `rv64d.ir:46866` (`zpmaCheck`): `matching_pma` 的 `None/Some` option match。它把 PMA miss 和 concrete region payload 分开。
3. `rv64d.ir:46885` / `46897` (`zpmaCheck`): region misaligned policy + symbolic alignment。CLINT PMA 的 `zAlignmentFault` 使这一路尤其重要。
4. `rv64d.ir:47023` (`zpmaCheck`): final `canAccess`，把 permission/access type 判断转成 `None` vs access fault。
5. `rv64d.ir:47118-47129` (`zphys_access_check`): PMP/PMA option tuple match。PMP exact summary 后这里仍合并 `pmaCheck` 的 symbolic option。
6. `rv64d.ir:46001` / `46037` plus `rv64d.ir:43973` (`within_mmio_*` / `within_clint`): CLINT 范围判断，决定 RAM/MMIO 分派。
7. `zclint_load` ladder：`rv64d.ir:44182`、`44202`、`44220`、`44238`、`44256`、`44274`、`44292`、`44310`。符号地址或 width 会沿 exact register map 逐项 fork。
8. `zclint_store` ladder：`rv64d.ir:44752`、`44772`、`44790`、`44808`、`44826`、`44844`、`44862`、`44880`。写路径更贵，因为命中后还有 state writes 和 dispatch。
9. `zclint_dispatch` callback branch：`rv64d.ir:44716` / `44721`。当 `zmip` 是否变化或 `mip_was_written` 不固定时会 fork，并可能进入 CSR callback。

## Summary 建议

适合优先 summary：

- `zpmaCheck`: 首选。返回域是 `option(ExceptionType)`，语义边界清晰，可把 PMA region first-match、`range_subset`、misaligned fault、permission/access type 统一下沉成 SMT/ITE，避免直接返回 `PMA_Region` payload。
- `zphys_access_check`: 适合作为 `pmaCheck` summary 之后的 wrapper。目标是消掉 PMP/PMA option tuple match，必须保留 `highestPriorityAlignmentOrAccessFault`。
- `zwithin_mmio_readable` / `zwithin_mmio_writable`: 可做小谓词 summary，保留 `get_config_rvfi`、CLINT bounds、HTIF state、width guard。它们适合在 PMA 后继续压 fork。

不建议作为第一优先级 summary：

- `zmatching_pma_bits_range` / `zmatching_pma`: 纯函数，但返回 `option(PMA_Region)`。直接 summary 会把 region struct 选择变成返回 payload 问题；更适合内联到 `pmaCheck`。
- `zclint_load`: 可做窄 summary，但不适合先做宽符号 summary。concrete addr/width exact hit 可以低风险处理；符号 ladder 需要多路 Ok/Err value ITE，收益需要 profile 证明。

暂不适合宽 summary：

- `zclint_store`: 有 `mtimecmp/mtime/zmip` 等状态写，且调用 `clint_dispatch`。除非完整建模 side effect 和 callback，否则应回退 IR。
- `zclint_dispatch`: 有 `zmip` 写入、`currentlyEnabled(Ext_Sstc)`、`menvcfg[STCE]`、日志和 `csr_write_callback("mip", ...)`。不能只把它当纯函数。

## 最短结论

PMP exact summary 后，热点转向 PMA/MMIO 的直接原因是：PMP 被压平后，访存检查链里下一个仍保留 IR 控制流的是 `pmaCheck -> matching_pma_bits_range`；成功通过 PMA/PMP 后，又必须走 `within_mmio_*` 决定 RAM vs MMIO；CLINT 命中后进入 `clint_load/store` 的精确地址 ladder 和 `clint_dispatch` side effects。

下一步若实现 summary，建议顺序是：

1. `zpmaCheck` exact summary。
2. 可选 `zphys_access_check` wrapper summary。
3. `zwithin_mmio_readable/writable` predicate summary。
4. CLINT 只做 concrete exact-hit 小 case；不要先做宽 `clint_store` / `clint_dispatch` summary。
