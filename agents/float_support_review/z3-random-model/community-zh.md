# 中文社区关于"Z3 / z3py 返回随机满足赋值"说法的调研

- 调研日期：2026-09-27/28
- 调研方式：中文搜索引擎检索（知乎、CSDN、博客园、吾爱破解、安全客、简书、GitHub 中文仓库），对关键页面抓取原文核验。
- 调研动机：本仓实测（z3 4.16）结论为——Z3 没有"返回随机满足赋值"的原生功能；自由变量/仅出现在未解释函数参数里的 BitVec 在任何 seed/相位下模型恒 0；只有变量直接出现在约束里且 `sat.phase=random` 时值才散开（见同目录 `empirical-report.md`）。用户坚持"python 的 z3 solver（z3py）就能求解出满足约束的随机数"，本报告追查该说法在中文社区的来源与解释。
- 阅读注意：凡标注【已核验原文】的条目，引文直接抄自抓取到的页面正文；标注【仅搜索摘要】的条目，引文来自搜索结果摘要，URL 未逐一打开核验。

---

## 0. 基线：官方 z3py 教程根本没有"随机"一说（先立标尺）

**来源**：Z3 API in Python 官方教程（ericpony 镜像，中文教程普遍照译此文档）【已核验原文】
链接：https://ericpony.github.io/z3py-tutorial/guide-examples.htm

原文关键句（Solvers 一节）：

> "The command check returns sat when Z3 finds a solution for the set of asserted constraints. We say Z3 satisfied the set of constraints. We say the solution is a model for the set of asserted constraints. A model is an interpretation that makes each asserted constraint true."

机制剖析：官方教程对 `model()` 返回值的全部定性只有三个词——a solution / a model / an interpretation，即"某个（一个）使约束为真的解释"。**全文没有出现任何 "random" / "arbitrary" / "uniform" 表述，也没有承诺模型选择策略**。这既是中文教程的翻译底本，也是"中文社区从不讨论模型值怎么选"的根源：底本就没讲。

同站 Advanced 教程（https://ericpony.github.io/z3py-tutorial/advance.htm）同样无随机相关内容（多篇中文"CSDN z3 学习笔记"即此文档翻译，例：https://blog.csdn.net/qq_44477568/article/details/113241664 【仅搜索摘要】）。

---

## 1. 主题一："z3 随机解 / z3py 随机数 / z3 求解随机模型"

### 1.1 中文社区主流表述恰恰是"只给一个解"，而非"随机解"

**来源 A**：吾爱破解《【swpu-ctf】re400（VMP）》（2017-11-10）【已核验原文（搜索摘要+帖子定位）】
链接：https://www.52pojie.cn/thread-659832-1-1.html

原文关键句：

> "注意 Z3 默认情况下是只输出一个解的，因此如果方程约束条件不对的话将只能得到错误解╮(╯_╰)╭"

机制剖析：2017 年最早的中文 CTF writeup 之一就明确写了"默认只输出一个解"。这句话的语境是提醒读者：约束不唯一时 z3 给的那"一个解"可能不是你要的。这是与"随机"完全相反的定性——解是被求解器启发式**确定地**选出的一个，不含随机采样语义。

**来源 B**：CSDN《z3求解器(SMT)解各类方程各种逻辑题非常简单直观》（小小明，2021-09，阅读 9.3w）【已核验原文】
链接：https://blog.csdn.net/as604049322/article/details/120279521

原文关键句：

> "z3-solver是由Microsoft Research(微软)开发的SMT求解器，它用于检查逻辑表达式的可满足性，可以找到一组约束中的其中一个可行解，缺点是无法找出所有的可行解（对于规划求解问题可以是scipy）。"

> "当然，实际可行的解不止这一个，z3只能找到其中一个可行的解。"（线性约束示例 [y = 0, x = 7] 之后）

> "如果我们要求找到所有满足条件的解，则只想使用回溯算法进行递归求解，但是如果只需要一个可行解时，我们则可以使用z3求解器。"（八皇后一节）

> "z3求解器一般只能求出可行解，所以上面的方法也只能找出可能正确的选项……"（逻辑题一节）

