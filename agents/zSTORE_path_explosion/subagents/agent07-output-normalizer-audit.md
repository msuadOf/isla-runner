# agent07: output normalizer audit

日期：2026-04-27

范围：审计 `agents/zSTORE_path_explosion/normalize_vmem_output.py` 是否足够支撑下一阶段 PMA/MMIO 对照。已阅读：

- `agents/findings.md`
- `agents/zSTORE_path_explosion/status.md`
- `agents/zSTORE_path_explosion/normalize_vmem_output.py`

未修改 `normalize_vmem_output.py`，未修改生产 Rust。

## 结论

当前 normalizer 适合做 Phase 2 plain-RAM/aligned 快速对照的粗粒度检查，但不足以支撑 PMA/MMIO 阶段的语义对照。

它目前能比较：

- 顶层 `gen` item 数量。
- `ret_val` 原始字符串的 multiset。
- 每条路径的 `memory-events` 数量分布。
- `ret_val + memory-events` 的 path shape multiset。
- memory event multiset，字段白名单为：
  - `kind`
  - `region`
  - `bytes`
  - `address_model`
  - `value`
  - `data`
  - `is_ifetch`
  - `is_exclusive`

主要缺口：

- 丢掉了 JSON event 中已经存在的 `address` 字段，只比较 `address_model`。这会漏掉 symbolic address 表达式/变量形态差异。
- 不比较 `test-ins` / `test-ins-encdec` / `isa-state`，因此不能确认两边是否在同一条固定样例上对照。旧文档已经说明 generator 非确定性会影响 address/data，PMA/MMIO 阶段必须尽量固定 input 后再比较。
- `ret_val` 只是原始字符串计数，不能解析异常构造子、异常地址字段、成功/异常分类，也不能比较 `ret_val` 相关 path constraints。
- 只收集 `memory-events`，而当前 Rust JSON 生产端 `collect_memory_events` 只覆盖 `Event::ReadMem` / `Event::WriteMem`。`mem_read_callback`、`mem_write_callback`、`mem_exception_callback`、函数 call/return trace、MMIO/CLINT dispatch 相关 trace 都不会进入当前 JSON，因此 normalizer 无法比较这些可观察行为。
- 对未知 event 字段静默忽略。若后续 JSON 增加 `callback-events`、`constraints` 或 MMIO 专用字段，旧 normalizer 可能继续给出“无差异”的误导结果。

## PMA/MMIO 阶段需要新增的比较项

1. MMIO event vs RAM event
   - 需要能区分普通 RAM `read_ram` / `write_ram` 产生的 `ReadMem` / `WriteMem` 与 MMIO `mmio_read` / `mmio_write` / `clint_load` / `clint_store` 路径。
   - 如果 MMIO 仍不产生 `ReadMem` / `WriteMem`，只靠当前 `memory-events` 不够，必须让 JSON 生产端或 sidecar trace 暴露 MMIO dispatch/callback 事件。
   - normalizer 层建议把 event category 规范化为 `ram_read`、`ram_write`、`mmio_read`、`mmio_write`、`exception_callback`、`unknown_callback` 等，而不是只用 `kind=read/write`。

2. exception callback
   - Sail 在 `mem_read_priv_meta` / `mem_write_value_priv_meta` 中成功时调用 `mem_read_callback` / `mem_write_callback`，失败时调用 `mem_exception_callback`。
   - PMA/PMP/MMIO summary 若把 access fault、alignment fault 或 MMIO error 提前返回，必须保留 `mem_exception_callback(bits_of(paddr), exceptionType_bits(e))` 这一类可观察行为。
   - 当前 JSON 完全不包含 callback，因此 normalizer 只能从 `ret_val` 和 `memory_event_count=0` 间接猜测异常，不能证明 callback 等价。

3. `memory_event_count`
   - 当前已有 `memory_event_count_counts`，应保留。
   - PMA/MMIO 阶段还需要按结果分类统计，例如：
     - `Retire_Success + 1 RAM event`
     - `Retire_Success + 0 event + MMIO callback`
     - `Memory_Exception + 0 memory event + exception callback`
   - 单纯的总数量分布无法判断“成功 RAM event 被误换成 MMIO callback”或“异常路径误生成 memory event”。

4. address / data / bytes
   - `bytes` 和 `data` 当前已在白名单内，`value` 也已覆盖 read value / write value symbol。
   - 必须新增 `address`，并同时保留 `address_model`。
   - 对 MMIO callback 也需要比较 callback addr、width、value/data。
   - 建议在固定 instruction input 后比较 exact address/data；未固定 generator 的随机样例只能把 address/data 差异标记为 probe/testcase 差异，不能直接判为语义差异。

