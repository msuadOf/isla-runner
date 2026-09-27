# CSR 符号化审计表（W21）

日期：2026-09-28 ｜ worktree `feat/memory-consistency`（W21 未提交态）｜ 配置底座 `configs/riscv64_difftest_mem_excluded_pma.toml` + `..._csr_sym.toml`

原则（用户确认）：**所有 CSR 原则上都应符号化，只有无探索意义的 bitfield 可钉死**。本表按"符号化 / 部分钉死 / 保持钉死"三档给出建议，衡量维度：探索价值（能开多少真实语义分支）× 求解成本（分叉/求解时长）× 重放配套（isa-state 输出 + difftest 前导编程 + emu 对齐）。

机制背景（W21 已落地）：`[symbolic_registers]` 声明 solver 期符号注入（`pin_mask/pin_value` 位级钉死 + `nonzero_groups` 位组域约束）；注入不要求寄存器在 `reg_list`——任意 CSR 名（symtab 存在且形状为 `bits(w)`/单 bits 字段 struct，w≤64）都可挂；encdec/assembly 物化门按当前路径模型具象化评估（`concretize_symbolic_csrs`）。

## 1. 逐 CSR 审计

| CSR | 现状（defaults/机制） | 建议档位 | 理由（探索价值/求解成本/重放配套） |
|---|---|---|---|
| **mstatus** | W21 已改 `[symbolic_registers]`：钉 SD(63)/MBE(37)/SBE(36)=0 + FS[14:13]≠0 域 | **部分钉死（本轮落地）** | FS/VS/MPP/SPP/MPIE/MIE/SPIE/SIE/TVM/MXR/SUM/MPRV/TSR/TW/UXL/SXL 全符号：MPP 开特权迁移分支、MPRV 开 M 态翻译语义、VS 开 V 上下文（与 vtype 配对约束已有）。钉死位均为无探索价值：SD 只读镜像、MBE/SBE 大小端必须 LE。重放配套已具备：isa-state 输出 mstatus 模型值，pipeline 直接加载。 |
| **misa** | 钉 `0x800000000034112f`（MXL=RV64, AFCDIM…） | **保持钉死** | 探索价值：写 misa 关扩展（WARL）路径理论上存在，但本模型扩展开关 `hartSupports` 已 IR 生成期烘死，misa 位图与 hartSupports 不一致的状态是"配置矛盾"而非真实架构状态，符号化只产自相矛盾用例。求解成本：encdec 门 `misa[F]/[D]` 分支化直接威胁 FD 物化稳定性。重放：emu misa 固定。结论：等"扩展状态迁移"独立议题再评估。 |
| **satp** | 钉 `0x0`（bare，翻译路径全死） | **部分钉死（需页表预设配套）**——见 §2 两难 | 收益：开翻译分支（见两难）；成本：MODE 三路 fork + 符号 PPN 使首层 PTE 读地址符号化，vmem 翻译循环是已知热点（W19 VLX/VSX 超时同族）。最小步：钉 MODE=sv39 + PPN=预设页表基址，符号化 ASID 位与其它 WPRI 位，先验证"翻译访存"单条通路。 |
| **mcountinhibit** | 钉 `0` | **保持钉死** | 只影响 cycle/instret 计数行为；单指令 solve-state 内计数不可观察（无 tick 语义），符号化探索价值≈0。随性能计数议题（Zicntr/Smcntrpmf）再动。 |
| **mcyclecfg / minstretcfg** | 钉 `0` | **保持钉死** | 同上：LPTR 冻结位在单指令窗口不可观察。 |
| **mtimecmp / stimecmp** | 钉 `0` | **保持钉死（可后移符号化）** | timer 比较事件由 `plat_insns_per_tick`/mtime MMIO 驱动，solve-state 单指令不触发比较；符号化当前无分支可开。若未来做多指令序列/中断注入议题，再符号化。 |
| **pmpcfg_n / pmpaddr_n** | W14 钉 NAPOT-全1-RWX（恒放行） | **部分钉死（分阶段）**——见 §2 两难 | 真实 PMP 拒绝用例的唯一来源；但 16 entry × 符号 cfg/addr 的匹配循环是 W13 路径爆炸+图内假 fault 107/2479 的直接来源。分阶段方案见两难节。 |
| **mtvec / mepc / mcause / mscratch / stvec / …** | 不在 defaults、不在 reg_list：IR 模型 init 给具体值（≈0），pre-state 输出不可见 | **可选符号化（低优先）** | trap 目标 CSR：单指令场景 trap 只写不读（mtvec 影响取向需中断使能+trap 深入），pre-state 符号化探索价值低、成本低。若做"trap 后续行为"（mret 链）议题再挂。 |
| **cur_privilege**（let 型） | reg_list 符号化（已有） | **维持符号** | U/S/M 三态是访存权限/CSR 可达性的一等分支来源。 |
| **fcsr / vlenb / dcsr…** | 不在 defaults/reg_list，惰性 | **按议题挂** | fcsr（FRM/FFLAGS）影响 FP 舍入分支——FD 议题后续（浮点 rm 分布）可挂；当前 FD 四 clause 不读。 |

