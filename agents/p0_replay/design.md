# P0 重放器设计

状态：设计稿（2026-11-07，Opus 起草，Claude 整理）。目标是把 Isla 合并符号执行产出的 Sv39/Sv48 LOAD/STORE 页表样本（samples v1），转换并验证为可在 XiangShan（emu）与 NEMU 上做 DiffTest 的测试程序。它是后续 fuzzing loop 拿到 DiffTest 反馈的前置阻塞项。

事实标注：【已核实】= 设计者读过代码/文档；【推测】= 尚未验证；【未验证】= 需要实验。

## 1. 三路结论通道

只比较 XiangShan 与 NEMU 查不出“XiangShan 错报页异常”：DiffTest 框架在 DUT 报 12/13/15 号页异常时调用 `guided_exec`，让 REF 带着 DUT 的 mtval 照样抛异常（`difftest/src/test/csrc/difftest/checkers/traps.cpp:83-98`，位于 `difftest-xiangshan/xiangshan/` 下）【已核实】。所以分三路：

| 通道 | 内容 | 能查出 |
| --- | --- | --- |
| C1 | XiangShan 与 NEMU 的 DiffTest | 一般不一致、访问异常 |
| C2 | ELF 内嵌期望值自检 | 页异常的错报/漏报，负对照“翻转叶子 V 位”只有它能检出 |
| C3 | 离线拿 Isla 结果与独立预测器交叉核对 | 重定位器自身是否写错 |

## 2. 现有管线需要改的地方

1. GOODTRAP 无条件：`pipeline.py:807,813` 发射 `0x0000006b`（rs1=x0），退出码恒为 GOOD，失败只靠超时暴露。P0 改用 `0x0005006b`（rs1=a0）：a0=0 为 GOOD，a0=1 为 BAD TRAP；每种失败原因配一个 `fail_<reason>` 桩，按 ELF 符号反查 BAD TRAP 的 pc 即知原因【已核实编码，TRAP 指令定义见 `CustomInstructions.scala:10`】。
2. 页表不放 `.data`，用运行时 `sd` 写入：`elfloader.cpp:127-129` 的 img_size 取最后一个段末尾减 0x80000000，首条指令提交时按它把 DUT 内存复制给 REF（`instructions.cpp:32-37`、`ram.h:145`）；段放到 2^39 附近会复制数百 GB【已核实】。每个样本只有 3~5 个 PTE 加 8 字节数据，约 50 条 `sd`。
3. 装配顺序不能复用 `make_assembly`：它先写 mstatus（`pipeline.py:787`）再 mret（`:793`）最后恢复内存；分页场景下样本 mstatus 的 MPRV 会让初始化写入也走翻译。
4. 异常路径现有只比 `mepc`；P0 的 C2 需检查 mcause 与 mtval（=VA）。

## 3. 分层与契约

| 层 | 输入 → 输出 | 契约 |
| --- | --- | --- |
| L0 解码 | samples v1 行 → walk 记录 | 复用 `pt_decode.decode_sample`；解码失败/未归属内存/`result_mismatch` 一律拒绝 |
| L1 可转换性判定 | walk → 接受/规范化后接受/拒绝(原因码) | 双配置预测器 `profile=sail` 与 `profile=xs` 各预测一次并记录差异 |
| L2 重定位/规范化 | 接受样本 → 派生样本 v1 + 地址映射表 | satp、x1、mstatus、cur_privilege、result 不变，只改 pre/post_memory 的地址与 PTE 值 |
| L2' Isla 复验（C3） | 派生 JSONL → check 报告 | 要求 100% 恰好被一条路径接纳且结果一致；不一致即重定位器 bug |
| L3 ELF 生成 | 派生样本 + `expected(profile=xs)` → program.S/ELF/case.json | 所有段在 [0x80000000, 0x80100000) 内；链接后重叠断言 |
| L4 运行 | ELF → emu 退出码和日志 | 复用 `pipeline.run_case`（`pipeline.py:996`） |
| L5 归类 | 日志 + case.json → 恰好一个桶 | 桶：agree、xs≠expected、xs≠nemu、已知差异(白名单)、框架误报、构建期拒绝 |

`expected` 取 `profile=xs` 的预测；仅当 sail 与 xs 预测相同且等于 Isla result 时标“Isla 可交叉”。

## 4. 物理重定位（已被取代，2026-11-07 用户决定）

