> 发布后状态：根memory `29aa4765` 及子模块已推送并更新到目标工作树，三仓clean。本文主体保留父仓提交前验收记录；实际发布与原补丁保护结果见[发布后收据](publication/post-publication.json)。

# float→memory 合流限定交付

父仓以 memory `31ef3b9a8aa3a9db4c03a1d99c191cadf1aadaef` 为第一父提交、float `0665526d7e14a207eb9928e282e627584b5635fe` 为第二父提交进入未提交合流。Isla 子模块固定 `4d085b14aa0f987436b86d72f41fab1df9e9a132`（其父 `7cce7834` 是 memory/float 双亲合流），模型固定 `bf861b3e687894480aec701a886a38d4e50b8a99`（双亲合流）。父仓 `topic=memory`，两个 gitlink 与版本记录已暂存；父仓发布和原目标快进尚未执行，两个组件已正式发布并逐 SHA 回读。本轮联合验收已在下列已测范围获[独立限定签收](review/acceptance/limited-signoff.md)，无未关闭的新增实现阻断；原域访存 partial 和旧分支 PASS 不写成整组通过。

## 已核来源与实现

模型仅增加两处 `get_start_element() -> nat` 调用适配，保持 memory 的越界 vstart 非陷阱、float 的77处纯数据选择回退、NaN/真实 trap 和既有 OPEN 实现。79 份 workaround 配置、130 个 region、22 个注释锚点已核；旧 float 132 region 是历史数量。普通严格检查及 RV32、RV64 VLEN128/256/512 四配置生成均退出0，五 IR 安装来源和索引字节一致；主 IR SHA-256 `40f34f706963afcca7dfbf8504ee888bdd004cd0c437712f097b7dda64a705c9`。见[模型最终签收](review/model/final-signoff.md)与[生成记录](validation/generation/report.md)。

Isla 最新 tree `3d852a5fac6a07ae906e502a430a8ee14a65c075` 的生产区由[核心独审](review/core-final-report.md)签收。JSON 并集使用同一最终求解模型提取完整前后态、FPR/fcsr、访存事件和前后内存；必需值求解失败整例拒绝，不混入 `gen`。两轮测试初始化补件只在测试区，最终程序按提交另行重编；未新增通用 ITE/符号化配置或 OPEN 策略。

## 最终程序的实际验证

受测 Release 程序 SHA-256 `3e44cdd6db67f88f94bc894b5b9c6f1de94b7deeb9eb3d9379c49bec1bafbd3e`，冻结输入账本原件 SHA-256 `30f6847f904ea22b8c7dd355cda988bf35bc9938ec46e7b564c408801365d5e2`；运行时官方 Z3 库 SHA-256 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。程序、五 IR、配置、工具、源码清单和实际命令见[构建验证](validation/report.md)及[可移植输入副本](validation/build/inputs-4d085b14-portable.json)。

| 范围 | 已核结果 | 限制 |
| --- | --- | --- |
| Rust 与永久 IR | workspace `--lib` 610/610、`--tests` 665/665；五入口26/26步；104负变异全部被拒 | 库、集成及永久 IR 回归，不代表全部 Clause |
| 异常与状态 | 新程序315/315异常数值/flags、300/300状态复算相符 | 315为定向约束 IR；300为 helper 级输入 |
| Schema Union 与控制 | 混合访存9/9、nat指令8/8、直接mask helper4/4；固定字 `C_ADDI4SPN=0x1fe0` 的 ExecuteAs seed17 实跑 x2=7→x8=1027、Retire/finished | union 定向配置钉 Machine/mstatus、RAM缩至4KiB；helper 不等于完整指令 |
| 汇编与真实 Make | 混合九例 GCC/Clang 三表示54/54字节一致；定向真实 Make 四入口 finished/无partial，产出的27条 JSON 又做162/162双工具链字节核对 | Make wrapper 仅注入固定机器字和前态，不能替代原域 |

定向实际 JSON、配置、命令和结果入口见[动态索引](validation/dynamic/index.md)；独立数值、内存顺序、后态及工具链复核见[动态独审进度](review/acceptance/progress.md)。ExecuteAs 新实跑的[结果](validation/dynamic/probes/executeas-fixedword/result.json)、[实际 JSON](validation/dynamic/probes/executeas-fixedword/output/rv64_zC_ADDI4SPN.json)和[独立核对](review/acceptance/final-4d08-executeas-independent.json)均绑同一最终程序与 seed17。

## 原域与历史限制

正式原域 Make 中，FLEQ_S finished/gen48；LOAD_FP exit2、partial/errors4/gen0；C_LD exit0、partial/unfinished7/gen89；STORE exit2、partial/errors922/unfinished112/gen130。partial 一律不计完整 PASS。旧 memory 同配置 STORE/C_LD 完整预算长批仍在运行，不能从部分同类错误推断全域无退化。core 对一条 P3 辅助译码 Poison 用183项门寄存器逐项重放新旧，均触发 zicfilp:31；对 STORE 与 C_LD 各一条主执行原 Ctor/102项前态重放新旧，均 SAT 且触发 core/types:78。三类代表的[最终独立分类](review/core/partial-boundary/report.md)支持所测代表为继承边界，不外推全部922/112/7；[原域边界](validation/dynamic/full-boundary.md)继续保留 partial 与未完成的旧基线长尾。

F1 具体/符号内存不一致在 bdd 与新候选同输入复现，仍是继承缺陷；见[独立复证](review/acceptance/final-4d08-f1-inheritance-independent.json)。无钉 `cur_privilege` 的固定机器字启动译码仍有符号跨 solver 边界；定向正例显式固定 Machine/mstatus，不称全域修复。旧 float 77 项完整预算、完整源码控制流、动态字符串反解析及硬件重放仍未验收；旧 float 的77纯数据回退限定 PASS只保留原版本证据。

最终[联合独审](review/acceptance/limited-signoff.md)已确认上述已测范围可限定签收，三类代表归因已完成。STORE/C_LD 旧基线长尾、全域无退化证明和既有 F1 不在本轮签收内。两组件正式分支已按完整 SHA 推送并逐项回读一致，见[组件发布收据](publication/components.json)；父仓提交/发布与原 memory 工作树保护更新仍待主负责人执行，目标前态只读guard见[收据](publication/target-before.json)。父仓证据只精选小型脚本、配置、实际 JSON/命令/结果和独审收据；含本机路径的副本仅规范化路径前缀，原件与副本 SHA-256 同列于[证据清单](implementation/evidence-selection.json)。原始大 IR、二进制、target 与 trace 未复制。`validation.status` 仅记 `limited-pass`；它不表示原域全部 Clause、全控制流或硬件验收。
