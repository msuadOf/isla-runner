# Z3 "随机模型 / 随机满足赋值" 英文社区调研

调研日期：2026-09-28。调研方式：WebSearch + 网页抓取（Stack Overflow 全文若干、GitHub issue/discussion 全文两篇，其余为搜索引擎收录的原文片段）。

目的：回应"python 的 z3 solver 就能求解出满足约束的随机数"这一说法，逐条核对社区帖子中"随机"到底从哪来。每条按以下三型归类：

- **(a) 约束形态**：帖子作者的约束本身迫使值非零/多样（变量直接出现在约束里、下界/等式逼出具体值）；
- **(b) 显式参数**：设置了 `random_seed` / `phase_selection=5(或10)` / `sat.phase=random` / `smt.arith.random_initial_value` 一类参数；
- **(c) 外部循环**：blocking（`a != m[a]`）、随机区间/随机约束注入、逐次换 seed 重解等求解器之外的做法。

**证据等级标注**：〔全文〕= 抓到了帖子完整原文；〔片段〕= 只有搜索引擎收录的原文摘录；〔仅标题〕= 确认存在但正文未能抓取。

---

## 1. "z3 random model" / "get random solution" 类帖子

### 1.1 Z3: Offering random solutions in solving（2013-09，被引用最多的一帖）
- 链接：https://stackoverflow.com/questions/18770582/z3-offering-random-solutions-in-solving 〔片段〕
- 问题：提问者要求 z3 "produce a random number in the range [101, MAXINT)"，例如 seed=1000 时每次得到不同满足值。被采纳回答来自 **Leonardo de Moura**（z3 作者）。其示例代码被 GitHub issue #1909 原文复刻（见 5.2），核心是：
  ```lisp
  (set-option :smt.auto-config false)
  (set-option :smt.phase-selection 10) ;; select random phase selection
  (declare-const a (_ BitVec 32))
  (assert (bvugt a (_ bv100 32)))
  (check-sat)(get-model)
  ```
- 机制判定：**(a)+(b)**。注意变量 `a` **直接出现在约束** `bvugt a 100` 中（这就是我们实测"变量出现在约束里值才散开"的最早出处形态）；随机性来源是 `phase-selection 10`（随机相位），且必须 `auto-config false` 防止参数被覆盖。回答正文文字未能直接抓取（仅能确认采纳答案存在、侧栏显示 9 票被多处链接）。

### 1.2 Z3 randomness of generated model values（2014-06）
- 链接：https://stackoverflow.com/questions/24327987/z3-randomness-of-generated-model-values 〔全文〕
- 问题（Carsten Rütz）：想影响 z3 模型值的随机性，"the options for this are very limited"；试 `smt.arith.random_initial_value` 无效；并明确写道："**Even model completion for variables unused in the given constraints seems to produce deterministic results all the time.**"（未被约束使用的变量的 model completion 也总是确定值——与我们"完全自由变量恒 0"的实测一致）。
- 评论区 usr 的做法："You could refine a given model by adding random constraints like `x >= rand()` until you get unsat." → **(c)**。
- 被采纳回答（**Christoph Wintersteiger**，z3 开发者）："There was indeed a bug that caused the random seed not to be passed through to the arithmetic theory. This is now fixed in the unstable branch." 并给出 `check-sat-using (using-params qflra :random_seed 1/2/3)` 三次得到三个不同模型的例子（模型值形如 `y=4294966763, x=4294966337` 等散布值），同时警告"there may be another place where this option isn't passed through correctly (e.g., when using set-logic…)"。→ **(b)**，且仅对 LIA simplex 且以 tactic 级 per-call 参数形式生效。

