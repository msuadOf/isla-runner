# GitHub 内存 issue 对照状态

2026-09-29：只读核对公开 GitHub 的 XiangShan #6475/#6486/#6296/#6605/#6085、PR #6316，以及 Sail-RISC-V #1574／PR #1752；主 agent 在当前工作区对 #6475 和 #6486 做定向 PoC 比较，无全量求解或批跑。实施与逐项证据见[报告](report.md)，步骤和边界见[计划](plan.md)。

- **验证 PASS（限定定向输入）**：本地 `xiangshan@a13efc8`、MinimalConfig emu `87141692…a85ee`、NEMU `9188e7dd…ef43`、pipeline `3b31333c…a0ace` 下，`vsseg3e32.v` 触发 #6475 同名 ROB `uopNum` 断言，唯独改 nf=2 的对照 GOODTRAP；#6486 GitHub 原 ELF 复现同 PC、同 store 数据分歧，合成单指令非零源值用例则 GOODTRAP。[机器核账](../../difftest-xiangshan/work/github-memory-review/evidence.json) SHA-256 `55c8474a…f45521`。它们是定向验证，未计入符号求解覆盖。
- **归因**：旧 #6475 批次无触发编码，现有管线可重现，因此首先是生成／代表值覆盖；#6486 精确前态与指令历史尚未拆开，不能只归 Z3 或 pipeline；#1574 的旧 SC 模型错误已获上游修复，但当前主 TOML 关闭错位支持，历史45条成功见证全对齐仅证未覆盖；#6605 的 locked PMP 被历史配置和当前重放前导排除；#6085 旧批无最终 JSON。#6296 的 VSSSEG 与 #6316 的 AMO **不会**被现有低地址标量 store preclass 跳过，修订历史泛化表述。[预分类小探针](../../difftest-xiangshan/work/github-memory-review/preclass-probe.json) SHA-256 `07a583b9…b3307`。
- **未闭合**：W19/W24/E/P2 原始内存 JSON、ELF 和逐例日志不在当前工作区，未读取；#6486 还不能证明是精确状态还是序列依赖，#6296 不能判断历史 JSON 是否出现精确地址。没有发现 Z3 SAT 错判证据。当前主树 `isla@31523abb` 的 JSON schema 没有历史内存字段，IR `d0123541…5e5409`，历史内存分支结果须保持版本限定。

**已修复 bug 另账（向量非访存，2026-09-29）**：旧 Vext 求解 `rv64_zVMVXS.json` 的 `gen[2]` 精确包含 #5809 的 `vmv.x.s`＋`vill=1`，当前本工作区 pipeline 重编 ELF 后在 payload 得 cause 2、GOODTRAP／退出 0；#5744 修复提交在当前 XiangShan HEAD 祖先链。计“历史求解触发条件覆盖且修复后行为验证”，不计当前 DUT bug 或 73df／d012 官方求解。旧 2026-09-18 trap 补跑基线也曾记录此条 success，故“过去完全没有重放”不成立。#5739 缺紧随 `vsetvli` 的 `csrr vl`，#6316 缺 MMIO／NC 谓词证明，均暂不计已修复覆盖。[分界与证据](report.md#已修复-bug-的触发条件覆盖另列的向量非访存例)、[机器核账](../../difftest-xiangshan/work/github-memory-review/fixed-coverage-evidence.json) SHA-256 `4af0be30…33f615`；旧 Vext JSON 的原 IR／配置身份本轮未重新绑定。