5. `ret_val` constraints
   - 当前只比较 `ret_val` 文本。它能看到 `Retire_Success(())`、`Memory_Exception(...)` 以及异常 ctor 名称，但看不到路径条件。
   - 需要至少解析并归一化：
     - return kind：`Retire_Success` / `Memory_Exception` / other
     - exception ctor：`E_Load_Access_Fault`、`E_SAMO_Access_Fault`、`E_Load_Addr_Align`、`E_SAMO_Addr_Align` 等
     - exception address term/model，如果 JSON 或 sidecar 可提供
   - 真正的 constraints 需要 JSON 生产端输出 path condition / fork constraints / solver model sidecar；只改 normalizer 无法从现有 JSON 还原。

## 脚本改动建议

只改 normalizer 的低成本建议：

```diff
 EVENT_FIELDS = (
     "kind",
     "region",
     "bytes",
+    "address",
     "address_model",
     "value",
     "data",
     "is_ifetch",
     "is_exclusive",
 )
```

中等改动建议：

- 增加 `normalize_ret_val(ret_val)`：
  - 输出 `ret_kind`、`exception_types`、`raw`。
  - 对 tuple 字段顺序不同但语义相同的 `Memory_Exception` 做弱归一化，避免 `ExceptionType0/1` 字段顺序造成噪声。
- 增加 `unknown_event_fields` 汇总：
  - 每个 event 中不在白名单里的字段要报告出来。
  - PMA/MMIO 阶段建议默认 `--strict-fields`，发现未知字段直接失败或至少单独列出。
- 增加 per-class shape：
  - `ret_kind + exception_type + memory_event_count + event_categories`。
  - 用于快速看“异常路径是否无 RAM event”、“成功路径是否进入 RAM/MMIO 正确类别”。
- 增加 `--include-instruction-key`：
  - 可选择把 `test-ins-encdec` 或固定 instruction key 纳入 shape，避免不同 generator 输出被误配。

需要 JSON 生产端配合的建议：

- 输出 callback events 或 trace sidecar，至少包含：
  - `mem_read_callback(access, addr, width, value)`
  - `mem_write_callback(access, addr, width, value)`
  - `mem_exception_callback(addr, exception_code)`
  - MMIO dispatch：`mmio_read/write`、`clint_load/store`、`htif_load/store`
- 输出 path constraints 或 summary：
  - fork/assume constraints，或
  - 每条 path 的关键 predicate model，例如 PMA region match、within_mmio、exception selection predicate。

## 预期 trace/probe 差异 vs 语义差异

预期 trace/probe 差异：

- builtin/summary 命中后绕过 IR helper 函数体，函数级 `Function` trace、probe、stop、function-assumption 可减少或消失。
- `pmpCheck` / PMA helper 内部局部分支被 SMT ITE 合成后，fork 数、trace_len、helper call stack 热点变化是预期的诊断差异。
- generator 未固定时，`test-ins`、寄存器选择、立即数、`address_model`、`data` 可能不同。旧文档已说明这种差异不能单独判为语义差异。
- symbolic variable 编号如 `Sym(188)` / `v693` 在不同 run 中可能漂移；需要用 ctor/category/model 或固定样例来降低噪声。

语义差异：

- `Retire_Success` 与 `Memory_Exception` 数量或分类不同。
- access fault 与 alignment fault ctor 不同，尤其 PMA misaligned `AccessFault` / `AlignmentFault` 优先级不同。
- 成功 RAM 路径少了 `ReadMem` / `WriteMem`，或异常路径错误地产生 memory event。
- RAM 路径与 MMIO 路径互换：例如本应走 `mmio_write` / `clint_store` 却产生普通 RAM `WriteMem`，或本应普通 RAM 却走 MMIO callback。
- callback 丢失或类型错误：成功读写未触发 `mem_read/write_callback`，异常未触发 `mem_exception_callback`，或 callback addr/width/value/exception_code 不一致。
- memory event 的 `bytes`、`address` / `address_model`、`data` / `value` 在固定 instruction input 下不一致。
- `ret_val` 相同但 path constraints 不同，导致实际可达地址范围、PMA region、MMIO predicate 或 exception selection predicate 不一致。

## 建议判定

当前 normalizer 对 PMA/MMIO 对照的状态是 `DONE_WITH_CONCERNS`：

- 可继续作为粗筛工具使用，尤其看 `ret_val_counts`、`memory_event_count_counts`、RAM event shape。
- 不能作为 PMA/MMIO semantic equivalence 的最终证据。
- 下一步最小必要增强是加入 `address`、ret_val 弱解析、未知字段报告。
- 完整 PMA/MMIO 对照必须让输出包含 callback/MMIO event 和 ret/path constraints；这不是单靠当前脚本能补齐的。
