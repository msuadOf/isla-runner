# 配置对齐事实调查（只读，2026-11-07）

来源：新开的只读 Codex 事实调查；其中“建议草案”和“最小验收”为 Codex 的建议，**未经设计采纳**，设计由 design.md 负责。

**【已核实】这条路可行：Isla 已支持用 TOML 替换 PMA 地图，地址范围调整不必重生成 IR。**但“全部样本直接可重放”仍**【未验证】**：设备行为、NAPOT、非叶 PTE 检查及异常优先级，不能全部靠现有配置对齐。

以下路径简写：`X`＝主仓 `difftest-xiangshan/xiangshan/`；`I`＝主仓 `isla/.worktrees/memory-consistency/`；`S`＝主仓 `sail-riscv/model/`；`E`＝`.worktree/mmu-symbolic-experiment/`。区间均左闭右开。

**【已核实】现有 emu 是 MinimalConfig。**本次读取的 emu、NEMU SO 哈希分别为 `87141692…`、`9188e7dd…`，与[构建账本:88](/data1/baiyifan/workplace/isla-runner/difftest-xiangshan/work/float-v3-20260929/current-workspace-audit.json:88)一致；源码版本记为 `a13efc87`。

| 状态 | XiangShan 物理区间（十六进制） | PMA：R/W/X/原子/缓存 |
|---|---|---|
| 已核实 | `[0,10000000)` | RW--- |
| 已核实 | `[10000000,20000000)`，Flash | RWX-- |
| 已核实 | `[20000000,38020000)` | RW--- |
| 已核实 | `[38020000,38021000)`，Debug | RWX--，仅 debug 模式允许 |
| 已核实 | `[38021000,39002000)` | RW--- |
| 已核实 | `[39002000,3a000000)` | ----- |
| 已核实 | `[3a000000,80000000)` | RW--- |
| 已核实 | `[80000000,80000000000)`，DRAM | RWXAA |
| 已核实 | `[80000000000,1000000000000)` | ----- |

【已核实】依据是实际初始化表，而非 `PMA.scala` 中的注释地图：[SoC.scala:57](/data1/baiyifan/workplace/isla-runner/difftest-xiangshan/xiangshan/src/main/scala/system/SoC.scala:57)、`X/src/main/scala/xiangshan/backend/fu/PMA.scala:182,214,237`。DRAM 容量为 **8190 GiB**，顶界为 **2^43**；总线地址宽度是 **48 位**，两者不能混同（`X/src/main/scala/xiangshan/Parameters.scala:623`）。

【已核实】低端 PMA 允许不等于接有设备。实际窗口包括 Flash、UART16550 `[310b0000,310b0080)`、TIMER `[38000000,38010000)`、BEU `[38010000,38011000)`、Debug、MMPMA `[38021000,38022000)`、SYSCNT `[38040000,38050000)`、APLIC `[31100000,31140000)`、PLL `[3a000000,3a001000)`、PLIC `[3c000000,40000000)`；仿真另有 SD、DMA、IntrGen、APB、UARTLite。其余低端地址按集合补集接错误响应，不能统称设备。完整划分入口：`X/src/main/scala/system/SoC.scala:75,240,255`、`X/src/test/scala/top/SimMMIO.scala:62–96`；错误响应为 DECERR，见 `X/utility/src/main/scala/utility/AXI4Utils/AXI4Error.scala:59,83`。**【未验证】**IMSIC 在当前仿真中的可用性；其端口被置零，见 `X/src/test/scala/top/SimTop.scala:99`。

| 状态 | 边界与保护行为 | 依据 |
|---|---|---|
| 已核实 | 翻译后 PPN 超出48位报访问异常；裸地址高位非零也检查访问异常，非简单截断 | `X/…/cache/mmu/MMUBundle.scala:849`；`TLB.scala:223,246` |
| 已核实 | PMP：32条实际实现、4 KiB 粒度；复位 OFF、未锁定、权限零。无匹配时 M 允许、S/U 拒绝 | `X/…/PMParameters.scala:30`；`backend/fu/NewCSR/CSRPMP.scala:82`；`backend/fu/PMP.scala:425` |

**【已核实】NEMU 并非没有 PMP/PMA 检查。**未找到配套源码；`bump-nemu.sh:8–12` 只指向外部 `$NEMU_HOME`。静态反汇编确认 SO 的 `check_paddr@0x778e0` 调用两种检查，读写入口均调用它；默认 `MEMORY_SIZE@0x12b1c8=0x7ff80000000`，RAM 基址为 `0x80000000`，默认范围与上述 DRAM 相同。二进制无源码行号，故这里给符号地址。

**【未验证】**NEMU 对全部设备、空洞、≥2^48 地址的最终行为，尤其异常优先级、动态忽略非法访问选项；不能据符号存在就断言完全一致。RAM 大小还可被运行参数覆盖，见 `X/difftest/src/test/csrc/emu/emu.cpp:171`、`difftest/refproxy.cpp:79`。

**【已核实】Isla 要分开配置“访问属性”和“内容”。**

