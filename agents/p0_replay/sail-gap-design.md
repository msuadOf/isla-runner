# Sail 补齐缺失的标准页表行为：Svnapot、Svpbmt、非叶保留位

状态：设计稿（2026-11-07），未实施、未运行。用户已定原则：Sail 里**尚未实现的标准行为**按 RISC-V 规范补上；已实现的标准行为不改；规范允许的宽松处理不屏蔽，交给后续 mismatch 过滤。

标注约定沿用 [design-gaps-and-fuzzing.md](design-gaps-and-fuzzing.md)：【已核实】有代码、文档或运行证据；【待查】未确认；未标注的是设计判断。Sail 行号以根目录 `sail-riscv/`（提交 4f2ac293）为准。规范引用来自本机 riscv-isa-manual-cn 检出（提交 cc306428，英文原文与中文译文并列），下文简称“手册”。

## 结论先行

1. **三项都属于“缺失的标准行为”，都要补，都是同一种故障：页故障（PF）。** 规范第 3 步规定：PTE 中出现任何“保留给未来标准使用”的位或编码，就报 PF。非叶 PTE 的 U/A/D、N、PBMT 都在这个范围里。置信度高：有手册原文，Spike 和 XiangShan 也都这样实现。
2. **design-gaps-and-fuzzing.md 的 R4、R7、R8 作废**，原因各不相同。R4 和 R8 是被用户的决策推翻的；R7 的问题在于原文对规范的解读本身就错了（见 §0）。
3. **上游三项都已经实现，但都不在本仓库 HEAD 的祖先链上**【已核实：截至 upstream/master 0b4eaa56】。三项分别是：Svnapot 6cc81f28、Svpbmt cb8e870e，以及非叶保留位 9c3fd5b8。9c3fd5b8 用 `pte_reserved_bits_must_be_zero = priv_isa_version >= 1.12` 控制，这正好说明规范从 1.12 起才要求这项检查。本仓库 HEAD 与上游的分叉点是 efdfe9b7（2026-03-01），中间还隔着 H 扩展等大改动，没有 `isa_version.sail`。推荐**以 upstream/master 0b4eaa56 的 `pte_is_invalid` 为语义参照手工移植**，不直接 cherry-pick。Svpbmt 只移植合法性部分，因为上游把 pbmt 一路传进访存 API，改动 20 个文件，而这些内存属性在模型里观察不到。
4. **改动集中在 `vmem_pte.sail` 第 3 步的合法性判断上**，`vmem.sail` 只多一处 NAPOT 的 PPN 替换。TLB 和故障类型映射都不改。所有新增检查得出的 cause 和 tval 都与现有的无效 PTE 页故障相同，所以不会产生新的“跨 cause 优先级”问题。
5. **Isla 侧的影响估计：** 非叶检查和 PBMT（PBMTE=0 的场景）几乎不增加类；NAPOT 是唯一需要实测的膨胀源。替换要写成无分支的形式，避免整棵 PMA/PMP 子树被复制。三项改动都要求重新生成 IR（约 110–500 秒/份，见 [ir-workflow](../../specs/ir-workflow.md)），不需要新的 Isla 配置项。

## 0. 对 design-gaps-and-fuzzing.md 的修订

原文保留，不删改。下表说明原结论适用的范围、为什么修订、现在以哪里为准。

| 原条目 | 原结论 | 修订 | 依据 |
| --- | --- | --- | --- |
| A.1、R4、C.2 | NAPOT 在 P0–P4 拒绝，变异时屏蔽；到 P5 再评估补 Sail | **作废**：现在就在 Sail 里补 Svnapot。R4 原因码和对应屏蔽一并撤销 | 用户决策（2026-11-07） |
| A.2 “规范只要求软件清零，没有规定硬件必须报异常” | 双方的做法都合规 | **事实有误**：手册第 3 步把“保留位被置位”列为必须报 PF 的情形（§1 第 1、2 行）。XiangShan 合规，Sail 缺这项检查 | 手册原文、Spike `mmu.cc` |
| A.2、R7、C.3 | 永久拒绝并屏蔽，不改 Sail | **作废**：在 Sail 里补上非叶 U/A/D 检查，并按同一条规则补上非叶 N 和 PBMT 检查 | 用户决策 + 上一行 |
| A.3、R8 | 对 cause 不同、规范又未定序的情形，用拒绝来处理 | **作废**：不拒绝、不屏蔽，样本保留，失配交给后续过滤。规则表仍然保留，用来给失配归类 | 用户决策 |
| A.4 小结表；B.3“必带屏蔽”列中的 NAPOT 编码、指针 U/A/D；B.8 中 P0、P1、P5 验收条件里的 R4/R7 计数 | 依赖 R4/R7 | **随 R4/R7 一并失效**，现行入口是本文 §0 | 同上 |
| config-alignment 的 Svpbmt 行 | 把 `menvcfg.PBMTE` 固定为 0，把差异缩小到双方共同支持的范围 | **改为补模型**。PBMTE=0 降为 P0 场景的前态选择（§6 决策 2），不再作为对齐手段 | 用户决策 |

