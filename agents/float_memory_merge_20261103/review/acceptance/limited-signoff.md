# float→memory 限定联合验收签收

**本轮合流在下列已测范围可签收，无未关闭的新增实现阻断。** 受签组件为 Isla `4d085b14aa0f987436b86d72f41fab1df9e9a132`、模型 `bf861b3e687894480aec701a886a38d4e50b8a99`；正式程序 SHA-256 为 `3e44cdd6db67f88f94bc894b5b9c6f1de94b7deeb9eb3d9379c49bec1bafbd3e`。本结论不是原域全部通过、全域无退化证明或 F1 修复签收。

本 reviewer 独立读取实际源码、提交、命令、日志、JSON、模型文件和 ELF 字节，未以 owner 状态表代替证据。父仓最终提交、metadata、gitlink 及发布回读仍须按最终暂存树和提交另封；本报告先签组件与联合验证范围。

## 已签范围

| 项目 | 实际证据与结果 |
| --- | --- |
| 模型和五 IR | 普通 strict 与四配置 SYMBOLIC 均退出 0；166 个模型文件同时匹配提交 blob 与工作树，149 个工具文件、配置及五安装 IR 哈希相符。[生成来源](generation-binding-independent.json) |
| 正式构建 | 1042 源文件匹配 clean 最终提交；真实二进制依赖指纹含 trace 与 SMT interrupt；官方 Z3 版本、库 SHA、ELF RUNPATH 相符。独立短探针真实调用 `Z3_interrupt`。[构建来源](build-binding-4d085b14-independent.json) |
| Rust 和永久 IR | 默认单库 394、workspace lib 610、workspace tests 665 全通过，零忽略和过滤；五 IR 共 26 步；104 负变异全部拒绝，独立重跑也全部拒绝。[回归](final-4d08-regressions-independent.json)、[独立负控](final-4d08-negative104-independent.json) |
| 新 315 | 从实际机器字和前态调用独立 SoftFloat，315/315 数值及 flags 相符；重建全部约束 IR，核 6566 初值、30870 保持字段、实际来源、seed17 和全 partial 计数。[数值](final-4d08-315-numerical-independent.json)、[来源](final-4d08-315-binding-independent.json) |
| 新 300 | 五 IR 各 60 组，独立按 old/incoming/pre-state 复算 fcsr、FS、SD 和其他位，300/300 相符。callback 顺序仅为静态 IR 合同。[状态](final-4d08-300-state-independent.json) |
| SchemaUnion | 9 个浮点/整数/原子/压缩访存 JSON 的 GPR/FPR/fcsr、完整前后态、事件和前后内存、原机器字及三表示均保留。按实际机器字和事件顺序复算相符。[并集](final-4d08-union-independent.json) |
| 原子提取和续执行 | 核心独审的真实 collector 正负控证明同最终 Model 提取、必需值失败整例拒绝；写前未观测初值的 null 与查询失败分开处理。最终真实 C_ADDI4SPN `0x1fe0` 在 x2=7 时续执行得到 x8=1027、Retire、finished；seed17 新复跑来源匹配。[核心审查](../core-final-report.md)、[ExecuteAs](final-4d08-executeas-independent.json) |
| nat 适配 | VFMERGE/VLSEG 对 vstart=0/1/2/全1 共 8 例复算通过；direct init_masked_source 的 mask 为 1/0/0/0，共 4 例。非活动保持、vstart 清零及内存事件相符；不改变 reduction 的非零 vstart 非法约定。[指令](final-4d08-nat-independent.json)、[helper](final-4d08-masked-helper-independent.json) |
| 真实 Make 和汇编 | 定向 FLEQ_S/LOAD_FP/STORE/C_LD 共 27 JSON finished；实际 run.mk、生产 tactic、双 7200 秒预算及 seed17 来源相符，wrapper 只附加固定机器字和前态。独立读取 GCC/Clang 生成 ELF `.text`：混合 54 项、定向 Make 162 项逐字节相符。[Make](final-4d08-directed-make-independent.json)、[54 项](final-4d08-assembly-independent.json)、[162 项](final-4d08-directed-make-assembly-independent.json) |

