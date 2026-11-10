# 编码约束分离与饱和分支：动态验证

本轮正式 Release 的 Isla 源提交为 `de00adb1be7edb20c4561e4074c9485bf028be80`，程序 SHA-256 为 `e95fa84208f748fb00c96260910000a950634a9d2b35b35c4bfd8b83c1b533ab`；实际链接官方 Z3 `1fd1d3613`，库 SHA-256 为 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。新 VLEN128/ELEN64 模型 IR SHA-256 为 `a877e245cda62b8430b13541faf05a3a2f47719dddad283dd336fa45e068f97e`。所有以下命令均使用 `-T 1`、`qffp`、单次 SMT 7200 秒；完整 Clause 的进程外限也是 7200 秒。

## 已完成

| 验证 | 输入与结果 | 证据 |
| --- | --- | --- |
| 新模型 VFUNARY0 | 新 IR 加旧 `sat/config.toml`，seed 17，完整 Clause 自然退出 0；墙钟 37.16 秒，user 33.98 秒，sys 3.09 秒；46 条 JSON、22 条退休及 24 条非法，summary `finished`，partial/error 均 0 | [结果](runs/new_sat/result.json) |
| 新模型 flags Clause | 新 IR 加原 flags 配置，seed 17，完整 `F_BIN_RM_TYPE_S` 自然退出 0；墙钟 1615.96 秒，user 1603.37 秒，sys 10.60 秒；728 条 JSON、680 条退休及 48 条非法，summary `finished`，partial/error/sampled 均 0 | [结果](runs/new_flags/result.json) |
| 旧显式 flags B | 冻结旧 `flags-arithmetic/B.ir` 与原配置，seed 17，完整 `F_BIN_RM_TYPE_S` 自然退出 0；墙钟 2884.43 秒，user 2834.45 秒，sys 45.80 秒；328 条 JSON、280 条退休及 48 条非法，summary `finished`，partial/error/sampled 均 0。退休见证中 flags changed 120 条（其中新增 NV 103 条），same 160 条 | [结果](runs/old_flags/result.json) |
| 旧 eager sat B 诊断 | 冻结旧 `sat/B.ir` 与原配置，seed 17，完整 `VFUNARY0` 在 7200 秒进程外限退出 124；墙钟 7200.20 秒，user 7119.08 秒，sys 71.91 秒；未生成完整 JSON。它保留旧不活动 lane 提前转换行为，不能计为本轮新模型验收通过 | [结果](runs/old_sat/result.json) |
| 特殊值与活动 lane 定向验证 | 新 IR，56/56 项完整 Clause 退出 0，156 条 JSON，3518/3518 条断言通过；覆盖左右独立 NaN、BF16 融合及五种舍入、三来源 sNaN、多 lane 异常累计、mask 与 vl0 | [汇总](semantic/summary.json) |
| BF16 与压缩指令编码 | 新 IR；BF16-vl0/vl1 各 6 条 JSON、各 2 条模型非法布局；Clang 对相应非法助记符各拒 2 条，精确二进制和 `.insn` 仍匹配。C_ADDI4SPN 1 条合法压缩编码的 ExecuteAs 续执行后态正确；GCC/Clang 三表示共 78/78 项 | [汇总](representations/summary.json) |
| 正式 Make 入口 | `make -f isla/scripts/run.mk -o build-isarch solve-FLEQ_S` 实际执行，seed 17，退出 0；墙钟 3.51 秒，user 2.77 秒，sys 0.63 秒；8 条 JSON 覆盖四种左右 qNaN 组合，语义 15/15 与 GCC/Clang 三表示 48/48 项通过 | [结果](make-smoke/result.json) |

## 完整旧输入对照

旧 `flags-arithmetic/B.ir` 加原配置在 CPU100 已以新 Release 完整完成，旧版本同输入在 7200 秒外限退出；这说明本轮初版编码约束分离已让该冻结显式 flags B 在预算内完成。新 flags 在 CPU102 也已完成，但模型不同，二者不计算纯性能加速比。旧 `sat/B.ir` 加原配置在 CPU101 已用足 7200 秒外限，仍未生成完整 JSON；此诊断针对旧不活动 lane 先做转换的负载，不能否定新模型 VFUNARY0 的完整完成结果。旧输入与历史版本外限结果见 [预检](preflight.json)，本轮逐项命令及结果在 `runs/old_flags/`、`runs/old_sat/` 保存。

上述定向配置固定了初态与部分操作字段，验收具体语义和编码关系；不代替默认全域的完整 Clause。新模型 VFUNARY0 使用旧 sat 配置的完整运行未缩域。两个旧输入的原始 IR 与配置均未修改。

实施方随后为减少无效候选保留了依赖指令输入的原 Assert；本报告上方初版数据仅适用于 `de00adb1`/`e95fa842` 版本，修订版须按自身二进制独立判断。

保留指令输入 Assert 的修订版已作为独立 `cf1aa14`/`abce451a` 批次完成旧显式 flags B、新模型 flags、新模型 VFUNARY0、56 项定向、三表示和真实 Make 入口。旧显式 flags B 也在完整原输入上自然退出；两批已生成结果的五项语义字段多重集相同。准确时间、版本和限定条件见[修订版报告](selective-report.md)。初版旧 sat B 已在外限退出 124，不列入正式 PASS。