**决定**：不在事后重定位，而是在 Isla 符号执行之前，把 XiangShan 的地址图和内存属性（DRAM 范围、PMA 区域与属性）作为内存配置交给 Isla，让 Isla 直接在正确的内存配置下生成样本；样本天然可重放，不需要重定位层。Sail 模型里 `[60:59]` 软件位、硬件 A/D 更新、非对齐、NAPOT、PBMT 等也应通过配置对齐到 XiangShan，以消掉规范化层。待核实项见 `agents/p0_replay/config-alignment.md`（事实调查产出）。下面保留原事后重定位方案，仅作为配置对齐不可行时的退路，原因：Isla 配置若无法表达某些 XiangShan 区域属性，才需要局部使用。

按样本自带 `pma_regions`（`pt_decode.py:226`）把地址分为 RAM 类（Isla 的 ram 与 experiment_low_ram）和非 RAM 类。核心是**保持地址的区域类别**，不是平移。

| 原 PA | 目标 |
| --- | --- |
| RAM 类，在 [0x80100000, 2^43) 内且不冲突 | 原值 |
| RAM 类，在 low_ram 或 [0x80000000, 0x80100000) | 从 DRAM 池分配（4K 页自 0x1_0000_0000 起；2M/1G 按页大小对齐；Sv48 的 512G 页取 2^39 倍数）；low_ram 在 XiangShan 是设备区，PTW 访问 MMIO 报 AF |
| 非 RAM 类，PA < 2^43 | 移到 2^44 起的区域，保留页内偏移和超级页低位（原样保留会变成“Isla 判 AF、XiangShan 读到设备”，TOR 解读为推测） |
| ≥ 2^43 | 原值；≥ 2^48 走 XiangShan 的 ppn_high 检查（`MMUBundle.scala:851`），值得保留 |

PPN 改写：指针项换成新页框号；L 级叶子 PPN′ = (base′>>12) | (PPN & (2^(9L)−1))，低位原样保留（“未对齐超级页”属性不变）。以页框为单位映射，同页框共用映射，自引用表、PTE 与数据同页的关系自动保留；超级页块内其它被访问页框整块搬；根页框必须留在 0x80200000，落在搬迁块内则拒绝。

规范化（Sail 下语义不变，可由 Isla 证明，不放白名单）：读到的 PTE `[60:59]` 清零（Sail 的 Svrsw60t59b 当软件位，XiangShan `pteResLen=7` 当保留位报 PF，`MMUConst.scala:160`）；指针项 U/A/D 清零（Sail 不拒绝，XiangShan 报 PF，`MMUBundle.scala:812`）。

拒绝原因码（每条写入 results，参照 `pipeline.py:1074-1097` 的 skipped 记录，不静默丢弃）：R1 解码失败/未归属内存；R2 根表冲突；R3 VA 非对齐或跨页；R4 L0 叶 N=1 且 ppn[3:0]=8（XiangShan 认为合法 64K NAPOT，Isla 判 PF）；R5 `pre_registers.tlb` 非空 TLB【推测需检查】；R6 重叠断言触发（应永不发生，触发即 bug）。

规模参考（Opus 对 Sv39 stride=1 的 16592 条样本的只读统计，`output/stride-validation/sv39-1-final/samples.jsonl`）：11640 条（70%）的 PTE 或数据落在 low_ram；读到的 PTE 中 `[60:59]` 非零共 23826 次；数据 PA 分布 DRAM 5282、low_ram 2628、[0,0x1000) 613、[2^43,2^48) 4438、≥2^48 3189。重定位和规范化是主路径。

派生样本复验代价低：satp、x1、mstatus 未变，原 solve-state 加 `--check-samples` 即可，约 0.1 秒/条；224 个形状代表约半分钟，Sv39 全量约 30 分钟。

## 5. 特权与翻译：P0 用 MPRV

顺序：M 态 satp=0，物理地址下用 `sd` 写 PTE、数据和诱饵值；`csrw satp` 后 `sfence.vma x0,x0`；一次 `csrw mstatus` 写样本值并置 MPRV=1、MPP=样本特权级、SUM/MXR 按样本、MIE=0；`li` 恢复 GPR（不访存）；执行被测指令。成功路径先清 MPRV 再做物理检查；异常 handler 也先清 MPRV。

