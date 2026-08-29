# Phase 5 smoke matrix 2026-04-28

本轮在修复两个 Phase 5 blocker 后，用 subagent 并行只读执行 smoke 矩阵。所有 case 只写 `/tmp`，没有修改仓库文件。

## 修复前置条件

- `phys_access_check` wrapper 不再直接调用会提交 event/assert 的子 builtin。`pmp_check_compute` / `pma_check_compute` 先只计算 summary 和 pending effects；wrapper 只有在 PMP/PMA 都完整命中且最终 option 合并不会产生 inner symbolic exception ctor 时，才统一提交 pending `ReadReg` / alignment assert。
- 若 PMP/PMA summary 没有同时开启、任一子 summary miss，或 symbolic option presence 下不同 exception fault 需要重新构造 inner `SymbolicCtor`，`phys_access_check` 直接整体回退 IR。
- `ISLA_RISCV_ASSUME_CLINT_OFF=1` 现在只让 `within_clint` 返回 false；`within_mmio_readable/writable` 在 HTIF 为 concrete `None()` 时仍返回 CLINT range predicate。这样 CLINT 地址仍走 MMIO 分派，再由 `mmio_read/write` 因无 CLINT/HTIF 命中返回 access fault，而不是落入 RAM。

## Matrix

| case | 目的 | run dir | exit | zSTORE | zLOAD | SymCtor | profiles | total forks | max fork | runtime notes |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| P0 | CLINT-on baseline, no `clint_load` builtin | `/tmp/isla-phase5-smoke-20260428-154550-p0-clint-on` | 0 | 32 | 27 | 0/0 | 59 | 425 | 10 | no runtime fallback/panic/timeout/`ExecError`/`SymbolicLength` |
| P1 | CLINT-on with concrete `clint_load` gate | `/tmp/isla-phase5-smoke-20260428-154639-p1-clint-load` | 0 | 32 | 27 | 0/0 | 59 | 425 | 10 | only 1 runtime fallback: `clint_load builtin fallback: symbolic paddr` |
| P2 | CLINT-off full gates | `/tmp/isla-phase5-smoke-20260428-154629-p2-clint-off` | 0 | 8 | 7 | 0/0 | 15 | 52 | 5 | no runtime fallback/panic/timeout/`ExecError`/`SymbolicLength` |
| P3 | CLINT-off, fixed signed `lw` | `/tmp/isla-phase5-smoke-20260428-154547-p3-signed` | 0 | 8 | 5 | 0/0 | 13 | 40 | 4 | no runtime fallback/panic/timeout/`ExecError`/`SymbolicLength` |
| P4 | CLINT-off, fixed unsigned `lwu` | `/tmp/isla-phase5-smoke-20260428-154604-p4-unsigned` | 0 | 8 | 5 | 0/0 | 13 | 40 | 4 | no runtime fallback/panic/timeout/`ExecError`/`SymbolicLength` |
| P5 | negative: `PHYS_ACCESS_CHECK=1`, `PMA_CHECK=0` | `/tmp/isla-phase5-smoke-20260428-154603-p5-phys-fallback` | 0 | 22 | 20 | not reported as nonzero | 32 | 157 | 7 | 6 expected `phys_access_check builtin fallback: PMP/PMA summaries are not both enabled`; no runtime panic/`SymbolicLength`; exception outputs have `memory-events=0` |

## Interpretation

- The earlier CLINT-off numbers (`zSTORE=6`, `zLOAD=6`; fixed kind `zLOAD=4`) are superseded by this run. The count increase is expected: CLINT range is no longer incorrectly treated as non-MMIO/RAM.
- P2/P3/P4 still keep the explosion under control: max fork is 5 for mixed load kinds and 4 for fixed signed/unsigned load kind.
- P5 confirms the `phys_access_check` wrapper now fails closed when child summaries are not both enabled, instead of committing child side effects and then falling back.
- The remaining hotspots in P2/P3/P4 are small and expected: `get_X`, `checked_mem_*`, `extend_value` for mixed load kind, and `set_X`.
