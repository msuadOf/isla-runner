# isarch 探索结果缓存：计划与架构（2026-11-10，v2）

v1 草案经 Codex 审核（task-mw9lhw6l），本版按其中的“必须改”五项和部分“建议改”修订。

## 目标

isarch 做完一次 path merge 符号执行后，把常驻内存里的探索结果写成缓存文件。下次运行读回缓存，经过简单重建，得到与原来**逐字段相同**的常驻路径，直接进入 corpus 认证、变异和 judge，不必重新探索。

用户要求（2026-11-10）：
- 缓存首选 JSON 等可读格式，便于阅读和核对；同一份内容另出一份二进制版，可以选用它来节省空间。
- 读回后简单重建，就能 replay 成原来的样子。
- isla 代码保持通用，不针对 sail-riscv 做专门处理。

## 已核实的事实

以下来自 Codex 两轮只读调查（task-mw9l4wuf、task-mw9lhw6l）：

1. **快照点**：探索时每条完成路径在 `src/isarch/exec.rs:1877` 保存 `ResidentPath`，时间早于样本检查和合并枚举。campaign 只用到这几样：
   - `ResidentPath` 的四个字段；
   - 每条路径的 `FastFacts`；
   - Target 的 `pre_state()` 原始值；
   - `symbolic_pma_sizes()` 记录的名字到 `Sym` 的映射。
   
   Session、当前 `SharedState` 和 Target 配置照常初始化，跳过探索时也不能跳过它们。类目录在 corpus 认证之后才建立。Z3 指针和闭包都不在快照范围内。
2. **现有 DAG 不能代替快照**：它丢了原始 `Exp` 树、非 SMT 事件、`next_var`、分段结构、完整访存事件、`memory_guards` 的结构、完整 `RegionMergeRecord` 以及 `MixedBits`。DAG 可以从快照派生出来。
3. **序列化现状**：
   - 核心类型大多没有 serde。`Name`、`SourceLoc`、`B64`、`B129` 已有，可以直接当叶类型复用。
   - 依赖里有 `bincode 1.3.3`，不支持 `deserialize_any`。所以 DTO 里不能放 `serde_json::Value`，也不能用内部标签、无标签枚举或省略字段。
   - 依赖里没有压缩 crate。
4. **重放**：`Solver::replay` 按父链重放 SMT 事件，`from_checkpoint` 再恢复 `next_var`。`from_checkpoint` 用的是时间种子；`new_seeded` 目前是 `pub(crate)`。
5. **`Name` 编号会进入 SMT 常量**，例如构造子判别式（`primop_util.rs:316`）。enum 成员的序号同样有含义。
6. `RegionMergeRecord.arm` 只有 `root` / `then` / `else` 三种值。`Event` 的 `region` 是 `&'static str`，没有通用的有限集合。
7. 启动时要做约 `N × (T+2)` 次 checkpoint 重放，缓存不会减少这一项。缓存省掉的是探索、DAG 导出和 FastFacts 分析。
8. 现有 campaign 在固定 ChaCha 种子下，`-T 1` 和 `-T 32` 跑 300 例结果逐字节相同（`fuzz-step4.md:38`）。源码里变异器先固定好自由输入，再借用模型值，时间种子主要影响求解过程本身。

## 架构

### 1. 一个 DTO 模型，两种编码

- 在 isla-lib 新建通用模块 `isla-lib/src/executor/path_cache/`。它覆盖事件、smtlib 的 `Def`/`Exp`/`Ty`、`Val`、`BitsSegment`、`SamplePath`、`RegionMergeRecord`、`GuardedRegisterRead`、`RegionPoint`、`DefAttrs`、`ReadOpts`/`WriteOpts` 等全部变体。已有 serde 的叶类型直接复用。核心类型的私有字段由各自所在模块提供受控的转换函数，不为此把字段整体改成公开。
- 枚举一律用 serde 的外部标签，字段不省略，整数宽度、位串长度和集合顺序都固定。
- 同一份 DTO 编成两种格式：
  - JSON：可读，也是权威版本；
  - bincode：二进制，省空间。
  
  两者解码出来的 DTO 必须完全相同。第一期不做压缩。