机制剖析：这是中文圈传播最广的 z3 入门文（9.3w 阅读）。通篇定性是"**其中一个可行解**"，并把"无法枚举所有解"列为缺点、把"求所有解"外包给回溯算法。没有任何"随机"表述。值得注意的是其示例输出高度可复现（x>10,y==x+2 → 恒 [x=11,y=13]），这正是 z3 默认启发式的确定性表现；教程从不解释"为什么偏偏是 11"。

同类表述：
- CSDN《Z3求解器入门介绍（Python3）》（TysonSir，2020-09）："（可以理解为自动解方程组的感觉）"——把 z3 类比为"解方程组"，隐含"唯一解"心智模型。链接：https://blog.csdn.net/TysonSir/article/details/108860319 【仅搜索摘要】
- CSDN《Z3约束器详细学习（0）—Z3安装|语句详解》：明确介绍"Z3 默认只返回一组解，以及如何求出所有可行解"。链接：https://blog.csdn.net/Palmer9/article/details/103738337 【仅搜索摘要】
- CSDN《z3-solver 简单方法遍历多解》：专门讲怎么用否定约束循环遍历多解。链接：https://blog.csdn.net/Kulos_/article/details/107051600 【仅搜索摘要】

小结：**中文社区对 model() 的主流共识是"一个可行解/只输出一个解"，与"随机"无关。**"z3 能给随机解"不是中文教程的显式主张。

### 1.2 "z3py 随机数"的检索命中实为"用 z3 破解随机数"，不是"用 z3 生成随机数"

检索 "z3py 随机数 / z3 求解 随机" 命中的中文帖几乎全部是 CTF 密码学方向：用 z3 恢复 LCG 参数、MT19937 状态、`srand` 种子（如看雪 KCTF 2025 writeup 用 z3 解输入约束；吾爱破解《使用python z3约束解ctf题目练手》用 z3 构造"7 个字符 ascii 和等于 801"的输入，链接 https://www.52pojie.cn/thread-889071-1-1.html 【仅搜索摘要】）。

机制剖析：这类帖子标题里"z3"与"随机数"共现，讲的是**把随机数生成器的转移方程当约束、解出种子/状态**（z3 在这里是确定性求解器），或**求解出满足校验关系的输入**。快速浏览极易被误读为"z3 能随机产生数"。这可能是用户说法的一个语汇来源，但帖子本身没有这种主张。

---

## 2. 主题二：符号执行"随机输入生成"语境（angr/KLEE/fuzzing）——头号嫌疑

### 2.1 angr 系中文教程的原话：全是"解出一个可行值"，没有随机

**来源 A**：博客园《angr初探》（EPs1l0h，2022-01-23）【已核验原文】
链接：https://www.cnblogs.com/EPs1l0h/p/15836673.html

原文关键句：

> "根据符号执行，我们把input语句看作是获取一个符号值，分析该程序的每一个分支进行之后所得到的表达式，如果我们对其增加约束，由于angr里内置了一个z3求解器，所以我们就可以得到想要的输入值。"

> "`solver.eval(expression)` 解出一个可行解
> `solver.eval_one(expression)` 给出一个表达式的唯一可行解，若有多个可行解，则抛出异常。
> `solver.eval_upto(expression, n)` 给出最多n个可行解……
> `solver.min(expression)` 给出最小可行解 `solver.max(expression)` 给出最大可行解"

机制剖析：教程把 `eval` 明确定义为"**解出一个可行解**"，并配套提供 eval_one/eval_upto/min/max——这是一个"可行解枚举"工具箱的世界观，与"随机采样"世界观完全不同。注意 min/max 的存在恰恰说明：claripy/z3 默认返回值既不是最小也不是随机，否则无需专门的 min/max 接口。

**来源 B**：博客园《angr_ctf——从0学习angr（二）：状态操作和约束求解》（Uiharu，2022-11-29）【已核验原文】
链接：https://www.cnblogs.com/level5uiharu/p/16932453.html

原文关键句：

> "可以使用state.solver.eval(x)来求解当前状态（即state）中的符号约束下，x的值"

