# P0 重放器设计（v2）

状态：设计稿 v2（2026-11-07）。v1 由 Opus 起草、Claude 整理；v2 由设计顾问依据 [E0 结果](e0-results.md)、[配置对齐事实调查](config-alignment.md)和用户 2026-11-07 的两项决定改写。目标不变：把 Isla 合并符号执行产出的 Sv39/Sv48 LOAD/STORE 页表样本（samples v1），变成可在 XiangShan（emu）与 NEMU 上做 DiffTest 的测试程序。它是 fuzzing loop 取得 DiffTest 反馈的前置阻塞项。

事实标注：【已核实】= 读过代码、文档或有运行证据；【推测】= 有依据但未验证；【未验证】= 需要实验。未标注的条目是设计决定或设计者判断，第 14 节汇总了其中最关键的判断。

引用约定：本轮亲自复读并引用行号的文件有 `emu.cpp`、`emu.h`、`main.cpp`、`args.cpp`、`difftest.h`、`difftest.cpp`、`checkers/traps.cpp`（均在 `difftest-xiangshan/xiangshan/difftest/src/test/csrc/` 下）、`Rob.scala`、`CustomInstructions.scala`、`SimMMIO.scala`、`SoC.scala:149-150`、difftest 的 `SimTop.scala`/`Gateway.scala`、Isla 的 `memory_model.rs`、`target.rs:1180-1202`、`difftest-xiangshan/paging_replay.py`、`difftest-xiangshan/pipeline.py`（40-56、800-816 行），以及实验配置 `.worktree/mmu-symbolic-experiment/symbolic/config.toml`。标“据 config-alignment”的行号来自该调查，本轮未复读；标“v1 引用”的行号沿用 v1，本轮未复核。

## 0. v2 相对 v1 的变更摘要

起因：两项用户决定（2026-11-07）。

- 决定一：不做事后重定位。改为在 Isla 符号执行之前，把 XiangShan 的地址类型和内存属性作为内存配置交给 Isla，让 Isla 直接生成可重放的样本。
- 决定二：DiffTest 的 L2TLB 检查器不开就不会误报，我们不开，该项不再处理。

E0 还推翻了一个 v1 假设：`0x0005006b` 并不会让现有 emu 报 BAD。

| v1 章节 | v2 处理 | 原因 |
| --- | --- | --- |
| §2 第 1 条“a0=1 即 BAD TRAP” | **被取代**，改为 §9 失败退出契约 | E0 负对照：失败桩 `li a0,1; .4byte 0x0005006b` 在现有 emu 上仍打印 GOOD、退出码 0【已核实，e0-results】 |
| §3 L1 双配置判定（profile=sail / profile=xs） | **被取代**，改为单一平台描述文件 | 期望值若取自“xs 配置预测”，等于照抄 XiangShan 的行为，C2 会随 XiangShan 缺陷一起变，失去检出能力 |
| §3 L2 重定位/规范化、L2' 重定位复验 | **被取代**。L2 删除；L2' 改为“同配置具体化复验” | 不再重定位；复验对象改为“harness 具体化后的输入”，见 §3 |
| §3 L3 `expected(profile=xs)` | **修订**：期望值取 Isla 结果 | 同上 |
| §4 物理重定位 | **被取代**，§5 只留摘要 | 决定一 |
| §6 规范化行（[60:59]、指针 U/A/D） | **被取代**。[60:59] 改为 IR 级对齐；指针 U/A/D 改为生成约束或带原因码拒绝 | 规范化会改写 Isla 的输入，而且属于照抄 XiangShan 行为 |
| §6 框架误报（L2TLB 检查器） | **删除**，只在平台描述文件留一条构建约束 | 决定二；E0 已核实当前 emu 未安装检查器 |
| §1 C3“重定位器是否写错” | **修订**：独立 pt_decode 预测与 Isla 的同配置交叉 | 没有重定位器了；C3 改为检验配置是否生效、预测器是否正确 |
| §8 E0~E4 | **修订**：E0 写成“已完成，限定结论”；新增 E-cfg、E-exit；E3 改写 | 见 §10 |
| §4 中的统计与“147/106/118 形状、224 代表” | **作废，待重算** | 这些数字都出自实验配置（含 `low_ram`/`experiment_low_ram`），换配置后不再成立 |
| §10 风险表 | **更新** | 见 §12 |
| 新增 | §4 平台描述文件、§9 失败退出契约、§13 fuzzing 接口 | — |

v1 中仍然成立、v2 原样保留的内容：§1 三路通道的划分、§2 第 2~4 条、§5 MPRV 方案、§7 比对内容、§9 大部分代码接口。

## 1. 三路结论通道

只比较 XiangShan 与 NEMU，查不出“XiangShan 错报页异常”。原因是 DUT 报 12/13/15 号异常时，DiffTest 会调用 `guided_exec`，让 REF 带着 DUT 的 mtval 照样抛出异常（`checkers/traps.cpp:83-98`）【已核实】。E0 的 b、c 两例在只读观测中都记录到 `force=1`【已核实，动态】。所以结论分三路：

| 通道 | 内容 | 能查出 |
| --- | --- | --- |
| C1 | XiangShan 与 NEMU 的 DiffTest | 一般不一致、访问异常（5/7 号不走强制同步，C1 有效） |
| C2 | ELF 内嵌期望值自检，期望值取自 Isla 结果 | 页异常的错报和漏报。负对照“翻转叶子 V 位”只有 C2 能检出 |
| C3 | 离线对比：独立 pt_decode 预测器在同一平台描述下的预测，与 Isla 结果 | 平台配置是否真正生效（如 PMA 注入失败、IR 没重生成），以及预测器自身错误 |

C2 的检出能力来自“期望值独立于 XiangShan”。因此平台描述文件只能拷贝规范允许平台自选的内容，不能拷贝 XiangShan 的行为（§4.1）。

## 2. 现有管线需要改的地方