## 1. 规范依据（手册 cc306428）

| # | 条款（按章节标题，章节号【待查】） | 原文要点 | 结论 | 置信度 |
| --- | --- | --- | --- | --- |
| 1 | Sv32 → Addressing and Memory Protection（`supervisor.adoc:2508`） | “For non-leaf PTEs, the D, A, and U bits are reserved for future standard use … must be cleared by software” | 非叶 PTE 的 U/A/D 属于保留位 | 高 |
| 2 | Virtual Address Translation Process 第 3 步（`supervisor.adoc:2546`） | “… or if any bits or encodings that are reserved for future standard use are set within pte, stop and raise a page-fault exception” | 第 1 行加上本条，就是“必须报 PF”。第 1 行本身没写 “or else PF”，强制性来自本条的通用规则 | 高 |
| 3 | `svpbmt.adoc:72` | 非叶 PTE 的第 62–61 位保留，“or else a page-fault exception is raised” | 非叶 PBMT≠0 要报 PF（PBMTE=1 时也一样） | 高 |
| 4 | `svpbmt.adoc:79-82` | 叶 PTE 的 PBMT=3 是保留值，“raises a page-fault exception” | 叶 PBMT=3 要报 PF | 高 |
| 5 | `machine.adoc:2787-2792` | PBMTE=0 时，实现的行为如同没有实现 Svpbmt；没有实现 Svpbmt 时，PBMTE 只读为 0 | PBMTE=0 时 PBMT≠0 报 PF（Sv39 PTE 格式说明 `supervisor.adoc:~2800`） | 高 |
| 6 | Svnapot 编码表 `ptenapot`，以及 `svnapot.adoc:92-96` | 只有 i=0 且 ppn[0][3:0]=1000 合法，表示 64 KiB；i=0 的其他取值和全部 i≥1 都是保留编码，“must be raised” PF；合法时，隐式读取返回的 PTE 副本中，ppn 的低 napot_bits 位被替换成 vpn[i] 的对应位 | 要求和 XiangShan 完全一致。非叶 PTE 只可能出现在 i≥1，N=1 时落在保留编码里，报 PF | 高 |
| 7 | `svnapot.adoc:110-117` | 地址翻译缓存可以给满足条件的“任意或全部 j”建立条目 | 只按精确 VPN 缓存也合规 | 高 |
| 8 | `svpbmt.adoc:~50-56` | “Implementations may override additional PMAs”，例如 PBMT=IO 时，非对齐访问**可能**报异常 | 属于规范允许的宽松处理，不建模（§2.3） | 高 |
| 9 | 第 9 步的 A/D 写回，配合 NAPOT 返回的 PTE 副本 | 第 9 步拿 pte 去和内存中的值比较；如果比较的是替换过 ppn 的副本，比较不会成功 | 规范原意应当是用原值比较【待查】。当前 `dirty_update=false`（Svade），走不到这一步，不影响本轮 | 中 |

旁证【已核实】：
- Spike（本机检出 88fc84de）`riscv/mmu.cc:440` 对非叶 PTE 执行 `if (pte & (PTE_D | PTE_A | PTE_U | PTE_N | PTE_PBMT)) break;`，即报故障。
- XiangShan `MMUBundle.scala:811` 的 `isNext()` 分支也对 U/A/D/N/PBMT 报 PF。
- 上游 sail-riscv 9c3fd5b8 在特权规范 1.12 及以上版本中，把非叶 PTE 的 A/D/U 和全部 ext 位都判为无效。本仓库 `vmem_pte.sail:85-87` 的注释也说明，这项检查依赖规范版本。

