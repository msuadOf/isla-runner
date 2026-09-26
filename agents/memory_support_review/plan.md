# Isla 内存一致性实施计划（feat/memory-consistency）

调查阶段已完成，结论见 [report.md](report.md)；本文件改为实施计划。用户已确认按本计划直接实施，完成后再依据最终代码评判。

## 目标

基于 `origin/feat/memory-support`（`f06371f`），在 solve-state 链路补齐五项能力：

1. 同地址读-读一致、写后读一致、字节重叠一致（经 `MemoryCallbacks` 字节数组建模）。
2. `memory_regions` 配置成为真实的符号地址访问范围约束。
3. 路径 JSON 输出 `pre_memory`/`post_memory`（开跑前需准备的字节、跑完应检查的字节）。
4. `memory-events` 顺序与执行顺序一致。
5. 压缩访存指令（`ExecuteAs(LOAD/STORE)`）在 solve-state 中继续执行，产生真实访存事件。

异常路径维持现有保留策略：我们的 solve-state 本来就把异常路径作为合法结果收集，不引入 isla-testgen 的 Kill/丢弃语义。

## 工作区与边界

- 工作区：`isla/.worktrees/memory-consistency`，分支 `feat/memory-consistency`，基于 `f06371f`。
- 只在该 worktree 内修改；不动 `isla/` 主工作树（`feat/float-support`）、不移动根仓库 gitlink。
- 本轮不改 `difftest-xiangshan/pipeline.py`（消费 `pre_memory`/`post_memory` 属下一轮）；不做多指令序列；不做 MMIO/设备副作用。
- 不重写 `memory.rs` 默认 read/write 语义；通过其已留出的 `client_info` 回调叠加数组语义，与上游 isla-testgen（`/home/baiyifan/workplace-local/isla-testgen`，`src/execution.rs:131-247`）同一范式，只参考不整文件拷贝（其 isla 子模块为 esop22-300 谱系，API 有差异）。
- 遵守 worktree 内 `AGENTS.md` 的注释/格式/TDD 要求：先写失败测试，再实现。

## 设计要点

1. **数组建模回调**：声明 `memory : Array(_ BitVec 64)(_ BitVec 8)`（地址位宽按 IR 世代核对）。`symbolic_read`：默认 `read_symbolic` 已新建读值变量并传入回调；回调加约束 `读值 == Concat(Select(mem, addr+bytes-1), …, Select(mem, addr))`（RV64 小端）。`symbolic_write`：构造逐字节 `Store` 链（`Extract(data, i*8+7, i*8)`），把数组常量重定义为新 const 并更新回调内部记录；返回的布尔写结果语义不变。不做 tag 数组（RV64 无 capability）。
2. **装配位置**：`Memory::clone` 对 `client_info` 的处理需实测；若克隆不保留回调，则在 solve-state 每指令复制内存处（`src/isarch/exec.rs:557-563`）或 executor `set_memory` 处重新装配，保证每条路径独立持有数组状态。
3. **区域约束**：复用/对齐 `isla-lib/src/memory.rs` 中 `smt_address_constraint` 的 OR 链方式（需核实 `f06371f` 上是否存在），把符号读写地址约束进已配置区域（concrete ∪ symbolic）的并集；未配置任何区域时不加约束，避免默认路径全 Unsat。
4. **pre/post 物化**：`src/isarch/exec.rs` 收集处先把轨迹事件反转为正序；由 ReadMem/WriteMem 事件加 model 重建触碰字节：读事件给出对应时刻的字节值（首次读即初值）；写事件的 `data` 决定该地址此后的内容；同一地址多次写取最后一次。输出到 `AssemGenJsonItem` 新字段 `pre_memory`/`post_memory`（`[{address, bytes, value}]`），model 查不到的分量输出 `null` 并计数，不编造。
5. **ExecuteAs 续执行**：solve-state 调 `zexecute` 得到 `ExecuteAs(instr)` 返回时，按 `rv64d.ir:385190-385198` 外层模式继续执行转换后的指令，事件与路径结果照常收集；C_LD/C_SD 应由此产生真实访存事件。

## 步骤（subagent 串行，主 agent 调度）

- **W2 核心**：回调 + 数组建模 + 区域约束 + 单测（同址读读相等、写后读、4 字节写后读中间 1 字节、区域外地址不可满足、未配置区域不受限）。
- **W3 输出**：事件顺序修正、pre/post 物化、ExecuteAs 续执行、`test/isarch/cli/solve-state/` 用例扩展。
- **W4 验证**：worktree 内 `cargo test`；CLI solve-state 真实访存抽查（`zLOAD`/`zSTORE`/`C_LD`/`C_SD`，`configs/riscv64_difftest_mem.toml`，单条 180s 时间盒，按需启用既有 builtin env gates），核对 pre/post 与事件一致性；记录到 `docs/RESULTS.md` 草稿。
- **文档同步**：结论回写 `agents/findings.md`、`status.md`、`specs/TODOs.md`、`docs/RESULTS.md`。

## 验收口径

- 单测直接证明：一致性三类、区域约束、事件顺序、物化。
- 真实访存用例：C_LD/C_SD 产生非空 `memory-events`；`zSTORE` 的 `post_memory` 与 WriteMem `data` 一致。
- 不宣称：多指令序列、MMIO/设备、性能达标、`pipeline.py` 集成。

## 风险

- 真实 LOAD/STORE 求解时间（分支测试注释记录曾 >15 分钟）：用既有 builtin gates、固定部分指令参数、时间盒控制；超时记录为受限验证而非通过。
- `Memory::clone` 与 `client_info` 的可克隆性未知：实测后选择装配点。
- worktree 全新构建耗时较长：可接受，验证阶段一次性完成。
- testgen 与 `f06371f` 的 API 差异：只搬范式，逐处对照本仓源码改写。
