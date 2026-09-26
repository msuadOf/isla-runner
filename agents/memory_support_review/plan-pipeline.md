# pipeline.py 内存上下文重放实施计划（已确认并实施完成；2026-09-27 W12）

承接 [plan.md](plan.md)（W2-W10，isla 侧 pre/post 输出已就绪）与 [plan-pma.md](plan-pma.md)（S1，PMA 地图已与重放环境对齐）。本计划只覆盖消费侧：`difftest-xiangshan/pipeline.py` 读取 `pre-memory`/`post-memory` 并生成可重放 ELF。**已于 2026-09-27（W12）实施完成：端到端成功路径 104/104 GOODTRAP，证据 `/tmp/isla-memimpl-w12-20260927-050541/`；结果与遗留见 [status](status.md) 与 findings。**

## 现状核实（2026-09-27，只读调查）

- `make_assembly`（pipeline.py:300）装配顺序：init（mstatus VS=0x600、medeleg=0、mtvec=trap_handler）→ V 上下文（vsetvli/vstart/vcsr）→ vreg 装载（.data `vector_initial_state` + vl1re8）→ 特权切换（PMP 全开 + mret）→ **标量 `li xN`（最后）** → `payload_ins:` → payload → GOODTRAP `.4byte 0x0000006b`（或预期 trap 时哨兵 `.4byte 0x00000000` + handler 按 `mepc==payload_ins` 判 GOODTRAP）。
- 寄存器初始化全部走 `li`；t0/t1 仅在其之前使用，标量装载后即 payload——内存初始化必须插在标量装载**之前**。
- 异常路径已有机制：`expects_trap` 匹配 `^(Illegal_Instruction|Memory_Exception)` → 哨兵+handler，不校验 mcause/mtval。
- 样例 green JSON（`/tmp/isla-memimpl-w10-20260927-032747/green/output/rv64_zSTORE.json`，2610 条）：131 条 Retire_Success（各 1 条访存事件，pre 段 1B×107/4B×17/8B×7，**value 全 null**（首触写），post 全非 null）；2479 条全部 E_SAMO_Access_Fault 类（无事件无 pre/post）；同一编码最多 100 条路径、8 个编码成败两类并存。
- **37/131 条成功条目的 pre 地址落在基址 4KB 内（含 0x80000000 本身）**——代码覆写风险是现实高频事件。
- README（worktree）字段语义：pre=首触内容（首触写 null）、post=最终字节、段长≤8B 小端、**地址分量也可能 null**。

## 设计要点（七个问题的推荐）

