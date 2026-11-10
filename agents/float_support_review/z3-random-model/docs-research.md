# Z3 随机模型能力调研（docs-research）

- 议题目录：`agents/float_support_review/z3-random-model/`
- 日期：2026-09-28（网络来源检索 + 本机只读实验）
- 背景：本项目 Rust 求解器经 z3-sys 0.5.0 逐 case 取满足模型，自由 BitVec 变量（vl、浮点载荷）总取 0。用户主张"python 的 z3 solver 就能求出满足约束的随机数"。本报告查清 Z3 随机模型能力边界与推荐做法。
- 方法：官方 Z3Guide 参数页 + 本机 z3 CLI 参数表实测（z3 4.16.0，`z3 -pd`；系统 libz3 4.13.3 见 §5）+ Stack Overflow（含 Z3 开发者 Wintersteiger 的回答）+ GitHub（Z3 issues、prove-rs/z3.rs tag）+ crates.io API + 论文/工具页。

## TL;DR

1. **Z3 没有任何"返回随机满足赋值 / uniform sampling"的原生 API 或选项**。`random_seed` 系列参数只随机化搜索启发式（相位选择、随机分支、restart），不构成采样接口；官方开发者的建议就是 blocking（取模型后加否定约束）再查。
2. 本机实测：**完全无约束的 BitVec 变量在任何 seed、任何 phase 策略下都恒取 0**（预处理还会把未约束子项直接消除）；只有"已被约束"的变量才随相位/seed 变化。isla 场景 vl/浮点载荷是自由变量 → 恒 0 是 Z3 的确定性模型构造行为，与 python/rust 绑定无关。
3. 用户在 python 看到"随机数"的最合理解释：其脚本对**有约束的变量**设置了随机相位（`smt.phase_selection=5` 或 `sat.phase=random`）且每次喂了不同 `random_seed`（或约束本身迫使非零）；同 seed 必同模型——是"换伪随机轨迹"而非采样。
4. 推荐做法排序：① blocking 枚举（官方推荐）；② `auto_config=false` + 随机相位 + 变 seed 复跑（便宜、无分布保证）；③ 哈希式近均匀采样工具（UniGen2/SPUR 等，CNF 接口，需 bit-blast 桥接）；④ 直接施加引导性约束（如最低位=1、vl>0），对工程场景最直接。

---

## 1. Z3 官方文档中模型多样化/随机相关参数及语义