### 1.3 Z3Py: randomized results (phase-selection) not random?（2014-06）
- 链接：https://stackoverflow.com/questions/24330928/z3py-randomized-results-phase-selection-not-random 〔全文〕
- 问题：把 de Moura 的 BV 例子翻译到 z3py，`phase_selection=5` + `random_seed` 之后结果仍然恒定。
- 被采纳回答（**Wintersteiger**）原话："**This case is simply too simple. It's essentially solved by the preprocessor and never gets to a point where it needs to select a phase, so random phase selection has no effect.**" 并说明 "Leo's answer … is now a little bit out of date and Z3 has changed… Z3 chooses to use a different solver"；补救办法是加 `(push)` 强制走增量 smt 求解器后示例才随 seed 变化。
- 机制判定：**(b) 失效的条件刻画**——即随机相位只有在"变量真正进入 SAT 分支搜索"时才起作用；预处理能直接解掉的约束、不出现的变量，参数再对也不动。这是与我们实测结论（变量须出现在约束中且 phase=random）最贴合的一条社区解释。

### 1.4 Z3py, random different solution generation（2020-02）
- 链接：https://stackoverflow.com/questions/60033332/z3py-random-different-solution-generation 〔全文〕
- 问题（Jack Feng）：`Tactic('qflra').solver()` + `a>10` + `smt.arith.random_initial_value` + 每轮换 `smt.random_seed` + blocking `s.add(a != m[a])`；输出先是 `4294966399, 4294966398, …` 后变成 `11,12,13…` 的近似连续数列，问怎么才能"均匀分布于解空间"。
- 评论（JohanC）："the random seed is used to make sure the result becomes predictable, not to get uniformly distributed solutions."
- 回答（alias，3 万声望用户）："**I think you're conflating what randomization does with sampling. … Sampling is an entirely different (and much more difficult) problem than setting some random numbers.** Otherwise, what you're doing is correct."
- 机制判定：**(b) 部分 + (c)**。首轮的大数值（≈2^32 附近）说明 `arith.random_initial_value` 注入了随机初值，随后连续数列来自 blocking 走解空间相邻点——"多样性"是外部循环给的，不是 solver 的随机模型。

### 1.5 z3py, give random solution using seed（2020-02）
- 链接：https://stackoverflow.com/questions/60033071/z3py-give-random-solution-using-seed 〔全文〕
- 问题（同一作者）：`a>0`，设 `arith.random_initial_value=True`、`phase_selection=5`、`random_seed=1`，加 blocking 循环，输出 `1,2,3,4,5…`，问"random 怎么不生效"。
- 回答：alias 直接标记为 1.4 的重复。→ 印证：LIA 单调约束下这些参数全都不改变取值顺序，blocking 只会从最小值开始确定性爬行。**(b) 无效 + (c)**。

### 1.6 [Question] Is it possible to add randomness to generated solutions?（2025-03，官方仓库讨论）
- 链接：https://github.com/Z3Prover/z3/discussions/7595 〔全文〕
- 提问（jonathan-dilorenzo）："if I pass Z3 the same formula, it will generate the same solution deterministically every time… I have a use-case (as part of a **Fuzzer**)… tell Z3 to randomize the solutions more (ideally w.r.t. a seed). Is there any setting that allows for this or **do I need to perturb the formula externally**?"
- 回复（**Nikolaj Bjørner**，维护者）见第 5 节；后续 verios-google 的追问是本次调研里与我们实测现象最接近的复现（见第 2 节）。

---

## 2. "model always returns 0 / same model every time" 类帖子

### 2.1 GitHub Discussion #7595 中的 IPv4 恒为下界案例（2025-08/09）
- 链接：https://github.com/Z3Prover/z3/discussions/7595 〔全文〕
- verios-google："our constraint is on an IPv4 address… address value >= 224.0.0.0, address value <= 239.255.255.255… **The solver keeps producing 224.0.0.0, even after changing the seed repeatedly.** That is a valid solution, was just hoping to generate other valid solutions as well. Why does this happen? **Is the constraint just too simple that randomness does not impact the result?**"（催更一次后 Bjørner 给出的解法见第 6.1 条）
- 机制判定：**只有换 seed（b 的弱形式）不够**；变量虽在约束里，但仅是区间下界，无 `sat.phase=random` 时恒取角落值。与我们"任何 seed 下恒 0"的观察同源：模型值是搜索启发式的副产物，不是均匀采样。

