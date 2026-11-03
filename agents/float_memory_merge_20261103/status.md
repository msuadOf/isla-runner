# float→memory 合流状态

2026-11-04：根仓候选以 memory `31ef3b9` 为 HEAD，`MERGE_HEAD=0665526d`。父仓冲突已处理；两个 gitlink 暂存指向 Isla `4d085b14`、模型 `bf861b3e`。Isla `4d085b14` 的父 `7cce7834` 是 memory/float 双亲合流，后继只补测试初始化。模型严格生成、五 IR、Isla 源码与最终程序在已测范围获[独立限定签收](review/acceptance/limited-signoff.md)：无未关闭的新增实现阻断，可继续父仓定稿。限定验收不包含原域全通过或全域无退化。实施与发布前态见[父仓记录](implementation/root-merge.md)和[目标guard](publication/target-before.json)。

float `591693df`／`0f7b8fbc` 的77处纯数据回退、四配置严格生成和限定动态结果，见[最终报告](../float_review_closure_20261102/final-report.md)及[交接](../float_review_closure_20261102/handoff-to-memory.md)；它们仅适用各自受测版本。旧全77预算、完整源码控制流和硬件重放仍未签收。本轮保持 NaN/trap 和 OPEN 实现，不新增通用策略配置，不研究 OPEN。

最终 `4d085b14`/Release 二进制 `3e44cdd6…` 的 workspace `--lib` 610/610、`--tests` 665/665、永久 IR 26/26 与 104 负变异拒绝已按[验证记录](validation/report.md)完成；模型/IR与最终输入独立签收见[模型报告](review/model/final-signoff.md)。这组结果只覆盖库、集成与 IR 回归。此前 v2 和 `7cce7834` 的动态结果只对应各自二进制，不迁给本版。

同一最终二进制上的定向 315/315 异常、300/300 状态、混合 Schema Union 9/9、nat 边界8/8与 helper4/4、三表示54/54及定向真实 Make 四入口已由[动态独审进度](review/acceptance/progress.md)逐项复算；原始结果与命令入口见[动态索引](validation/dynamic/index.md)。这些输入含显式 Machine/mstatus 或其他定向约束，不能替代原域完整 Clause。此前旧程序结果仍只适用其自身版本。

原域 Make 结果已分账：FLEQ_S finished/gen48；LOAD_FP exit2、partial/errors4/gen0；C_LD exit0、partial/unfinished7/gen89；STORE exit2、partial/errors922/unfinished112/gen130。两项访存旧 memory 基线仍在完整预算内运行，错误类别已有部分基线同类证据，但全域是否退化尚不能下结论，见[原域边界](validation/dynamic/full-boundary.md)。partial 一律不计完整 PASS。

三个原域 Poison 代表已在旧/新同完整状态复放，见[核心分类](review/core/partial-boundary/report.md)。P3 一条、STORE/C_LD 主执行各一条都触发同一对应的既有模型异常；该证据只解释三条代表，不外推全部 922/112/7。F1 具体/符号内存不一致仍在。STORE/C_LD 同配置旧基线长尾未完成，仍不能判全域无退化；OPEN 与通用策略配置保持冻结。

两个组件已从正式远端目标分支逐 SHA 回读一致，见[组件发布收据](publication/components.json)。待完成：父仓提交与发布回读、原 memory 两文件保护及目标快进；原域 partial、全域控制流、旧 float 77 全预算和硬件重放继续按各自边界处理。冻结输入 SHA-256 为 `30f6847f904ea22b8c7dd355cda988bf35bc9938ec46e7b564c408801365d5e2`。本次精选证据见[清单](implementation/evidence-selection.json)。