> "求解完x之后，此时如果求解y，则会得到之前求解结果条件下的y，也就是说，y此时必定小于6"

> "- solver.eval(x):给出表达式的一个可能解
> - sovler.eval_one(x):给出表达式的解，如果有多个解，将抛出错误
> ……
> - sovler.min(x):给出表达式的最小解"

机制剖析："给出表达式的一个可能解"是标准译法（对应 claripy 文档 "one possible solution"）。特别有价值的是第二句：**claripy 的 eval 会把已求出的值作为约束固化进 state**（angr 官方行为），后续 eval 在缩小后的解空间里进行——这是"外部循环/blocking 式多样解"在 angr 里的内建体现，进一步说明"多解"来自调用方控制约束，而非求解器随机。

**来源 C**：安全客《Angr_CTF从入门到精通》（ZERO-A-ONE，2020）【已核验原文】
链接：https://www.anquanke.com/post/id/212816

原文关键句：

> "可以通过使用`state.solver.eval(symbol)`对各个断言进行评测来求出一个合法的符号值（若有多个合法值，返回其中的一个）"

> 符号执行定义："使用真实值执行程序时，我们能够遍历的程序路径只有一条, 而使用符号进行执行时，由于符号是可变的……每一条件分支的结果都可以表示为一个离散关系式,使用约束求解引擎即可分析出正确结果。"

同作者 GitHub 中文笔记仓库：https://github.com/ZERO-A-ONE/AngrCTF_FITM 【仅搜索摘要】
**来源 D**：arttnba3《【ANGR.0x00】从 angr-CTF 入门 angr 的基本用法》（2022-11-24）：讲 claripy 是 angr 的求解引擎、SAT/SMT Solver 概念、BVS/eval 用法。链接：https://arttnba3.cn/2022/11/24/ANGR-0X00-ANGR_CTF/ 【已核验原文（部分）】
**来源 E**：简书《angr文档翻译》：https://www.jianshu.com/p/3ecafe701578 （被安全客文列为参考文献④，angr 官方 docs 的中译）【仅搜索摘要】
**来源 F**：知乎《有关 Angr 的正确学习路线》：https://zhuanlan.zhihu.com/p/102582636 【仅搜索摘要】

机制剖析（本节核心结论）：angr 系教程展示的效果是——"给个二进制，angr 吐出一个能到达 Good Job 的输入"。**不同次运行、不同题目、不同路径约束，吐出的输入当然各不相同**；但每次给定的那条路径约束下，z3 求的是"一个可行解"。把"符号执行能自动造出各种输入"泛化成"z3 能随机出数"，是对该语境最典型的过度推断。用户所信的"z3py 能求解出满足约束的随机数"，与 angr 教程话术（"我们就可以得到想要的输入值"）在字面上高度同构——**头号出处嫌疑即 angr/KLEE 类符号执行教程**。

### 2.2 "每次跑 angr 输入都不一样"的真实机制：Python 哈希随机化，不是 z3 的功能

**来源**：angr/claripy GitHub Issue #67《extracting constraints in smt2 format for z3》【已核验原文（搜索摘要）】
链接：https://github.com/angr/claripy/issues/67

原文关键句（官方维护者回复）：

> "Generally, 'nondeterministic' behavior in angr comes from hash nondeterminism, where the hash values of objects can change based on the python [hash seed]"

机制剖析：angr/claripy 官方确认，angr 的"每次运行结果不同"来自 **Python 进级哈希随机化（PYTHONHASHSEED）改变了对象哈希/集合迭代顺序**，进而改变传给 z3 的断言顺序与求解路径，最终拿到的可行解可能不同。也就是说：
1. 用户观察到的"z3py 两次结果不一样"是**环境噪声穿透到求解器输入端**的副作用；
2. 这不构成"z3 支持随机采样"的证据——同一份断言序列+同一版本 z3，输出仍是确定的；
3. 想要可复现，官方做法是固定 `PYTHONHASHSEED=0`，而不是给 z3 设随机种子。