### 2.2 model completion 的确定性（SO 24327987 内嵌证据）
- 链接：https://stackoverflow.com/questions/24327987/z3-randomness-of-generated-model-values 〔全文〕
- 提问者原话（见 1.2）：未进入约束的变量的 model completion 值恒定。z3 官方参数文档佐证：`model.completion`（bool，默认 false）"enable/disable model completion"（https://microsoft.github.io/z3guide/programming/Parameters/ 〔片段〕）；z3 Models 文档演示用 `m.eval(x + y, model_completion=True)` 才会给未约束变量填具体值（https://z3prover-z3.mintlify.app/concepts/models 〔片段〕，官方文档镜像）。
- 机制判定：**自由变量的"模型值"是补全默认值**，与随机无关；社区无人声称 completion 会随机化——与我们"完全自由 BitVec 恒 0"一致。

### 2.3 Is z3 model the same for a same program?（2016-02）
- 链接：https://stackoverflow.com/questions/35623686/is-z3-model-the-same-for-a-same-program 〔仅标题〕
- 在 24327987 的 Linked/Related 列表反复出现，主题为"同一程序模型是否相同"。未能抓到正文，仅可作为"该问题群存在"的索引。

### 2.4 How do I make z3 float solution not random（2023-04，反向问题）
- 链接：https://stackoverflow.com/questions/76031510/how-do-i-make-z3-float-solution-not-random 〔片段〕
- 摘录："Bottom line: If you want determinism, don't use python. Or, you can use Python to generate the SMTLib, but then save that…"（浮点解在 Python 绑定层面表现不稳定，建议改用命令行 z3 跑固定 smt2）。反向印证：Python 侧的"随机"来自进程/环境差异而非 z3 的随机模型功能。

---

## 3. "z3py different results each run" / random_seed 是否改变模型

### 3.1 Randomness in Z3 Results（2013-03）
- 链接：https://stackoverflow.com/questions/15731179/randomness-in-z3-results 〔片段〕
- 问题摘录："I am using the Z3 Python interface as part of a research tool… I noticed some pretty odd behavior when I run the Z3 solver repeatedly…"（同约束重复运行结果漂移）。正文与回答未能抓取；该帖是 SO `z3+random` 标签群的高龄入口之一。

### 3.2 Z3 producing different models when run multiple times（2017-12）
- 链接：https://stackoverflow.com/questions/47839976/z3-producing-different-models-when-run-multiple-times 〔仅标题/片段〕
- 提问围绕"关掉 auto-config、设了 random seed 之后多次运行仍得到不同模型"。正文未能抓取，标题与搜索摘要确认其存在于本主题群。

### 3.3 Controlling randomness in Z3（2020-05）
- 链接：https://stackoverflow.com/questions/62127692/controlling-randomness-in-z3 〔仅标题〕
- 反向诉求（想暴露/增大随机性使连续查询返回不同模型）。正文未能抓取。

