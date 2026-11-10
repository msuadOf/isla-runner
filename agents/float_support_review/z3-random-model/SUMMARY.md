# Z3 随机满足赋值能力研究结论（2026-09-28）

双路研究：实测见 [empirical-report.md](empirical-report.md)（z3 4.16.0 CLI，E1–E8），文档/社区见 [docs-research.md](docs-research.md)。主 agent 复核：本机 `isla/target/release/isarch` 与官方诊断二进制 ldd 均为 `/home/linuxbrew/.../libz3.so.4.16`（Z3 4.16.0），与实验 CLI 同源；docs-research 中"实链 4.13.3"为 crate 元数据推断，不符合本机实际，以 ldd 为准。

## 定论

1. **Z3 无原生"求随机满足赋值"功能**（4.16 参数表无此项；Z3 开发者 Wintersteiger 明言模型不会随机分布，官方推荐 blocking 枚举）。`random_seed` 系列只改搜索轨迹，不构成采样。
2. **"python z3 能求随机数"的最合理解释**：用户的 python 变量带约束且脚本开了随机相位（`smt.phase_selection=5` / `sat.phase=random`）并逐次换 seed——值会变。差异在**约束形态**（变量是否直接出现在子句里），不在语言绑定。
3. **对本项目的真实形态实测无效**：vl/载荷只出现在 pure 函数（UF）调用参数里（E4，5 配置×12 seed=60/60 恒 0）或完全自由（E5，48/48 恒 0，还会被 `elim_unconstrained` 预处理直接消除）——seed/phase/freq 全部无效，model completion 恒填 0。仅当变量直接出现在约束里（E3）`sat.phase=random` 才让值散开（12 跑 9 个值，仍偏端点、无均匀性）。
4. **assumption 注入完全可靠**（E6/E7）：域内随机猜测 100/100 命中且模型值即注入值，域外诚实 UNSAT。随机性只能由调用方 seeded RNG 提供，Z3 负责"符合条件"判定。

## 机制排序（面向 isla-lib solve 循环）

1. **assumption 注入（推荐）**：case 生成循环对多样性维度（vl、操作数载荷）先采样、以 `check-sat-assuming (= dim k)` 注入；一次 check 成交，配合 curated 类别+均匀混合分布与固定 RNG seed 记账。
2. blocking 枚举扩展（Z3 官方推荐路线的变体）：把 case 身份投影扩到值类别（vl==0?、指数类、snan/qnan），同类别模型被 block——与 1 等效但走约束而非 assumption。
3. `sat.phase=random` + 变 seed：仅对直接受约束变量有效，无均匀保证，不解决本项目形态。
4. UniGen2/SPUR 等哈希采样器：CNF 接口需 bit-blast，工程成本高，不推荐。

## 社区求助贴/博客调研（2026-09-28 补充，详见 community-en.md / community-zh.md）

- **英文社区不存在"Z3 原生随机模型"的说法**：Wintersteiger（SO #18770582 的经典回答）、Bjørner、de Moura 三位开发者在 SO/GitHub 的回答口径一致——seed 只扰动搜索轨迹；相位随机仅当变量真正进入分支搜索才生效（被预处理解掉或未约束的变量取值恒定）；均匀采样是外部算法领域（UniGen/SPUR/CMSGen/SMTSampler）。Bjørner 给过的"随机"代码实为 `sat.phase=random` + 外部逐 seed 重建求解器，与本仓库实测吻合。
- **Z3 开发者 2014 年 SO #24330928**（简单约束被预处理直接解出、随机相位无效）与 2026 年 z3 4.16 实测完全一致——该问题七年前已被官方否定回答。反向帖子（SO #76031510"如何让 z3 浮点解不变"）恰好佐证：真正进入搜索的变量（浮点）值确实会跨运行漂移，这是"python 能求随机数"印象的另一来源。
- **中文社区正规教程无此主张**，主流共识是"model() 只给其中一个可行解"；"随机"印象三个真实来源：① angr/符号执行教程话术 + angr 跨运行差异实为 PYTHONHASHSEED（claripy#67 官方定性）；② 2026 年疑似 AI 生成的 CSDN 文错误宣称"Z3 默认随机化"；③ blocking 多解循环被误读。中文圈对 sat.phase 与 model completion 零讨论。

## 对分支覆盖缺口的意义

E4/E5 恒 0 从求解器层面证明了官方产物中 vl=0 退休、载荷退化的必然性（不是生成器选择问题）；assumption 注入的 100% 命中率给出修复路径。实施须走 isla-lib 组件隔离 + TDD + 独审 + 67/89 回归 + 小 clause A/B 的仓库流程。