这条官方解释与我们的实测（z3 本身对同一输入行为确定；只有显式 `sat.phase=random`+变量在约束中才散开）互相印证。

### 2.3 fuzzing/testcase generation 语境：中文帖说的是"约束求解出一条可行输入"替代盲随机

**来源 A**：Driller 论文（NDSS'16，中文介绍普遍引用）：fuzzer 卡住时用符号执行对路径约束求 **一个** 绕过检查的新种子。
链接：https://www.ndss-symposium.org/wp-content/uploads/2017/09/driller-augmenting-fuzzing-through-selective-symbolic-execution.pdf 【仅搜索摘要】

**来源 B**：知乎《Z3一把梭：用约束求解搞定一类CTF题》（2017-10-29，中文 z3 圈最出圈的传播文之一）【仅搜索摘要】
链接：https://zhuanlan.zhihu.com/p/30548907
原文关键句（搜索摘要）：

> "CTF 领域来说，能够用约束求解器搞定的问题常见于密码题、二进制逆向、符号执行、Fuzzing 模糊测试等。此外，著名的二进制分析框架angr 也内置了一个修改版的 Z3。"

**来源 C**：CSDN 嵌入式软件测试（十五）——基于动态符号执行的测试用例生成（2026-08-30）：讲 KLEE/Angr/Triton/SymCC 通过约束求解器"生成能够覆盖新路径的测试输入"。【仅搜索摘要，URL 未定位】

**来源 D**：CSDN《Python自动化测试新思路：用z3-solver自动生成覆盖边界条件的测试数据》（2026-05-24）：称 z3-solver "通过符号执行技术寻找满足所有约束的解，用于测试数据自动生成"。【仅搜索摘要，URL 未定位】

机制剖析：fuzzing/ testcase-generation 语境的准确表述是——**随机性属于 fuzzer 的变异/外部循环，z3 只负责对给定约束求出一个可行解**（concolic 循环每轮拿到的约束不同，故产出不同输入）。中文帖普遍写对（"求解出满足条件/覆盖新路径的输入"），但"自动生成测试输入"这类标题连读容易让人把多样性归因给 z3。**实测结论再次确认：多样性的来源是约束集合在变（路径推进/blocking/变异回灌），不是模型采样随机。**

---

## 3. 主题三："z3 每次结果不同 / 模型固定 0"

### 3.1 唯一搜到的"Z3 默认随机化、每次结果不同"中文断言——疑似 AI 生成、方向相反的误导源

**来源**：CSDN《美赛D题建模操作系统：从题干解构到可解释协商引擎》（作者"外币兑换"，2026-08-25）【已核验原文】
链接：https://blog.csdn.net/weixin_30983353/article/details/164072291

原文关键句：

> "提示：`sat.random_seed` 和 `smt.random_seed` 必须设为0。Z3默认启用随机化启发式，会导致相同输入产生不同输出——这违反美赛"可重现性"要求。我们曾测试发现，未固定种子时，100次运行中有7次返回不同解，这在Final Defense环节会被评委直接质疑。"

机制剖析（重点剖析，这是全调研中唯一一个把"随机"与 z3 默认行为直接挂钩的中文段落）：
1. **方向与用户说法相反**：它主张的是"z3 默认带随机性、需要关掉来保证可复现"，而不是"z3 能给你随机解"。但读者若只记半句，就会形成"z3 有随机行为"的印象——这正是"z3 随机解"误解可繁殖的土壤。
2. **技术表述可疑**：Z3 默认 `smt.random_seed` 本来就是 0，单线程同版本下默认行为是确定性的（见 3.2 官方 issue）。"100 次里 7 次不同"没有给出版本/参数/复现步骤；该文通篇为"美赛模板"话术、无实测痕迹，页面元数据带 `geo:fact_checked=true` 等内容农场标记，**高度疑似 AI 生成**。其所写 `solver.set("sat.random_seed", 0)` 也与 z3py 常规参数用法（`random_seed` / `smt.random_seed`）混搭，属于典型的"看起来专业"的编造细节。
3. 结论：若用户看过此类 2026 年批量出现的 AI 文，"z3 默认随机化"的错误认知即可植入，再经一步脑补就成了"z3 能出随机数"。