### 3.4 GitHub issues（z3 官方仓库）
- **#740 Invalid model generated without warning**（2015）：提问含 "Does Z3 store any state between solver calls (e.g., the state of random number generators)?"（https://github.com/Z3Prover/z3/issues/740 〔片段〕）
- **#909 Setting :random-seed has practically no effect**（2015）：换 random seed 后求解时间变化 >2x，但对结果影响近乎为零（https://github.com/Z3Prover/z3/issues/909 〔片段〕）
- **#1821 Making Z3 determenistic (using random seed)**（2018）：'I have heard that using "random_seed" it is possible to enforce a more deterministic behavior of the solver… z3.set_params(random_seed=2) but it doesn't feel like my situation got better.'（https://github.com/Z3Prover/z3/issues/1821 〔片段〕）
- **#6679 make z3 solver (python) deterministic**（2021）、**#7525 Nondeterministic behavior observed despite seed set**（2023）：均为"想要确定性却拿不到"的镜像问题（链接见 https://github.com/Z3Prover/z3/issues/6679 、https://github.com/Z3Prover/z3/issues/7525 〔片段〕）
- **#10860（2026-09）Workflow Suggestions**：仓库维护流程建议里出现"Weekly check for non-deterministic sat…: result + model hash across N repeated runs with different sat.random_seed"（https://github.com/Z3Prover/z3/issues/10860 〔片段〕）——官方仓库自己把"换 sat.random_seed 会改模型哈希"当作回归检测手段，说明 seed 的作用是扰动搜索，而非提供采样功能。
- 参数文档佐证：`phase`（SAT）取值 `always_false / always_true / basic_caching / random / caching`，默认 `caching`，另有 `phase.sticky` 默认 true（Z3 Parameters 文档镜像 https://git.uninsane.org/Z3/z3/src/commit/…/params/params.md ，经搜索摘录〔片段〕；官方版见 https://microsoft.github.io/z3guide/programming/Parameters/ ）。Apalache 文档亦说明其 `smt.randomSeed` 映射到 z3 的 `sat.random_seed` 与 `smt.random_seed` 两个参数（https://apalache-mc.org/docs/apalache/tuning.html 〔片段〕）。

小结：这一类的社区图景是 **random_seed 的官方定位是"可复现/扰动启发式"**（同一 seed 应同结果；换 seed 不保证换模型），与我们实测"任何 seed/相位下自由变量恒 0、只有约束内变量 + phase=random 才散开"完全兼容。

---

## 4. "sample solutions SMT solver uniformly"（UniGen / AlmostAll / SPUR / DMC / SMTSampler）

社区（论文 + 作者博客 + 工具页）对这些工具的统一叙事：**均匀采样是独立于求解器的算法**（通用哈希 / 局部随机游走 / 近似计数），不是任何 SMT solver 的参数或功能。

- **UniGen**：Chakraborty, Meel, Vardi,《Balancing Scalability and Uniformity in SAT Witness Sampling》（https://arxiv.org/pdf/1403.6246 〔片段〕）——基于 universal hashing 的 almost-uniform 采样器，与计数共享技术。
- **AlmostAll**：Meel Group LICS 2022（https://meelgroup.github.io/publication/lics22/ 〔片段〕）——只需一次近似计数调用，保证 O(log n · log(1/ε) + 1/ε)。
- **DMC（distribution-aware model counting / 加权计数采样）**：属于 Meel Group 加权计数线（入口页 https://meelgroup.github.io/ 〔片段〕）。在通用论坛（SO/reddit）几乎无独立讨论帖，主要存在于论文与工具链（Arjun 等）语境；调研未找到"用 DMC 直接给 z3 出随机模型"的社区教程。
- **SPUR**：SAT 域均匀采样器；评测文献《Uniform and Scalable SAT-Sampling for Configurable Systems》（https://dl.acm.org/doi/10.1145/3377813.3381341 ，ACM DL 条目经搜索摘录〔片段〕）与《Uniform Sampling of SAT Solutions for Configurable Systems: Are We There Yet?》（Plazar 等，https://inria.hal.science/hal-01991857 〔片段〕）将 SPUR/UniGen2/Smarch/QuickSampler 同台比较；后者结论被引用为"only Spur satisfies both scalability and uniformity"。社区要点：**这些采样器以 SAT 求解器为子程序、外部反复调用**，从不声称 solver 本身有随机模型能力。
- **CMSGen**：Mate Soos（CryptoMiniSat 作者）博客《CMSGen, a Fast Uniform-Like Sampler》（https://www.msoos.org/2021/09/cmsgen-a-fast-uniform-like-sampler/ 〔片段〕）及后续《Checking Uniform-Like Samplers》（https://www.msoos.org/2022/06/checking-uniform-like-samplers/ ）、《Our tools for solving, counting and sampling》（https://www.msoos.org/2024/02/our-tools-for-solving-counting-and-sampling/ ）。关键表述：CMSGen 是"uniform-like"、快、加权，但 **"no formal guarantees"**（无均匀性形式保证）——作者自己把"solver 随手给的模型"与"采样器保证"区分得很清楚。
- **SMTSampler**：Dutra, Bachrach, Sen，《SMTSampler: efficient stimulus generation from complex SMT constraints》（ICCAD'18，https://dl.acm.org/doi/10.1145/3240765.3240848 〔片段〕）：摘要即写 "We developed a new technique SMTSampler which can **sample random solutions** from Satisfiability Modulo Theories (SMT) formulas with bit-vectors…"。做法（据其论文与后续 GUIDEDSAMPLER 文档线）：从 solver 要一个种子解，然后按 Hamming 距离做**随机游走 + 少量 solver 调用修复**——即随机性在求解器外部的局部搜索里。
- 佐证立场：Vardi 在 Simons Berkeley 讲稿《The SAT Revolution: Solving, Sampling, and Counting》（https://simons.berkeley.edu/sites/default/files/docs/4393/moshevardi.pdf 〔片段〕）概括该线工作："Based on universal hashing • **Uses an SMT solver** • Scales to millions of variables"——solver 是被外部哈希框架反复调用的黑盒。