## 2. Sail 最小改动方案

### 2.1 检查的位置与顺序

规范顺序是：第 2 步读 PTE，访问失败报访问异常（AF）；第 3 步检查保留位或保留编码，命中报 PF；第 4 步区分指针还是叶；第 5 步检查超级页对齐；第 6–8 步检查 U、R/W/X 权限；第 9 步检查 A/D。三项新检查**全部归在第 3 步**：

- 新增 `private function pte_has_reserved_encoding(pte_flags, pte_ext, ppn, level) -> bool`，放在 `vmem_pte.sail` 中 `pte_is_invalid` 的后面。
- `pt_walk`（`vmem.sail:114`）的判断改成 `if pte_is_invalid(...) | pte_has_reserved_encoding(...)`，复用同一个 `PTW_Invalid_PTE` 分支和同一个回调，不另开故障分支。`let ppn = PPN_of_PTE(pte)` 要提到这个判断之前。
- 和现有优先级的关系：新检查排在“本级 PTE 读取 AF”之后、“读下一级 PTE”之前。例：L2 指针 U=1，并且它指向的下一级页表地址不可访问。旧 Sail 会继续遍历，最后报 AF 5；新 Sail 报 PF 13，与 XiangShan 一致。新检查与超级页对齐、U、RWX、A/D 这些检查同属 PF，cause 和 tval 都相同，先后顺序观察不到。
- 写法：每个条件尽量写成一次位掩码比较，例如非叶时判 `(pte[63..61] @ D @ A @ U) != zeros()`，少用 `|` 链。这样 Isla 里新增的守卫最少。Sail 的 `|` 在 Isla 中是否会降低成多个分叉【待查】。

函数语义（Sv32 上 ext 位恒为 0，N 和 PBMT 两项自然不成立；U/A/D 一项对 Sv32 同样适用）：

```text
非叶（V=1 且 R=W=X=0）: U|A|D != 0  或  N != 0  或  PBMT != 0
叶:                     PBMT == 0b11（仅当 Svpbmt 已启用且 PBMTE=1 时可达）
                        或  N == 1 且 not(level == 0 且 ppn[3:0] == 0b1000)
```

扩展关闭（或 PBMTE=0）时，N≠0、PBMT≠0 已经被 `pte_is_invalid`（`vmem_pte.sail:88-89`）判为无效，上面对应的项不会被走到，所以行为不变。

### 2.2 非叶 U/A/D（同时补非叶 N 和 PBMT）

- 只改 `vmem_pte.sail` 的新函数和 `vmem.sail` 的一处调用，不加配置项（决策 1）。
- 不改 `pte_is_non_leaf`，也不改 `pte_is_invalid` 中已有的各项。G 位不是非叶 PTE 的保留位，不检查。
- 与上游 9c3fd5b8 的差别：上游对非叶检查的是“全部 ext 位≠0”，范围包括 RSW[60:59]。本文只检查 N 和 PBMT。原因是 E-cfg-b 会把 `Svrsw60t59b` 设为 false，到那时 [60:59] 在各级 PTE 上都已经判为无效；在支持 Svrsw60t59b 的配置下，非叶 PTE 的 [60:59] 应当怎样处理【待查】。

### 2.3 Svpbmt：范围限定为“PTE 合法性 + menvcfg.PBMTE”

| 文件 | 改动 | 依据或对齐 |
| --- | --- | --- |
| `model/core/extensions.sail:478` | `hartSupports(Ext_Svpbmt) = config extensions.Svpbmt.supported : bool & (xlen == 64)` | 同上游 |
| 同文件 `currentlyEnabled_measure` | 增加 `Ext_Svpbmt => 3, // > Sv39` | 终止性度量要求被依赖项的值更小 |
| `model/sys/vmem_pte.sail:76` | `currentlyEnabled(Ext_Svpbmt) = hartSupports(Ext_Svpbmt) & currentlyEnabled(Ext_Sv39)` | 同上游 |
| `vmem_pte.sail:89` | 改成 `pte_ext[PBMT] != zeros() & (not(currentlyEnabled(Ext_Svpbmt)) \| menvcfg[PBMTE] == 0b0)` | 手册 §1 第 5 行 |
| `model/core/sys_regs.sail:394` `legalize_menvcfg` | 增加 `PBMTE = if currentlyEnabled(Ext_Svpbmt) then v[PBMTE] else 0b0`。复位仍是 `legalize(zeros)`，值为 0 | XiangShan `MachineLevel.scala:768` 复位 0、可写 |
| `model/postlude/validate_config.sail` | Svpbmt 在 RV32 上或缺 Sv39 时判配置非法 | 同上游 |
| `config/config.json.in` 及 IR 生成实际使用的配置 | 增加 `"Svpbmt": {"supported": @CONFIG_XLEN_IS_64@}` | 与 XiangShan 对齐（RV64 下为 true） |