1. ~~GOODTRAP 无条件，改用 `0x0005006b`（rs1=a0），a0=1 为 BAD TRAP~~。**被取代**：编码本身没错，但现有 emu 不把 a0 当退出码（§9.1）。现行契约见 §9。
2. 页表不放 `.data`，用运行时 `sd` 写入（保留）。原因：img_size 取最后一个段末尾减 0x80000000，首条指令提交时按它把 DUT 内存复制给 REF；段若放到 2^39 附近，会复制数百 GB（v1 引用 `elfloader.cpp:127-129`、`instructions.cpp:32-37`、`ram.h:145`）。E0 已按这一做法实现【已核实，e0-results】。
3. 装配顺序不复用 `make_assembly`（保留）。它先写 mstatus 再 mret（v1 引用 `pipeline.py:787,793`），分页场景下 MPRV 会让初始化写入也走翻译。
4. 异常路径要检查 mcause、mtval（=VA）和 mepc（保留）。E0 生成器已实现（`paging_replay.py:228-230`）【已核实】。

## 3. 分层与契约

| 层 | 输入 → 输出 | 契约 |
| --- | --- | --- |
| P 平台 | 平台描述文件 → Isla config.toml、harness 参数、两个哈希 | 唯一来源，见 §4 |
| L0 解码 | samples v1 行 → walk 记录 | 复用 `pt_decode.decode_sample`。以下一律拒绝并写原因码：解码失败、未归属内存、`result_mismatch`、样本的生成侧哈希与当前平台不符 |
| L1 可重放性判定 | walk → 接受 / 拒绝（原因码） | 只判定、不改写。平台描述用生成约束挡住的类别，若仍有样本漏进来，按原因码拒绝（§7） |
| L2 具体化 | 接受样本 → 具体输入（含 null 字节的填充值和诱饵） | 填充规则确定、可复现；所有写入地址落在 DRAM 且不在保留区 |
| L2' 同配置复验（E3） | 具体输入 → Isla `--check-samples` 报告 | 用同一生成侧哈希的配置；要求 100% 恰好被一条路径接纳且结果一致。不一致说明具体化改变了语义 |
| L3 ELF 生成 | 具体输入 + Isla 期望 → program.S/ELF/case.json | 所有 ELF 段在 [0x80000000, 0x80100000) 内，链接后做重叠断言（E0 已实现，`paging_replay.py:252-257`）【已核实】 |
| L4 运行 | ELF → emu 完整日志与退出码 | 复用 `run_probe` 的命令形式和进程组止损，保留完整日志 |
| L5 归类 | 日志 + case.json → 恰好一个桶 + 原因码 | 契约见 §9.3。桶：agree、xs≠expected(原因)、xs≠nemu、已知差异、other-failure、timeout、limit、构建期拒绝 |
| C3（离线） | walk + 平台描述 → 预测结果 | 与 Isla 结果逐条对比；不一致进 C3 报告，不进运行桶 |

v1 的 L1“双配置判定”与 L2“重定位/规范化”已被取代，原因见 §0。

## 4. 平台描述文件（platform profile）

### 4.1 作用与原则

用一份文件描述“受测平台在规范允许的自选空间里做了哪些选择”。由它同时生成三样东西：Isla 的内存与扩展配置、测试程序的布局与初值、两个哈希。

**拷贝原则（设计决定）**：

- 只拷贝规范允许平台自选的部分：内存图与 PMA、扩展有无、A/D 更新策略（Svade/Svadu）、非对齐访问是否支持、PMP 条目数和粒度。
- 不拷贝 XiangShan 的具体行为。例如“非叶 PTE 的 U/A/D 置位就报 PF”是规范未规定的实现选择，不能写进 Isla 配置。否则 C2 的期望值会随 XiangShan 的可能缺陷一起变。
- 规范未规定、两边又不一致的行为，用生成约束避开；约束做不到时，带原因码拒绝。

### 4.2 字段表

| 段 | 字段 | 内容（MinimalConfig，a13efc87） | 进入哪个哈希 |
| --- | --- | --- | --- |
| `regions` | 物理区域列表 | 每项写 `base/size/kind/pma`。kind 取 ram、hole、device、harness 四类之一（§4.3）。数据据 config-alignment 的 PMA 表【已核实，据 config-alignment】 | 生成侧 |
| `harness` | 保留区 | [0x80000000, 0x80100000)：代码、handler、失败桩所在窗口 | 生成侧 |
| `harness` | 根页表区 | [0x80200000, 0x80203000)，与现有 `page_tables` 区一致（实验配置 `config.toml:239-243`）【已核实】 | 生成侧 |
| `isa` | 扩展有无 | Svrsw60t59b：平台选“未实现”（XS 当保留位，属扩展有无的自选）。Svnapot：XS 支持、模型不支持，收窄到共同子集（生成约束或 R4）。Svpbmt：XS 支持、模型不支持，用 menvcfg.PBMTE=0 收窄。Svade=是、Svadu=否 | 生成侧 |
| `isa` | 非对齐 | 硬件支持 LOAD/STORE（双方一致【已核实，据 config-alignment】）；P0 另加生成约束“自然对齐” | 生成侧 |
| `isa` | PMP | 32 条可用、4 KiB 粒度（据 config-alignment）。harness 用 NAPOT 全开 RWX | 生成侧 |
| `csr_init` | menvcfg / mstatus / medeleg / mideleg | menvcfg=0（PBMTE=0、ADUE=0）；mstatus 基值 0x600 再按样本覆盖 MPRV/MPP/SUM/MXR；委托寄存器清零 | 生成侧 |
| `ir` | Sail→IR 产物 | IR 文件 SHA-256 与 provenance JSON 哈希（含扩展开关） | 生成侧 |
| `isla` | 运行器 | isarch 二进制 SHA-256 | 生成侧 |
| `env` | 受测与参考 | emu SHA-256（现 `87141692…`）、NEMU SO SHA-256（现 `9188e7dd…`）、XiangShan commit、GCC 版本【已核实，e0-results】 | 运行侧 |
| `env` | emu 构建约束 | **emu 构建须未启用 `DEBUG_L2TLB`**。E0 已核实当前 emu 未安装 L2TLB 检查器【已核实，e0-results】；该约束随 emu 哈希记录 | 运行侧 |
| `env` | pt_decode | 预测器源码 SHA-256 | 运行侧（C3 报告也记录） |