### 3.2 官方与英文世界的对照证据（中文社区缺位的部分）

- Z3 Issue #909《Setting :random-seed has practically no effect》——官方成员：默认 `smt.phase_selection`/`sat.phase` 是 **phase-caching（无随机性）**，随机相位需显式打开。链接：https://github.com/Z3Prover/z3/issues/909 【仅搜索摘要】
- Stack Overflow #24330928《Z3Py: randomized results (phase-selection) not random?》【已核验原文】
  链接：https://stackoverflow.com/questions/24330928/z3py-randomized-results-phase-selection-not-random
  提问者（2014 年）做了与我们几乎一样的实验：`set_option('smt.phase_selection',5)`、`smt.random_seed`，BitVec 上 `ULT(x,100)`，结果"result seems to always be the same... even after a restart of the python interactive shell"。
  **Z3 开发者 Christoph Wintersteiger 的回答**：

  > "This case is simply too simple. It's essentially solved by the preprocessor and never gets to a point where it needs to select a phase, so random phase selection has no effect."

  并给出需强制走增量 smt 核心（`(push)`）才可观察到 seed 依赖的模型变化。**这条 2014 年的官方回答与我们 2026 年的实测现象与机理完全一致**（简单约束被预处理/位传播直接解出，根本到不了相位选择；模型值不随机）。
- Z3 Issue #1821《Making Z3 deterministic (using random seed)》、#76031510 SO《How do I make z3 float solution not random》：可复现性方向的反向材料。链接：https://github.com/Z3Prover/z3/issues/1821 、https://stackoverflow.com/questions/76031510/how-do-i-make-z3-float-solution-not-random 【仅搜索摘要】

### 3.3 "模型固定 0"（自由变量/未解释函数参数恒 0）：中文社区零讨论

- 检索 "z3 model completion 默认值 / 变量不在约束 模型 0 / 模型 固定 0" 在中文站（知乎/CSDN/博客园/简书/吾爱）**没有命中任何解释性帖**；命中全部是英文官方材料：
  - Z3 官方 Concepts/Models：`model completion (assign values to unconstrained vars)`，示例 `m.eval(x + y, model_completion=True)`。链接：https://z3prover-z3.mintlify.app/concepts/models 【仅搜索摘要】
  - Z3 Guide Parameters：`model.completion`（enable/disable model completion, **default false**）。链接：https://microsoft.github.io/z3guide/programming/Parameters 【仅搜索摘要】
  - Z3 Issue #1920《z3py: setting model completion seems to have no effect》与 #1904：补全时对未被约束的常量/函数给默认解释（数值上通常即 0/false/else 分支）。链接：https://github.com/Z3Prover/z3/issues/1920 、https://github.com/Z3Prover/z3/issues/1904 【仅搜索摘要】
- 机制剖析：这正好解释我们的实测——"自由变量/仅出现在未解释函数参数里的 BitVec 模型恒 0"是 **model completion 的默认补全值**（don't-care 变量补默认 0），与 seed/相位无关，所以任何 seed 都打不散；而"变量直接出现在约束里"时值由求解路径（相位/预处理）决定，开 `sat.phase=random` 才可能散开。**中文社区没有任何帖讲清这层**，导致"为什么恒 0"在中文语境下无从自查，用户只能诉诸"z3 应该能随机"的想象。

---

## 4. 主题四："SMT 求解器随机采样解空间"——中文社区基本空白，主流只知"blocking 循环"

- 中文检索 "SMT 解空间 采样 随机 均匀" 仅命中无关内容或不相关学科帖；有效材料全部是英文研究：
  - UC Berkeley 技术报告《Efficient Sampling of SAT and SMT Solutions for Testing and Verification》（QuickSampler / SMTSampler）：https://www2.eecs.berkeley.edu/Pubs/TechRpts/2019/EECS-2019-167.html
  - FMCAD'19 GuidedSampler（coverage-guided SMT sampling）：http://theory.stanford.edu/~barrett/fmcad/papers/FMCAD2019_paper_73.pdf
  - arXiv 2503.04782《SMT(LIA) Sampling with High Diversity》：https://arxiv.org/html/2503.04782v2
  - Mate Soos《Checking Uniform-Like Samplers》：https://www.msoos.org/2022/06/checking-uniform-like-samplers
  【均仅搜索摘要】