风险：directed-difftest 的 `F-amo-on-nc-page-fault/variant1/dbg08_mprv` 停在 TRAPH，推测是未开放 PMP 所致（MPRV 且 MPP≠M 时按低特权做 PMP 检查，见 `pipeline.py:673-687`、findings F6b），实验 E1 确认。
升级到真 S 态：P0 稳定后，或需要覆盖取指翻译/委托时。代码“岛”挂在样本未用到的根表槽位（Sv39 用 index 2 的 1G 大页 VA=PA=0x80000000；Sv48 的 VPN3 冲突，改用 VPN3≠0 的 VA 别名）。等价性实验：同一样本两方案比较 (结果类别, cause, tval, rd, post-memory, PTE 回读)，允许不同的只有 mstatus.MPP 与 mepc 的 VA 别名；Isla 侧可另起 cur_privilege=Machine、MPRV=1/MPP=S 的 solve-state 证明。

## 6. 预言机对齐与白名单

| 差异 | 处理 |
| --- | --- |
| A/D | 生成侧保持 dirty-update 关闭，与 XiangShan 一致（ADUE 只读 0，Svade）；期望 A=0 报 PF、STORE 在 D=0 报 PF。NEMU 是否硬件更新【未验证】：成功路径与 handler 回读叶 PTE，内存被改则回读不同、C1 报 ABORT |
| 非对齐 | P0 拒绝（R3） |
| [60:59]、指针 U/A/D | 规范化 |
| N/NAPOT | 拒绝（R4）；N=1 但不构成 NAPOT 两边都 PF，接受 |
| PBMT | harness 显式写 `menvcfg=样本值(0)`，PBMTE=0，两边 PF |
| [58:54] 保留位 | 两边 PF |
| PMP/PMA | PMP 全开，复用 `pmp_open_setup`；PMA 靠重定位保持类别 |

框架误报（阻塞级，推测）：`L2TLB.scala:697` 只要 PTW 响应 fire 且非 af 就发事件（pf 也算）；`checkers/tlb.cpp:209-230` 用简化规则 `pf = !v || (!r && w)`，不认保留位/PBMT/N/未对齐超级页/指针 U/A/D，不一致返回 STATE_ERROR，`difftest.cpp:158` 转 ABORT。后果推测：这几类 PF 样本在 NEMU 参与比对前就被判 ABORT。处理：另编关闭 `CONFIG_DIFFTEST_L2TLBEVENT` 的 emu 专跑这几类；或白名单加严格签名。

白名单规则：每条写明输入谓词（由预测器计算）、日志精确签名、规范依据、负责人、到期日；谓词与签名同时匹配且 C2 通过才算命中；只能吸收 C1 已知现象，永不吸收 C2 失配；命中计数进 results；每个里程碑关白名单重跑一次，过时条目删除。

## 7. 比对内容

| 项 | 成功路径 | 异常路径 | 通道 |
| --- | --- | --- | --- |
| rd（LOAD） | DiffTest 提交比对 + 自检再比 | — | C1、C2；期望来自样本数据，可与 Isla 交叉 |
| STORE 写入 | STOREEVENT 比 paddr/data（构建已开）；自检物理回读 | 回读目标，期望不变 | C1、C2 |
| post-memory 与 PTE 回读 | 清 MPRV 后逐 8 字节比；PTE 期望不变（Svade） | 同左 | C2 |
| cause/tval | — | 自检比 mcause 与 mtval=VA | 仅 C2 可信（页异常被 C1 强制同步；访问异常 5/7 不走强制路径，C1 有效） |
| mepc | — | 等于被测指令 | C1、C2 |
| mstatus.MPP/MPIE | MPRV 方案下 MPP=M，属 harness 状态 | 只比 XiangShan 与 NEMU | C1 |

STORE 目标在 pre_memory 为 null 时，填充值取 post 值按位取反，保证“写入丢失”可见。

## 8. 验收与实验

负对照：N1 翻转合法叶 V 位但期望仍成功 → XiangShan 报 PF，C1 被强制同步通过，**C2 必须在 `fail_unexpected_trap` BAD TRAP**；N1′ 翻转 V 位并改期望为 PF → 必须 GOOD；N2 叶 A=0（LOAD）/D=0（STORE）：期望 PF 时 GOOD，期望成功时 BAD；N3 期望 rd 翻 1 位 → `fail_rd` BAD；N4 SUM/MXR 翻转（无新 Isla 运行时 C3 不可用，需注明）；C1 阳性对照复用 lowaddr 非对齐 mcause 分歧（`pipeline.py:48-51`）。