**两个哈希（设计判断）**：

- 生成侧哈希 `platform_gen_sha256`：对 `regions/harness/isa/csr_init/ir/isla` 的规范化序列化取 SHA-256。它决定 Isla 产出什么样本，随样本流转。
- 运行侧哈希 `platform_env_sha256`：对 `env` 取 SHA-256，只写进 case.json 和结果记录。

拆开的理由：重编 emu 或换 NEMU 不应让样本库作废，而改内存图或 IR 必须让样本库作废。

### 4.3 物理区域四选一映射

| kind | 适用区间（MinimalConfig） | Isla `pma_regions` | Isla `memory_regions` | 期望行为 |
| --- | --- | --- | --- | --- |
| ram | DRAM [0x80000000, 2^43) 去掉 harness 和根表 | `attr="ram"`，base `0x80000000`、size `0x7FF80000000`（与实验配置 `config.toml:227-231` 相同）【已核实】 | symbolic，围绕根表切成多段（见下） | 正常访存 |
| harness | [0x80000000, 0x80100000) | 在 ram 的 PMA 内，不挖掉 | excluded | 触及即判死，Isla 不产出此类样本 |
| hole | PMA 禁止访问的区间：[0x39002000, 0x3a000000)、[2^43, 2^48)；以及 ≥2^48（XiangShan 用 ppn_high 检查报 AF，据 config-alignment） | 不写 | 不写 | 双方都报 AF。AF 不走强制同步，由 C1 交叉 NEMU【推测：NEMU 只测过一个 ≥2^48 地址，见 §12】 |
| device | [0, 0x80000000) 中 PMA 允许访问的部分：设备窗口、DECERR 空洞，以及 Flash/Debug 等 | `attr="mmio"` | excluded | 判死。设备有副作用，DECERR 的异常行为也未核实，P0 一律不覆盖。Sail 若在发出访存前就因 PMA 属性分叉出 AF（例如 PTW 碰到 mmio），excluded 抓不到；因此 AF 目标落在 device 或 harness 区的样本在 L1 按 R9 拒绝 |

**device 必须两层都写**【推测】。依据是 `memory_model.rs:8-19` 的语义说明：

- symbolic 区只是声明，不产生约束。
- 可访问性完全由模型自身的 PMA/PMP 判定，不可访问时模型直接分叉出 access fault。
- excluded 通过给“实际发出的访存”追加地址约束来判死。

所以，若 device 区不写 PMA，Sail 在访存前就会分叉出 AF，excluded 的约束碰不到这条路径。结果是 Isla 期望 AF，而 XiangShan 可能读到设备。E-cfg 要用计数验证这一点（§10）。

**生成器必须处理的坑**：

- **symbolic 区间不能重叠**【已核实：实验配置用 `ram_before_pt`/`ram_after_pt` 绕开根表，见 `config.toml:155-165`，`config.toml:140-141` 注释说明区域不允许重叠】。config-alignment 的草案把 symbolic `ram` 从 0x80100000 起一直到顶，会包住 `page_tables`，必须切成 [0x80100000, 0x80200000)、根表、[0x80203000, 2^43) 三段。
- 实验配置里的 `low_ram`、`experiment_low_ram`、`ram_before_pt`（起点 0x80000000，与 harness 重叠）、`mmio_hole` 都要删除或改写。`mmio_hole` 由 device 的 excluded 覆盖。CLINT 落在 device 区，保留 `clint_enabled=false`（`config.toml:18`）。
- `code` 区 [0,0x1000) 是 concrete。删掉后，solve-state 取被测指令是否还依赖它【未验证】。v1 的“solve-state 不建模取指”本身也是【推测】。列为 E-cfg 检查项。
- `[threads]` 落在 0x80100000–0x80300000，`[symbolic_addrs]` 落在 0x80310000–0x80410000（`config.toml:46-54`）。solve-state 是否用到它们，是否会与 symbolic 区或根表冲突【未验证】，列为 E-cfg 检查项。

### 4.4 逐项对齐表

