# GitHub 内存 issue 与本仓 PoC／求解／DiffTest 对照

日期：2026-09-29。范围为选定的 VSSEG、SC/AMO、错位向量访存和 PMP 案例。上游状态已直接读取 GitHub issue、评论和修复提交；本仓 W19/W24/E/P2 历史统计引用仓内[覆盖状态](../memsolve_branch_coverage/status.md)、[矩阵](../memsolve_branch_coverage/coverage-matrix.md)、[找 bug 计划](../memory_support_review/plan-bughunt.md)及[发现记录](../findings.md)。历史原始内存 JSON/ELF 位于当前工作区外，本轮未读取，不能据摘要做逐例守恒核账。

## 受测版本与判因口径

本轮当前工作区：`isla@31523abb`＋dirty，`sail-riscv@4f2ac293`＋dirty，主 IR `isla/rv64d.ir` SHA-256 `d0123541…5e5409`；`difftest-xiangshan/xiangshan@a13efc8775abb093e23727772a562f0605380685`、MinimalConfig emu `87141692…a85ee`、配套 NEMU SO `9188e7dd…ef43`。定向测试所用 `pipeline.py` SHA-256 `3b31333c…a0ace`；当前 `exec.rs` `0b600118…bf60`、`init.rs` `8d8a6839…2682`、`vmem_utils.sail` `30a797af…0e06`、`vext_mem_insts.sail` `66c009e2…d29d`、当前 TOML `71fb63e1…ad2d`。W19 使用另一内存分支 IR `33c2efef…`，W24 使用该分支后续版本；下文不将其 PASS 迁到当前主 IR。

“完整符号输入域”只表示未预先限制变量；一次可满足路径通常仅输出一个具体模型。**缺某个触发值不等于 Z3 判错或 UNSAT**。要判因，须依次检查模型与配置是否允许、目标路径是否在预算内完成、最终 JSON 是否包含该编码和值、pipeline 是否保留和按原状态编译、最后硬件／参考模型实际观察了什么。当前主树 `isla/src/isarch/exec.rs:643–742` 对 constructor 参数整体符号化；`:889–902` 的未约束有限域多样化只在 Illegal 路径调用，Retire 路径没有按具体编码穷举。它解释了为何同一架构结果下的 `nf/EEW` 可能只落一个代表编码，但不是 Z3 正确性缺陷。

## 逐 issue 对照

