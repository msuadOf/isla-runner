# agent09: clint_load builtin/summary 可行性

日期：2026-04-27

范围：分析 `sail-riscv/model/sys/platform.sail::clint_load` 是否适合做 Isla builtin / summary。已阅读：

- `agents/findings.md`
- `agents/zSTORE_path_explosion/status.md`
- `agents/zSTORE_path_explosion/principles.md`

未修改生产代码。

## 结论

`clint_load` 适合做低风险、小范围 summary，但首版应收紧到 concrete exact hit，symbolic addr/width 回退 IR。

原因：

- 函数本体没有写寄存器，也不会调用 `clint_dispatch` / `csr_write_callback`。
- 成功路径只读取 `mip`、`mtimecmp`、`mtime` 三类寄存器之一，并返回 `Ok(bits)`。
- 错误路径只返回 `Err(accessFaultFromAccessType(access))`。
- 当前 IR 中 `get_config_print_clint()` 固化为 `false`，所以默认不会实际执行 CLINT log 分支。

但 symbolic summary 不建议首版做，因为 executor 的 `ReadReg` event 没有条件字段。若把 symbolic addr 下的多个 exact hit 合成一个 SMT ITE，builtin 往往需要提前读取多个 CLINT 寄存器，会把 IR 中“只在实际命中分支读取一个寄存器”的可观察 `ReadReg` 行为改掉。

## clint_load exact addr/width 分支

源码位置：`sail-riscv/model/sys/platform.sail:66-125`。函数先计算：

```sail
let addr = addr - plat_clint_base
```

所以下表地址是相对 `plat_clint_base` 的 offset。当前 rv64/rv32 配置里的 base 是 `0x02000000`，对应绝对地址可加上该 base。

| 相对地址 | width | 返回 | 读取寄存器 |
| --- | --- | --- | --- |
| `0x00000` (`MSIP_BASE`) | `4` | `Ok(zero_extend(32, mip[MSI]))` | `mip`，取 `MSI` bit |
| `0x00000` (`MSIP_BASE`) | `8` | `Ok(zero_extend(64, mip[MSI]))` | `mip`，取 `MSI` bit |
| `0x04000` (`MTIMECMP_BASE`) | `4` | `Ok(zero_extend(32, mtimecmp[31..0]))` | `mtimecmp` |
| `0x04000` (`MTIMECMP_BASE`) | `8` | `Ok(zero_extend(64, mtimecmp))` | `mtimecmp` |
| `0x04004` (`MTIMECMP_BASE_HI`) | `4` | `Ok(zero_extend(32, mtimecmp[63..32]))` | `mtimecmp` |
| `0x0bff8` (`MTIME_BASE`) | `4` | `Ok(zero_extend(32, mtime[31..0]))` | `mtime` |
| `0x0bff8` (`MTIME_BASE`) | `8` | `Ok(zero_extend(64, mtime))` | `mtime` |
| `0x0bffc` (`MTIME_BASE_HI`) | `4` | `Ok(zero_extend(32, mtime[63..32]))` | `mtime` |
| 其它组合 | 任意 | `Err(accessFaultFromAccessType(access))` | 无 CLINT 寄存器读取 |

注意：源码注释列出了 hart 1 的 `msip` / `mtimecmp` 地址，但当前 `clint_load` 只实现上表这些 exact aligned access。

## symbolic addr/width 的路径爆炸来源

IR 位置：`isla/rv64d.ir:44163` 的 `zclint_load`，rv32 同构。

局部爆炸来自 `if/else if` 链被编译成连续 `jump`：

- 每个 exact hit 都先判断 `addr == CONST`，symbolic addr 会 fork 出 hit / miss。
- 每个 hit 再判断 width，例如 `width == 4` 或 `width == 8`，symbolic width 会继续 fork。
- `MSIP_BASE` 分支使用 `('n == 8 | 'n == 4)`，IR 中先测 `8`，失败再测 `4`，比单 width 分支多一层 fork。
- `MTIMECMP_BASE` 和 `MTIME_BASE` 各自重复出现一次 `width=4` 和一次 `width=8` 分支，同一个 symbolic addr 会在相同地址常量上重复经历判断。
- 未命中所有 exact hit 后才进入 not-mapped fault，所以 symbolic addr 需要穿过整条候选地址链。

当前 `get_config_print_clint()` 在 IR 中是常量 `false`，所以 log guard 不是当前默认路径爆炸来源。若未来改成运行时可变配置，命中每个分支后还会多一个 print guard，并且 log 表达式会额外读取对应寄存器值。

上游还有独立的 MMIO fork 来源：

- `within_mmio_readable` 先判断 CLINT / HTIF 范围。
- `mmio_read` 再在 `within_clint` 和 `within_htif_readable` 之间 dispatch。
- `within_clint` 是范围判断，不等价于 `clint_load` 内部的 exact addr/width 判断；即使已经证明在 CLINT range 内，仍可能不是上表 exact mapped register。

## 首版安全支持范围

建议首版 gate 只支持：

- 函数名：`clint_load` / IR `zclint_load`。
- `paddr` concrete bitvector。
- `width` concrete integer，且为 `4` 或 `8`。
- `paddr - plat_clint_base` 精确命中上表成功分支。
- 命中后只读取对应一个寄存器，并构造相同 `Ok` ctor 和 payload 位宽。

不支持时回退 IR：