| 实验 | 内容 | 通过标准 |
| --- | --- | --- |
| E0 框架探针 | 从 page_tables.json 手挑 5 个 Sv39 代表：L0 叶成功、V=0 PF、保留位 PF、叶 PPN≥2^36 AF、PTE 在 [2^43,2^48) AF | 弄清 L2TLB 检查器是否误报、NEMU 对 ≥2^48 PA 是截断还是报 AF；成功样本必须 GOOD |
| E1 | MPRV 与手写真 S 态：一个成功样本、一个 PF 样本 | 比较元组相同 |
| E2 | A=0 load、D=0 store，带 PTE 回读 | GOOD 且回读不变；若 ABORT 说明 NEMU 硬件更新，标已知差异并调整 |
| E3 | 224 个代表重定位+规范化后跑 check-samples | 100% 接纳且一致；列 xs 与 sail 预测差异清单 |
| E4 | 224 个代表 + N1~N3 在 emu 上跑 | 每例恰好一个桶、无法解释为零、负对照按预期失败 |

## 9. 与现有代码的接口

新增 `difftest-xiangshan/paging_replay.py`，子命令 `convert`（samples → 派生 JSONL + 拒绝报告）、`build`（生成 ELF）、`classify`（解析 BAD TRAP pc 与 L2TLB 签名）。新函数 `relocate_sample`、`predict(sample, profile)`（在 `pt_decode.classify_pte:90`、`decode_sample:252` 外加 xs 配置：保留位 [60:54]、指针 U/A/D、ppn_high、XiangShan PMA）、`paging_assembly`。复用：`parse_encoding` `:266`；`pmp_open_setup` `:673`；`LINKER` `:846`（代码放 .text.init，不发射远处 .data）；`elf_alloc_ranges` `:411`、`memory_overlaps_ranges` `:429`；`run_case` `:996`；skipped 记录 `:1074`。不复用：`memory_plan` 逐字节 sb（`:377`）、`privilege_setup`（`:690`）、`make_assembly` 装配顺序（`:783-793`）。pt_decode 暂在 isla-enumerate 工作树 `agents/path_merge_call_support/pt_decode/`，先按路径导入并在 case.json 记录其 SHA-256，稳定后迁移。

注意：handler 4 字节对齐（`.option norvc` 加 `.align 2`）；写 satp 与 PTE 后、开 MPRV 前必须 `sfence.vma`；清零 `medeleg`/`mideleg`；P0 每样本一个 ELF（MinimalConfig 单例约 2~3 秒，24 路并行 Sv39 全量约 30~40 分钟），多样本打包放 P1。
粗估工作量：重定位器与预测器配置约 500 行加测试，2 天；汇编生成与归类 1 天；E0~E4 1.5 天；合计约 4~5 个 Codex 工作日。

## 10. 风险与未验证项

| 项 | 状态 |
| --- | --- |
| 页异常走强制同步 | difftest 侧已核实；NEMU 是否无条件服从为推测（只看到 SO 导出符号） |
| L2TLB 检查器误报 ABORT | 门控与比对逻辑已核实；是否触发属推测，待 E0 |
| NEMU 对 PA≥2^48 截断或对 PMA 外 PTE 读的行为 | 未验证（E0） |
| NEMU A/D、MPRV | 未验证（E1、E2） |
| XiangShan PMA 低区可读写 | 条目已读到；TOR 解读为推测 |
| Sv48 在 MinimalConfig 可用 | 推测（`Parameters.scala:78` 默认 true） |
| `solve-state --clause` 不建模取指 | 推测 |
| `pre_registers.tlb` 为空 | 未验证 |

对事实调查结论的修正：GOOD 无条件、失败靠超时；根表 0x80200000 本来就在 DRAM，问题在 low_ram 里的中间级 PTE/数据与非 RAM 类地址，且 [0,0x1000) 在 Isla 里不是 RAM；mret 清 MPRV 只在 MPP≠M 时发生；XiangShan 与 NEMU 的 A/D 差异基本被强制同步掩盖，真正需要提防的是 L2TLB 检查器和 PA 截断；`pmp_open_setup` 文档字符串写 “Locked NAPOT”，config.toml 注释写“L0”，但 0x1f 不含 L 位（0x80），实际均未锁定。
“约 147 种形状”来自 Sv48 LOAD 全量样本；stride 抽样报告中 Sv39 为 106 种（stride=1）、Sv48 为 118 种（stride=11），为不同次运行，口径需核对。
