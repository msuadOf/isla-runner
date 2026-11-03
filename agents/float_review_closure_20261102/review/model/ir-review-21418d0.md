# 模型21418d0：新IR与memo来源独审

模型 `21418d0b0d4942fae20061ed580ee04aff4a8a61` 的普通严格检查与四配置 SYMBOLIC 严格生成来源通过。新输入清单 SHA256 为 `44641223d4541b042a337c9adab6ac902f34d3af82f3835213f28b39cc247b19`。本审查不把 `8ad5e8e` 的动态结果迁作新版本结果；动态验收由其责任人另记。

独立复核166个受控模型文件、149个真实工具/标准库/插件/配置文件，与现场文件和生成记录一致；实际 Sail 二进制及编译用 Z3 与已审旧批次一致。普通检查及四次生成均 exit 0，严格参数和 SYMBOLIC 配置符合要求。新旧每配置 memo 的哈希、完整记录数相同，源/目的 inode 均不同，新五个目的 inode 彼此不同；旧文件均未改变。生成器在拷贝后仍实际执行严格检查/生成。详见 [独立来源和memo审计](memo-reuse-21418d0.json) 与 [复核脚本](audit_generation_21418d0.py)。generation.json 的 model_files 还收录一个忽略的工作目录 sail_smt_cache；166个受控源码单独与 git 清单核账，实际 --memo-z3-path 指向每配置目的文件。

四配置逐函数规范化比较 `8ad5e8e`→`21418d0`：函数集合和数量不变，仅 `zassembly_forwards`、`zassembly_forwards_infallible`、`zassembly_forwards_matches` 变化。数值/flags/原因分支等54个语义目标（RV32实际52个）、zexecute 和所有其余函数均保持不变。逐配置证据为 `assembly-ir-delta-*.json`。

实际新IR的三组 assembly 函数中，五个固定RM_RNE模式均先于原generic模式；成功臂构造对应无RM助记符并退出，失败边继续后继specific/generic；generic仍读取原RM并调用 `frm_mnemonic_forwards`。四配置合计60项检查通过，详见 [实际IR顺序](assembly-ir-order-21418d0.json)。真实forward执行证据和reverse的NonExec限制见 [现行汇编设计](assembly-design.md)。

永久CFG检查器另行审查。候选 `9f7fa5…` 已拒绝12个既有负控，但发现add/mul/sqrt/fma的NV原因出口改false仍被放过；已交实现者修复。该问题在检查器，实际新IR的原因及出口仍符合此前独立CFG审查。

最终补记：检查器已修原因出口漏洞；最终候选`48f80379…`通过独立四配置绿、迁移检查器绿、旧IR红与16个定向负控全拒。正式签字见 [永久检查器最终独审](checker-review-final.md)，前述9f7fa5缺陷为已修历史记录。