权威来源：官方 [Z3Guide Parameters 页](https://microsoft.github.io/z3guide/programming/Parameters)（在线参数总表）与本机 z3 4.16.0 CLI 的 `z3 -pd` 输出（两者个别项有版本差异，已标注）。

### 1.1 参数表

| 参数 | 类型/默认 | 语义 | 出处 |
| --- | --- | --- | --- |
| `auto_config`（全局） | bool / true | 用启发式自动选 solver 并配置。**关掉它，phase/seed 类参数才能按你设的生效**（SO 实证见 §3） | Z3Guide Global；`z3 -pd` |
| `tactic.randomizer.seed` | uint / 0 | randomizer 预处理器的随机种子 | `z3 -pd` tactic 模块 |
| `sat.phase` | symbol / caching | SAT 相位选择策略：`always_false`、`always_true`、`basic_caching`、`random`、`caching`（4.16 另有 `local_search`）。**直接决定布尔/BV 位偏置（偏 0、偏 1 或随机）** | `z3 -pd`；Z3Guide sat |
| `sat.phase.sticky` | bool / true | 粘性相位缓存 | Z3Guide sat |
| `sat.random_freq` | double / 0.01 | 随机 case split 的频率（搜索中以 1% 概率随机分支） | Z3Guide sat |
| `sat.random_seed` | uint / 0 | SAT 求解器随机种子。**浮点（fpa2bv→SAT）与 bit-blast 后的 BV 走这条线** | Z3Guide sat |
| `smt.random_seed` | uint / 0 | SMT 内核随机种子 | Z3Guide smt |
| `smt.phase_selection` | uint 0–7 / 3 | SMT 内核相位启发式：0=always false，1=always true，2/3/4=相位缓存变体，**5=random**，6=出现次数，7=theory。旧内核等价物，现代路径多数场景已由 `sat.phase` 接管 | Z3Guide smt |
| `smt.phase_caching_on/off` | uint / 400/100 | 相位缓存开/关的冲突数周期 | Z3Guide smt |
| `smt.arith.random_initial_value` | bool / false | 线性算术 simplex 初始值取随机值（想让 Int/Real 模型值变化需开它；实测仍常按顺序吐值，见 §3） | Z3Guide smt |
| `smt.elim_unconstrained` | bool / true | 预处理直接**消除未约束子项**——这是自由变量根本不进搜索、恒取默认值 0 的机理之一 | Z3Guide smt |
| `nlsat.seed` | uint / 0 | 非线性求解器随机种子 | Z3Guide nlsat |
| `nlsat.randomize` | bool / true | nlsat 中见证点的选取随机化 | Z3Guide nlsat |
| `nlsat.shuffle_vars` | bool / false | 随机变量序 | Z3Guide nlsat |
| `sls.*`（`sls.random_seed`、`random_offset`、`walksat`、`wp`、`restart_init`、`vns_mc` 等） | — | QF_BV 随机局部搜索求解器（`sls-qfbv` tactic / `smt.sls.enable=true`），随机性最强，可给出差异大的 BV 模型，但启发式、无分布保证 | Z3Guide sls 模块 |
| `fp.spacer.random_seed` | uint / 0 | CHC/Spacer 内部 SMT 求解器随机种子 | Z3Guide fp 模块 |
| `model.completion` | bool / false | **模型补全**：给模型中无解释的符号补一个解释（默认值）。语义是"补默认值（BV 为 0）"，与随机化无关 | `z3 -pd` model 模块 |
| `model_evaluator.completion` | bool / false | 求值表达式时对模型外符号补解释 | `z3 -pd` |

### 1.2 版本注意：`sat.phase_stochastic` 已不存在

- z3 4.16.0 CLI 实测 `z3 -in sat.phase_stochastic=true` → `ERROR: unknown parameter 'phase_stochastic' at module 'sat'`；系统 libz3 4.13.3 的字符串表中也没有 `phase_stochastic`，但有 `phase selection strategy: always_false, always_true, basic_caching, random, caching, local_search`。
- 即旧资料（4.8 时代文档/SO 帖）里的 `sat.phase_stochastic`（bool）已被 `sat.phase`（symbol，取 `random`）取代；旧 SMT 内核等价物是 `smt.phase_selection=5`（Z3Guide smt 有明确记载）。
- 另外：4.16 的 `z3 -pd` 已不打印 smt/nlsat 模块段，但 `smt.random_seed`、`nlsat.seed` 仍被接受（传错类型会报 "Expected values for parameter random_seed is an unsigned integer"，实测）。

## 2. Z3/z3py 是否存在"返回随机满足赋值/uniform sampling"的原生 API 或选项？

**结论：No。**

- 官方参数总表（Z3Guide + `z3 -pd`）中不存在任何 "model.random / sampling / uniform" 类参数；`random_seed` 族只影响搜索轨迹（phase、case split、restart），模型值是搜索副产物，无分布保证。
- Z3 开发者（微软研究院，Z3 主要维护者之一）[Christoph Wintersteiger 在 SO "Using Z3 to sample from a constrained space"](https://stackoverflow.com/questions/39220169/using-z3-to-sample-from-a-constrained-space) 的原话："Z3 can give you a model, i.e., one example… You can then assert the negation of the model to force the solver to produce a different assignment… **Z3 models will not be distributed randomly across the search space**"。即官方口径：要多样化解就 blocking，Z3 不做随机采样。
- 另一帖 [SO 24330928](https://stackoverflow.com/questions/24330928/z3py-randomized-results-phase-selection-not-random)：de Moura 曾示范过用 `phase_selection=5`"随机化模型值"，但 Wintersteiger 指出这只是搜索启发式的副作用，且"case is simply too simple"（预处理直接解掉，随机相位根本不起作用）——并非受支持的采样功能。
- 社区要求 uniform sampling 的讨论均指向外部工具（XORSample'/UniGen 系），见 §4。

## 3. 用户在 python 里观察到"随机数"的最可能解释

### 3.1 本机可复现实验（z3 4.16.0 CLI，命令见附录 A）

| 实验 | 结果 |
| --- | --- |
| 无约束 `x:BV64`，默认 | `#x0000000000000000` |
| 无约束 `x:BV64`，`sat.random_seed=42` | 仍为 0 |
| 无约束 `x:BV64`，`sat.phase=always_true` | **仍为 0**（自由变量的值来自模型构造/预处理消除，相位影响不到它） |
| 约束 `bvuge x 5`，默认 / seed=42 | `x=5`（两者相同——小公式换 seed 不改变模型） |
| 约束 `bvuge x 5`，`sat.phase=always_true` | `x=0xfffffffffffffffb`（**有约束时相位直接改值**） |
| FP32 约束 `fp.gt x 1.0`，默认连跑 5 次 | 5 次全为 `(fp #b0 #x7f #b00000000000000000000001)`（比 1.0 大的最小数，完全确定） |
| 同上，`sat.random_seed=1..5` | 5 次全同 |
| 同上，`smt.random_seed=1..5` | 5 次全同 |
| 同上，`sat.phase=random` + `sat.random_seed=1..5` | **5 个互不相同的值**（指数/尾数都变） |
| 同上，`sat.phase=always_true` | `(fp #b0 #xfe #b11111111111111111111111)`（接近 +inf 的最大有限数） |

### 3.2 解释排序（按可能性）

1. **随机相位 + 变 seed 的组合生效**。社区标准 z3py 写法是 `set_option('auto_config',False)`、`set_option('smt.phase_selection',5)`（或 `sat.phase=random`）、`set_option('smt.random_seed', n)`，见 [SO 60033071](https://stackoverflow.com/questions/60033071/z3py-give-random-solution-using-seed) 与 [SO 24330928](https://stackoverflow.com/questions/24330928/z3py-randomized-results-phase-selection-not-random)。Wintersteiger 在 24330928 的回答还点明两个坑：太简单的公式被预处理器直接解掉、随机相位根本不触发，需要 `(push)` 强制走增量求解器才能得到随 seed 变化的模型；且 `auto_config=false` 是前提。若用户脚本满足这些条件且每次喂了不同 seed（常见 `random.randint` 喂进去），且变量**带有约束**（如 `x > 1.0`、`x != 0`），就能观察到"随机数"。这是最合理机制——本机实验证实只有 phase 随机化 + 变 seed 才改变模型值。
2. **约束形态差异**。用户 python 实验里的浮点变量多半不是完全自由的（比较/范围约束使 0 或极小值不可取）；isla 场景 vl、浮点载荷是完全自由变量，Z3 对其补默认值 0（`smt.elim_unconstrained=true` 甚至在预处理就消除它们），seed/phase 都影响不到（实验第一组三行）。**差异在约束，不在语言绑定。**
3. **确定性而非随机**。Z3 固定 seed 时完全确定（同 seed 同模型，实验第一组、FP 默认组）。跨进程"每次不一样"要么是脚本喂了不同 seed，要么是 Z3 在量词/不可判定片段下的真非确定性（[Z3 issue #7525 "Nondeterministic behavior observed despite seed set"](https://github.com/Z3Prover/z3/issues/7525)、[issue #1821 "Making Z3 deterministic (using random seed)"](https://github.com/Z3Prover/z3/issues/1821) 记录了 seed 之外的残余非确定来源）。
4. **子系统 seed 各管一段**。纯浮点问题经 fpa2bv 位爆破进 SAT，控制它的是 `sat.random_seed`/`sat.phase`，不是全局 `random_seed` 也不是 `smt.random_seed`（[SO 76031510 "How do I make z3 float solution not random"](https://stackoverflow.com/questions/76031510/how-do-i-make-z3-float-solution-not-random)；工具侧佐证：[Apalache 文档](https://apalache-mc.org/)把自己的 seed 同时映射到 `sat.random_seed` 与 `smt.random_seed`）。
5. 反例佐证：算术理论即使开 `smt.arith.random_initial_value=True + phase_selection=5 + blocking`，`Int a>0` 依旧按 1,2,3,4… 顺序吐（[SO 60033071](https://stackoverflow.com/questions/60033071/z3py-give-random-solution-using-seed)）——理论求解器的模型值往往就是系统性补全值，并非随机。

## 4. 社区推荐做法与 uniform sampling 工具

### 4.1 多样化模型的推荐做法（按工程优先级）

1. **Blocking 枚举**（官方开发者推荐）：取到模型后加 `x != v`（或整个相关赋值的否定），再 `check`。出处：[SO 39220169（Wintersteiger）](https://stackoverflow.com/questions/39220169/using-z3-to-sample-from-a-constrained-space)；亦可配 `check-sat-assuming` 对候选特征做假设性试探。缺点：模型分布强偏、枚举空间大时慢。
2. **随机化相位 + 变 seed 复跑**：`auto_config=false`；`sat.phase=random`（4.13+）/ `smt.phase_selection=5`（旧内核路径）；`sat.random_seed` 与 `smt.random_seed` 同设；FP/BV 场景建议同设 `sat.random_seed`；简单公式需 `(push)` 走增量求解器才触发随机相位（SO 24330928 实测）。便宜、跨 run 可复现（记录 seed），但**无均匀性保证**。出处：SO 24330928/60033071；Ochs et al., SPLC 2024（"Consistency Is Key"）即用 `smt.random_seed` + `smt.phase_selection=5` + `sat.phase=random` 做配置多样化。QF_BV 可再试 `sls-qfbv` tactic（随机局部搜索，模型差异更大）。
3. **引导性约束**（工程上最直接）：不追求随机，直接对关心的变量加定向约束（如 `vl > 0`、载荷最低位=1、`fp.isNormal`），或用 `Optimize` 软目标。对"vl/浮点载荷恒 0"的痛点，这是见效最快的一条。
4. **XOR 哈希式近均匀采样**（真要分布保证时）：对公式加随机 XOR/parity 约束把解空间切 cell 再取模型（思想源头 [Gomes/Sabharwal/Selman, NIPS 2006, XORSample'](https://www.cs.cornell.edu/~sabhar/publications/xorSamplingNIPS06.pdf)），Z3 可以承载这些 XOR 约束（BV 约束直接写），但工程上一般直接用下述工具。

### 4.2 uniform sampling 专用工具（一句话 + 能否接 Z3）

| 工具 | 一句话 | 与 Z3 的关系 |
| --- | --- | --- |
| UniGen2 | Chakraborty/Meel/Vardi 的 3-wise 独立哈希近均匀（almost-uniform）CNF 解采样器，JACM 系工作 | 输入 CNF/DIMACS；Z3 公式需先 bit-blast 成 CNF 再接（间接可接；同族后续为 UniGen3/WAPS/CMSGen，见 [Meel 组页面](https://meelgroup.github.io/)） |
| AlmostAll | **未检索到以此命名的工具**（GitHub/arXiv/论文检索均无）；疑指 XORSample' 一类 "almost-uniform" 技术或 UniGen 前身（UniWit）。建议向提出者确认所指 | — |
| DMC | Lagniez/Marquis/Szczepanski（[IJCAI 2018](https://www.ijcai.org/proceedings/2018/185)）基于 D4 的分布式 CNF 精确模型计数器（配套采样用） | CNF 接口；与 Z3 需 bit-blast 桥接 |
| BIRD | Dutra et al.（AAAI 2019）高效 CNF-XOR SAT 求解器，是 ApproxMC 类哈希式计数/采样管线的引擎 | CNF-XOR 接口（非 SMT）；间接 |
| SPUR | [ZaydH/spur](https://github.com/ZaydH/spur)（SAT 2018），基于 sharp# 精确计数的**完美均匀**采样器 | CNF 输入；间接 |
| SMT 侧现成方案 | SMTSampler（Berkeley，测试/验证用 SMT 解采样）、JFSampler（浮点公式专用）、CSB（[STP 扩展](https://arxiv.org/abs/2607.04142)：bit-blast 后接 CNF 计数/采样器）、PanSampler、SMT(LIA) sampling | 多以 Z3/STP 为底层或同类 SMT 前端；JFSampler 对 FP 公式与本场景最贴近 |

## 5. z3-sys 0.5.0 链接的 Z3 上游版本

- **crate 本体不 vendor 任何 Z3 源码**：[crates.io API](https://crates.io/api/v1/crates/z3-sys/0.5.0) 显示 z3-sys 0.5.0 发布于 2019-08-29，`features` 为空、无依赖、crate 仅约 53KB、无 build.rs（本机 cargo registry 解包核实）——纯 bindgen FFI 绑定，靠 `links="z3"` 链接系统 libz3。`z3-src`/`static-link-z3` 的源码 vendoring 是该 crate 0.6/0.7 之后（2022 起）才引入的机制，因此"vendor 源码 tag"对 0.5.0 **不存在**。
- 仓库侧佐证：[prove-rs/z3.rs 在 tag `z3-sys-v0.5.0` 的文件树](https://github.com/prove-rs/z3.rs/tree/z3-sys-v0.5.0)只有 `z3-sys/`、`z3/`、`.gitignore`、`.travis.yml`、`Cargo.toml`、`README.md`——无 z3 源码子模块。
- 绑定面对应的 API 代际为 Z3 4.8.x（2019 年，彼时上游最新 4.8.7/4.8.8 前后）。
- **本项目实际链接的版本由环境决定**：
  - 本仓库 `Dockerfile`：`FROM ocaml/opam` + `apt-get install z3 libz3-dev` → Debian 仓库的 z3；
  - 本机实测：`pkg-config --modversion z3` = **4.13.3.0**（Ubuntu `libz3-4 4.13.3-1build1`）→ Rust 构建在开发机上实际链接 **libz3 4.13.3**；
  - PATH 中的 z3 CLI 是 homebrew 的 **4.16.0**，与 Rust 链接的系统 libz3 是两套安装，CLI 实验仅用于验证行为趋势。
- **参数差异对结论的影响**：4.8.x 时代存在 `sat.phase_stochastic`（bool）；4.13+ 已删除（4.13.3 字符串表无此项、4.16 CLI 报 unknown parameter），由 `sat.phase=random` 取代；`smt.random_seed`/`nlsat.seed` 在 4.16 仍有效但不再出现在 `-pd` 输出。因此：若在 Rust 侧做随机化，应写 `sat.phase=random`（写旧参数名会在 4.13/4.16 报 unknown parameter）；本报告的核心结论（无原生采样 API、自由变量恒补 0、blocking 为官方推荐）在 4.8/4.13/4.16 一致。

## 来源链接表

| # | 来源 | 用途 |
| --- | --- | --- |
| 1 | https://microsoft.github.io/z3guide/programming/Parameters | 官方参数总表（sat/smt/nlsat/sls/fp 全表） |
| 2 | 本机 `z3 -pd`（z3 4.16.0 CLI）与传参实测 | 参数表对照、unknown parameter 验证 |
| 3 | https://stackoverflow.com/questions/39220169/using-z3-to-sample-from-a-constrained-space | Wintersteiger：blocking 建议、"Z3 models will not be distributed randomly" |
| 4 | https://stackoverflow.com/questions/24330928/z3py-randomized-results-phase-selection-not-random | 随机相位在 z3py 的行为边界（auto_config=false、push、预处理吃掉小公式） |
| 5 | https://stackoverflow.com/questions/60033071/z3py-give-random-solution-using-seed | z3py 随机化组合写法；Int 顺序吐值反例 |
| 6 | https://stackoverflow.com/questions/76031510/how-do-i-make-z3-float-solution-not-random | FP→SAT 路径受 sat.random_seed 控制而非 smt.random_seed |
| 7 | https://github.com/Z3Prover/z3/issues/1821 | random_seed 与确定性讨论 |
| 8 | https://github.com/Z3Prover/z3/issues/7525 | 设 seed 后仍非确定的场景 |
| 9 | https://www.cs.cornell.edu/~sabhar/publications/xorSamplingNIPS06.pdf | XORSample'：XOR 约束近均匀采样思想源头 |
| 10 | https://meelgroup.github.io/ （及 UniGen/UniGen2/WAPS/CMSGen/Barbarik 文档线索） | 哈希式采样工具族 |
| 11 | https://www.ijcai.org/proceedings/2018/185 | DMC：分布式 CNF 模型计数 |
| 12 | https://github.com/ZaydH/spur | SPUR：完美均匀采样器 |
| 13 | https://arxiv.org/abs/2607.04142 | CSB：STP 上的 BV 计数/采样（bit-blast→CNF 工具链范例） |
| 14 | https://crates.io/api/v1/crates/z3-sys/0.5.0 | z3-sys 0.5.0 发布时间/features/体积 |
| 15 | https://github.com/prove-rs/z3.rs/tree/z3-sys-v0.5.0 | tag 处文件树：无 vendored z3 |
| 16 | 本仓库 `Dockerfile`、`isla/isla-lib/Cargo.toml`（z3-sys="0.5.0"）、`pkg-config`/`dpkg` 实测 | 实际链接 libz3 4.13.3 |
| 17 | https://apalache-mc.org/（Fine-Tuning 文档） | 工具把 seed 映射到 sat.random_seed + smt.random_seed 的旁证 |

## 附录 A：本机验证命令（z3 4.16.0 CLI，只读，可复现）

```sh
# 参数表
z3 -pd
# 已废弃参数
echo "(check-sat)" | z3 -in sat.phase_stochastic=true   # ERROR: unknown parameter
# 自由 BV 恒为 0（换 seed / 相位都一样）
echo "(declare-const x (_ BitVec 64))(check-sat)(get-model)" | z3 -in
echo "(declare-const x (_ BitVec 64))(check-sat)(get-model)" | z3 -in sat.random_seed=42
echo "(declare-const x (_ BitVec 64))(check-sat)(get-model)" | z3 -in sat.phase=always_true
# 有约束 BV：默认/seed 相同、相位改值
echo "(declare-const x (_ BitVec 64))(assert (bvuge x #x0000000000000005))(check-sat)(get-model)" | z3 -in
echo "(declare-const x (_ BitVec 64))(assert (bvuge x #x0000000000000005))(check-sat)(get-model)" | z3 -in sat.phase=always_true
# FP32 x>1.0：默认/单换 seed 全同；phase=random + 变 seed 才产生不同模型
echo "(declare-const x (_ FloatingPoint 8 24))(assert (fp.gt x ((_ to_fp 8 24) (_ bv1065353216 32))))(check-sat)(get-value (x))" | z3 -in
for s in 1 2 3 4 5; do echo "(declare-const x (_ FloatingPoint 8 24))(assert (fp.gt x ((_ to_fp 8 24) (_ bv1065353216 32))))(check-sat)(get-value (x))" | z3 -in sat.phase=random sat.random_seed=$s; done
# 系统链接库版本
pkg-config --modversion z3   # 4.13.3.0
```

## 未决/待确认

- "AlmostAll" 工具名未能检索到对应实物（§4.2），需向提出者确认是否指 XORSample'/UniGen 前身一类 almost-uniform 方法。
- 4.8.x 时代 `sat.phase_stochastic` 的官方参数原文未能取到原始文档（raw.githubusercontent.com 网络受限）；已用"4.13.3/4.16 中不存在 + z3guide 记载 `smt.phase_selection=5=random`"从侧面确认其已被取代，如需原文可在网络恢复后查 z3 4.8.x 源码 `src/sat/sat_params.cppgt.cpp`。
