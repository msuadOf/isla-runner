# XiangShan GitHub 浮点相关 issue 清单

核对时间：2026-09-29 04:50–06:53 UTC。来源为 `OpenXiangShan/XiangShan` 的公开 **issue**，包括 open 和 closed，不把 PR 当 issue。GitHub Search 查询 `repo:OpenXiangShan/XiangShan is:issue` 返回 898 条；9 页取得 898 个不同编号，`incomplete_results=false`。随后读取 **898/898 条公开 issue 页面**；37 条首屏时间线未完的 issue 再取第二页，最终每条 `timeline_visible=timeline_total`。四名 Sol 子代理与主代理按数组索引分五批，每条独立记录在[逐条账本](github-issue-audit/README.md)所列 `batch-1.json` 至 `batch-5.json`，180＋180＋180＋180＋178＝898，编号无重漏。旧向量专题列出的 89 个编号均在快照中。[全量标题／正文](github-issues-all-20260929.json) SHA-256 `b6af07e46878c0a9aa1b9cabc67de30c1986f1b8e1ed9782dfc53ac9b050c15e`；[完整页面／评论／关联 PR](github-issue-details-20260929.json) SHA-256 `af17f7dc329426e1c21827df3fc7eccde0c260610ce06b6ed5e3a71e85990e29`。

**纳入标准**：浮点指令、浮点寄存器或状态、浮点访存、向量浮点指令直接是报告的目标或触发条件。标量 F/D/H、向量浮点、压缩浮点访存和跨 PMP／异常／写回的共享逻辑均纳入。长日志里偶然出现一条浮点指令、单纯设置 FS/`fcsr` 作为通用前导、`vsext.vf4` 这类**整数向量扩展指令**均不构成浮点 issue。`closed` 仅是 GitHub 状态；只有维护者明确确认或合并修复 PR 时才写“确认／已修”。“已修”指 GitHub 上游，不自动证明当前本地 `xiangshan@a13efc8` 已包含修复。

## 直接涉及浮点指令或状态的 XiangShan 问题