| 项 | 当前 Sail/IR 与 XiangShan 的差异（据 config-alignment） | v2 处理 | 需要重生成 IR | 状态 |
| --- | --- | --- | --- | --- |
| DRAM 范围与顶界 | 实验配置 PMA ram 已是 [0x80000000, 2^43)，但另加了 `experiment_low_ram` | 删除 low_ram 两项，按 §4.3 生成 | 否（运行时注入，`target.rs:1180-1202`）【已核实】 | 注入路径已核实；样本落点【未验证，E-cfg】 |
| 低端设备与空洞 | XiangShan 低端 PMA 为 RW，但多数地址没接设备（DECERR） | device：mmio 加 excluded；hole：不写 | 否 | 判死效果【推测，E-cfg】 |
| ≥2^48 物理地址 | XiangShan 在 PTE 阶段查 ppn_high 报 AF；Sail 可能先判权限 | 地址落 hole；“多错误同时成立”见 §7 | 否 | 单错误时双方都 AF【已核实：E0 的 d 与 d-alias-control，只测一个地址】 |
| Svrsw60t59b（[60:59]） | Sail 当软件位，XiangShan 当保留位报 PF | 平台选“未实现”，改 provenance JSON 后重生成。这是扩展有无，不是照抄行为 | **是**（约 501 秒/份，据 config-alignment） | 【未验证】 |
| A/D | `dirty_update=false`，与 XiangShan 的 Svade 一致 | 无需改，profile 记录 Svade | 否 | 【已核实，据 config-alignment】；NEMU 侧【未验证，E2】 |
| 非对齐 | 双方硬件都支持 LOAD/STORE；异常优先级未核实 | profile 记“支持”；P0 加生成约束“VA 自然对齐”。实验配置已有 `__isla_always_aligned="true"`（`config.toml:71`），它是否就是这一约束【推测】；做不到时退回原因码 R3 | 否 | 【未验证】 |
| Svnapot | Sail 写死不支持，XiangShan 支持 64 KiB NAPOT；无配置开关 | 生成约束：L0 叶不得构成“N=1 且 ppn[3:0]=8”。约束机制不可用时用 R4 拒绝。N=1 但不构成 NAPOT 时双方都 PF，接受 | 补齐需改模型 | 约束机制【未验证】 |
| Svpbmt | Sail 写死不支持；XiangShan 支持，PBMTE 复位 0 | `csr_init.menvcfg=0`，双方都把 PBMT 位当保留位报 PF | 否 | 双方 PF【推测】；E0 未单独测（b 的 V=0 掩盖了 PBMT） |
| [58:54] 保留位 | 双方都报 PF | 无需处理 | 否 | 【已核实：E0 c 例】 |
| 非叶 PTE 的 U/A/D | 规范只要求软件清零；Sail 不拒绝，XiangShan 报 PF；无配置键 | **生成约束**：指针 PTE 的 U/A/D=0。约束不可用时用 R7 拒绝。不改 Sail、不写白名单 | — | 约束机制【未验证】 |
| PMP 参数 | Sail count/usable=16、grain=0；XiangShan 32 条、4 KiB | profile 记 XiangShan 的值。harness 全开，LOAD/STORE 样本不碰 PMP CSR，所以 **P0 可推迟重生成**（设计判断） | 是 | 【未验证】 |
| MPRV/SUM/MXR | 是 CSR 状态，不是功能开关 | harness 按样本恢复（§6） | 否 | 【已核实，据 config-alignment】 |
| 设备副作用、Debug 条件、独立 AMO 权限 | Isla 配置无法表达 | device 区判死；AMO 留到 P1 | — | 【已核实：无法表达，据 config-alignment】 |

### 4.5 生成物与哈希流转

1. `profile → config.toml + profile.lock.json`。lock 内容是 `{platform_gen_sha256, config_toml_sha256, ir_sha256, isarch_sha256}`。生成器先校验实际 IR 与 isarch 的哈希等于 profile 中的值，不符即拒绝生成。
2. Isla 运行时，samples 的运行清单拷贝 lock。样本行或清单必须带 `platform_gen_sha256`；只带在清单上时，清单要同时记录 samples 文件的 SHA-256 以完成绑定。P0 由启动 Isla 的外部包装脚本写清单（lock 全文加 samples 的 SHA-256），不改 Isla、不依赖 isla-enumerate 工作树；isla-enumerate 在样本行中原生携带哈希留作后续。
3. `convert` 读样本时，比对样本的哈希与当前 profile 的生成侧哈希，不符时按 R0 拒绝。
4. `--check-samples`（L2'、E3）必须用同一 lock 生成的 config.toml。包装脚本运行前校验 `sha256(config.toml) == config_toml_sha256`。这样不需要改 Isla 的配置解析。
5. profile 同时生成 harness 参数：链接窗口、保留区、menvcfg、PMP 设置、根表地址。
6. case.json 记录：两个哈希、lock 全文、ELF 哈希、符号表、pt_decode 哈希。归类时校验 ELF 哈希与 case.json 一致。

## 5. 物理重定位（v1 §4，已被取代）

被取代的原因：决定一。配置对齐后，样本的物理落点由 Isla 在正确的内存图下产生，不需要事后改地址和 PTE。

v1 方案的要点，仅作历史参考，不作为退路实施：

- 按区域类别保持地址性质：低端 RAM 移入 DRAM 池，非 RAM 移到 2^44 起，≥2^43 原样保留。
- 按页框改写 PPN；根表固定在 0x80200000。
- 对 [60:59] 和指针 U/A/D 做规范化。

不作为退路的原因：

- 规范化本身属于照抄 XiangShan 行为（§4.1）。
- 重定位后需要 Isla 复验才可信，复杂度不低于直接重跑配置。

v1 的统计数字（16592 条中 70% 落在 low_ram、[60:59] 非零 23826 次、数据 PA 分布等）来自实验配置，**已失效**，由 E-cfg 重算。

## 6. 特权与翻译：P0 用 MPRV（保留 v1 §5）

执行顺序：

1. M 态、satp=0，在物理地址下用 `sd` 写 PTE、数据和诱饵值。
2. `csrw satp`，然后 `sfence.vma x0,x0`。
3. 一次 `csrw mstatus`：写样本值，并置 MPRV=1、MPP=样本特权级，SUM/MXR 按样本，MIE=0。
4. 用 `li` 恢复 GPR（不访存）。
5. 执行被测指令。
6. 成功路径先清 MPRV，再做物理回读检查；异常 handler 也先清 MPRV。

E0 的生成器已按此实现（`paging_replay.py:207-226`）【已核实】。

遗留风险：directed-difftest 的 `F-amo-on-nc-page-fault/variant1/dbg08_mprv` 停在 TRAPH，推测是 PMP 未开放（v1 引用 `pipeline.py:673-687`）。由 E1 确认。

升级到真 S 态的做法与等价性实验同 v1：代码岛挂在样本未用到的根表槽位；比较元组 (结果类别, cause, tval, rd, post-memory, PTE 回读)。

## 7. 预言机对齐、约束、拒绝与已知差异（修订 v1 §6）

**期望值来源**：C2 的期望值一律取自 Isla 结果（样本的 result、post 寄存器和 post_memory），不取自预测器。预测器只用于 C3 和拒绝判定。