机制判定：**全类皆为 (c)（外部算法），部分组合 (b)**（CMSGen 依赖 CryptoMiniSat 的随机相位/扰动）。没有任何一篇把它描述成"z3 打个参数就出均匀随机模型"。

---

## 5. z3 开发者（Wintersteiger / Bjørner / de Moura）对"random model"请求的原话

### 5.1 Wintersteiger（两帖被采纳回答，均〔全文〕）
- SO 24327987（2014）："Thanks for catching that! **There was indeed a bug that caused the random seed not to be passed through to the arithmetic theory.** This is now fixed in the unstable branch… Now produces three different models… It looks like there may be another place where this option isn't passed through correctly (e.g., when using set-logic instead of calling the qflra tactic directly), we're still looking into that."（链接：https://stackoverflow.com/questions/24327987/z3-randomness-of-generated-model-values ）
- SO 24330928（2014）："This case is simply too simple. It's essentially solved by the preprocessor and never gets to a point where it needs to select a phase, so random phase selection has no effect. … We can still get the random behavior if we force it to use the incremental solver by adding a (push) command…"（链接：https://stackoverflow.com/questions/24330928/z3py-randomized-results-phase-selection-not-random ）

### 5.2 de Moura
- SO 18770582（2013）被采纳回答：以 `smt.phase-selection 10`（注释原文 "select random phase selection"）+ `auto-config false` 的 BitVec 例子示范"如何拿到不同解"；该示例在官方 issue #1909（2018）中被提问者 Evgeniy Shishkin 原文复刻并抱怨"已不产生非确定性"（https://github.com/Z3Prover/z3/issues/1909 〔issue 正文全文〕）。即：**de Moura 从未给出"原生随机模型"开关，给的是"随机相位 + 变量在约束里"的搜索级技巧**，且四年后官方仓库里确认该技巧对简单约束失效。
- 2015-09 GitHub 优化器相关 issue 评论（经搜索摘录〔片段〕，原始 issue 号未能确认，标题 "What is the status of the optimization stuff in the unstable"）："There isn't any direct support for extracting all models. There are specialized all-sat solvers, but Z3 does not incorporate any of these."——连"取多个模型"都无原生支持，需外部 blocking。

### 5.3 Bjørner（Discussion #7595，2025，〔全文〕）
- 第一轮（2025-03-25）："**use options smt.random_seed=NNN and sat.random_seed=NNN to ensure either SMT or SAT core uses randomization.**"
- 第二轮（2025-09-09，面对"换了 seed 仍恒出 224.0.0.0"的追问）直接贴代码（完整见 6.1）：`set_param("sat.phase", "random")` + 每轮 `set_param("sat.random_seed", count)` + 新建 Solver 重解。
- 解读：Bjørner 给出的"官方解法"本身就是 **(b)+(c) 组合**（显式随机相位 + 外部逐 seed 循环重建求解），而非任何"随机模型" API；且第一轮只给 seed 参数被用户实测证明无效，第二轮才补上 `sat.phase=random`——与本项目实测"必须 phase=random 且变量在约束里"逐点吻合。

