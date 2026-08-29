# VVTYPE 局部限制与均衡采样计划

## 目标

让最新 `../sail-riscv` 生成的 RV64 IR 在不固定 `vtype`、`vl`、`vstart`、mask、向量寄存器值或寄存器编号的前提下，满足：

1. `make solve-VVTYPE` 在 30 分钟内自然结束，不依赖外层 timeout 杀进程；
2. `VVTYPE` 的 21 个 mnemonic 全部出现在最终 JSON；
3. 每个 mnemonic 的输出数量接近一致，避免 gather 和 `vssubu` 占据绝大多数样本；
4. 没有 `Timeout`、SMT timeout 或 `SymbolicLength("subrange_internal")`；
5. 保留 masked/unmasked、成功/非法指令、SEW/LMUL、寄存器和运行态 CSR 的符号覆盖。

## 基线

- 固定 IR SHA-256 `452aa5fd...e7b5` 的运行在 40 分钟外层 timeout 时退出 124。
- 已完成 731 条路径，覆盖 21/21 mnemonic，但分布严重不均：
  - `vrgather.vv=279`
  - `vrgatherei16.vv=218`
  - `vadd.vv=95`
  - `vssubu.vv=58`
  - 最少的若干指令只有 2 条
- 另有 43 条 `subrange_internal SymbolicLength` 和 5 条路径 timeout。
- fork 深度 P95=79、max=82；`vssubu.vv v0, v31, v30` 单一汇编形态重复 50 次，确认是 lane 路径重复，不是编码覆盖增长。

## 根因与源码对齐

### 1. 当前 region 只覆盖 gather

`isla/src/isarch/exec.rs::solve_execution_limits` 只限制 `vext_arith_insts.sail` 中两个 gather 的 mask/index 分支。

当前 `../sail-riscv/model/extensions/V/vext_arith_insts.sail` 中仍有未受限的 lane 分支：

- `VV_VSADDU`：113-114
- `VV_VSADD`：117-118
- `VV_VSSUBU` mask：121-124
- `VV_VSSUBU` unsigned compare：122-123
- `VV_VSSUB`：127-128
- `VV_VSMUL`：131-136
- `VV_VRGATHER` mask/index：181-187
- `VV_VRGATHEREI16` mask/index：190-196

这些 region 必须按 `if` 表达式的精确 SourceLoc 配置，不能用 `112-136` 这种宽区间；宽区间会同时选中 `match funct6` 的 case dispatch，触发 concretize 后可能漏掉 mnemonic。

### 2. gather 的前置合法性分支造成早期偏斜

`vext_arith_insts.sail:64-74` 在主 `match funct6` 前特判 gather，并调用：

- `valid_vtype` / `valid_rd_mask` / `valid_reg_group`：`vext_utils_insts.sail:31-53`
- `valid_reg_overlap`：`vext_utils_insts.sail:71-85`

这些位置需要局部 branch limit，压缩重复的非法寄存器/重叠路径，但保留每个判断的 true/false 两侧各一个代表路径。

### 3. `vssrl/vssra` 的动态切片不是 branch limit 问题

`get_fixed_rounding_incr` 在 `vext_utils_insts.sail:735-743` 使用符号 `shift_amount` 做动态 bit/slice，当前 IR 会报 `SymbolicLength("subrange_internal")`。局部 branch/loop limit 无法把动态结果位宽变成静态位宽。

需要在 Sail 中做最小等价改写：使用固定宽度的动态 shift 后取静态 bit，并用固定宽度 shift 判断 sticky bits，消除动态 slice；不固定 shift amount，不缩小合法运行态。

### 4. 执行完成数不等于需要保留的测试数

即使执行规模被压到可控范围，gather 的合法性分支仍天然比简单 ALU 指令多。最终 JSON 需要针对 `zVVTYPE` 做确定性均衡采样，而不是把线程完成顺序原样写出。

## TDD 与实现步骤

### A. SourceRegion 精确性测试