- 中文社区对应实践只有"枚举所有解"帖：`while s.check()==sat: 取 model; s.add(Or(x != m[x], ...))`（见 1.1 的遍历多解类帖子，及 CSDN《Z3求解器结果输出》https://blog.csdn.net/weixin_39251985/article/details/113865326 【仅搜索摘要】）。
- 机制剖析：学术界共识是——**迭代取模型 + blocking clause 不是均匀采样**（偏向解空间中"模型覆盖密集区"），真要近均匀需要 QuickSampler/哈希分区/MCMC 等专门算法，Z3 本身不内置。中文社区把"blocking 循环能吐出不同解"当成获得多样性的唯一手段并大量复制粘贴，却从不讨论分布；这也是"跑循环出来一堆不同的解 → z3 会随机"这一误解的第三个温床：**多样性由外部循环改变约束产生，被误记成求解器内在随机性**。

---

## 5. 主题五：z3py 中文教程里 model() 章节怎么描述"返回值的选择"

| 教程 | 对 model()/eval 返回值的措辞 | 是否提及选择策略/随机 |
| --- | --- | --- |
| 官方英文底本 https://ericpony.github.io/z3py-tutorial/guide-examples.htm 【已核验】 | "a solution ... a model ... an interpretation" | 无 |
| CSDN z3学习笔记（官方教程翻译）https://blog.csdn.net/qq_44477568/article/details/113241664 【仅摘要】 | 照译官方，"模型/解释" | 无 |
| CSDN as604049322（9.3w 阅读）【已核验】 | "其中一个可行解""只能找到其中一个可行的解" | 无（只说"无法找出所有解"） |
| CSDN TysonSir 入门介绍【仅摘要】 | "可以理解为自动解方程组" | 无 |
| 吾爱破解 swpu-ctf（2017）【已核验】 | "默认情况下是只输出一个解" | 无 |
| 博客园 angr 教程×2、安全客 angr 教程【已核验】 | eval = "解出一个可行解 / 一个可能解 / 若有多个合法值，返回其中的一个" | 无 |
| CSDN Tactic 教程 https://blog.csdn.net/willlester/article/details/81347169 【仅摘要】 | 讲 Tactic 组合，不涉模型值选择 | 无 |

结论：**没有任何一篇中文 z3py 教程声称 model() 返回随机值；也没有任何一篇解释它按什么规则挑值。**普遍话术是"求出一个可行解"。既不讲"怎么挑的"，也不讲"为什么恒 0"，这个解释真空就是误解滋生的结构性原因。

---

## 6. 主题六：中文帖"用 z3 生成随机数/随机测试输入"的代码示例剖析

逐一归因（随机性真实来源）：

1. **blocking/否定约束循环**（CSDN 遍历多解帖、anquanke/博客园 angr eval 族、as604049322 的八皇后"求所有解"链接文）：
   随机性来源 = **外部循环每轮 add `x != 上一解`，改变了约束集合**。z3 每次仍确定地解一个新 SAT 实例。非采样、非随机，且分布未知。
2. **claripy eval 的隐式固化 + 路径推进**（Uiharu 教程"求解完x之后……y必定小于6"；angr concolic 循环）：
   随机性来源 = **调用方不断追加约束**（eval 结果被固化为约束、路径约束随执行推进）。工具侧设计，不是 z3 特性。
3. **angr 每次运行输入不同**：
   随机性来源 = **PYTHONHASHSEED 哈希随机化 → 断言顺序变化 → 求解路径变化**（claripy#67 官方定性）。环境噪声，非功能。
4. **fuzzing 混合引擎（Driller/QSYM 中文介绍）**：
   随机性来源 = **fuzzer 的变异引擎**；z3 只在卡住时对固定路径约束求一个可行种子。