- 供人阅读的视图继续用现有 DAG，DAG 由快照派生。

### 2. 文件布局与发布

```
<cache>/
  manifest.json   # 总是 JSON；最后写，写完即“发布”
  segments.json | segments.bin   # trace 分段：id、父段 id、checkpoint 计数、段内事件
  paths.json    | paths.bin      # 每路径：signature、num、next_var、叶段 id、SamplePath、records、FastFacts
```

- **原子发布**：先写好数据文件，最后写 `manifest.json`。manifest 记录每个数据文件的编码、条目数和本批次 id。读的时候发现缺文件、条目数不对、批次 id 混用，都直接 panic。
- **trace 分段去重**：按实际共享的 `Arc` 节点分段，父段写一次，读回时重建同样的共享结构。空段也保留。段 id 和 `Sym` 编号是两套独立的编号空间。
- **manifest 内容**：
  - schema 版本、位宽 `B`；
  - 来源记录：IR、配置和二进制的 sha256，clause，isarch 参数；
  - 探索完整性：complete 或 partial，以及错误汇总；
  - 路径清单；
  - Target 运行期数据：前态原始值、PMA 符号绑定；
  - 名字环境，见下一节。

### 3. 名字环境核对（不做编号重定位）

manifest 保存生产者的这几样：
- 完整原始符号表，即编号到字符串的映射，直接取原始表内容，不经过 `to_str()`，否则越界时会得到 `zUNKNOWN`；
- `mangled_names` 反混淆映射；
- 完整的有序 enum 表：类型编号、成员数，以及每个位置上的成员编号和名字；
- 源文件表。

读回时核对：
- 生产者的每个编号 `i`，在当前表里都必须存在，而且原始字符串完全一致；当前表允许在后面追加新编号。
- 反混淆映射在生产者涉及的范围内一致。
- 每个 enum 的有序成员表完全一致：`DefineEnum` 的 size 对得上，所有 `EnumMember.member` 都在范围内，当前 `enum_members` 反向表也一致。
- 源文件的每个索引指向同一路径。

任何一项不一致就 panic，报出第一处差异。

这一层保证旧 SMT 常量里的名字编号仍然指同一个名字。**它不保证当前 IR 里这个名字对应的函数实现没有变**，这一点见第 6 节。

### 4. `&'static str`

- `arm` 在 DTO 里用三值枚举，恢复成核心类型时映射回三个静态字面量。第一期不改核心字段。
- `region` 放进进程级去重表：在锁内完成“查询—分配—插入”，只有第一次出现时才 leak。累计占用约等于所有不同名字的字节数加上索引；重复加载同样的名字不会增加分配。

### 5. isarch 接入

- `--path-cache-write <dir>`，可配合 `--path-cache-format json|bin|both`（默认 both）：探索完成后写缓存，之后照常继续。
- `--path-cache-read <dir>`，可配合 `--path-cache-encoding json|bin`（默认 json）：跳过探索，从缓存重建 `ResidentPath`、`FastFacts` 和 Target 运行期数据，再进入原有的 fuzz 流程。两种编码都存在时，可以加 `--path-cache-crosscheck`，把两份都解码出来比对 DTO 是否相同。
- **classifier 改造**：允许直接传入恢复出来的 FastFacts，并且分别控制“重新导出 DAG”和“重新计算事实”两件事。从缓存读取时默认两件都不做，可以用参数单独打开，作为核对手段。
- 通用的值、表达式、事件和 checkpoint 重建放在 isla-lib。场景、Target、corpus 和 CLI 适配放在 isarch 的 `src/isarch/path_cache.rs`。

### 6. 与当前 IR 的语义一致性（独立里程碑，本期不做）

缓存上跑 judge，只能证明缓存内部是自洽的。审核确认目前没有现成的入口能做“corpus → 全具体单路径 → 完整后态”，原因有三：
- `pre_memory` 是稀疏的，首次访问是写时初值为 `None`；
- 具体前态不能和同名的符号 CSR 混用；
- 寄存器全部给定具体值，也不保证只走一条路径。