**不建模 PBMT 对内存属性的影响**（决策 2）。理由有三条。第一，`pma.sail:68-69` 注释写明 cacheable/coherent 在模型中没有效果，idempotent 和 ordering 在单核顺序模型里也观察不到。第二，PBMT 可能带来的可观察差异，比如 PBMT=IO 时非对齐访问或 AMO 报 AF，规范写的是“may”，属于宽松处理，按用户原则交给 mismatch 过滤。第三，上游的完整实现会改 `mem_read_priv`/`mem_write_value_priv` 的签名，牵动 zaamo、zicbo、fetch 等 20 个文件，IR 改动面大，却换不来可观察行为。XiangShan 对 NC/IO 页上非对齐访问和 AMO 的实际行为【待查】，留待 mismatch 出现后再归类。

编译风险【待查】：`vmem_pte.sail` 能否引用 `menvcfg`（模块依赖）；`legalize_menvcfg` 在寄存器初始化时调用 `currentlyEnabled(Ext_Svpbmt)`，这个函数的分散子句在后面的文件里才定义，初始化顺序是否有问题。上游这两种用法都有，但本仓库的基线较旧。如果编译不过，`legalize_menvcfg` 退回用 `hartSupports(Ext_Svpbmt) & hartSupports(Ext_Sv39)`。

### 2.4 Svnapot

| 文件 | 改动 |
| --- | --- |
| `extensions.sail:474` | `hartSupports(Ext_Svnapot) = config extensions.Svnapot.supported : bool & (xlen == 64)`；`currentlyEnabled_measure` 增加 `Ext_Svnapot => 3` |
| `vmem_pte.sail:75` | `currentlyEnabled(Ext_Svnapot) = hartSupports(Ext_Svnapot) & currentlyEnabled(Ext_Sv39)` |
| `vmem_pte.sail` 新函数 | 合法性检查放在第 3 步（§2.1）。上游把它放在权限检查之后，两者 cause 相同，观察不出差别；本文放在第 3 步，因为这是规范规定的位置 |
| `vmem.sail:152-159` 叶成功分支 | upstream/master 仍用 `if` 判断并替换（`vmem.sail:249-255`），本文不照搬。level==0 时**无分支替换**：`m = replicate_bits(pte_ext[N], 4)`，`ppn' = [ppn with 3..0 = (ppn[3..0] & ~m) \| (vpn[3..0] & m)]`。走到这里时 N=1 已经等价于“合法 NAPOT”，不需要再判断。level>0 的分支不动（N=1 已在第 3 步被拒绝） |
| `PTW_Output` 和 A/D 写回 | `pte` 字段保留内存里的原值，只有输出的 `ppn` 是替换后的值。这样 `update_PTE_Bits` 写回的 PTE 不会带上替换过的 PPN（§1 第 9 行） |
| `validate_config.sail`、`config.json.in` 及 IR 实际使用的配置 | 同 Svpbmt，`"Svnapot": {"supported": @CONFIG_XLEN_IS_64@}` |

**TLB 不改。** NAPOT 叶在 level 0 上，`add_to_TLB`（`vmem_tlb.sail:141`）算出的 levelMask 是 0，存进去的是替换后的 ppn，所以是按精确 VPN 缓存，命中时 `tlb_get_ppn` 返回正确的 PA。规范允许这样做（§1 第 7 行）。