1. 更新 `solve_execution_limits_use_local_sampling_as_primary_path_bound`：验证所有新增 region 被解析。
2. 新增边界测试，明确：
   - `VV_VSADDU` 的 lane `if` 被选中；对应 `match` case 标签不被选中；
   - `VV_VSSUBU` 的 mask 与 compare 被选中；
   - gather mask/index 被选中；gather case 标签不被选中；
   - `assert_sew` / `assert_lmul_pow` 不在限制 region 内，继续完整枚举 4×7 种有效配置。

### B. 扩展 VVTYPE 局部 branch profile

1. 保持 `max_forks_per_branch=1`、`LimitBehavior::Concretize` 和固定 sampling seed。
2. 将上述精确 SourceRegion 加入默认 VVTYPE profile。
3. 不增加全局 `max_forks_per_path`，不限制 region 外的其它 clause。
4. 不对有限、静态上界的 `foreach` 设置过小 loop 上限；lane 爆炸由对应条件分支的 branch limit 处理。

### C. 消除 fixed-rounding 动态位宽错误

1. 先补 Sail first-party/IR helper 测试，覆盖 VXRM 四种模式和 shift=0/1/中间值/SEW-1。
2. 将动态 bit/slice 改为固定宽度 shift + 静态 bit 访问。
3. 验证 `vssrl.vv`、`vssra.vv` 不再出现 `SymbolicLength`。
4. 保留当前未提交的 saturation/vxsat 修改，不覆盖并发工作。

### D. VVTYPE 输出均衡器

1. 在 `src/isarch/exec.rs` 增加纯函数，对 `zVVTYPE` 的最终 `AssemGenJsonItem` 按 mnemonic 分组。
2. 每个 mnemonic 默认最多保留 4 条，按以下桶轮转选取，避免只留下最快完成的非法路径：
   - Retire + unmasked
   - Retire + masked
   - Illegal + unmasked
   - Illegal + masked
3. 桶内按 encoding、ret_val、ISA state 的稳定键排序，保证多线程完成顺序不影响结果。
4. 非 `zVVTYPE` clause 完全不改变输出行为。
5. 单测验证 21 组过量/不足样本、稳定顺序、masked/ret 类型轮转和非 VVTYPE 旁路。

### E. 生成与验收

1. 用最新 `../sail-riscv` 重新生成 `generated_isla_rv64d`，复制为 `./rv64.ir` 并记录哈希。
2. 先做 5 分钟 smoke，要求 21/21 mnemonic、无错误，观察任务队列是否收敛。
3. 最终运行：`make solve-VVTYPE IR_FILE=./rv64.ir OUTER_TIMEOUT=30m`。
4. 验收标准：
   - exit 0，墙钟时间 <30m；
   - 最终 JSON 存在；
   - 21/21 mnemonic；
   - 每种 4 条，目标总数 84；若某 mnemonic 语义上不足 4 条，则要求 min>=3 且 max-min<=1，并记录原因；
   - 每个 mnemonic 至少一条 `Retire_Success`；
   - `Timeout=0`、SMT timeout=0、`SymbolicLength=0`；
   - fork max 显著低于基线 82，且任务队列自然清空。

## 修改热点

- `isla/src/isarch/exec.rs`
- `isla/isla-lib/src/source_loc.rs`（仅当现有 region 选择测试能力不足时）
- `sail-riscv/model/extensions/V/vext_utils_insts.sail`
- `sail-riscv/test/first_party/...` 的定点舍入回归测试
- 生成产物 `isla/rv64.ir`
- `agents/vvtype_balanced_local_limits/status.md`
- 稳定结论同步到 `isla/agents/findings.md`

## 修改边界

- 保留 Isla 与 sail-riscv 当前全部 staged/unstaged 修改；重叠文件只做最小局部 patch。
- 不固定运行态 CSR、mask、寄存器或向量数据。
- 不用删除指令、跳过错误路径或扩大 timeout 来“通过”。
- 不修改 Z3 tactic。
- 均衡器只影响最终测试样本选择，不改变 Sail 执行语义。