| 差异 | v2 处理 |
| --- | --- |
| A/D | 平台选 Svade，期望 A=0 报 PF、STORE 在 D=0 报 PF。成功路径和 handler 都回读叶 PTE；NEMU 若硬件更新 A/D，回读会不同，C1 报 ABORT（E2） |
| 非对齐 | 生成约束只产出自然对齐的 VA；漏进来的按 R3 拒绝 |
| [60:59] | IR 级对齐（Svrsw60t59b=否），不再规范化 |
| 指针 U/A/D | 生成约束；漏进来的按 R7 拒绝 |
| N/NAPOT | 生成约束；漏进来的按 R4 拒绝。N=1 但不构成 NAPOT 时接受 |
| 未对齐超级页（L1/L2 叶子低位 PPN 非零） | 规范强制报 PF，双方应一致，不约束、不拒绝；【未验证】，E0 未测，E4 代表集至少放一例 |
| PBMT | menvcfg=0，双方 PF |
| [58:54] | 双方 PF |
| PMP/PMA | PMP 全开（复用 `pmp_open_setup`）；PMA 由 profile 生成 |
| 多错误同时成立（例如高 PPN 加权限错误） | 预测器标出每个样本同时成立的错误集合。规范规定了优先级的，保留：XiangShan 若与 Isla 不同，就是真发现，进 `xs≠expected`。规范未规定的，按 R8 拒绝 |

**拒绝原因码**：每条拒绝都写入 results，不静默丢弃。

| 码 | 含义 |
| --- | --- |
| R0 | 生成侧哈希不符 |
| R1 | 解码失败或未归属内存 |
| R3 | VA 非对齐或跨页 |
| R4 | 构成 64K NAPOT |
| R5 | `pre_registers.tlb` 非空 |
| R6 | 重叠断言触发（应永不发生） |
| R7 | 指针 PTE 的 U/A/D 非零 |
| R8 | 多错误且规范未定优先级 |
| R9 | 落入 harness 或 device 区（配置应已判死，出现即说明配置漏洞） |

v1 的 R2（根表冲突）随重定位一起取消；同类情况归入 R9。

**已知差异**（取代 v1 的白名单，去掉了 L2TLB 部分）：只用于登记已经人工确认的 XiangShan 与 NEMU 之间的 C1 现象。规则如下：

- 每条写明输入谓词（由预测器计算）、日志精确签名、规范依据、负责人、到期日。
- 谓词与签名同时匹配、且 C2 通过，才算命中。
- **永不吸收 C2 失配**。
- 命中计数写入 results；每个里程碑关闭已知差异表重跑一次，删除过时条目。

## 8. 比对内容（保留 v1 §7）

| 项 | 成功路径 | 异常路径 | 通道 |
| --- | --- | --- | --- |
| rd（LOAD） | DiffTest 提交比对，自检再比一次 | — | C1、C2 |
| STORE 写入 | STOREEVENT 比 paddr/data；自检做物理回读 | 回读目标，期望不变 | C1、C2 |
| post-memory 与 PTE 回读 | 清 MPRV 后逐 8 字节比；PTE 期望不变（Svade） | 同左 | C2 |
| cause/tval | — | 自检比 mcause 与 mtval=VA | 页异常只有 C2 可信；访问异常 5/7 号 C1 有效 |
| mepc | — | 等于被测指令 | C1、C2 |
| mstatus.MPP/MPIE | MPRV 方案下属于 harness 状态 | 只比 XiangShan 与 NEMU | C1 |

STORE 目标在 pre_memory 中为 null 时，填充值取 post 值按位取反，保证“写入丢失”可见。

## 9. 失败退出契约（新增，取代 v1 §2 第 1 条）

### 9.1 现状事实

- **现有 emu 不把 a0 当退出码**【已核实，e0-results】。DiffTrapEvent 的 `code` 取自 XSTrap 指令的提交写回数据（`Rob.scala:1816,1818`），而 ALU 对功能码 0x7f 不选 rs1（据 e0-results）。trap 的 `pc` 取自同一条提交的 PC（`Rob.scala:1817`）。E0 实测该 pc 准确落在 `fail_unexpected_trap_trap` 上【已核实，e0-results】。
- **退出码 0 不等于通过**【已核实】。非 FUZZING 构建中，`is_good_trap()` 在 GOODTRAP、LIMIT_EXCEEDED、SIM_EXIT 三种状态下都返回真（`emu.h:93-98`），`main` 返回 `!is_good`（`main.cpp:44,64`）。也就是说，`-C`/`-I` 上限耗尽同样退出 0；只有 ABORT 和 BADTRAP 退出非零。
- **DiffTest 对 trap 之前的提交做比对**【已核实】。`difftest_nstep` 每步先调用 `difftest_step()` 比对 REF（其中 `proxy->compare(dut) || pc_mismatch` 在 `difftest.cpp:711`），之后才调用 `difftest_state()` 检查 trap（`difftest.cpp:123-131`）。因此 DUT 走到哪个桩，是在每次提交都与 NEMU 对齐之后才走到的。由此推论：若 DUT 的分支错跳到 `good_trap`，REF 不会跟着跳，结果应是 ABORT 而不是假 GOOD【推测：只核实了执行顺序，E-exit 不覆盖这一推论】。例外：被强制同步的页异常中，REF 跟随 DUT，所以这类情况只能由 C2 判定，这正是 C2 存在的理由。
- 顶层 `exit` 信号：difftest 的 `SimTop.scala:129` 取 `gateway.exit.getOrElse(0.U)`，`Gateway.scala:253` 的汇总结果给出 `exit = None`。推测软件无法驱动它【推测：未逐一核对 Gateway 的全部配置分支】。

### 9.2 候选对比

