# Isla 种子变异与符号执行反馈：2025–2026 年论文对照

调查日期：2026-10-22。本文是研究讨论，没有实施或性能实验。论文数字均为作者报告，不是本项目复现结果。下述方案为待验证假设，不宣称研究首创。

接续：上句描述第一轮调查范围。用户随后要求多实验评估，现已建立 [实验矩阵](experiments.md) 并完成 [既有随机化生成侧 pilot](pilot-results.md)；新变异器、约束修复及DUT反馈效果仍未验证。

再接续：用户当前要求先系统学习反馈选择与符号执行闭环，专题见 [覆盖反馈综述](coverage-feedback-review.md)。本轮已通过作者公开全文补全FuSS的实现架构，下面表中“仅摘要”保留为首轮阅读范围，不作为当前证据上限。

## 论文与证据范围

会议年份与 arXiv 首次公开年份分别记录，避免把 2025 年底预印本误称为 2025 年正式会议论文。

| 工作 | 发布情况与阅读范围 | 与本设想的关系 |
| --- | --- | --- |
| [GenHuzz](https://www.usenix.org/conference/usenixsecurity25/presentation/wu-lichao) | USENIX Security 2025；官方页、正式 PDF | 语言模型生成 RISC-V 指令，以硬件反馈强化学习更新生成策略；反馈改变生成分布已有先例。 |
| [Encarsia](https://www.usenix.org/conference/usenixsecurity25/presentation/bolcskei) | USENIX Security 2025；官方页及 [作者项目页](https://comsec.ethz.ch/research/hardware-design-security/encarsia/) | 基于 177 个真实 bug 的调查自动注入有架构可观测效果的 bug；其评测质疑结构覆盖和判错器的有效性。不能把“覆盖增加”直接视为“检错增强”，也不能外推为所有覆盖都无用。 |
| [FuSS](https://doi.org/10.1145/3760529) | ACM TECS 24(5s)，2025-09-26；仅核实 [Crossref 出版方元数据及摘要](https://api.crossref.org/works/10.1145/3760529) | 覆盖平台期调用选择性符号执行，利用已有 fuzzing 轨迹求较短输入序列；“fuzzing + 符号执行”已非常接近本设想。全文实现细节未核实。 |
| [GoldenFuzz](https://www.ndss-symposium.org/ndss-paper/goldenfuzz-generative-golden-reference-hardware-fuzzing/) | NDSS 2026，预印本 2025-12；[全文](https://arxiv.org/html/2512.21524v1) III-B、III-D、VIII | 先以快速 GRM 改善指令串接和有效执行，再以 DUT 覆盖继续引导；按指令块生成，以偏好反馈更新生成策略。GRM 阶段主要提高有效性，不是拿 GRM 覆盖替代 RTL 覆盖。 |
| [ReFuzz](https://www.ndss-symposium.org/ndss-paper/refuzz-reusing-tests-for-processor-fuzzing-with-contextual-bandits/) | NDSS 2026，预印本 2025-12；[全文](https://arxiv.org/html/2512.04436v2) III、IV、VI | 复用先前处理器上的漏洞测试与高覆盖测试，以 contextual bandit 在不同覆盖阶段选择有效测试，并结合原有 fuzzer 变异。历史 bug 样例复用和自适应选择已有先例。 |
| [SimFuzz](https://arxiv.org/abs/2601.11838) | 2026-01 预印本；未核实正式会议；[全文](https://arxiv.org/html/2601.11838v1) III、IV | 从历史 bug 种子出发做块内指令变异，尽量保留控制转移，以类型、opcode、子语义、字段相似性指导探索，不依赖覆盖反馈。作者报告 17 个 bug、14 个此前未知。相似性是启发式，不是路径约束证明；正文与 Algorithm 2 的阈值方向存在表述差异，本讨论不采用其具体阈值实现。 |
| [HiFuzz](https://arxiv.org/abs/2607.06619) | 2026-07 预印本自报 ITC 2026 接收；未独立核实会议页；[全文](https://arxiv.org/html/2607.06619v1) III-C–E | 程序级和块级策略分层，底层由受约束生成器填充指令；组合语义新颖度和模块覆盖收益。全局结构与局部指令分开优化可借鉴，不必首先引入完整 RL。 |
| [DejaVuzz](https://arxiv.org/abs/2504.20934) | 2025 公开；[全文](https://arxiv.org/html/2504.20934v1) 3–4 | 面向瞬态执行，动态可切换内存改善训练/触发，差分信息流和污点覆盖指导变异。其观测及判错目标与普通功能差分不同。 |
| [TargetFuzz](https://arxiv.org/abs/2509.26509) | 2025-09 预印本；[全文](https://arxiv.org/html/2509.26509v1) III | 直接对硬件逻辑目标做 SAT 求解，并以输入间 Hamming 距离约束多样性。求解层次不同于 Isla 的 ISA 模型；不能把 Sail 中目标直接等同为 RTL 内部信号目标。 |

另读 [2026-09 SoK](https://arxiv.org/html/2609.27300v1) 的反馈链、输入生成和评测章节。该文区分目标、oracle、guidance、输入表达能力与预算，强调代理反馈可能丢失目标信息。早期 [HyPFuzz（USENIX Security 2023）](https://www.usenix.org/conference/usenixsecurity23/presentation/chen-chen) 已结合形式工具、fuzzing、目标点选择和时间调度；作为先例列出，不混入 2025–2026 年成果。

## 对研究空间的判断

把 Isla 输出接到普通变异器上，工程上有价值，但不足以单凭这个组合证明新颖性。GoldenFuzz 已让参考模型参与生成，SimFuzz/ReFuzz 已利用高质量种子，FuSS/HyPFuzz 已结合求解与 fuzzing。

较值得检验的问题是：ISA 符号模型能否把种子变成带目标条件和输入关联的可变异对象，使变异稳定留在某类困难场景中，又探索不同 RTL 行为？例如保持“某活动 lane 的访存跨越指定边界”，同时变化寄存器组、stride、mask、数据和前缀依赖。相似性启发式不能保证条件保留，普通随机变异可能频繁破坏该条件；约束求解是否因此带来净收益，需要测量。

## 种子与变异单位

建议种子携带：程序/指令块、完整初始架构状态、内存字节、实际平台配置、语义目标、版本/IR 哈希和父种子。约束可以通过重放重建，未必序列化完整 solver。汇编、ELF、预期结果是这些输入的派生产物。

| 层次 | 变异举例 | Isla 的作用 |
| --- | --- | --- |
| 数据与状态 | 非零模式、浮点分类/舍入边界、mask、vl/vstart、地址边界 | 在目标条件下求多组输入，联合调整相关变量。 |
| 编码与寄存器 | nf/EEW/LMUL、源目的组重叠、RAW/WAR/WAW | 校验译码、扩展使能和寄存器组约束；编码改变后重新执行模型。 |
| 短序列与上下文 | 生产者→消费者、store→load、LR→SC、配置切换 | 检查状态串接；前一条终态必须满足下一条所需初态。独立 witness 不能直接拼接。 |

修改任一实际输入后，重新生成预期架构结果与内存效果，不能继续使用父种子的 post-state。用于硬件执行的初始化代码还须能实际建立记录状态，并处理 CSR WARL 等行为；直接写模拟器内部状态不能替代此项验证。

## 三类符号执行协作

1. **路径内多样化**：保留路径条件 Φ，对可变维度增加目标或 blocking 约束，生成不同可满足输入。同一 Sail 路径仍可能产生不同 RTL 行为。随机改 Z3 seed 不能保证目标值域覆盖或均匀采样。
2. **跨路径探索**：保留分叉前的路径前缀，翻转目标分支，再执行后续。不能把整条旧路径条件与其某个相反条件同时保留，否则往往直接矛盾。
3. **目标条件下修复**：变异器改变部分输入，求解器联合调整其他输入，维持跨界、数据依赖或活动 lane 等场景条件。求解不可满足或超时必须独立记账，不能作为合法性结论。

更换指令或序列结构会改变语义，必须重新建立对应约束，不能无条件套用父种子的 Φ。完整路径保持也可能过严；可比较“保持整个路径”与“只保持目标条件”的探索能力。

## 两种反馈形成闭环

```mermaid
flowchart LR
  I[Isla 生成语义种子与目标条件] --> M[结构化变异]
  M --> R[快速具体模型执行与预期结果重算]
  R --> D[DUT 执行与差分]
  D --> A[语义及 RTL 覆盖档案]
  A --> M
  A --> Q[按成本与收益选择求解目标]
  Q --> I
```

语义反馈可包含译码 clause、实际模型边、异常类型、访存形态，以及与目标相关的值分类。单靠 branch coverage 会漏掉 ITE 或纯数据算术表达的数值差异。合法异常与非法编码测试应各有预算，不能把所有异常都过滤掉。

RTL 反馈可包含模块覆盖、明确选择的微架构事件、断言和差分失配。具体信号需要后续核实，本文未声称 harness 已提供。Sail 不描述 ROB、LSQ 等实现状态；不能直接用 ISA 约束求“某条 RTL 控制信号必为 1”。可以学习哪些语义种子、操作或前缀曾为某模块带来收益，优先探索它们，再用实际硬件运行检验。

两个档案分别维护。模型覆盖不再增加时，仍保留带来 RTL 新行为的样例；也为尚未显示 RTL 收益的语义角落保留探索预算。不要把两个量纲不同的覆盖数直接相加，更不要把语义新颖度作为所有样例进入 DUT 的硬门槛。

频繁候选先用快速具体参考执行；昂贵符号执行用于目标条件修复、未覆盖语义目标及探索停滞后的补种。是否复用 solver checkpoint、如何切片和导出约束，是后续实现问题。每一阶段分别统计成本。

## 与当前项目的对应

- 原 `isla/` HEAD 为 `7b7337b`，工作区还有未提交内容。本轮只读核对 `src/isarch/exec.rs` 已输出编码、`isa-state-complete`、`isa-state-post` 和 `path-signature`；这不证明所有指令的重放都已联合验收。
- `isla/isla-lib/src/executor/execution_limits.rs` 的 `advance_path_signature` 仅对 fork 方向序列做 splitmix64 更新，没有编码静态分支位置。不同分支上的相同方向序列可能得到相同签名，散列本身也有碰撞；不能单独作分支覆盖键或 SMT 约束。
- 内存工作树 `isla/.worktrees/memory-consistency@47ac90c` 已有 `value_hints.rs`、编码分片与调度；它们是配置驱动的定向探索基础，不是已完成的自适应闭环。
- 随机化工作树 `isla/.worktrees/witness-pure@2fefa72` 的 `Solver::randomize_witness` 通过临时 assumptions 尝试输入随机化，不代表自动命中目标边界。
- 上述能力分属不同版本，不能描述为现有统一可用工具；合并边界仍按 [分支核查](../branch_merge_review/report.md) 处理。原有第二波 [P4 覆盖账本/P6 短序列计划](../memory_support_review/plan-bughunt.md) 与本议题衔接。

## 最小实验建议

先固定一个 DUT 版本、一个模型/IR 和可实际重放的向量访存子集。逐层比较：Isla 生成；相同 Isla 种子加普通变异；加目标约束保持/修复；加语义反馈；加 RTL 与语义双反馈。另比较普通随机种子与 Isla 种子，避免把优质种子效应误认为求解反馈效应。

每组固定墙钟和总资源预算，多次独立随机运行；记录生成/求解/编译/参考执行/RTL/重置开销。覆盖只计 payload 或单列初始化覆盖，避免 wrapper 变化制造收益。报告有效执行比例、已验证 bug 集的命中率、首次触发时间、独立根因数，以及语义/RTL 覆盖曲线。

用历史真实 bug 和可观测的注入 bug 分别评测；历史 bug 种子与检验 bug 按家族隔离，直接命中已提供样例只计复现。普通分歧先区分 DUT、参考模型、平台差异与初始化错误；侧信道需要单独的泄漏 oracle，普通架构差分不足。

主要验收问题：**相同总成本下，保持目标条件并改变上下文，是否比普通变异发现更多独立错误，或更快命中保留 bug 集？** 若只有 testcase 数或覆盖上涨，而检错与成本无改善，研究假设仍未得到支持。