315、nat 和 Make 的对应双预算按各自实际命令记录；额外固定 ExecuteAs 正确性补例用 120 秒限时，不冒充完整域预算验收。旧 v1/v2/7cce 结果保留原身份，最终数值与混合项均在最终新程序上重新运行。

## 原域与继承边界

最终程序 `3e44cdd6` 的真实原域 Make 已独立核命令、seed、哈希和全部 267 个 gen 的 schema/三表示/事件重放。结果如下，三个访存项均不记 PASS。[原域账本](final-4d08-full-make-independent.json)、[JSON 独审](final-4d08-full-make-schema-independent.json)。

| Clause | exit | gen | status | errors | unfinished | assertion-filtered |
| --- | --- | --- | --- | --- | --- | --- |
| FLEQ_S | 0 | 48 | finished | 0 | 0 | 0 |
| LOAD_FP | 2 | 0 | partial | 4 | 0 | 1 |
| STORE | 2 | 130 | partial | 922 | 112 | 1 |
| C_LD | 0 | 89 | partial | 0 | 7 | 0 |

LOAD_FP 在同配置 bdd 基线也实际 partial/gen0。STORE/C_LD 的主 Poison 在 bdd 原域在途日志中已发生；完整基线对照尚未结束，仍保持原预算，**全域无退化未证**。[在途发生事实](baseline-partial-observed-snapshot.json)不是完整退出结果。

对 STORE 回环 Poison、STORE 主执行 Poison、C_LD 主执行 Poison 三个代表，旧/新诊断 runtime 与各自 IR 已在同输入复放：P3 的 183 项门寄存器逐项相同，含 145 项已初始化与 38 项未初始化，各只有一个 callback，均为 SAT Poison、相同 zicfilp Hypervisor unsupported 异常；主执行保留原 Ctor 和 102 项前态，均复现相同保留 privilege 异常。它们支持所测代表的继承分类，**不能外推全部 922/112/7 路径**。[v4 STORE 主代表](partial-replay-independent.json)、[v5 P3/C_LD](partial-replay-v5-independent.json)、[核心分类](../core/partial-boundary/report.md)。

bdd 在无 symbolic CSR 时使用原始 ctx.regs 做门，回环错误还会只记录日志后丢弃；合流按最终 Model 状态检查并记错符合用户的 failclosed 合同。不能用旧 errors=0 与新 errors=922 的差值直接宣称新回归，也不能据此宣称全部旧路径已经分类。[源码边界](p3-source-boundary-independent.json)。

**F1 具体/符号内存后端不一致仍在。** 同配置、同机器字、同址 `0x80000000`，bdd 和最终候选均固定地址读 0、自由符号地址可读全1或0。本轮只确认继承，未修复该缺陷。[F1 复证](final-4d08-f1-inheritance-independent.json)。

float 的全 77 预算边界、OPEN 冻结项、未钉控制状态的辅助译码范围、未测全控制流覆盖及未做硬件重放均保持。未纳入旧外树 F1–F5 补丁，不扩通用配置或 OPEN 策略研究。

## 提交与原工作区

Isla 的 `7cce7834` 双亲为原 memory `bdd047bc` 与 float `591693df`；最终 `4d085b14` 是其测试兼容后继，四文件生产前缀逐字相同。模型 `bf861b3e` 双亲为 memory `c70482a7` 与 float `0f7b8fbc`。原六输入 HEAD、diff 与 memory 两 dirty 文件再次核对保持。[原输入复核](inputs-preserved-before-final.json)。

在上述限制准确保留、父仓 gitlink/metadata 指向实际组件、组件可从正式远端获取的前提下，可继续完成本轮父仓合流提交与发布；没有要求扩修既有全域缺陷才能交付本轮限定合流。