| 层 | 字段及语义 | 依据 |
|---|---|---|
| 已核实：属性 | `pma_regions`：`base/size`；`attr=ram/rom/mmio/hole`，可覆盖 `readable/writable/executable/cacheable/coherent`、幂等性、`reservability`、`misaligned` 等 | `I/isla-lib/src/config.rs:195,844` |
| 已核实：内容 | `memory_regions.region_type=symbolic/concrete/excluded`；symbolic **不限制地址**；excluded 丢弃触及路径，不产生硬件异常 | `I/src/isarch/memory_model.rs:8` |
| 已核实：名称 | `ram`、`experiment_low_ram` 是区域名字；当前后者确实把低端声明为 RAM | `E/symbolic/config.toml:227,233` |

**【未验证：建议草案】**先采用 DRAM 范围的 LOAD/STORE 重放配置；删除原 code、low_ram、experiment_low_ram 及其他重叠声明，保留其余必要配置：

```toml
clint_enabled = false

[[pma_regions]]
name = "ram"
base = "0x80000000"
size = "0x7ff80000000"
attr = "ram"

[[memory_regions]]
name = "harness"
base = "0x80000000"
size = "0x100000"
region_type = "excluded"

[[memory_regions]]
name = "ram"
base = "0x80100000"
size = "0x7ff7ff00000"
region_type = "symbolic"
```

【已核实】该草案保留图外访问异常，禁止实际读写 harness 保留区；无需把保留区从 PMA DRAM 中挖掉。运行时注入入口为 `I/src/isarch/target.rs:1180–1202`。

【已核实】完整地图可将上表 RW 区映射为 `attr="mmio"`、RWX 区再设 `executable=true`、禁访区用 `hole`。但**设备副作用、Debug 条件、总线空洞、独立 AMO 权限无法完整表达**；Sail 当前 AMO 仅检查读写权限，见 `S/sys/mem.sail:104`。因此完整 MMIO 不能直接承诺可重放。

| 状态／项目 | 当前 Sail／IR → XiangShan；如何对齐 |
|---|---|
| 已核实：Svrsw60t59b | 当前 `extensions.Svrsw60t59b.supported=true`；XS将 `[60:54]` 当保留位。改 JSON 为 false，**重生成 IR**。依据 `E/ir-provenance-rv64d.json:450`；`X/…/MMUConst.scala:160`、`MMUBundle.scala:807` |
| 已核实：A/D | `memory.translation.dirty_update=false`，与 XS Svade 一致；ADUE只读0，A/D不足报PF。无需改。`I/rv64d.ir:10754`；`X/…/NewCSR/CSRBundles.scala:71`、`TLB.scala:462` |
| 已核实：非对齐 | JSON及IR实际为支持，TOML旧 `plat_enable_misaligned_access=false` 未改变此常量；XS硬件LOAD/STORE支持。修改相关JSON需重生成IR；异常优先级仍未验证。`I/rv64d.ir:10760`；`X/…/Parameters.scala:196` |
| 已核实：Svnapot | Sail写死false；XS支持64 KiB NAPOT。**无配置开关可补齐**，须改模型并重生成，或拒绝相关样本。`S/sys/vmem_pte.sail:75`；`X/…/MMUBundle.scala:815` |
| 已核实：Svpbmt | Sail写死false；XS支持，PBMTE复位0且可写。固定 `menvcfg.PBMTE=0` 可缩小到共同范围；完整支持须改模型。`S/sys/vmem_pte.sail:76`；`X/…/NewCSR/MachineLevel.scala:768` |
| 已核实：保留位 | `[58:54]`均拒绝；Sail未拒绝非叶U/A/D，XS拒绝。后者无配置键，须修模型或拒绝。`S/sys/vmem.sail:123`；`X/…/MMUBundle.scala:812` |
| 已核实：PMP | 当前count/usable=16、grain=0；对齐用 `count=64,usable_count=32,grain=10,na4_supported=false`，**重生成IR**。重放继续显式开放NAPOT-RWX，不能把复位OFF当全开。`S/pmp/pmp_regs.sail:11`；`E/ir-provenance-rv64d.json:73` |
| 已核实：MPRV/SUM/MXR | 是CSR状态，不是功能开关；普通非虚拟化场景按MPP、SUM、MXR工作，重放恢复对应位即可。默认mstatus=`0x600`，三位均0。`S/sys/sys_control.sail:11`、`vmem_pte.sail:134,150`；`X/…/NewCSR/NewCSR.scala:1550`、`TLB.scala:465` |

【已核实】重生成是 Sail→IR 编译，已有同类记录约 **501秒/份**，不是本次耗时保证（`I/ir/provenance/manifest.json:543`）；需记录版本、配置、哈希，并核对 workaround 坐标，见 [ir-workflow.md:5](/data1/baiyifan/workplace/isla-runner/.worktree/replay-p0/specs/ir-workflow.md:5)。

**【未验证：最小验收】**先锁定运行器哈希——现存 isarch 已与实验 manifest 不同——只改上述配置跑一次 Sv39 LOAD 合并，检查成功数据访问及实际页表读取全部位于 DRAM、避开保留区；异常路径允许目标在图外。随后各取一例验证顶界、≥2^48、A/D、保留位、非叶U/A/D及NAPOT，再扩展STORE/Sv48。

【已核实】剩余需拒绝或修模型的还有高PPN检查时机及多错误优先级：XS在PTE阶段检查高PPN，Sail可能先判权限（`MMUBundle.scala:851`；`S/sys/vmem.sail:146`）。页异常也不能仅靠DiffTest签收：框架会引导NEMU跟随DUT抛页异常，必须保留ELF期望值自检（`X/difftest/src/test/csrc/difftest/checkers/traps.cpp:83–98`）。
