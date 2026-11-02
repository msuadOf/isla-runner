# 保留指令输入 Assert 的独立复验

本批次为 Isla 源提交 `cf1aa1431d5f2d05584c78c0e7c84862a9a9b1fa`，正式 Release 冻结程序 SHA-256 `abce451a11e0e4a8a3c9658d4a8462634f284085f219cca79f439ca176853a1a`；仍实际链接官方 Z3 库 SHA-256 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。新模型 VLEN128/ELEN64 IR SHA-256 为 `a877e245cda62b8430b13541faf05a3a2f47719dddad283dd336fa45e068f97e`，与上一批次同字节。每条 Clause 固定 seed 17、T1、qffp、单次 SMT 7200 秒、整个 Clause 外限 7200 秒。

| 验证 | 当前结论 | 证据 |
| --- | --- | --- |
| 新模型 VFUNARY0/原 sat 配置 | 自然退出 0，墙钟 22.33 秒、user 18.59 秒、sys 3.68 秒；summary `finished`，partial/error 均 0；初版与本版 46/46 条前后态多重集相同 | [结果](runs/selective/new_sat/result.json)及[逐条比较](runs/selective/new_sat/semantic-comparison.json) |
| 新模型 flags/原 flags 配置 | 完整 `F_BIN_RM_TYPE_S` 自然退出 0，墙钟 1127.51 秒、user 1118.55 秒、sys 7.71 秒；728 条 JSON、680 条退休及 48 条非法，summary `finished`，partial/error/sampled 均 0。按指令、编码、完整前态、后态、返回值比较，初版与本版 728/728 条多重集相同 | [结果](runs/selective/new_flags/result.json)及[逐条比较](runs/selective/new_flags/semantic-comparison.json) |
| 冻结旧显式 flags B | 原 B IR 与原配置的完整 `F_BIN_RM_TYPE_S` 自然退出 0，墙钟 2626.07 秒、user 2582.16 秒、sys 40.43 秒；328 条 JSON、280 条退休及 48 条非法，summary `finished`，partial/error/sampled 均 0。flags changed 120 条（其中新增 NV 103 条）、same 160 条；初版与本版按五个语义字段的 328/328 条多重集相同 | [结果](runs/selective/old_flags/result.json)、[分类](runs/selective/old_flags/coverage.json)及[逐条比较](runs/selective/old_flags/semantic-comparison.json) |
| 56 项定向语义 | 56/56 完整 Clause 退出 0，156 条 JSON、3518/3518 条断言通过；NaN/BF16、活动 lane 与五种舍入的输入和 oracle 同上一批次。初版与本版 56/56 任务的 156 条前后态多重集均相同 | [汇总](selective/semantic/summary.json)及[逐条比较](selective/semantic-comparison.json) |
| BF16/压缩三表示 | 3/3 任务退出 0；BF16 两组各 6 条 JSON、各 2 条非法布局，Clang 助记符拒绝符合预期；C_ADDI4SPN 1 条 ExecuteAs 后态核对通过；GCC/Clang 三表示共 78/78 项 | [汇总](selective/representations/summary.json) |
| 真实 Make 入口 | `make -f isla/scripts/run.mk -o build-isarch solve-FLEQ_S` 实际执行，退出 0；墙钟 3.19 秒、user 2.47 秒、sys 0.62 秒，8 条 JSON、15/15 语义断言及 48/48 三表示通过 | [结果](selective/make-smoke/result.json) |

两批旧 flags B 使用相同冻结 IR、配置、seed 17 和 CPU100；初版 `de00adb1` 墙钟 2884.43 秒，本版 2626.07 秒。两个批次的并发环境不同，以上为逐次时间观察，不单凭这对数字归因或推广速度收益。初版旧 `sat/B.ir` 在 CPU101 的完整诊断已于 7200 秒外限退出 124、未生成完整 JSON；它属于前一版本 `de00adb1`，且包含旧不活动 lane 提前转换行为，不能并入本批次或据此否定新模型的完成验收。各任务实际退出、wall/user/sys、输入/程序哈希保存在对应 `result.json`；完整定向配置限定初态和操作字段，不代替默认全域完整 Clause。
