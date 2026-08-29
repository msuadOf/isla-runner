# Agent14: PMA summary 与 VMEM plain-ram / legacy / off builtin 的关系

日期：2026-04-27

## 结论摘要

`pmaCheck` exact summary 应服务 VMEM `off` / full semantics 路线，而不是服务 `plain-ram` fast path。

原因是 `pmaCheck` 的语义输出只是 `option(ExceptionType)`：它回答“PMA 是否拒绝本次访问，若拒绝是什么 fault”。它不回答“这次访问是否是普通 RAM”。在 Sail 语义里，`pmaCheck` 返回 `None()` 后，上层 `checked_mem_read` / `checked_mem_write` 仍会继续调用 `within_mmio_readable` / `within_mmio_writable`，再决定走 `mmio_read` / `mmio_write` 还是 `read_ram` / `write_ram`。因此 `pmaCheck` summary 只能压缩 PMA 权限/fault 判断，不能被用来替代 plain-RAM 前提。

当前 `plain-ram` VMEM builtin 是一个更强的外部前提 fast path：它绕过 `translateAddr -> mem_* -> phys_access_check -> pmpCheck/pmaCheck -> within_mmio_*` 整条链，直接发 Isla memory event。它只有在外部显式声明 identity translation、PMP permits、plain RAM、alignment 等前提时才安全。`pmaCheck` exact summary 即使证明 `None()`，也不能自动满足 `ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM=1`。

## 1. pmaCheck summary 应服务哪条路线

推荐定位：

- `pmaCheck` exact summary 服务 VMEM `off` / full semantics：`vmem_read_addr` / `vmem_write_addr` 回 IR 后，经过 `translateAddr`、`mem_read` / `mem_write_value`、`phys_access_check` 时命中。
- 它也服务 `plain-ram` fallback：当 `plain-ram` gate 因前提不足回退 IR 后，后续 full semantics 可继续受益。
- 它不服务 `plain-ram` fast path：fast path 命中时不应调用 `pmaCheck`，也不应从 `pmaCheck` 结果推导普通 RAM。
- 它不服务 `legacy` fast path：`legacy` 直接 `frame.memory().read/write`，本身就是非等价性能基线，PMA/PMP/translation/MMIO 都被绕过。

实现粒度上，优先 summary `pmaCheck` 而不是直接 summary `matching_pma_bits_range`。后者返回 `option(PMA_Region)`，符号地址横跨多个 region 时会携带不同 payload，容易把 region 选择问题提前暴露成大枚举；`pmaCheck` 可以在 `option(ExceptionType)` 层合成 fault 条件，同时保持上层 RAM/MMIO 分派不变。

## 2. 与现有 VMEM_ASSUME_* / PMP_PERMITS 的重叠关系

`ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION`：

- 与 `pmaCheck` exact summary 不重叠。
- 它声明虚拟地址可按物理地址处理；`pmaCheck` 只处理已得到的物理地址。
- full semantics 下仍应让 `translateAddr` 执行或用独立 identity translation summary/前提处理。

`ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS`：

- 与 `pmaCheck` exact summary 不重叠。
- 它声明 PMP 不拒绝；`pmaCheck` 处理 PMA。
- 与 `pmpCheck` exact summary 部分替代关系更强：如果走 full semantics 并启用 `ISLA_RISCV_BUILTIN_PMP_CHECK=1`，就不应再把 `PMP_PERMITS` 当作 full semantics 证据。

`ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM`：

- 与 `pmaCheck` exact summary 有表面重叠，但语义更强。
- `pmaCheck == None()` 只表示 PMA 允许访问。CLINT/MMIO region 也可以 PMA readable/writable，并由后续 `within_mmio_*` 分派到 MMIO callback。
- `PLAIN_RAM` 还隐含 non-MMIO、普通 RAM memory event、不会触发 CLINT/HTIF/device side effect。因此不能由 `pmaCheck None` 自动推出。

`ISLA_RISCV_VMEM_ASSUME_ALIGNED`：

- 与 `pmaCheck` 的 misaligned fault 分支有部分交集，但用途不同。
- 该 env 现在会对 symbolic address 加低位 alignment SMT 约束，主要用于 VMEM fast path 和 `split_misaligned` guard，避免进入动态 bitvector width。
- `pmaCheck` 仍必须按 PMA region 的 `misaligned_fault` 字段保留 `NoFault` / `AccessFault` / `AlignmentFault` 行为；不能因为有 aligned fast-path 场景就删除 PMA misaligned fault 语义。