## 2. 两个两难

### 2.1 PMP 符号化 vs 求解爆炸（pmpcfg_n/pmpaddr_n）

- **符号化的收益**：真实"PMP 拒绝"用例。当前钉 NAPOT-全1-RWX 后 `pmpCheck` 恒 None（W14 决策），U/S 态访存永不被 PMP 拒绝——PMP 是 RISC-V 安全部件的一等语义分支，长期钉死等于该维度覆盖为 0。W13 全符号时代曾产出 PMP 拒绝路径，但 107/2479 为图内假 fault（模型 PMP 语义与 NEMU/emu 分歧 2 条已单列）。
- **符号化的成本**：`pmpControl` 循环结构性生效（IR `sys_pmp_count=16` 是 let 非 primop，config 关不掉）：64 个符号 pmpaddr + 16 个符号 pmpcfg，每 entry 的 A 位（4 值）、L、R/W/X、addr 区间比较（符号⊆比较）都分叉；W13 实测这是最大的单一路径爆炸源。
- **重放配套**：① isa-state 必须输出全部参与匹配的 pmpcfg/pmpaddr 模型值（当前机制天然支持：挂 `[symbolic_registers]` 即走 pre_state 输出，但 64+16 个键会让 isa-state 变长，可考虑只输出非零 entry）；② pipeline 前导须在 M 态先 `csrw pmpcfg*/pmpaddr*` 再降权执行测试指令（当前 pipeline 无 CSR 前导编程能力，需新增）；③ emu 侧 PMP 语义与模型的 2 条真分歧（W13）未上报修复前，PMP 拒绝用例重放必然失败一批。
- **建议路径**：分三阶段。阶段一：只符号化 **pmpcfg0 的低字节**（entry0 的 L/A/R/W/X）保持 addr0=全1——开"entry0 关闭/换模式/去权限"分支，成本约 2^8 域内；阶段二：符号化 pmpaddr0（钉 pmpaddr1..63=全1 兜底匹配），开"地址落在 entry0 界内/外"分支；阶段三：全符号独立泳道 + per-region fork limits（W19 预算工具已有）。

### 2.2 satp 符号化 vs 页表预设（satp）

- **符号化的收益**：开翻译分支。当前钉 0（bare）后 sv39/sv48 翻译路径全死——`vmem` 的两段翻译、PTE 权限位检查、MXR/SUM 影响、TLB 语义（模型无 TLB 但走查循环在）全部不可达；这与 FD 当年的处境同构（配置性不可达）。
- **符号化的成本**：satp MODE 字段符号即三路 fork（bare/sv39/sv48/sv57 非法）；PPN 符号使第一层页表读的**地址**符号化——数组内存模型上符号地址读 = 全数组内容 fork，叠加每层 512 项走查，W19 已证明该族（VLX/VSX 间接访存）吞吐掉 5-12 倍。裸符号化基本必然超时。
- **重放配套**：① **必须**配套页表内容预设——`page_table_config`（identity/offset/protected/symbolic 预设）在 testgen 侧有基建，但 solve-state 尚未接线；② isa-state 输出 satp 模型值之外，还要输出被触及 PTE 的物化内容（pre-memory 已有机制可承载）；③ pipeline 前导要按预设把页表写进 emu 物理内存，且 emu 页表遍历与模型逐位一致（W12 两遍 ELF 窗口机制可复用）；④ satp 符号化与 mstatus.MPRV 符号化（本轮已开）有耦合：MPRV=1 时 M 态也走翻译，分支相乘。
- **建议路径**：先"**钉模式与根、符号其余**"：`pin` MODE=bare 之外先做 MODE=sv39 + PPN=固定页表基址的最小通路（页表内容用 identity 预设，符号化 ASID 与 WPRI 位），验证一条"翻译后访存成功 + 翻译 fault"用例能端到端重放；再逐步放开 PPN（多组预设页表基址枚举）与 MODE。

## 3. 汇总计数

- **符号化（已落地）**：mstatus（部分钉死档：3 位钉死 + 1 组域约束）
- **部分钉死（建议，需配套）**：satp（需页表预设）、pmpcfg_n/pmpaddr_n（需 pipeline CSR 前导 + 分阶段）
- **保持钉死（本轮建议）**：misa、mcountinhibit、mcyclecfg、minstretcfg、mtimecmp、stimecmp（共 6 个，共同点：单指令窗口不可观察或与 IR 固化状态矛盾）
- **维持现状机制（reg_list/惰性）**：cur_privilege（符号）、fcsr 等按议题挂

## 4. 与本轮验收的关系

FD 四 clause（C_FLD/C_FSD/C_FLDSP/C_FSDSP）恢复即 mstatus 行的第一行验证：G8 判定的"②配置性不可达（物化守卫）"解除，gen 从 0 恢复到日志已执行分布；satp/PMP 两难按 §2 路径另行立项。