| 组／上游问题 | 精确触发与上游状态 | 本仓未命中阶段及可证程度 |
| --- | --- | --- |
| VSSEG [XiangShan #6475](https://github.com/OpenXiangShan/XiangShan/issues/6475) | v3 `50cdcfc2c`、`e32/m1`、合法 `vsseg3e32.v v6,(t1)`；原附件约 200 指令，ROB `uopNum` 下溢。维护者[评论](https://github.com/OpenXiangShan/XiangShan/issues/6475#issuecomment-5539019581)称 kunminghu-v3 尚未支持所测新向量指令，暂不处理；不能把 open issue 自动写成已获上游确认的受支持功能 bug。 | 旧 VSSEG 51 个 JSON 没有该具体编码（仓内 P2 记录）。本轮用当前 pipeline 的**定向** `0x42036327`、`e32/m1` 生成 ELF，本地 emu 2–3 秒内 `robEntries 37 uopNum is overflow!`、退出 1；同前导、仅将 payload 改为 `vsseg2e32.v` 的对照 GOODTRAP、退出 0。汇编仅 payload 两行不同，证明当前 JSON→ELF→emu 链能触发，历史自动漏检首先发生在具体编码的生成／代表值覆盖。P2 历史记录称分片后 28/28 组合覆盖且自动触发，但原始 P2 包在工作区外，本轮未复验其求解账。不能称 Z3 UNSAT 或算错。 |
| VSSEG [XiangShan #6486](https://github.com/OpenXiangShan/XiangShan/issues/6486) | v3 `0cdabfc7c`、`e16/m2`、合法 `vsseg2e16.v v8,(t1)`；原 ELF 在 PC `0x8000031e` 的 Store Commit：REF `0xdac10000`、DUT `0`。维护者[评论](https://github.com/OpenXiangShan/XiangShan/issues/6486#issuecomment-5541945998)同称 v3 segment 功能 WIP。 | 当前工作区下载的上游原 ELF 用本地 `a13efc8` emu/NEMU 再现相同 PC、地址 `0x80010070`、REF／DUT 数据分歧、ABORT。另构造同一指令编码、`e16/m2`、非零且不同的 v8/v10 初值，单指令 pipeline ELF **GOODTRAP**；故仅选到编码且非零值仍不足以覆盖原 POC。原 ELF 在此前执行了多种向量/访存指令；尚未隔离究竟是精确前态还是指令历史所必需。旧 W24 的 F4 缺 VPR 初值会进一步遮蔽数据差异；当前 `pipeline.py:555–572` 在 JSON 有 `vr*` 时能装载，缺字段时不装载。此项是取值／状态物化／单指令重放的组合缺口，不能单归 Z3 或 pipeline。 |
| SC [Sail-RISC-V #1574](https://github.com/riscv/sail-riscv/issues/1574) | 先对齐 `lr.w`，再用 `base+3` 执行 `sc.w`；旧 Sail 将数据拆成 4 个字节写入而未抛对齐异常。维护者[确认](https://github.com/riscv/sail-riscv/issues/1574#issuecomment-3979533460)，[PR #1603 的提交](https://github.com/riscv/sail-riscv/commit/59cfe00880a21128ed7eb99ddb90ec4bf2ce924b)在 2026-03-12 修复。 | 当前 `sail-riscv/model/sys/vmem_utils.sail:182–189` 仍仅调用普通 `check_misaligned`，旧问题在允许错位访问的模型域内可达；但当前主树 `isla/isla-lib/src/init.rs:75–116` 可覆盖顶层 let，`configs/riscv64_difftest.toml:81` 设 `plat_enable_misaligned_access=false`，此配置下输入域本身排除该行为。历史内存分支的 STORECON 成功 JSON 45/45 全对齐，只证明没有触发输入；是生成／预算／见证值覆盖缺口，尚不能在路径截断与模型取值间二选一。pipeline 单 payload 也不能重现上游 LR→SC 序列；`classify_fault_preclass` **不会**跳过 `sc.w`。 |
| AMO [XiangShan PR #6316](https://github.com/OpenXiangShan/XiangShan/pull/6316) | 修改 AtomicsUnit 的 MMIO／NC 区异常优先级和残留异常位；[cbf2d93](https://github.com/OpenXiangShan/XiangShan/commit/cbf2d93f399696f36d7d6f94bf2a9993a26641fd) 已合并，当前 `AtomicsUnit.scala:319–320,465` 有对应代码。 | W19 AMO 因引擎 panic 无最终 JSON，pipeline 无从处理；W20 后有 670 gen，但旧配置排除了 MMIO 并钉全许可 PMP。E 线摘要称 v2/v3 仍见“同类”差异，原始 E 包不在当前工作区；若地址并非 MMIO/NC，不能据此断言 #6316 回归。`classify_fault_preclass` 也不识别 `amoswap`，故“被低地址 preclass 吞掉”不是当前或 W24 管线源码支持的说法。 |
| 错位 VSSSEG [XiangShan #6296](https://github.com/OpenXiangShan/XiangShan/issues/6296) | M 模式、`0x40491397` 低地址错位，段式跨步存储；NEMU cause 6、DUT cause 7，上游 issue open，维护者指出 v3 向量仍在开发。 | 旧 VSSSEG 有 JSON，缺当前工作区内的原始逐例 JSON/ELF，无法判断是否包含同一有效地址和 vtype。W24 `pipeline.py@41ff806` 与当前 `3b31333c` 的低地址预分类正则仅识别 `sb/sh/sw/sd`，小探针验证 `vssseg` 返回 `(None,None)`；它**没有**跳过该向量 case。历史 F8 对错位异常优先级有“实现自由”裁定，单靠 cause 6/7 不能宣称新 RTL 错误。E 线另见 RAM 内错位死锁／丢字节，是新变体，不能混为 #6296 原现象。 |
| PMP／向量 [XiangShan #6605](https://github.com/OpenXiangShan/XiangShan/issues/6605) | M 模式 locked PMP NAPOT 拒绝 `0x80600000`；`vsse32.v` 漏 trap，而同址 `vse32.v` trap 7。后续[评论](https://github.com/OpenXiangShan/XiangShan/issues/6605#issuecomment-5771691075)扩展到 S/U 与页错误；其内部根因是报告者推测，未获维护者确认。 | W19/W24 配置把 PMP 钉全许可、`satp=0`，**生成输入域不含**拒绝访问／页错误情形。当前 pipeline `:673–686,784–787` 每例先写全地址 RWX PMP，无法从普通 JSON 重放 locked-deny POC；旧版为降特权路径设置开放 PMP，M 态也未构造 locked deny。VSX/VLX 旧批次无最终 JSON，又是预算／SMT 成本缺口。主要是配置和重放前导边界，不是 Z3 解错。 |
| VSXSEG [XiangShan #6085](https://github.com/OpenXiangShan/XiangShan/issues/6085) | `vsoxei32.v` 预期 store 未提交，上游 `DefaultConfig`、`f09207872d`、约 447 条指令、`vl=4`；issue open。 | 旧 W19 的 VSXSEGTYPE 三档到 3600 秒仍无最终 JSON；这批**没有输入交给 pipeline**，属于生成阶段的路径／SMT 成本或外限截断，尚无单次 SMT 与路径数拆账，不能写成 Z3 算错。上游 `DefaultConfig` 也不同于本轮 MinimalConfig。 |
| Sail segment 组界 [PR #1752](https://github.com/riscv/sail-riscv/pull/1752) | `vd + nf×2^max(EMUL_pow,0) > 32` 应 Illegal；旧 Sail 绕回寄存器号，PR 已合并。 | W24 的 F1 已凭 12 探针识别为**模型 bug**，不是漏检。当前 `vext_mem_insts.sail:230–246` 调 `illegal_store` 与 `valid_reg_group`，但旧 `vext_utils_insts.sail` 缺整体末端检查；不能把该分歧误记为 XiangShan bug 或 Z3 bug。 |

## 本工作区定向产物与判别力

[机器核账](../../difftest-xiangshan/work/github-memory-review/evidence.json) SHA-256 `55c8474a476e4fa96b9b26e885a0fe46b6fc325c9030a269e529d3a8f5f45521`，脚本 `difftest-xiangshan/work/github-memory-review/audit.py` 退出 0；记录两个 issue 的输入、ELF、结果、日志和本地 emu／NEMU／pipeline 哈希。`#6475` 的同前导 `nf=3` 失败／`nf=2` 成功为强因果对照；`#6486` 的原 ELF 失败／合成单指令成功仅证明合成状态**未覆盖**原触发条件，尚不能定位精确缺少的状态或历史。所有合成 JSON 均为**定向输入**，没有 Sail 求解器输出，绝不计入 W19/W24 官方覆盖率。

[预分类小探针](../../difftest-xiangshan/work/github-memory-review/preclass-probe.json) SHA-256 `07a583b90ae9c7b449cf8c164f241e5925167854f02bee89fef7b1d2787b3307`：同一 pipeline SHA 下，低位 `sw` 得 skip，`sc.w` 和 `vssseg` 均不 skip。`source_entries` 会跳过缺编码或非 RV64 条目（`pipeline.py:210–234`），`build` 还可能因地图假设、pre/post 缺口或代码重叠跳过（`:885–912`）；当前 fault handler 只确认 `mepc==payload_ins`，不核 Sail 的 `mcause`，fault 路径也不核 `post-memory`（`:778–807`）。故“生成过 JSON”与“测到 GitHub bug”之间仍必须有逐例 ID／编码／初态／ELF／退出守恒。

## 已修复 bug 的触发条件覆盖：另列的向量非访存例

“已修复覆盖”要求原求解条目包含旧 bug 的完整触发状态、ELF 确实执行该 payload、当前 DUT 的关键观察点与修复后预期一致，且修复提交在当前 HEAD 的祖先链上。它说明 PoC 能测到**已修复的触发条件**，不说明当前 DUT 仍有 bug；只有指令名相似、任意异常 GOODTRAP 或修复提交存在均不足以计数。

- [XiangShan #5809](https://github.com/OpenXiangShan/XiangShan/issues/5809)：旧求解 [rv64_zVMVXS.json](../../isla/agents/validation/Vext-test-9-16-difftest-xiangshan/make-solve-json/rv64_zVMVXS.json) SHA-256 `cc032413…454f7a` 的 `gen[2]` 已是 `vmv.x.s x10,v2`／`0x42202557`、`vtype.vill=1`、预期 Illegal。最初的 Retire-only 批次过滤了它；2026-09-18 trap 补跑的旧基线 `case-4815` 曾记 success，之后满载批次记过 60 秒无返回，旧结果需按批次区分。本轮把**同一原始 JSON 行**单独经当前 pipeline 编成 ELF `e9aa3b79…ebcc5`，当前 `xiangshan@a13efc8` 的 payload PC `0x8000007c` 实际执行该字并报 cause 2，GOODTRAP／退出 0；trace `6f750d0c…491a`。上游修复 PR #5744 的提交 `fdd634f…48a` 是当前 HEAD 祖先。故计 **历史求解条目已覆盖触发条件，当前 DUT 修复后行为已验证**。这不属于 73df 标量浮点或当前 d012 官方求解；旧 Vext JSON 的当时 IR／配置身份未在本轮重新绑定，不能迁记当前官方库存。
- [XiangShan #5739](https://github.com/OpenXiangShan/XiangShan/issues/5739)：PR #5743 提交 `75bf3fb…eed` 已进入当前 HEAD。旧 VSETVLI JSON SHA-256 `ab373edf…491560` 虽有 `rd=x31`，上游 bug 还要求紧随 `vsetvli` 读取 `vl` 的 `csrr` 观察点；单指令 ELF 没有该序列，**不计已修复覆盖**。
- [XiangShan PR #6316](https://github.com/OpenXiangShan/XiangShan/pull/6316)：修复提交 `cbf2d93…41fd` 在当前 HEAD 祖先链；当前定向 `amoswap.w` trace `2b7948bb…15de` 在低地址报 cause 6、GOODTRAP。然而本轮没有证明运行时地址满足该修复的 MMIO／NC 条件，handler 也不核预期 cause；**只计定向运行，不计 PR 触发覆盖**，更不能据此断言修复回归。

上述核对由当前工作区 `python3 difftest-xiangshan/work/github-memory-review/audit_fixed_coverage.py` 退出 0；[逐项哈希、源码条目、ELF、trace 与运行版本](../../difftest-xiangshan/work/github-memory-review/fixed-coverage-evidence.json) SHA-256 `4af0be30be3127e2a96614217c0bacaf8718e680ce4d56c7be1208d60233f615`。当前 runtime／配置为本报告开头所列 MinimalConfig emu、NEMU、pipeline；IR 仅作为旧 JSON 的历史来源，未在本轮执行当前 IR。

## 对“Z3 还是 pipeline”的判定

- **可以排除 pipeline 为首要漏检处**：#6475 旧批无目标编码而本地同管线可触发；#6085 无最终 JSON；#1574 旧批无错位 SC 成功 JSON。这里是模型／配置／符号执行或见证选择阶段；没有 Z3 错判 SAT 的证据。
- **明确是输入配置或重放能力缺口**：#6605 的 locked PMP、satp 域；#1574 当前 TOML 把错位支持关闭；#6486 的完整向量源值和可能的前置序列。#6486 尚不能把状态不足与序列依赖严格分开。
- **不能按历史标签下结论**：#6296 的向量 case 不被标量 preclass 过滤；#6316 当前 DUT 已含上游修复，E 线“同类”差异须先比对地址属性和修复谓词；#6475/#6486 维护者称 v3 功能 WIP。DUT/REF 在允许的异常优先级上不同，也不自动等于 RTL bug。

最省成本的后续判别是：对 #1574 在**同一冻结 IR/配置**下分别钉对齐与错位地址，只取路径 SAT／fork／最终 JSON 去向，不先开全批；对 #6486 从原 ELF 提取 payload 前完整 v8–v11、vl/vtype、内存和 CSR，再喂单指令管线，若仍通过才定位前置历史；对 #6296 按同一 case ID 留存 JSON→manifest→payload 编码与地址，检查是否生成而未运行。任何完整求解的超时或缺最终 JSON 仍记未完成。