`ISLA_RISCV_ASSUME_PMP_OFF`：

- 与 PMA 不重叠，但会隐藏 PMP 语义。
- 当前 `pmpCheck` 分支里该 env 优先于 `ISLA_RISCV_BUILTIN_PMP_CHECK=1`。因此 full semantics profile 不应同时设置 `ISLA_RISCV_ASSUME_PMP_OFF=1`。

## 3. 避免隐式关闭 PMA/MMIO 的规则

必须保留的边界：

- `pmaCheck` summary 只返回 `None()` 或 `Some(ExceptionType)`，不能直接执行 RAM read/write。
- `None()` 只代表 PMA allow，不代表 non-MMIO。
- `pmaCheck` 后的 `within_mmio_readable` / `within_mmio_writable`、`mmio_read` / `mmio_write`、`clint_load` / `clint_store` 仍由 IR 或后续独立 exact summary 负责。
- 对 PMA no-match 必须返回 `accessFaultFromAccessType(access)`，不能当作 RAM。
- 对 first matching PMA region 必须保留 `range_subset` 的 wraparound bitvector 语义、region 顺序、misaligned_fault、read/write/execute/reservability/CBO 权限差异。
- 不支持的 region list shape、symbolic/unsupported access ctor、无法构造 fault ctor、无法安全读取 `pma_regions` 时应回退 IR。
- 如果 summary 直接读取 `pma_regions` register，应像 PMP exact summary 读取 `pmpcfg_n` / `pmpaddr_n` 一样记录 ReadReg event；但仍要记录它不是函数级 trace/probe/stop 等价。

最重要的反例是 CLINT/MMIO：CLINT PMA region 可 readable/writable，`pmaCheck` 可以返回 `None()`，但正确后续行为是 `within_mmio_* -> clint_*`，不是普通 RAM memory event。任何把 `pmaCheck None` 接到 `read_ram` / `write_ram` 的 VMEM 粗粒度 builtin 都是在隐式关闭 MMIO。

## 4. 推荐 env gate 组合和文档说明

### Full semantics / PMA profile

用于验证 `pmaCheck` exact summary 是否服务真实 VMEM 链路：

```text
ISLA_RISCV_VMEM_BUILTIN_MODE=off
ISLA_RISCV_TEST_ZSTORE_WIDTH=4
ISLA_RISCV_TEST_ZLOAD_WIDTH=4
ISLA_RISCV_VMEM_ASSUME_ALIGNED=1
ISLA_RISCV_BUILTIN_SPLIT_MISALIGNED=1
ISLA_RISCV_BUILTIN_RANGE_SUBSET=1
ISLA_RISCV_BUILTIN_PMP_RANGE_MATCH=1
ISLA_RISCV_BUILTIN_PMP_ADDR_MATCH_TYPE=1
ISLA_RISCV_BUILTIN_PMP_CHECK_RWX=1
ISLA_RISCV_BUILTIN_PMP_LOCKED=1
ISLA_RISCV_BUILTIN_PMP_CHECK=1
ISLA_RISCV_BUILTIN_PMA_CHECK=1   # 建议新增，初期显式开启
ISLA_RISCV_PROFILE_FORKS=1       # profile 时开启
```

明确禁用/不设置：

```text
ISLA_RISCV_ASSUME_PMP_OFF        # 不设置
ISLA_RISCV_BUILTIN_PMP_MATCH_ADDR # 不设置，保持默认关闭
ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION # 不设置，除非本次专门测试 identity guard
ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS          # 不设置
ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM            # 不设置
ISLA_RISCV_VMEM_ASSUME_MISALIGNED_FAULTS    # 不设置
```