- 被排除的方案：把 levelMask 设成 0xF、缓存整个 64 KiB。行为上同样合规，但要给 `add_to_TLB` 加参数。TLB 不是架构状态，这样改只能让过期条目的表现更接近 XiangShan，而规范对这一点两种做法都允许。
- 对 Isla 的影响：Isla 中 TLB 的初值全为 None，单次访存的场景不会走到命中路径（设计判断）。

**PA 的生成**：例如 L0 叶 PPN=0x80308、VA=0x20005008（vpn[0]=5），得到 PA=0x80305008。随后对最终 PA 做 PMP/PMA 检查，这部分逻辑不变。

### 2.5 明确不改的部分

`check_PTE_permission`、`update_PTE_Bits`、`translationException`、`pmaCheck`/PMA 结构、`senvcfg`（不含 PBMTE，这是规范规定）、超级页对齐检查、`pte_is_invalid` 中已有的 V、W&!R、RSW、reserved 各项。

## 3. 对 Isla 符号执行的影响预判

前提：P0 场景中 `menvcfg` 在 `config-xs.toml` 里没有出现，应当是复位值 0【待查：以场景初态的实际值为准】；VA（x1）固定；遍历的层级是具体值。

| 改动 | 新增守卫 | 类数变化（设计判断） | 风险 |
| --- | --- | --- | --- |
| 非叶 U/A/D/N/PBMT | 每个走到的指针层级加一个，Sv39 最多 2 个，Sv48 最多 3 个 | 每层多出约 1 个 PF 类（如果析取被拆成多个分叉，最多约 5 个）。原有类里这些位是自由的，而规范最小见证本来就取 0，所以原有类都保留 | 低。Sv48 LOAD 最多增加约 15 类，相对 6918 可以忽略 |
| Svpbmt，PBMTE=0 | 语义上没有新守卫：新函数里的 PBMT 两项不可达 | **应当不变**，作为回归门 | 低。如果类数变了，说明降低或求解有问题，先查 |
| Svpbmt，PBMTE=1（将来的维度格点） | 叶 PBMT 从“≠0 报 PF”变成“=3 报 PF”；非叶 PBMT≠0 报 PF | 每个叶层级大约 ±1 | 低 |
| Svnapot | L0 叶上加 N 与 ppn[3:0] 的守卫；PA 的 [15:12] 位变成依赖 N 的掩码表达式 | 原来 N=1 一律 PF；现在合法 NAPOT 会进入完整的叶检查。无分支写法下，后面的子树是共用的，只在 PMP/PMA 边界检查与 PA[15:12] 有关时才分裂【待查】。如果用上游的 `if` 写法，L0 叶成功部分的子树最坏会翻倍 | **中，需要实测**。Sv48 LOAD 在 predict 模式下已经要 783 秒（F16） |

- 不需要新的 Isla 配置项。需要的步骤是重新生成 IR，并在 provenance 中记录 commit、配置和哈希。
- workaround 坐标【已核实】：79 份 workaround 只锚定 vext、zv* 和 `prelude.sail`，没有 vmem、sys_regs、extensions、validate_config，所以坐标不受影响。IR 哈希变化只会告警（`strict=false`）。
- 种子作废：IR 一变，现有 14036 条种子和全部 lock 都失效（design §13），要重新生成。所以 IR 重生成最好和 E-cfg-b 同批做（决策 3）。

## 4. TDD 验证方案

### 4.1 Sail 层最小测试（先写失败的测试，再写实现）

放在 `sail-riscv/test/first_party/src/`，参考已有的 `.S` 和 `test_pmp_access.c` 的写法：M 态建好 Sv39 页表，`mret` 进入 S 态访存，在 trap 处理程序里检查 mcause 和 mtval，成功的情况检查读到的标记值。下面的地址沿用 design-gaps A.1：VA=0x20000000，根表 0x80200000，L2 指针 `0x0000000020080401`，L1 指针 `0x0000000020080801`。如果测试的链接地址不同，可以平移 PPN，但低 4 位和标志位保持不变。