### 5.4 SO 24219509 Use of random-seeds in Z3（2014-06）
- 链接：https://stackoverflow.com/questions/24219509/use-of-random-seeds-in-z3 〔片段〕
- 提问即："What is the use of the option random-seed in z3? **Can it be used to generate random models?**" 回答者被提问者在评论中称为 "Nikolaj"（Bjørner）。回答正文未能抓取，但提问者跟评原话可证其结论方向："**Thanks Nikolaj for the answer. One thing is for sure, for LIA we can't get random models.** But for bit-vectors how does phase-selection works…"——官方回答的直接效果是让提问者得出"LIA 拿不到随机模型"的结论。

---

## 6. "用 z3 拿随机数"的可运行代码片段剖析

### 6.1 Bjørner 在 Discussion #7595 给出的片段（2025-09）〔全文〕
```python
from z3 import *
ip = BitVec("ip", 32)
set_param("sat.phase", "random")
count = 0
while True:
    count += 1
    set_param("sat.random_seed", count)
    s = Solver()
    s.add(ULE(0 + 256*(0 + 256*(0 + 256*224)), ip))
    s.add(ULE(ip, ((255*256 + 255)*256 + 255)*256 + 239))
    print(s.check())
    print(s.model())
```
剖析：
1. **约束形态 (a)**：`ip` 直接出现在两条 ULE 约束里（不在约束里的变量/仅作 UF 参数的变量在此片段中不存在——Bjørner 特意让变量被约束）；
2. **(b)**：`sat.phase=random` 是值能散开的必要条件（前一轮用户只换 seed 无效的对照就在同一帖）；
3. **(c)**：随机性注入靠**外部** while 循环逐次改 `sat.random_seed` 并**重建 Solver**；
4. 结论：这不是"z3 原生随机模型"，而是官方维护者手把手教的"相位随机 + 外部 seed 扫描"组合拳。

### 6.2 Jack Feng 的两个片段（SO 60033071 / 60033332）〔全文〕
- 60033071：`Int a, a>0` + `arith.random_initial_value=True` + `phase_selection=5` + `random_seed=1` + blocking → `1,2,3,4,5…`。剖析：LIA 下这些参数不改变取值；可见的"多样"完全来自 **(c) blocking 循环**，且是确定性的最小值爬行。
- 60033332：qflra + 每轮换 seed + blocking → `4294966399, 4294966398, …, 11, 12, …`。剖析：首个大数值证明 `smt.arith.random_initial_value`（**(b)**）确实给 simplex 注入过随机初值；之后又回到连续值——**多样性衰减**，alias 指出这根本不是 sampling（见 1.4）。

### 6.3 Wintersteiger 的两个片段（SO 24327987 / 24330928）〔全文〕
- 24327987：`check-sat-using (using-params qflra :random_seed N)` 三连，N=1/2/3 → 三个散布模型。**(b)** 纯参数方案，但限定 qflra tactic、且当时还依赖 bug 修复。
- 24330928：BV `bvult x 100` + `phase_selection=5`：无 push 时被预处理直接解掉，参数无效；加 `(push)` 后才随 `random_seed=456` 变化。**(b) + 约束/求解器路径依赖**——"参数是否起作用取决于约束有没有真正走到分支搜索"的最直接官方证据。

### 6.4 社区惯用 blocking 枚举模板
- usr 评论（SO 24327987）："adding random constraints like `x >= rand()` until you get unsat" → **(c)** 随机约束注入。
- Brandon Rozek 博客《Obtaining Multiple Solutions Z3》（2022-12，https://brandonrozek.com/blog/obtaining-multiple-solutions-z3/ ，源文件 https://git.brandonrozek.com 仓库 `website/content/blog/obtaining-multiple-solutions-z3.md`）〔片段〕："It turns out after searching around StackOverflow (see references) **the only way is to add the previous solutions as constraints**."——以 Diophantine 方程 `5a+4b-3c=0` 演示 blocking。**(c)**。
- CPMpy 的 z3 求解器文档在"多解"一节同样引用 SO 问答并注明 "a 'model' for z3 is a solution"，用 solveAll/blocking 实现（https://cpmpy.readthedocs.io/en/latest/solvers/z3.html 〔片段〕）。**(c)**。