1. **初始内存准备：选 (a) 前导汇编 store 逐段写入。** 地址任意散布 DRAM，链接期 .data 需按地址动态造 section+objcopy，复杂且 pre=null 段仍需运行期决定填值；前导 store 只用 t0/t1（sb 逐字节，≤8 条/段，免对齐判断），插在 `privilege_setup` 与 `scalar_loads` 之间（User 态下 PMP 已全开，store 合法；不破坏 JSON 标量值）。program.S 可读、commit trace 可见，调试性最好。
2. **最终字节检查：选 (a) 尾声 load+compare。** DiffTest 只逐提交比对体系结构状态（寄存器/CSR），不比内存；且我们要验的是 Isla 模型期望对硬件，NEMU 比对表达不了。实现：payload 后逐段按小端取字节比较（lb+期望值），全过 → GOODTRAP `0x0000006b`；任一失配 → 跳**该段专属 park 标号**（`j self`），run 侧超时判 failure，`--dump-commit-trace` 末 PC 即定位失配段。附带红利：失配若同时造成 DUT≠NEMU，会在比较指令处 different-at 直接暴露。
3. **fault 路径：最小方案=直接复用现有 expect_trap 机制重放并计数。** PMA 地图已对齐重放环境，圈外 store 在真 emu 必然 access fault，`mepc==payload_ins` → GOODTRAP，零新代码；manifest 中按 `path_class: ok/fault` 计数。第二步（可选）在 handler 内加 mcause 断言（解析 ret_val 中 `E_Load_Access_Fault`→5 / `E_SAMO_Access_Fault`→7，失配 park）；mtval 需解码有效地址，**不做**，留后续。
4. **null 与采样：** pre value=null（自由字节）按固定 `0xA5` 填充（非零模式避免掩盖"硬件恰返回复位零"类 bug；确定性可复现）。**地址 null 的段、post value null 的检查段跳过该段并计数；若全部 post 段皆 null 则跳过整条。** 采样默认**全量**（131 条成本可忽略，(encoding, isa-state) 已全互异）；加 `--sample-mode {all,first-per-encoding}` 供大批量；既存 `--ret-val-regex` 可先行过滤路径类。
5. **一致性约束：** 装配顺序固定为 [特权/向量上下文] → [pre store] → [标量 li] → payload → [post 检查] → GOODTRAP/park；pre store 依赖 t0/t1，必须在标量装载前；pre/post 是权威重放结果，`memory-events` 仅抄录进 case.json 作诊断，不生成代码；pre 段按 JSON 给定顺序（即重放序）发射，段间无重叠（样例已验证 0 重叠），未来重叠时按后写覆盖语义即正确。
6. **实施边界：** 只改 `difftest-xiangshan/pipeline.py`、`difftest-xiangshan/tests/test_pipeline.py`、README（新增"内存上下文重放"节）；不动 run 脚本/Dockerfile/LINKER。新增测试对齐既有 unittest 风格（importlib 载入 pipeline、对 make_assembly 做子串+顺序断言、mock subprocess 验 run_case）。**实施前先 `git status --short -- difftest-xiangshan/` 确认干净（本轮调查时为空；根仓库另有 79 处未提交属并行会话，一律不碰、不顺手 stage/commit），实施后复查 diff 仅限上述三文件；提交需用户单独指示。** 验收命令见下。
7. **风险与对策：**
   - **代码覆写**：任何 pre/post/events 触碰地址落在 `[0x80000000, 0x80000000+0x2000)` → 该条 skip 并记 `skipped_reason`（本样本将跳约 37 条）；备选精确方案=post-link 读 ELF 实际范围（两遍构建），首版用静态窗口。
   - **多段写序**：按给定序逐段 sb，无重叠即无歧义。
   - **ELF 体积**：≤ 数段×8 字节 sb，可忽略。
   - **emu RAM 假设**：`DEFAULT_EMU_RAM_SIZE=256MB` 是编译期宏，XIANGSHAN_TOOLS emu 是否覆盖未确认；批量跑前先用一条探针用例（store 0x8ffffff8 后 GOODTRAP）实测上界，不符则收紧地址接受范围。（已实测解除：探针 GOODTRAP 2/2，256MB 上界成立。）
   - **失配信号是超时**：单条失败耗满 timeout（默认 120s），批量失败时慢；必要时对本批降低 `--timeout`。
   - post 检查 load 若真机 fault → 走非预期 trap → park 超时，与失配同判 failure（trace 可区分 mepc）。

## 步骤

1. **前置检查**：核对根仓库未提交状态（保留并行会话内容）；实测 emu DRAM 上界探针。
2. **解析层**：pre/post 段解析（`N'hHEX` 小端、null 语义、地址范围/窗口过滤、skip 计数进 case.json 与 manifest 汇总）+ 单测。
3. **pre 发射**：make_assembly 插入前导 store（sb 逐字节、0xA5 填充、顺序断言：在 mret 之后/标量 li 之前）+ 单测。
4. **post 检查**：尾声逐段比较 + 段专属 park 标号 + GOODTRAP 收尾（仅成功路径）；fault 路径维持现有机制 + `path_class` 计数 + （可选）mcause 断言 + 单测。
5. **采样与元数据**：`--sample-mode`；case.json 抄录 pre/post/memory-events。
6. **真机验证**：green JSON 端到端跑通并核对跳过/成功/失败分类；结果记 `docs/RESULTS.md`，同步 `status.md`、`specs/TODOs.md`、`findings.md`。

## 验收口径

- `python3 difftest-xiangshan/tests/test_pipeline.py` 全绿（含新增内存用例）。
- 用 green JSON 实跑：`prepare-json → build → run`（真实 emu+NEMU so），成功路径 post 检查全过或如实记 fail；skipped 条目有清单与计数；fault 路径经现有 trap 机制 GOODTRAP。
- 对照：手工抽查 ≥3 条（如已知地址 sb）在 difftest.log/commit trace 中确认 pre 写入与 post 检查行为符合模型 JSON。
- 不宣称：多指令序列、MMIO、mtval 校验、emu 重建。

## 明确不做（本轮）

mtval/有效地址校验、fault 路径 mcause 以外的语义断言、多指令序列内存链、动态采样策略、worktree isla 侧改动。