- symbolic addr。
- symbolic width。
- concrete addr/width 但不是上表 success hit。
- 无法查到 `Ok` / `Err` ctor、`mip` / `mtimecmp` / `mtime` register name、或无法确认返回 payload 位宽。
- `get_config_print_clint()` 不是当前 IR 常量 false 的配置，除非 builtin 显式补齐等价 log 行为。

可选的下一步扩大范围：

- concrete unmapped fault：只有在 `access` 是 concrete ctor 且能等价构造 `accessFaultFromAccessType(access)` 时，才可直接返回 `Err(...)`；否则继续回退 IR。
- solver-proved exact hit：如果不是 concrete addr，但 solver 能证明当前 path 下唯一命中某个 exact 分支，也可以按 exact hit 处理。若不能证明唯一命中，回退 IR。

不建议首版支持：

- symbolic addr 的 ITE summary。
- symbolic width 的 ITE summary。
- `clint_load` + `within_mmio_readable/mmio_read` 合并成更大 summary。

主要原因是条件化 `ReadReg`、log 和 caller callback 证明成本会上升，收益应等 `pmaCheck` / `within_mmio_*` 边界确定后再评估。

## 需要保留的可观察行为

`ReadReg`：

- exact hit 必须产生与 IR 等价的寄存器读取事件。
- executor 中普通 `Id` 读会通过 `get_id_and_initialize` 添加 `Event::ReadReg(name, accessor, value)`。
- 如果 builtin 直接读取 register，应该使用类似 `read_register_cloned` 的路径补 `Event::ReadReg`，不能只从 `frame.regs_mut().get(...)` 取值。
- concrete exact hit 应只读取实际命中的那一个寄存器：
  - MSIP: `mip`
  - MTIMECMP: `mtimecmp`
  - MTIME: `mtime`
- symbolic ITE 如果提前读取所有候选寄存器，会新增原 IR 单一路径上不存在的 `ReadReg` event；这就是首版 symbolic fallback 的主要理由。

callbacks：

- `clint_load` 自身不调用 `mem_read_callback` / `mem_exception_callback`。
- 这些 callback 在 `mem_read_priv_meta` 中根据最终 `MemoryOpResult` 触发：成功读调用 `mem_read_callback(...)`，异常调用 `mem_exception_callback(...)`。
- 因此 summary 应挂在 `clint_load` 层，而不是绕过 `mem_read_priv_meta`；只要返回的 `Ok/Err` 等价，上层 callback 仍会保留。
- `clint_load` 不写 `mip`，不调用 `clint_dispatch`，也不会触发 `csr_write_callback`。这是它比 `clint_store` 风险低的关键点。

log：

- 每个分支都有 `if get_config_print_clint() then print_log(...)`。
- 当前 IR 的 `zget_config_print_clint` 返回常量 `false`，所以默认执行中没有 CLINT print log。
- builtin 若依赖这个事实，应在文档和 gate 中写明；如果未来该配置变为可打开，必须补齐对应 log 或回退 IR。

函数级 trace/probe：

- 当前 `call_isla_implemented_function(...)` 命中 builtin 时会在 `Instr::Call` 中提前返回，绕过后续函数级 probe、trace function、stop condition、function assumption 逻辑。
- 这与已有 PMP summary 有相同诊断可观察性边界。若用户依赖函数调用 trace，而不是最终语义结果，需要关闭该 builtin 或增加专门 trace 兼容处理。

## 与 pmaCheck 的风险比较

`clint_load` 风险低于 `pmaCheck` 的部分：

- 分支数固定且很小：8 个 success exact 组合加一个 fault fallback。
- 不遍历 `pma_regions` list，不处理 first-match region payload。
- 不需要合成 `option(PMA_Region)` 或 PMA attribute struct。
- 不判断 misaligned fault policy、read/write/execute/reservability/cache access 等权限矩阵。
- 不参与 `phys_access_check` 中 PMP/PMA fault 优先级合并。
- 没有写寄存器副作用，也没有 `clint_dispatch`。

`clint_load` 风险高于或不同于 `pmaCheck` 的部分：

- 它直接读取 architectural/platform register，`ReadReg` event 是关键可观察行为；`pmaCheck` 更接近纯检查函数，主要返回 `option(ExceptionType)`。
- symbolic summary 会面临条件化寄存器读取问题；`pmaCheck` 可以把很多权限和区间判断压成布尔/option ITE，而不会引入多个设备寄存器读取。
- `clint_load` 是 MMIO 设备语义，返回值来自可变设备寄存器；不能像普通区间 predicate 一样只看地址关系。
- 若未来启用 CLINT print log，log 内容包含读取值，summary 还要保证 log 和 ReadReg 顺序/次数不产生误差。

综合判断：`clint_load` 的语义面比 `pmaCheck` 小很多，适合作为 concrete exact-hit fast path；但它不是理想的首个 symbolic ITE summary 目标。若目标是减少当前 `clint_load=65` 这类 symbolic fork 热点，真正有收益的版本需要解决条件化 `ReadReg` 和 caller trace 对照问题，否则应先做 `pmaCheck` / `within_mmio_*` 这类更接近纯 predicate 的层。

## 建议判定

`DONE_WITH_CONCERNS`

- 可以安全推进 concrete exact-hit-only builtin。
- symbolic addr/width 首版必须回退 IR。
- 该首版语义风险低，但对当前 symbolic CLINT fork 热点的收益有限。
- 若要实质降低 `clint_load` 热点，需要后续单独设计条件化 `ReadReg` / MMIO callback / trace 对照方案。
