# 合流动态验收索引

受测模型 `bf861b3e`，Isla `4d085b14`，正式 Release SHA-256 `3e44cdd6db67f88f94bc894b5b9c6f1de94b7deeb9eb3d9379c49bec1bafbd3e`，RV64 VLEN128 IR SHA-256 `40f34f706963afcca7dfbf8504ee888bdd004cd0c437712f097b7dda64a705c9`。正式输入为候选目录 `agents/float_memory_merge_20261103/validation/build/inputs-4d085b14.json`（SHA-256 `30f6847f904ea22b8c7dd355cda988bf35bc9938ec46e7b564c408801365d5e2`），逐文件源码清单在该输入内。以下结论均限实际所列输入；先前作废的批次见 [aborted-v1.json](aborted-v1.json)。

| 验收项 | 新批次与实际结果 | 边界 |
| --- | --- | --- |
| SoftFloat 异常 | [315汇总](runs/final315-4d08/summary.json)：315/315，实际新 IR/Release；固定 oracle 见 `expected-315.json` | 定向约束 IR，每例最终 JSON 与完整 summary；不替代完整 Clause 原域。 |
| flags 状态 | [300结果](runs/final300-4d08/flags-300/result.json)：五 IR 各60/60，共300/300 | 直接 Rust helper；callback 顺序只按 IR 静态合同核。 |
| SchemaUnion 混合访存 | [九组输出](runs/final-union-4d08/union/launch.json)：FLD/FSD/FLW/FSW、LD/SD/AMO、C_LD/C_SD，各退出0、finished、一个真实 gen；[三表示](runs/final-assembly-4d08/assembly/result.json) 54/54 | 定向配置由正式 FD 与 memory 两配置叠加，RAM缩至4KiB；显式 Machine/mstatus 前态。GCC/Clang 对三种表示逐机器字核对。 |
| nat 两调用 | [指令边界](runs/final-vstart-4d08/vstart/summary.json)：VFMERGE、VLSEGTYPE 的 vstart=0/1/2/全1，各 finished/gen1/Retire，8/8；[直接 helper](runs/final-mask-4d08/masked-source/result.json)：`init_masked_source` 返回 Ok(mask) 四边界 4/4 | VFMERGE 用已见证合法机器字；VLSEGTYPE 只证明它自己的 `init_masked_source` 调用。helper 的 `%i,%i,%bv -> Ok(mask)` 是模型函数合同，不是完整指令。 |
| ExecuteAs | [固定机器字/seed17新探针](probes/executeas-fixedword/result.json)：C_ADDI4SPN `0x1fe0`，初态x2=7，末态x8=1027，Retire，summary.finished/无partial；另有[原回归](runs/executeas-4d08/checks.json) | 同一Release/IR上的定向程序入口；最终 Model 的collector单测另由core独审核。 |
| 真实 Make 定向 | [四入口](runs/directed-make-4d08/make/)：FLEQ_S、LOAD_FP、STORE、C_LD 均退出0、finished、partial计数0、有 gen；保留 run.mk 原 recipe/策略，验收目录 wrapper 只在正式 isarch 前注入固定机器字和 Machine/mstatus 前态 | 每目标 `result.json` 保存原 make 命令、实际 wrapper argv 和二进制/IR/config 哈希。属于定向入口，不称原域完整通过。 |
| 真实 Make 原域 | [FLEQ_S](runs/full-make-4d08/make/FLEQ_S/result.json) finished/gen48；[LOAD_FP](runs/full-make-4d08/make/LOAD_FP/result.json) partial/errors4/gen0；[C_LD](runs/full-make-4d08/make/C_LD/result.json) partial/unfinished7/gen89；[STORE](runs/full-make-4d08/make/STORE/result.json) partial/errors922/unfinished112/gen130 | T1、seed17、Clause/SMT各7200s，浮点 qffp，访存 qfaufbv。partial 不计PASS。 |
| F1 基线 | [同输入比较](runs/final-f1-4d08/f1-compare/result.json)：bdd与新候选固定地址均读0，自由符号地址同址均见全1与0，四组 finished | F1 缺陷从 bdd 继承；本合流没有修复，不署PASS。旧基线从 bdd commit 独立归档构建，非共享 target。 |

定向 Make 产出的 27 条实际 JSON 又经 [GCC/Clang 三表示](runs/directed-make-assembly-4d08/assembly/result.json) 162/162 机器字核对。上述四入口仍属于 wrapper 参数注入的定向域；正式原域部分结果不因这一检查改变。

STORE 回环 Poison、STORE 顶层 Poison、C_LD 顶层 Poison 各一个实际代表，已由[独立新旧同输入复放](../../review/core/partial-boundary/report.md)和[验收复核](../../review/acceptance/limited-signoff.md)确认在旧 bdd 与新候选各自 IR 上触发相同模型异常。该结论限三个代表；其余错误和未完成路径未逐例分类，STORE/C_LD 完整 bdd 原域还在 7200 秒预算内运行，不能据此声称全域无退化。详见[原域边界](full-boundary.md)。

缺必需字段不进入 `gen` 的生产负控由 [core 独审](../../review/core-final-report.md) 的真实 collector 探针/4项变异承担；本目录的 JSON 字段检查和突变负控只验证验收器，不冒充生产 failclosed 证明。ExecuteAs 同一最终 Model 的生产回归也由该 core 独审记录，本目录的压缩 `C_LD/C_SD` 则另验实际机器字和最终后态。

旧正式输入 `inputs-stage-final.json` 因测试 runner 字节漂移作废；对应 315/300 进程退出143，没有新版本PASS。7cce7834/50465535 中间批次的结果保留其旧程序身份，不迁签至4d085b14。无钉 `cur_privilege` 的固定机器字探针会在独立译码 solver 拒绝跨 solver 符号值；定向正例显式钉 Machine 与合法 mstatus，原域仍按其真实配置分账。

## 证据归档范围

可提交脚本、期望值、配置母本叠加结果与本索引。精选结果保留：315 `launch.json`、`summary.json`、每项 `command.json`/`result.json`/`output/*.json`；300 `result.json` 与五份实际 helper 日志；union 九项 `config.toml`/`result.json`/实际 JSON；assembly `result.json` 与每项 `results.json`；nat 八项 `config.toml`/`result.json`/实际 JSON；helper `result.json`/`run.log`；四项定向 Make 和已完成原域 Make 的 `launch.json`/`result.json`/`make-dry-run.log`/`wrapper-argv.json`/实际 JSON；F1 `result.json` 与四组实际 JSON。315 的大 base.ir/正式程序副本、Cargo target、旧 bdd 归档源码与 target 不入仓。

`inputs*.json`、多数 `launch.json`/`command.json`/`result.json` 及原始 JSON provenance 含本机绝对路径；归档副本要保留原件SHA并规范化路径，不能修改原始运行产物。315 每项 `run.log`、seed日志与 Make原始过程日志可只记录SHA，不需逐份复制；300五份状态日志与 helper日志须保留以支持独立重算。STORE/C_LD 旧基线长尾在结束前只记待定，不先声称全域继承或无退化。

原域访存逐类错误、bdd同配置运行及代表机器字对照的实时边界见 [full-boundary.md](full-boundary.md)。