| 候选 | 可靠性 | 对 C1 的干扰 | 吞吐 | fuzzing 反馈 |
| --- | --- | --- | --- | --- |
| A. 退出 PC 反查符号（E0 已部分实现） | 高。pc 取自真实提交，且 trap 前每次提交都被 NEMU 比对过；E0 已实测负对照落点正确 | 无，程序路径不变 | 零开销 | 好：每个失败原因一个桩，pc 直接给出原因码 |
| B. 失败桩制造确定的 DiffTest 不一致（利用已知分歧） | 低。依赖某个会被修掉的缺陷或 NEMU 差异 | 严重：C2 失败和真实 C1 失败混进同一个 ABORT 桶 | 无额外开销 | 差：所有失败都变成 ABORT |
| C. 失败桩自环，再用 `-I`/`-C` 上限截断 | 中低。退出码仍是 0；没有 trap 时打印的 pc 是 trap 事件残值，不可靠（`emu.cpp:657-658` 打印的是 `get_trap_event()->pc`） | 无 | 差：每个失败都要跑满上限 | 差：拿不到原因码，还和真实挂死混在一起 |
| D. 失败桩向约定地址写原因字，HIT 后读内存快照 | 不可行。emu 只在非 GOOD、非 LIMIT 时保存快照（`emu.cpp:269`），没有“GOOD 后导出内存”的选项（`args.cpp:84-145` 的选项列表） | — | — | 要改 emu |
| E. 失败桩经 UART 打印原因、cause、tval、rd | 中。UARTLite 在 0x40600000（`SoC.scala:149`），SimMMIO 已接入（`SimMMIO.scala:85`）。emu 是否把 UART 输出打到 stdout【推测】；MMIO 写在 DiffTest 下如何对齐 NEMU【未验证】 | 有：在 harness 里引入 MMIO 访问 | 小 | 最好：能带实际值，但只作诊断 |
| F. 修受测 emu 的 XSTrap 结果传递 | 高，可得到真 BAD 和非零退出码 | 无 | 零 | 与 A 相同 |

### 9.3 推荐：A 为判定契约，E 为可选诊断，F 不做

**判定契约（L5 归类，取代 `classify_log` 的现行逻辑）**。每次运行必须用 case.json 中的符号表，并先校验运行所用 ELF 的哈希与 `elf_sha256` 一致。

1. **agree** 的条件是以下几点同时成立：
   - 日志恰好出现一次 `HIT GOOD TRAP at pc = X`；
   - X 等于 `symbols["good_trap_ins"]`，这是正向匹配；
   - 没有 `ABORT`；
   - 进程正常结束，退出码 0。
2. **xs≠expected(reason)**：X 等于某个 `fail_<reason>_trap`。打印 GOOD 还是 BAD 都算，这样 emu 将来修好后照样兼容。原因码取 `<reason>`。
3. **xs≠nemu**：出现 ABORT，且没有命中已知差异。
4. **timeout**：超过外部墙钟上限；**limit**：出现 `EXCEEDING CYCLE/INSTR LIMIT`。两者都不是 agree。
5. **other-failure**：其余全部情况，包括 X 不对应任何符号、多次 HIT、日志缺少 HIT 行。

**现行代码有漏洞，必须修**【已核实】：`paging_replay.py:274-276` 只在“pc 落在 `fail_` 前缀符号上”时判失败。pc 对不上任何符号时 `symbol=None`、`false_good=False`，`agree` 仍为真。v2 要求按第 1 条正向匹配 `good_trap_ins`。

**生成侧加固**：

- 保留 `li a0,1; .4byte 0x0005006b` 失败桩和 `li a0,0` 的 GOOD 桩。它们在现有 emu 上无害，emu 修好后自动变成真 BAD。
- 生成后对 objdump 做静态检查：`good_trap` 只能经 `check_memory` 顺序落入，全程序只有 GOOD 桩一条 `0x..06b` 指令位于 `good_trap_ins`，每个失败桩有唯一符号。

**推荐理由（设计判断）**：

- A 的可靠性来自两个已核实事实：trap pc 取自真实提交；DiffTest 在 trap 前每次提交都比对过 REF。
- A 不改受测对象，也不在 harness 里引入新的访存。
- A 零开销，并且天然给出原因码。
- 它的唯一弱点是“退出码 0 不代表通过”，而这在现有 emu 上本来就成立（LIMIT 同样退出 0）。所以无论如何都必须以归类器为唯一判定来源。

**UART 诊断（可选，P1）**：失败桩在判定之后经 UARTLite 打印 `reason/cause/tval/rd`，给 fuzzing 提供实际值。前提是先做两件事：确认 emu 把 UART 输出打到 stdout；用一个最小程序确认 MMIO 写在 DiffTest 下不引起 ABORT。UART 输出不参与判定。

**是否修受测 emu（F）**：不建议现在修（设计判断）。

- 工作量：Chisel 改动本身很小，ALU 结果选择为 0x7f 选 rs1；但需要重新生成 MinimalConfig 的 RTL 并用 Verilator 重建 emu，耗时以小时计【推测】。
- 风险一：改的是受测对象。新 emu 哈希一变，按根 AGENTS.md 第 3 条，E0 的全部 PASS 退为待复验。
- 风险二：会形成一个与上游不同的 XiangShan 分支，需要单独维护。
- 收益：只是“退出码可用”。信息量不超过 A。
- 只有当下游工具（例如 fuzzing 框架）只能读退出码、不能读日志时，才值得在隔离的源码副本里做，并作为新的运行侧环境记录。

### 9.4 验证：负对照实验 E-exit

不改 emu，在当前 emu 上进行。

| 例 | 构造 | 必须得到 |
| --- | --- | --- |
| X1 复判 | 用 v2 契约重新归类 E0 已有的 7 份日志（不重跑，注明“复判”） | a~e、d-alias-control 为 agree；b-wrong-expected 为 `xs≠expected(unexpected_trap)` |
| X2 游离 GOOD | 在 `good_trap_ins` 之外、用 `.L` 局部标签（不进 nm 符号表）放一条 `0x0000006b`，让成功路径跳过去 | other-failure（专测正向匹配） |
| X3 N3 | a 的期望 rd 翻 1 位 | `xs≠expected(rd)` |
| X4 上限 | 成功路径改成自环，运行时加 `-I 10000` | limit，退出码 0 也不得判 agree |
| X5 正例 | a 原样重跑 | agree |