| ID | 配置 / 前态 | 关键 PTE | 访问 | 期望 |
| --- | --- | --- | --- | --- |
| U1 | 默认 | L2 = `0x0000000020080441`（A=1）；再分别测 `…0411`（U=1）、`…0481`（D=1） | LOAD 0x20000000 | mcause 13，mtval=VA（旧 Sail 会成功） |
| U2 | 默认 | L2 = `…0441`，PPN 指向 PMA 空洞 | 同上 | 13，不是 5（优先级） |
| U3 | 默认 | L2 = `0x0000000020080421`（G=1） | 同上 | 成功（G 不是保留位，对照） |
| P1 | Svpbmt=true / false | 写 `menvcfg` 的 bit 62 后读回 | csrrs | 读回 1 / 0 |
| P2 | PBMTE=0 | L0 = `0x20000000200c00c7`（PBMT=01） | LOAD | 13 |
| P3 | PBMTE=1 | 同 P2；再测 `0x40000000200c00c7`（PBMT=10） | LOAD | 成功 |
| P4 | PBMTE=1 | L0 = `0x60000000200c00c7`（PBMT=11） | LOAD | 13 |
| P5 | PBMTE=1 | L1 指针 = `0x2000000020080801`（PBMT=01） | LOAD | 13 |
| N1 | Svnapot=true | L0 = `0x80000000200c20c7`（N=1，PPN=0x80308，ppn[3:0]=1000） | LOAD 0x20000000 | 成功，PA=0x80300000 |
| N2 | 同上 | 同上，紧接 N1 再访问 | 先 LOAD 0x20005008，再 LOAD 0x20000000 | 第一次 PA=0x80305008，验证 VPN 替换（TLB 索引与 N1 不同，会重新遍历）；第二次 PA=0x80300000，走 TLB 命中路径 |
| N3 | 同上 | L0 = `0x80000000200c24c7`（ppn[3:0]=1001） | LOAD | 13 |
| N4 | 同上 | L0 = `0x80000000200c00c7`（ppn[3:0]=0000） | LOAD | 13 |
| N5 | 同上 | L1 叶 = `0x80000000201000c7`（N=1 的 2 MiB 叶） | LOAD | 13 |
| N6 | 同上 | L2 指针 = `0x8000000020080401`（N=1） | LOAD | 13 |
| N7 | Svnapot=false | 同 N1 | LOAD | 13（开关关闭时行为不变） |

另外 STORE 至少覆盖 N1 和 U1，期望的 cause 是 15。

### 4.2 回归门

1. Sail 自带的测试全部通过，first_party 原有用例不退化。
2. 两个配置都设为 false 时，与旧模型相比，唯一的行为差异只能是 U1/U2/N6 这类非叶检查。用 4.1 全表在旧、新两个模拟器上对照，确认这一点。
3. 每生成一次 IR，记录 Sv39 LOAD（约 25 秒，T64）的路径数、类数和形状数。只改 PBMT（PBMTE=0）时，类数必须与上一份 IR 相同。这道门有一个前提：场景初态中 `menvcfg` 是具体值 0（S0 核对）。

### 4.3 改完以后接 E3/E4

- 现状【已核实】：E3/E4 被设备 PMA 签收和生成侧 lock 卡住（[E1–E4 结果](e1-e4-results.md)），不能拿它们作本轮的验收前提。
- 过渡验证：把 4.1 中 U1、N1、N3、P2 这几个前态手工写成 Isla 样本，在新 IR 上跑 `--check-samples`。要求恰好一条路径接纳，并且 result 与 Sail 测试一致（PF 13 或读到的值）。这一步的作用是证明新 IR 确实带上了新行为。
- 前置解除后：四个场景在同一个 lock 下重新生成代表。E3 要求每个形状的代表 100% 恰好被一条路径接纳。E4 的口径不变，另外要求：NAPOT 形状和“非叶保留位 PF”形状的代表都落在 agree 桶；原来的 R4/R7 计数项删除，不再统计。
- 风险【待查】：NEMU 是否支持 Svnapot、Svpbmt 和非叶检查。如果不支持，C1 会 ABORT，这会被误当成发现。所以 E4 之前，先按 E0 的方法为 N1、U1、P3 各跑一个定向用例，观察 NEMU 的行为。

## 5. 实施顺序与给 Codex 的指令要点

顺序：非叶检查 → Svpbmt → Svnapot。从风险最小、没有配置项的开始，每一步单独提交、单独测试、单独生成 IR，便于把类数变化归到具体改动上。