所以独立复核单独列为后续里程碑，预估 3 到 5 个工作日：基于 `execute_ir_function_with_checkpoint_and_limits` 从全新上下文执行，比对所有可满足的完成结果，未知初值要如实报告。在它做出来之前：
- 缓存的 manifest 和输出 provenance 里标注“未做当前 IR 复核”；
- 来源记录和当前 IR 不一致时打印 warning；
- 需要当前 IR 语义保证时，重新探索并跑 `--check-samples`。

### 7. 结构检查（损坏即 panic，不用哈希）

- schema 和位宽一致；
- 父链无环，段数与 `num` 一致，空段计数正确；
- 定义引用的 `Sym` 已经由 `DeclareConst`、`DefineConst` 等声明过，函数引用由 `DeclareFun` 声明，两类分开检查；
- `next_var` 大于所有已用的 `Sym`；
- records 的 id 唯一，父引用存在，arm 合法，条件符号和访存索引可解析（不要求 id 小于 `records.len()`）；
- manifest 的路径清单、signature 与 paths 文件一致；
- Target 的符号绑定都指向已声明的 `Sym`。

## 实施拆分（TDD，逐步验收）

| 步 | 内容 | 验收 |
| --- | --- | --- |
| 1 | 叶类型与名字环境 | 先写测试：编号不一致、enum 换序、源文件和反混淆映射不一致，都必须 panic；然后实现双编码 |
| 2 | 完整事件与共享 trace | 所有 `Event`/`Exp`/`Def`/`Val` 变体往返；空段、共享节点、父链错误；不依赖 campaign |
| 3 | 路径与 records | 完整字段、`memory_guards`、record 全局编号、FastFacts 往返；从恢复结果重新导出 DAG |
| 4 | isarch 接入 | 写 both，读两种编码，恢复 Target 数据，跳过探索和事实分析；残缺目录和混合批次被拒绝 |
| 5 | 闭环与效果 | 见下面的“验收与效果数据” |

另外加一个**合成 IR 通用性测试**：不含任何 RISC-V 名字，覆盖 enum、构造子、函数应用和全部事件类型。

## 验收与效果数据

1. **单测**：上面第 1–4 步的 TDD 测试全部通过，`cargo fmt` 通过，已有测试不回退。
2. **集成**：用 Sv39 generic STORE 场景，按 `isla/agents/path_merge_call_support/fuzz-isarch-loop-smoke.md` 重建；再加一个整数 clause RTYPE。
   - A：不用缓存跑两次，比较完整的 corpus 认证结果、`judged`、`mutants`。现有设计下这些应该是确定的。若出现差异，先定位到具体字段和自由度，不要直接改成只比部分字段。
   - B：写缓存（both）；C：读 JSON；D：读 bin。
   - C 和 D 要做到：重建出的 DTO 与 B 完全相同；从恢复结果重新导出的 DAG 与 B 逐字节相同；FastFacts、path-index、corpus 认证、`judged`、`mutants` 都与 B 相同。
3. **效果数据**：
   - 探索耗时；
   - 缓存写出耗时；
   - JSON 解析和 bin 解析的耗时，与 Z3 重放耗时分开记录；
   - 从开始读缓存到 campaign 开始的总耗时，和不用缓存时对比；
   - JSON 和 bin 的文件大小，路径数，段去重率。

## 范围外

压缩、跨 IR 的编号重定位、第 6 节的独立复核、执行帧续跑（`Memory` 闭包）、Python 工具。

## 实施位置与资源

- Isla 工作树 `.worktree/isla-path-cache-20261110`，分支 `feat/isarch-path-cache`，基于 `a38c5e02`。
- IR 只读复用 `.worktree/pathmerge-all-20261110/isla/rv64d.ir`，由 cbb4766f 生成。
- 同机正在跑全量实测，最多 2 个 isarch，每个 `-T 32`。本任务的 isarch 一次只跑一个，`-T 32`；cargo 编译用 `-j 16`。