说明：`ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 在这里是为了让 `split_misaligned` guard 添加 alignment 约束并移开动态 width 阻断，不表示 plain-RAM，也不表示 PMA/MMIO 被关闭。

### Plain-RAM fast path regression

用于确认 VMEM fast path 本身仍按显式前提工作：

```text
ISLA_RISCV_VMEM_BUILTIN_MODE=plain-ram
ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=1
ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=1
ISLA_RISCV_TEST_ZSTORE_WIDTH=4
ISLA_RISCV_TEST_ZLOAD_WIDTH=4
ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION=1
ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS=1
ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM=1
ISLA_RISCV_VMEM_ASSUME_ALIGNED=1
```

说明：这组验证只证明 fast path 在外部普通 RAM 前提下可用。它不证明 PMA/MMIO 语义完整。日志中应确认没有 VMEM builtin fallback；否则测试实际进入 full semantics。

### Legacy performance baseline

```text
ISLA_RISCV_VMEM_BUILTIN_MODE=legacy
ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=1
ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=1
ISLA_RISCV_TEST_ZSTORE_WIDTH=4
ISLA_RISCV_TEST_ZLOAD_WIDTH=4
```

说明：`legacy` 只保留为旧性能基线和路径压缩上限参考。它绕过 translation/PMP/PMA/MMIO，不应作为语义对照目标。

### PMP-off / PMA-MMIO diagnostic

```text
ISLA_RISCV_VMEM_BUILTIN_MODE=off
ISLA_RISCV_ASSUME_PMP_OFF=1
ISLA_RISCV_VMEM_ASSUME_ALIGNED=1
ISLA_RISCV_BUILTIN_SPLIT_MISALIGNED=1
ISLA_RISCV_PROFILE_FORKS=1
```

说明：该组合只用于暴露 PMA/MMIO 后续热点。它不是 full semantics，因为 PMP 被显式关闭；不能和 `ISLA_RISCV_BUILTIN_PMP_CHECK=1` 的结果混写为同一语义证据。

## 5. fixed zSTORE / zLOAD 验证建议

验证 `pmaCheck` exact summary 本身时：

- 启用：`VMEM_BUILTIN_MODE=off`、fixed width、`VMEM_ASSUME_ALIGNED=1`、`BUILTIN_SPLIT_MISALIGNED=1`、默认小 summary、`BUILTIN_PMP_CHECK=1`、新增 `BUILTIN_PMA_CHECK=1`、`PROFILE_FORKS=1`。
- 禁用/不设置：`ASSUME_PMP_OFF`、`BUILTIN_PMP_MATCH_ADDR`、`VMEM_ASSUME_IDENTITY_TRANSLATION`、`VMEM_ASSUME_PMP_PERMITS`、`VMEM_ASSUME_PLAIN_RAM`、`VMEM_ASSUME_MISALIGNED_FAULTS`。
- 期望检查：PMP 不再是热点；PMA/MMIO 热点减少；`ret_val` 和 memory event/MMIO side-effect 边界不能把 access fault 或 MMIO 改成 ordinary RAM success。

验证 plain-RAM regression 时：

- 启用：`VMEM_BUILTIN_MODE=plain-ram`、fixed width、identity/PMP/plain-RAM/aligned 四个显式前提。
- 禁用/不设置：`ASSUME_PMP_OFF`、`VMEM_ASSUME_MISALIGNED_FAULTS`，除非专门跑 concrete misaligned fault case。
- 期望检查：普通 aligned `zSTORE` / `zLOAD` 仍为 `Retire_Success(())`，每条有效访存 path 保持一个 ordinary memory event；日志不出现 VMEM fallback。

验证 fallback/negative case 时：

- 使用 `VMEM_BUILTIN_MODE=plain-ram`，但故意缺少 `VMEM_ASSUME_PLAIN_RAM` 或 `VMEM_ASSUME_PMP_PERMITS`。
- 期望检查：VMEM builtin 回退 IR；如果启用了 `pmaCheck` summary，它只能影响 full semantics 内部 PMA fault/allow 判断，不能把缺失前提补成 plain-RAM success。

## 推荐文档措辞

建议把 gate 分成四类写入后续文档：

- path selection：`ISLA_RISCV_VMEM_BUILTIN_MODE`、`ISLA_RISCV_BUILTIN_VMEM_*`
- external assumptions：`ISLA_RISCV_VMEM_ASSUME_*`
- exact summaries：`ISLA_RISCV_BUILTIN_PMP_CHECK`、建议新增的 `ISLA_RISCV_BUILTIN_PMA_CHECK`
- diagnostics：`ISLA_RISCV_ASSUME_PMP_OFF`、`legacy`、`ISLA_RISCV_PROFILE_FORKS`

核心说明应写清楚：exact summary 是对原 IR/Sail 子函数的等价压缩；external assumption 是用户声明的场景收窄；diagnostic 是为定位热点而删减语义。三者不能混用为同一类证据。