1. **S0 只读核对**（不改文件）：对照上游 6cc81f28 和 cb8e870e 的 diff；确认 §2.3 的两个编译风险点；列出生成 IR 时实际读取的配置 JSON。根目录 `isla/ir/provenance/rv64d*.json` 是记录文件，真正的输入以 [ir-workflow](../../specs/ir-workflow.md) 为准【待查】。另外确认 Isla 场景初态下 `menvcfg` 是具体值，不是符号。
2. **S1 非叶检查**：先写 U1–U3，确认 U1、U2 失败；然后加 `pte_has_reserved_encoding` 的非叶部分和 `pt_walk` 的调用；测试通过；跑 4.2 的回归门 2。
3. **S2 Svpbmt**：先写 P1–P5，然后改 §2.3 表中的各处。
4. **S3 Svnapot**：先写 N1–N7，然后改 §2.4 表中的各处。替换必须用无分支写法，不能用 `if`。
5. **S4 IR**：前两份 IR（S1、S2 之后）只用来测 Sv39 LOAD 的类数；最后一份（S3 之后）与 E-cfg-b 的配置变更（`Svrsw60t59b=false`、PMP 对齐）合并，作为正式 lock 的候选，再测 Sv48 LOAD 的耗时和类数。
6. **S5**：4.3 的过渡验证。E3/E4 等前置解除后再做。

指令要点：
- 在 `.worktree/` 的独立工作树里工作，按 [GIT.md](../../GIT.md) 在 sail-riscv 子模块内提交。
- 每个函数只按本文写的语义实现，不要自行扩大范围。
- 每一步都要报告：失败测试 → 通过测试的命令和结果；类数对照表；遇到的编译风险点。
- 单次测试或生成如果超过预期的两倍（Sv39 超过 60 秒，IR 超过 600 秒），停下来汇报，不要自行加测。
- 评审用 gpt-6.1-sol high，范围只限本次 diff。

可改的文件：
- `sail-riscv/model/core/extensions.sail`：只改 Svnapot、Svpbmt 两行的 `hartSupports`，以及 `currentlyEnabled_measure`。
- `sail-riscv/model/sys/vmem_pte.sail`。
- `sail-riscv/model/sys/vmem.sail`：只改 `pt_walk`。
- `sail-riscv/model/core/sys_regs.sail`：只改 `legalize_menvcfg`。
- `sail-riscv/model/postlude/validate_config.sail`。
- `sail-riscv/config/config.json.in`，以及 S0 列出的 IR 生成配置。
- `sail-riscv/test/first_party/` 下的新测试，和 CMake 里的注册。
- 本议题的结果文档。

不可改的文件：`isla/` 源码、`sail-riscv/configs/isla/workarounds/`、`vmem_tlb.sail`、`vmem_ptw.sail`、`mem.sail`、`pma.sail`、访存 API 的签名、XiangShan、NEMU，以及 §2.5 列出的函数。

## 6. 需要用户决策的点

| # | 决策 | 推荐 | 排除的备选与原因 |
| --- | --- | --- | --- |
| 1 | 开关形式 | Svnapot、Svpbmt 用配置键，RV64 下默认 true，与 XiangShan 和上游一致；非叶保留位检查硬编码，不加开关 | 非叶检查也加开关：规范有明文、Spike 也这样做，加开关只为复刻旧版规范，目前没有这个需求，还会多一个配置面。移植上游的 `priv_isa_version` 机制：本仓库基线没有 `isa_version.sail`，引入它超出本轮范围。Svnapot/Svpbmt 硬编码 true：做不了 4.2 的“关闭对照”回归门 |
| 2 | Svpbmt 范围与前态 | 只做 PTE 合法性和 PBMTE，不建模内存属性；P0 场景 PBMTE 固定为 0，PBMTE=1 留到 P3 作为一个维度格点 | 完整移植上游 cb8e870e：改 20 个文件和访存签名，换来的属性效果在模型里观察不到。把 PBMTE 设成符号：所有 PBMT 守卫都要按 PBMTE 再分一次，类数翻倍的风险没有收益支撑 |
| 3 | IR 生成节奏 | 分三次生成（每次只测 Sv39 LOAD 的类数，用于归因），最后一次与 E-cfg-b 合并为正式 lock 候选 | 一次生成全部：NAPOT 如果膨胀，无法归因到具体改动。每次都测全部四个场景：Sv48 太贵（783 秒以上），中间版本又不会作为 lock |