### 6.5 汇总表

| 片段 | 出处 | (a) 约束迫使 | (b) 显式参数 | (c) 外部循环 | 备注 |
|---|---|---|---|---|---|
| Bjørner IPv4 | GH Discussion #7595 | 是（ULE 界） | `sat.phase=random`（必要） | 是（逐 seed 重建 solver） | 官方推荐姿势 |
| de Moura BV | SO 18770582 | 是（bvugt 界） | `phase-selection 10` | 否（重复 check-sat） | 2018 年 issue #1909 复测失效 |
| Wintersteiger qflra | SO 24327987 | 是（x+y>0） | `random_initial_value`+`random_seed` | 否（三次 check-sat-using） | 依赖当年 bug 修复 |
| Wintersteiger push | SO 24330928 | 是（bvult） | `phase_selection=5` | 否（push 强制增量） | 无 push 则被预处理短路 |
| Jack Feng #1 | SO 60033071 | 半（a>0） | 有但无效 | 是（blocking） | 输出 1,2,3… |
| Jack Feng #2 | SO 60033332 | 半（a>10） | `random_initial_value`（首轮生效） | 是（blocking+换 seed） | 多样性随即衰减 |
| Rozek / usr / CPMpy | 博客/评论/文档 | 否 | 否 | 是（blocking / 随机约束） | 社区共识做法 |

---

## 社区共识总结

1. **不存在"z3 原生随机模型"的说法或功能。** 没有任何一篇帖子（2013–2026，含 z3 三位核心开发者的亲自回答）声称 z3 有"返回随机满足赋值"的 API 或开关。开发者给所有此类请求的答案都是：`smt.random_seed`/`sat.random_seed`（扰动搜索）、`phase_selection=5|10`/`sat.phase=random`（随机相位）、必要时 `smt.arith.random_initial_value`（LIA simplex 随机初值），或者"到求解器外部去扰动公式"（#7595 提问者的原话选项，Bjørner 的代码最终也是外部循环）。
2. **random_seed 的社区定位是"可复现"，不是"采样"。** 高票回答（alias）原话："random seed is used to make sure the result becomes predictable, not to get uniformly distributed solutions"（JohanC 评论）；"Sampling is an entirely different (and much more difficult) problem"。
3. **"随机"能否出现取决于约束形态与求解路径。** Wintersteiger 的官方解释（约束被预处理直接解掉/变量没进分支搜索 → 随机相位无效）与 Bjørner 追加 `sat.phase=random` 才解决 224.0.0.0 恒定问题，共同印证：只有变量真正出现在约束里、且 SAT 相位被随机化时值才散开；**未约束变量/model completion 的值是确定的默认值**（SO 24327987 提问者观察 + z3 文档 `model.completion` 默认 false）——与本项目 z3 4.16 实测（自由变量或仅作 UF 参数的 BitVec 在任何 seed/相位下恒 0）一致。
4. **均匀/随机采样被一致视为求解器之外的独立算法领域。** UniGen/AlmostAll（哈希+近似计数）、SPUR（SAT 均匀采样）、CMSGen（"uniform-like"、明确"no formal guarantees"）、SMTSampler（种子解 + Hamming 随机游走）全部是外部框架反复调用求解器，从不声称求解器自身能出随机模型。
5. **"python z3 solver 能求出随机数"的说法在社区语境下的最接近对应物**是 6.1 的 Bjørner 片段或 6.4 的 blocking 循环：即 (b) 显式随机相位 + (c) 外部循环/换 seed 重建求解器，且变量必须出现在约束中。脱离这三个条件（比如变量完全自由），社区没有任何帖子报告过非零/随机取值——这与我们的实测相吻合。