通过标准：5 例全部符合，且每例恰好落入一个桶。X2 和 X4 是专门针对“退出码 0 / 打印 GOOD 不等于通过”的反例。

## 10. 验收与实验（修订 v1 §8）

负对照 N1~N4 的定义同 v1：

- N1：翻转 V 位，期望仍为成功，必须得到 `xs≠expected(unexpected_trap)`。
- N1′：翻转 V 位，期望改为 PF，必须 agree。
- N2：A/D 置 0。
- N3：rd 翻 1 位。
- N4：SUM/MXR 翻转。没有新的 Isla 运行时 C3 不可用。

“BAD TRAP”一律改读为 §9.3 的 `xs≠expected(reason)`。

| 实验 | 内容 | 通过标准 | 状态 |
| --- | --- | --- | --- |
| E0 框架探针 | 5 个 Sv39 代表加错误期望负对照、低位别名对照 | — | **已完成，限定结论**（见下） |
| E-exit | §9.4 | §9.4 | 待做；X1 只需复判 |
| E-cfg 配置对齐 | 见下 | 见下 | 待做，是 E3/E4 的前置 |
| E1 | MPRV 与手写真 S 态：一个成功样本、一个 PF 样本，样本取自 E-cfg | 比较元组相同 | 待做 |
| E2 | A=0 的 load、D=0 的 store，带 PTE 回读，样本取自 E-cfg | agree 且回读不变；若 ABORT，说明 NEMU 会硬件更新，登记已知差异 | 待做 |
| E3（改） | E-cfg 每个形状取一个代表，经 L2 具体化（含填充值和诱饵）后，用同一 lock 跑 `--check-samples` | 100% 恰好一条路径接纳且结果一致；同时报告 C3 不一致清单 | 待做 |
| E4 | E3 的代表（至少含一例未对齐超级页、一例 PBMT 非零、一例 N=1 非 NAPOT），加 N1~N3，在 emu 上运行 | 每例恰好一个桶，无法解释的为零，负对照按预期失败 | 待做 |

**E0 限定结论**（详见 [e0-results.md](e0-results.md)）：

- 5 个正例的 C1+C2 限定 PASS。范围限于 Sv39 `ld`、这 5 个输入，以及当前 emu 与 NEMU SO 的哈希。
- 页异常强制同步已动态确认。
- 当前 emu 未安装 L2TLB 检查器，保留位 PF 未被 ABORT。
- NEMU 对一个 ≥2^48 地址（含低位别名对照）报 AF，没有截断。
- 负对照的 C2 分支正确，但按 v1 契约“必须 BAD”判为 FAIL。按 v2 契约的签收待 E-exit X1 复判。
- PBMT、N、未对齐超级页三类未测。它们不再因 L2TLB 检查器构成风险，但仍按 §4.4 和 §7 约束或拒绝。

**E-cfg 配置对齐实验**：

1. 由 profile 生成配置。以实验配置为底，删除 `low_ram`、`experiment_low_ram`、`ram_before_pt`、`mmio_hole`、`code`（`code` 删除后能否运行是检查项）。按 §4.3 加入 harness excluded、device 的 mmio 加 excluded、围绕根表切开的 symbolic 区。
2. 锁定 isarch 与 IR 的哈希写入 lock。config-alignment 已指出，现存 isarch 与实验 manifest 不一致。
3. 分两步：
   - E-cfg-a：只改内存配置，不重生成 IR，用来隔离内存图的影响；
   - E-cfg-b：Svrsw60t59b=否，重生成 IR 后重跑。
4. 跑 Sv39 LOAD 合并，samples 模式与 count 模式各一次。
5. 用 pt_decode 检查每条样本的每次 PTE 读和数据访问的物理地址，并跑 C3。

E-cfg 通过标准（全部可判定）：

1. lock 中 isarch、IR、config.toml 的哈希与实际运行一致。
2. 成功路径上，所有 PTE 读与数据访问的 PA 都在 DRAM 内，且不在 harness 区。
3. 任何样本中，触及 harness 或 device 区的访问计数为 0。若不为 0，说明 device 的“mmio 加 excluded”推测不成立，需改方案。
4. AF 样本的目标 PA 只能落在 hole 区；落在 device、harness 或 ram 区的 AF 一律计为违规（L1 按 R9 拒绝并计数）。
5. C3：预测器与 Isla 结果 100% 一致；若有不一致，逐条给出原因并修正后复跑。
6. E-cfg-b 中 [60:59] 非零的 PTE 一律得到 PF。
7. `code` 区、`[threads]`、`[symbolic_addrs]` 三个检查项都有明确结论。

样本数、守卫类数（`counted_classes`）、形状数只报告与旧运行（`sv39-1-final`，16592 条）的差异并给出解释，**不作为通过阈值**。新的形状代表数替代 v1 的“224”。

## 11. 与现有代码的接口（修订 v1 §9）

在 `difftest-xiangshan/paging_replay.py`（E0 已建）上扩展：

- 子命令 `profile`（profile → config.toml + lock）、`convert`（加入 R0~R9 判定，去掉地址映射）、`build`、`run`、`classify`（按 §9.3 重写）。
- 新函数 `predict(walk, profile)`：在 `pt_decode.classify_pte`、`decode_sample` 之外，按 profile 计算可重放性、错误集合和预测结果（v1 引用 `pt_decode.py:90,252`）。`relocate_sample` 取消。

复用与不复用同 v1：

- 复用：`pmp_open_setup`、`LINKER`、`elf_alloc_ranges`、`memory_overlaps_ranges`。E0 已复用【已核实，e0-results】。
- 不复用：`memory_plan` 的逐字节 sb、`privilege_setup`、`make_assembly`。