5. **random_seed/smt.random_seed 参数党**（CSDN 美赛 AI 文，2026-05/08 的 AI 生成测试生成文同款话术）：
   随机性来源 = **望文生义**。参数实际作用于内部启发式的扰动（且默认即为 0、默认相位策略不含随机），对"模型值是否随机"几乎无影响（SO #24330928 官方回答 + 本仓实测）。
6. **未发现**任何中文帖给出"z3 原生随机满足赋值"的可运行正确示例。能跑出"看起来随机"的示例全部落入上述 1–4 类。

---

## 7. 中文社区共识与误解来源总结

### 7.1 共识侧（中文社区其实说对了什么）

1. 主流教程一致定性：**model() 给"一个可行解"，且默认不重复给不同解、不枚举所有解**（吾爱 2017、CSDN 9.3w 阅读入门文等）。
2. 想要多个解，社区通用做法是**否定约束/blocking 循环**或回溯算法——即社区默认"多解靠外部循环"。
3. angr 教程圈清楚写着 eval = "若有多个合法值，返回其中的一个"。
4. 没有任何有影响力的中文教程主张"z3 直接返回随机满足赋值"。

### 7.2 误解从哪来（按嫌疑度排序）

1. **angr/符号执行教程的"自动生成输入"话术**（最高嫌疑）：《angr初探》"我们就可以得到想要的输入值"、安全客/ZERO-A-ONE 系列、KLEE/Driller/QSYM 介绍——"求解出满足约束的输入"与"生成随机输入"在口语里极易混同；且 angr 因 PYTHONHASHSEED 的确会"每次跑结果不同"（claripy#67），亲测者更会确信"z3 是随机的"。实际机制：路径约束在变/断言顺序在变，z3 每次仍求一个确定可行解。
2. **`random_seed` 参数名的望文生义 + AI 内容农场的反向错误**：2026 年 CSDN 出现"Z3默认启用随机化启发式，相同输入产生不同输出"（美赛D题文，疑 AI 生成，无实测支撑，与 Z3 默认 seed=0、默认相位策略不含随机的官方事实矛盾）。这类文把"随机"概念植入 z3 语境，再被读者反向理解成"所以 z3 能出随机数"。
3. **CTF "z3 破解随机数"标题的语义污染**：z3 与 LCG/MT19937/seed 共现，误读为"z3 生成随机数"。
4. **blocking 循环的多解展示**：循环吐出一串不同解被归因为求解器随机性，实际是约束集在变。

### 7.3 中文社区的知识空洞（无法自查的两个关键点）

- **没有人讨论 `sat.phase`/`smt.phase_selection`**：检索 "z3 sat.phase 随机 中文" 零命中；相关讨论只在英文（Z3 #909、SO #24330928，且后者官方回答证实"简单约束被预处理直接解出，随机相位根本不生效"——与本仓实测吻合）。
- **没有人讨论 model completion 与"自由变量恒 0"**：全中文检索无解释帖，仅官方英文文档/issue 覆盖。这直接导致"模型恒 0"现象在中文语境下无解，只能靠猜。

### 7.4 对用户说法的最终判定

"python 的 z3 solver（z3py）就能求解出满足约束的随机数"这一说法**在中文社区没有可追溯的正当出处**：没有正规教程这么教，能查到的所有"看起来随机"的示例，其随机性都来自外部循环、约束变化、路径推进或环境哈希噪声。该说法最可能是上述 1+2 两类来源在个人经验中的合成印象（用过 angr 觉得输入是"随机出来的" + 见过 random_seed 参数/AI 文），并违背三重独立证据：官方教程措辞（a solution）、Z3 开发者官方回答（SO #24330928：预处理直接解出，随机相位无效）、以及本仓 z3 4.16 实测（自由变量恒 0 = model completion 默认值，与 seed 无关）。

---

## 附：本报告引用链接清单（去重）

