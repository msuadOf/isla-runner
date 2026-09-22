# V 扩展 SYMBOLIC 重复实现收敛

用户已授权执行重构。

1. 合并 MASKTYPEI、MOVETYPEV 指令主体。
2. 共用 read/write_vreg、init_masked_result（含 carry/cmp）、vrev8 的普通实现，仅保留后端入口宏。
3. 检查普通及 SYMBOLIC 类型，验证 C++ 与 Isla IR 生成。