| Issue | 扩展／部件 | 报告的触发条件与现象 | GitHub 状态及核对结论 |
| --- | --- | --- | --- |
| [#2642](https://github.com/OpenXiangShan/XiangShan/issues/2642) | D／FMA | `fmadd.d` 产生非规范 NaN，而非应有的 canonical NaN 位型。 | 关闭、`bug/fixed`；维护者称内部已知，未在该 issue 绑定公开修复 PR。 |
| [#2767](https://github.com/OpenXiangShan/XiangShan/issues/2767) | F／舍入 | `fmsub.s` 等 FMA 在 RNE/RUP/RDN/RMM 特例使用错误舍入模式；乘法段向加法段传错模式信号。 | 关闭、维护者确认；[PR #2779](https://github.com/OpenXiangShan/XiangShan/pull/2779) 已合并，评论另提 #2586。 |
| [#2890](https://github.com/OpenXiangShan/XiangShan/issues/2890) | RVV 浮点／共享活性 | 后续评论的 SAXPY 程序使用 `vfmacc.vf`，在 DefaultConfig 上挂起；维护者指向提交 [`1a0c5d77`](https://github.com/OpenXiangShan/XiangShan/commit/1a0c5d77fed8b13a9fa5f70d1f25d808a311dd7b)／[PR #3140](https://github.com/OpenXiangShan/XiangShan/pull/3140)，报告者复测该 PR 后通过。 | 关闭、已修一组包含 FP 指令的 RVV 工作负载；**没有证据定位为 FP 运算单元根因**。后来重开时连 `vsetvli` 都失败，维护者指出软件未置 `mstatus.VS`，不能算新的 FP bug。 |
| [#3839](https://github.com/OpenXiangShan/XiangShan/issues/3839) | Zfhmin／FS | `mstatus.FS=Off` 时 `flh/fsh` 未报非法指令。 | 关闭、维护者明确确认；[PR #3841](https://github.com/OpenXiangShan/XiangShan/pull/3841) 已合并。 |
| [#3864](https://github.com/OpenXiangShan/XiangShan/issues/3864) | C＋D／异常 | `FS=Off` 的压缩 `c.fldsp` 报非法时，`mtval` 使用展开后的 32 位编码，而非原 16 位编码。 | 关闭、维护者明确确认；[PR #3859](https://github.com/OpenXiangShan/XiangShan/pull/3859) 已合并。 |
| [#3927](https://github.com/OpenXiangShan/XiangShan/issues/3927) | D／FLD、PMP | M 模式未配 PMP 时，`fld` 执行结果与参考模型分歧。 | 关闭、维护者称真实 bug；[PR #3967](https://github.com/OpenXiangShan/XiangShan/pull/3967) 已合并。 |
| [#3951](https://github.com/OpenXiangShan/XiangShan/issues/3951) | Zfh／FADD | `fadd.h` 对 `-0.0` 等符号位的结果错误。 | 关闭；虽有 `question/answered` 标签，维护者明确称已知 bug、YunSuan 已修；当时尚未合入 XiangShan，本 issue 无合入 PR 证明。 |
| [#3952](https://github.com/OpenXiangShan/XiangShan/issues/3952) | Zfh／FADD | `fadd.h fs11,ft0,fs7` 在所列半精度输入上结果错误。 | 关闭；维护者称已知 bug、YunSuan 已修但当时尚未合入 XiangShan；与 #3951 同族，保留独立 issue 编号。 |
| [#3979](https://github.com/OpenXiangShan/XiangShan/issues/3979) | Zfh／FLH | `flh` 写入 FP 寄存器后的高位填充不正确；标题称“未符号扩展”，核对时应按 FLEN 的 NaN-boxing 规则解释。 | 关闭、维护者确认并称已修；[PR #3994](https://github.com/OpenXiangShan/XiangShan/pull/3994) 已合并。 |
| [#4129](https://github.com/OpenXiangShan/XiangShan/issues/4129) | D／FLD＋整指令融合 | `lui x0,...` 后 `fld` 的 lui-load fusion 未处理 LUI 目的寄存器为 `x0`，导致异常 `mcause/mtval` 分歧。 | 关闭、维护者确认；[PR #4131](https://github.com/OpenXiangShan/XiangShan/pull/4131) 已合并。 |
| [#4639](https://github.com/OpenXiangShan/XiangShan/issues/4639) | D／FLD、LoadUnit／异常 | 标题仅写 `mtval different`；维护者评论明确故障发生在 `fld`，`mtval` 随 emu 版本和随机种子变化。 | 关闭、`bug/fixed`；报告者定位 LoadUnit 提交 [`8769efd7b`](https://github.com/OpenXiangShan/XiangShan/commit/8769efd7b4782ab06aed08c14e330f602918c930)，关联已合并 [PR #4760](https://github.com/OpenXiangShan/XiangShan/pull/4760)。 |
| [#5768](https://github.com/OpenXiangShan/XiangShan/issues/5768) | RVV 浮点 move/merge／FRM | `frm=5/6/7` 时 `vfmerge.vfm`、`vfmv.v.f`、`vfmv.f.s`、`vfmv.s.f` 漏非法指令检查。 | 开放、`bug/confirmed`；维护者称 v3 向量单元仍在开发。 |
| [#5773](https://github.com/OpenXiangShan/XiangShan/issues/5773) | Zfh／FLH、异常优先级 | `flh fs3,1(a7)`、地址 `0x1`：参考模型报 `mcause=4`（错位），DUT 报 5（访问错误）。 | 开放、`bug/confirmed`；v3 WIP 回复，异常优先级是否实现自由须在复现配置下另核。 |
| [#5830](https://github.com/OpenXiangShan/XiangShan/issues/5830) | RVV＋F/D／NaN-boxing | `SEW=32` 的 `vfmv.f.s` 写 64 位 FP 寄存器时未把高 32 位填 1。 | 开放；维护者明确确认，称将修复。 |
| [#6057](https://github.com/OpenXiangShan/XiangShan/issues/6057) | 浮点 CSR／异常 | 对 `csrr a3,frm` 报非法时，`mtval` 错取后面 `fcvt.l.s` 的指令字。 | 关闭、维护者确认；评论指向修复 [PR #6084](https://github.com/OpenXiangShan/XiangShan/pull/6084)，本次未将其合入状态另作本地版本证明。 |
| [#6139](https://github.com/OpenXiangShan/XiangShan/issues/6139) | `fsd/fsw/fsh` 等／PMP、MMIO | 跨页且第二个 PMP 区无写权限时，包含浮点存储的纯 store 用例发生 `mtval` 起始地址／第二段地址分歧。 | 开放、`bug/reported`；报告者明确说可能只是 DUT/NEMU 差异，**未确认 RTL bug**。 |
| [#6141](https://github.com/OpenXiangShan/XiangShan/issues/6141) | `fld/flw/flh` 等／PMP、MMIO | 跨页且第二个 PMP 区无读权限时，包含浮点加载的纯 load 用例在错位／访问错误异常之间分歧。 | 开放、`bug/reported`；报告者明确说不一定是硬件 bug，**未确认异常优先级错误**。 |
| [#6267](https://github.com/OpenXiangShan/XiangShan/issues/6267) | F／FSW、StoreUnit/PMA | `fsw fa1,716(t6)` 访问 `0x2cc` 无 PMA 覆盖区域，参考模型报 store access fault，DUT 15,000 周期无提交。 | 开放、`bug/WIP feature`；维护者将其放在 v3 向量重构相关问题中暂缓，浮点 store 是报告的实际停摆指令。 |
| [#6303](https://github.com/OpenXiangShan/XiangShan/issues/6303) | F／异常链 | 循环中的 `fcvt.s.l` 先报非法，随后另一非法指令形成嵌套异常；下一轮 DUT 无提交。`flw`／`fsflags` 也在序列内。 | 开放、`bug/reported`；维护者调查中。根因可能是通用陷入路径，**不证明 FP 单指令本身错误**。 |
| [#6516](https://github.com/OpenXiangShan/XiangShan/issues/6516) | F/D／FCVT、fflags | `fcvt.s.l`、`fcvt.lu.s` 等需舍入的转换漏置 `NX`；维护者定位 FP 转换单元 fflags 选择器延迟。 | 关闭、维护者确认；[PR #6519](https://github.com/OpenXiangShan/XiangShan/pull/6519) 已合并。 |
| [#6528](https://github.com/OpenXiangShan/XiangShan/issues/6528) | F／FMADD、NaN-boxing | `fmadd.s` 读取未正确 NaN-box 的 FP32 源时，把低 32 位当正常数而非 canonical NaN。 | 关闭、`bug/confirmed`；[PR #6532](https://github.com/OpenXiangShan/XiangShan/pull/6532) 已合并。#6527 后来被报告者归入同一根因。 |
| [#6540](https://github.com/OpenXiangShan/XiangShan/issues/6540) | D／FSD＋RVV、异常 CSR | 向量 store 页故障后，`fsd` 再页故障，`stval` 留着前一次向量地址。 | 关闭、`bug/confirmed`；[PR #6548](https://github.com/OpenXiangShan/XiangShan/pull/6548) 已合并；这是共享故障状态问题，FP store 是明确复现指令。 |
| [#6639](https://github.com/OpenXiangShan/XiangShan/issues/6639) | RVV 浮点 move | `vfmv.s.f` 在所列 `e64/tu` 输入上把元素 0 和应保留的 tail 元素都写零。 | 开放、`bug/reported`＋`WIP feature`；维护者称 v3 向量单元开发中，未确认修复。 |
| [#6642](https://github.com/OpenXiangShan/XiangShan/issues/6642) | RVV 浮点标量操作／NaN-boxing | `vfadd.vf` 把未 NaN-box 的 FP32 标量按普通 `1.0` 运算，未按 canonical NaN 处理。 | 开放、`bug/reported`＋`WIP feature`；维护者暂缓。 |
| [#6643](https://github.com/OpenXiangShan/XiangShan/issues/6643) | RVV→FP move／提交 | `vfmv.f.s` 的 FU 输出已正确 NaN-box，但提交的 FP 寄存器值错误；与 #5830 的“FU 未装箱”现象分开。 | 开放、`bug/reported`＋`WIP feature`；维护者暂缓。 |
| [#6644](https://github.com/OpenXiangShan/XiangShan/issues/6644) | RVV 浮点 reduction／活性 | `vfredusum.vs` 被接受却未分配 IQ 路径，15,000 周期无提交；watchdog 后的结果差异仅诊断，不是错误退休证据。 | 开放、`bug/reported`＋`WIP feature`；维护者暂缓。 |
| [#6647](https://github.com/OpenXiangShan/XiangShan/issues/6647) | 标量 FP 后端／写回仲裁 | 目的为 `x0` 的 FP→整数操作不预留 `WbFuBusyTable` 时隙；后续 FP 操作同周期占用 FEX0 端口，触发多输出断言。 | 开放、`bug/confirmed`；维护者调查中。 |

## 相关报告：重复、参考模型、未证实或被否定

这些 issue 仍列出，避免把“关闭”误读为“香山修好了一个 RTL bug”，也避免漏掉与浮点直接相关的历史报告。

| Issue | 浮点关联 | 核对结果 |
| --- | --- | --- |
| [#3587](https://github.com/OpenXiangShan/XiangShan/issues/3587) | 读 `fflags` 后 FS 状态变化 | 关闭；报告者更新 XiangShan/NEMU 并重建后称问题消失，未定位单独 RTL 修复。 |
| [#3709](https://github.com/OpenXiangShan/XiangShan/issues/3709) | `csrc mstatus` 后 `fle.d` 分歧 | 关闭；维护者归因 XS/NEMU 不一致并指向 [NEMU PR #580](https://github.com/OpenXiangShan/NEMU/pull/580)，不单列香山 RTL bug。 |
| [#3829](https://github.com/OpenXiangShan/XiangShan/issues/3829) | 压缩 `fld` 在错位 MMIO 的 `mcause=4/5` 分歧 | 关闭；标题／正文未写浮点，维护者评论明确目标是 `c.fld`，并确认是 **NEMU** 过早判错位；[NEMU PR #628](https://github.com/OpenXiangShan/NEMU/pull/628) 已合并，DUT 报访问错误。 |
| [#3844](https://github.com/OpenXiangShan/XiangShan/issues/3844) | `fsh/flh` 错位 MMIO 的异常类别差异 | 关闭；维护者修正对 MMIO 异常的解释，关联已合并 [NEMU #650](https://github.com/OpenXiangShan/NEMU/pull/650)／[#657](https://github.com/OpenXiangShan/NEMU/pull/657)。 |
| [#3860](https://github.com/OpenXiangShan/XiangShan/issues/3860) | `fld` 非法时 `mtval/mstatus` 分歧 | 关闭；维护者确认 `mtval` 与 #3864 重复，`mstatus` 部分涉及参考模型的 dbltrp/SMRNMI 差异。 |
| [#3954](https://github.com/OpenXiangShan/XiangShan/issues/3954) | `fcsr.UF` 分歧 | 关闭、`bug/invalid`；维护者在新版本无法复现，怀疑 XiangShan/NEMU/YunSuan 版本不匹配。 |
| [#4550](https://github.com/OpenXiangShan/XiangShan/issues/4550) | `fcvt.w.s` 后 FS 变 Dirty | 关闭；维护者解释该 FP 指令允许保守地置 Dirty，报告者接受，不计错误。 |
| [#4980](https://github.com/OpenXiangShan/XiangShan/issues/4980) | MMIO `fld` 后 FS 状态不同步 | **开放、`bug/confirmed`／`module: tool`**；维护者明确说 DiffTest 跳过 MMIO `fld` 时没有同步 CSR，而 `fld` 会把 `mstatus.fs` 置 Dirty。是浮点触发的**DiffTest 工具问题**，并非已证 XiangShan RTL 错误。 |
| [#5426](https://github.com/OpenXiangShan/XiangShan/issues/5426) | `vfredusum.vs`、RDN 下 masked 元素 | 关闭、`module: tool`、`bug/fixed`；维护者确认 **NEMU** 对 ±0 处理错，RTL 正确；关联 [NEMU #975](https://github.com/OpenXiangShan/NEMU/pull/975)。 |
| [#5449](https://github.com/OpenXiangShan/XiangShan/issues/5449) | VectorFloatFMA 对齐逻辑 | 关闭、`bug/invalid`；报告者承认单元测试把格式参数设错，未在 XiangShan 运行。 |
| [#5922](https://github.com/OpenXiangShan/XiangShan/issues/5922) | `vfmerge.vfm` 的保留 `frm` | 关闭、`note: duplicate`；报告者明确并入 #5768。 |
| [#6034](https://github.com/OpenXiangShan/XiangShan/issues/6034) | `vfsgnj.vv` 将 FS 置 Dirty | 关闭；维护者认为实现允许置 Dirty、不会改变 `fflags`，不认定 bug。 |
| [#6063](https://github.com/OpenXiangShan/XiangShan/issues/6063) | `vfrec7` 输入 ±∞ 时疑似丢 `NV` | **仍开放**、`bug/reported`；维护者指出该输入按规范 flags 应为 0，位宽截断结果也为 0，未确认功能错误。 |
| [#6080](https://github.com/OpenXiangShan/XiangShan/issues/6080) | VectorFloatAdder 的 `Cat(0.U,...)` 宽度写法 | 关闭；维护者确认不会造成实际功能问题，仅计划改写代码风格。 |
| [#6093](https://github.com/OpenXiangShan/XiangShan/issues/6093) | VectorFloatAdder 溢出舍入 GRS 位 | 关闭、`bug/invalid`；维护者核实所指溢出信号是冗余代码，无实际功能 bug。 |
| [#6410](https://github.com/OpenXiangShan/XiangShan/issues/6410) | 文中推断 `vfmv/vfmerge` 也缺寄存器组对齐检查 | 关闭、`bug/invalid`；测试矩阵只实测整数 `vmv/vmerge`，**没有 FP move 的复现**，维护者最终称 v2/v3 不算 bug。保留这条推断供后续定向验证，不计浮点触发覆盖。 |
| [#6527](https://github.com/OpenXiangShan/XiangShan/issues/6527) | 原报 `fcvt.d.w` 错置 `NV` | 关闭；报告者承认根因实际是 #6528 的 `fmadd` NaN-boxing 问题，同由 [PR #6532](https://github.com/OpenXiangShan/XiangShan/pull/6532) 修复；**不计第二个独立 FCVT bug**。 |

## 与 FP 有交集，但不是浮点执行语义问题

| Issue | 交集 | 为何单列 |
| --- | --- | --- |
| [#4190](https://github.com/OpenXiangShan/XiangShan/issues/4190) | 向量吞吐 benchmark 含 `vfadd.vv` | 关注通用向量译码宽度和假依赖；维护者确认部分性能问题，但没有浮点专属结果错误。 |
| [#3735](https://github.com/OpenXiangShan/XiangShan/issues/3735) | `fpSchdParms` 误用 `VecDqDeqWidth` | 关闭；维护者确认 FP 调度参数**代码笔误**，[PR #3749](https://github.com/OpenXiangShan/XiangShan/pull/3749) 已合并。issue 未提供运行时浮点错误复现，故与执行语义 bug 分开。 |
| [#864](https://github.com/OpenXiangShan/XiangShan/issues/864) | 构建时报 `hardfloat` 名称缺失 | 构建／依赖问题，不是 F/D 指令错误。 |
| [#870](https://github.com/OpenXiangShan/XiangShan/issues/870)、[#1489](https://github.com/OpenXiangShan/XiangShan/issues/1489) | `berkeley-softfloat-3` 子模块获取／初始化 | 网络或依赖安装问题；#870 的公开时间线 16/16 项已补齐。关闭状态不证明该用户后续构建问题已解决。 |
| [#2467](https://github.com/OpenXiangShan/XiangShan/issues/2467)、[#4832](https://github.com/OpenXiangShan/XiangShan/issues/4832) | `fudian`／`FloatPoint` 编译缺失 | FP 模块构建问题，不表示硬件浮点语义失败。 |

**明确排除的易混条目**：[#5809](https://github.com/OpenXiangShan/XiangShan/issues/5809) 的 `vmv.x.s`、[#5829](https://github.com/OpenXiangShan/XiangShan/issues/5829) 的同指令符号扩展、[#5840](https://github.com/OpenXiangShan/XiangShan/issues/5840) 的 `vzext.vf8` 和 [#6152](https://github.com/OpenXiangShan/XiangShan/issues/6152) 的 `vzext/vsext.vf4` 均是**整数向量**指令；其中 `vf4/vf8` 表示扩展比例，并非 vector floating point。#5809 虽已被本仓旧求解 JSON 命中且在当前香山上验证修复后行为，仍不应放入浮点 bug 分母。仅在长 fuzz trace 中出现 `fsw/fcvt` 的非 FP 目标（如 #6085 的向量 store 未提交）也未混入。[#981](https://github.com/OpenXiangShan/XiangShan/issues/981) 是 FDivSqrt 的 `FuType` 配置疑问，维护者解释后报告者接受；[#1468](https://github.com/OpenXiangShan/XiangShan/issues/1468)、[#1940](https://github.com/OpenXiangShan/XiangShan/issues/1940)、[#2019](https://github.com/OpenXiangShan/XiangShan/issues/2019)、[#2668](https://github.com/OpenXiangShan/XiangShan/issues/2668) 也均为使用／设计提问，不是 bug 报告。

本清单是 **GitHub issue 身份与上游处置状态**，不是本仓 PoC 的覆盖报告，也没有重跑这些 issue。898 条标题、正文和公开时间线均已逐条核对；截图或附件里才出现的 FP 信息仍可能需要人工补录。要对照本仓标量／向量 JSON，须再逐条核对触发谓词、指令序列、所用 XiangShan commit 与该 commit 是否包含修复；当前 73df 标量运行的 1322/1322 可支持输入通过，仅适用于其冻结 IR／配置／emu 和输入分区。
