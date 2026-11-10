# float向memory合流实施计划

## 固定输入与范围

float父提交固定0665526d7e14a207eb9928e282e627584b5635fe，对应Isla591693df2bc32019ea300511509ed683df09522e及模型0f7b8fbc6724103f91f929ef6918f123df75d6c9。目标为.worktree/runner-memory：父memory31ef3b9a8aa3a9db4c03a1d99c191cadf1aadaef、Islabdd047bc67c357f3c6e9c4d34b5ec9daaf81ab57、模型c70482a73be2a67c5a89d88b1e6c2bbea224940c。仅合流既有功能和必要兼容冲突处理，不开发通用ITE/符号化配置，不修改OPEN实现策略。

## 当前阶段

本轮先做状态核对、隔离提交级冲突预检与Sol独审，输出具体实施分解；不在原memory工作树执行merge、reset、clean、stash或提交。原memory Isla有README.md/scripts/run.mk未提交改动，先记录完整补丁与文件哈希；合流候选与这两项的叠加要另审，不默认为可覆盖。主master及其他研发树亦有并行改动，全部不参与本次输入。

## 实施顺序

1. 固定三仓SHA、实际gitlinks、dirty补丁/哈希、工具和资源；分别计算共同祖先和两侧增量。
2. 临时独立bare对象库用merge-tree做三仓提交级预检；保存stdout/stderr、冲突路径与两侧blob。再核memory未提交补丁与float对应改动，不修改原文件。独立GPT-6.1 Sol审查冲突分类及方案。
3. 在独立候选树先合Sail-RISC-V，逐段保留memory模型与float收敛语义；不整文件取任一边。KEEP NaN/陷阱/原部分符号化；纯数据分支回退和OPEN现状保持，workaround区域按合并后位置核对。
4. Isla候选合memory+float，保留内存事件/初态与最终Model约束、枚举重放、ExecuteAs续执行和三汇编表示。Rust生产冲突优先最小语义拼合；五IR及provenance不做文本拼合，而由合并模型重新生成。memory两项dirty配置另保留并在候选叠加，最终明记来源。
5. 原工具链ordinary strict、RV32与RV64 VLEN128/256/512四配置SYMBOLIC严格生成；重核模型/工具/配置/五IR哈希及workaround所有region/锚点。构建链接指定官方Z3。
6. 合流后新版本跑Rust相关回归、浮点永久IR/定向数值、内存具体/符号一致性和访存见证、ExecuteAs及GCC/Clang三表示；真实make入口分别验浮点/访存/压缩。保持原域、每Clause/单SMT7200秒；旧partial/超时分账，不把旧PASS署新版本。具体最小充分矩阵由冲突影响与Sol确定。
7. 子模块源码/生成IR/实际结果分阶段GPT-6.1 Sol独审，修合流新缺陷后分别形成组件合并提交。父memory最后合float，gitlink指向两个组件合并结果，topic仍为memory，重新填写组合版本及限定验收状态。先确保组件可获取再发布父gitlinks；移动原目标前复核dirty状态未变。

## 当前风险与退出边界

memory目标有未提交配置；不能只对commits预检便称整个工作区可直接合并。磁盘/data1只余约4GiB，不在此启动大型生成或实验，隔离预检使用有余量的文件系统。旧float全77预算/旧memory partial边界仍保留，不引入额外功能研究。预检不等于构建或语义验收通过。


## 预检确认后的必要分解

实际冲突为根9、Isla15（含原dirty叠加为16）、模型19配置。额外2处Sail nat/OkErr自动合并接口矛盾必须最小适配，不能以Git无冲突当编译通过。Make原SOLVE_CONFIG及float ISA_CONFIG的覆盖和trace feature兼容必须实际dry-run；metadata必须取消“排除float”的旧组合声明。模型/Isla生成IR与侧车重新产出，不挑一侧旧IR。独审及详细路径见[预检报告](preflight-report.md)。

当前目标memory的四个Rust源码不等于旧F1–F5修复签收版本，本轮不自动摄取其他dirty研发树；回归须用目标基线对照区分原缺陷与合流新缺陷。用户已授权本次合流，当前按其要求先交付预检与具体步骤，不额外引入人工审批闸。


## 2026-11-04 正式实施授权与原子并集标准

用户已明确执行全部六步。唯一候选根为`.worktree/merge-float-memory-20261104`，两子模块独立clone、原memory/float保持；另行记录父merge策略的commitGraph环境错误，不修改共享commitGraph或其他研发树。

Schema Union为两侧既有可求解/可导出合同的并集：memory-events、pre/post-memory、FPR/fcsr、三汇编表示、ExecuteAs最终状态。一个最终Z3 Model一次原子提取，任何必需字段求值/类型失败整case拒绝，不进gen，summary partial与诊断准确。合法empty/not-applicable、write-first且未观察/未请求旧字节的自由pre-memory null与求值失败严格区分，不把错误降为空值；不得静默漏FPR或内存事件。

实施分工：fm_model_impl仅模型与预算映射；fm_isla_impl仅Rust/Make与相应测试；fm_validation_impl仅四配置实际生成、五IR/全部sidecar及正式build/permanentIR；fm_dynamic_impl仅新315/300、混合schema及Make/双工具链动态验证；fm_root_impl仅父docs/metadata/gitlinks待定。独立GPT-6.1 Sol分别fm_model_sol_review、fm_core_sol_review、fm_acceptance_sol_review，实施者不得代签。

主agent统一调度、原源保护、最终组件和根memory提交/可获取性及更新目标。各owner不能改其他owner文件、不能spawn二级代理。OPEN冻结、float77回退、memory vstart非trap及官方Z3/Make本地补丁效果必须保持；不开发通用配置/新优化。