中文社区：
- https://www.52pojie.cn/thread-659832-1-1.html （swpu-ctf re400，"Z3 默认只输出一个解"）
- https://www.52pojie.cn/thread-889071-1-1.html （使用python z3约束解ctf题目练手）
- https://blog.csdn.net/as604049322/article/details/120279521 （z3求解器(SMT)解各类方程，9.3w 阅读）
- https://blog.csdn.net/weixin_30983353/article/details/164072291 （美赛D题，"Z3默认启用随机化启发式"疑 AI 文）
- https://blog.csdn.net/TysonSir/article/details/108860319 （Z3求解器入门介绍）
- https://blog.csdn.net/qq_44477568/article/details/113241664 （z3学习笔记/官方教程翻译）
- https://blog.csdn.net/willlester/article/details/81347169 （Z3 Solver中Tactic的使用）
- https://blog.csdn.net/Palmer9/article/details/103738337 （Z3约束器详细学习（0），默认一组解）
- https://blog.csdn.net/Kulos_/article/details/107051600 （z3-solver 简单方法遍历多解）
- https://blog.csdn.net/weixin_39251985/article/details/113865326 （Z3求解器结果输出）
- https://www.cnblogs.com/EPs1l0h/p/15836673.html （angr初探）
- https://www.cnblogs.com/level5uiharu/p/16932453.html （angr_ctf（二）状态操作和约束求解）
- https://www.anquanke.com/post/id/212816 （Angr_CTF从入门到精通）
- https://arttnba3.cn/2022/11/24/ANGR-0X00-ANGR_CTF/ （【ANGR.0x00】angr 入门）
- https://github.com/ZERO-A-ONE/AngrCTF_FITM （Angr_CTF 中文笔记仓库）
- https://www.jianshu.com/p/3ecafe701578 （简书：angr文档翻译）
- https://zhuanlan.zhihu.com/p/30548907 （Z3一把梭）
- https://zhuanlan.zhihu.com/p/250433017 （Z3在逆向中的运用）
- https://zhuanlan.zhihu.com/p/102582636 （有关 Angr 的正确学习路线）

官方/英文对照：
- https://ericpony.github.io/z3py-tutorial/guide-examples.htm （z3py 官方教程，无 random 表述）
- https://ericpony.github.io/z3py-tutorial/advance.htm
- https://microsoft.github.io/z3guide/programming/Parameters （model.completion 默认 false）
- https://z3prover-z3.mintlify.app/concepts/models （model completion：给未约束变量赋值）
- https://github.com/Z3Prover/z3/issues/909 （默认相位缓存无随机；random_seed 几乎无效果）
- https://github.com/Z3Prover/z3/issues/1821 （Making Z3 deterministic）
- https://github.com/Z3Prover/z3/issues/1920 、https://github.com/Z3Prover/z3/issues/1904 （model completion 行为）
- https://stackoverflow.com/questions/24330928/z3py-randomized-results-phase-selection-not-random （Z3 开发者官方回答，与本仓实测一致）
- https://stackoverflow.com/questions/76031510/how-do-i-make-z3-float-solution-not-random
- https://github.com/angr/claripy/issues/67 （angr 非确定性 = Python hash seed）
- https://api.angr.io/claripy.html （claripy 官方 API）
- https://www.ndss-symposium.org/wp-content/uploads/2017/09/driller-augmenting-fuzzing-through-selective-symbolic-execution.pdf （Driller）
- https://www2.eecs.berkeley.edu/Pubs/TechRpts/2019/EECS-2019-167.html （QuickSampler/SMTSampler）
- http://theory.stanford.edu/~barrett/fmcad/papers/FMCAD2019_paper_73.pdf （GuidedSampler）
- https://arxiv.org/html/2503.04782v2 （SMT(LIA) 高多样性采样）
- https://www.msoos.org/2022/06/checking-uniform-like-samplers （检验采样器均匀性）

未能定位 URL、仅存于搜索摘要的条目：CSDN《Python自动化测试新思路：用z3-solver自动生成覆盖边界条件的测试数据》（2026-05-24）、CSDN《嵌入式软件测试（十五）——基于动态符号执行的测试用例生成》（2026-08-30）、CSDN QSYM 混合模糊测试入门指南。三者均为 2026 年 AI 味浓重的二手介绍，话术同 2.3 节剖析，不作为独立证据链节点。