pt_decode 仍按路径从 isla-enumerate 工作树导入，在 case.json 记录其 SHA-256。

profile 文件建议放在 `difftest-xiangshan/platforms/`。生成侧哈希在 P0 由外部包装脚本随运行清单记录（§4.5 第 2 步），isla-enumerate 原生携带留作后续。

粗估工作量（推测）：

| 项 | 估计 |
| --- | --- |
| profile 生成器与 lock 校验 | 约 1 天 |
| 预测器 profile 化与拒绝码 | 约 1 天 |
| 归类器重写与 E-exit | 0.5 天 |
| E-cfg（含一次 IR 重生成，约 501 秒/份） | 1 天 |
| E1~E4 | 1.5 天 |
| 合计 | 约 5 个 Codex 工作日 |

## 12. 风险与未验证项（更新 v1 §10）

| 项 | 状态 |
| --- | --- |
| 页异常走强制同步 | **已核实**：difftest 侧代码，加 E0 动态观测 `force=1` |
| L2TLB 检查器误报 ABORT | **不再作为风险**（用户决定二）。当前 emu 未安装检查器【已核实，e0-results】；只保留 profile 中的构建约束（§4.2） |
| NEMU 对 ≥2^48 PA 的行为 | **部分核实**：只测了 PA=`0x1040043000000` 一个地址及其低位别名，结果 AF、未截断。其他 ≥2^48 地址、[2^43,2^48) 的数据访问【未验证】 |
| 退出码契约 | **已证伪 v1 假设**（a0 不生效）；v2 改用 pc 正向匹配，待 E-exit |
| 现行 `classify_log` 对无符号 pc 判 agree | **已核实漏洞**，§9.3 规定修复 |
| device 区“mmio 加 excluded”能否判死 PTW 与数据访问 | 【推测】，E-cfg 第 3 条判定 |
| DECERR 空洞、[0x39002000,0x3a000000) 上三方（XiangShan、Sail、NEMU）的 AF 是否一致 | 【未验证】。P0 把 DECERR 归 device 判死，只保留 PMA 禁止的 hole |
| 生成约束机制（NAPOT、指针 U/A/D、对齐）在 Isla 中是否可用 | 【未验证】。不可用时退回 R3/R4/R7 拒绝，代价是覆盖缺口和样本浪费，E-cfg 报告比例 |
| Svpbmt 在 menvcfg=0 下双方 PF | 【推测】，E0 未单独测 |
| 多错误优先级（高 PPN 与权限等） | 【已核实存在差异来源，据 config-alignment】；按 §7 的 R8 或真发现处理 |
| 设备副作用、总线空洞、Debug 条件、独立 AMO 权限 | 无法用配置表达【已核实，据 config-alignment】；device 判死，AMO 留到 P1 |
| `code` 区删除、`[threads]`/`[symbolic_addrs]` 与新布局的关系 | 【未验证】，E-cfg 检查项 |
| IR 重生成（Svrsw60t59b、PMP）后 workaround 坐标仍有效 | 【未验证】；按 `specs/ir-workflow.md` 核对 |
| NEMU 的 A/D、MPRV | 【未验证】（E1、E2） |
| Sv48 在 MinimalConfig 可用 | 【推测】（v1 引用 `Parameters.scala:78`） |
| `solve-state --clause` 不建模取指 | 【推测】 |
| `pre_registers.tlb` 为空 | 【未验证】；E0 的转换器已拒绝非空 TLB |
| v1 的全部统计数字 | **已失效**，E-cfg 重算 |

对 v1 事实修正的保留项：

- mret 清 MPRV 只发生在 MPP≠M 时。
- `pmp_open_setup` 的文档字符串和 config.toml 注释都写了“锁定”，但 0x1f 不含 L 位（0x80），实际均未锁定（v1 引用）。

## 13. 与 fuzzing 的接口

本设计对 fuzzing 交付“种子库 + 归类接口”，不涉及变异策略。契约如下：

**种子记录**（每条一个，可独立重放）：

- 具体输入：satp、GPR、mstatus 相关位、特权级、被测指令编码，以及完整的 pre-memory（含 L2 的填充值和诱饵，即实际写进 ELF 的值）；
- Isla 期望（result、cause、tval、rd、post-memory）；
- `platform_gen_sha256`；
- **守卫赋值标签**：样本所在守卫类的打包守卫真值，取 isla-enumerate 的投影见证；
- **稳定节点键**：合并路径中守卫节点的标识，要求在同一 IR、同一 isarch、同一 profile 下跨运行不变；
- 拒绝原因码（被拒的种子也入库，标记为不可重放）。

**归类接口**：

- 调用形式为 `classify(case.json, log) → {bucket, reason, trap_pc, trap_symbol, platform_env_sha256}`。
- 同一种子、同一运行侧哈希下结果确定。
- 桶和原因码集合有版本号，新增时只追加、不改义。

**判定唯一性**：fuzzing 只能读归类结果，不得读 emu 退出码（§9.1：退出码 0 不代表通过）。

**失效规则**：

- 生成侧哈希变化时，守卫标签与节点键全部作废，种子要重新生成或经 `--check-samples` 重新确认。
- 只有运行侧哈希变化时，种子保留，归类结果需重跑。

待 isla-enumerate 确认【未验证】：守卫赋值标签和节点键的现有导出格式，以及其稳定性范围。

## 14. 设计判断汇总（非事实）

- 期望值取 Isla、平台描述只拷贝规范自选项（§4.1）。
- 哈希拆成生成侧与运行侧两个（§4.2）。
- device 区判死而不覆盖；DECERR 空洞也归入 device（§4.3）。
- PMP 参数的 IR 重生成可推迟（§4.4）。
- 不把 v1 重定位方案留作退路（§5）。
- 失败契约选 A，不修 emu（§9.3）。
- E-cfg 的类数和形状数不设阈值（§10）。
- 工作量估计（§11）。
