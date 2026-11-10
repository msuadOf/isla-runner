# 8948cc4 初态配置复审（2026-10-29）

范围：审阅已合入 general 的8948cc4提交；读取干净功能工作树，不修改源码。静态核对部分位约束、执行/pre_state符号一致性和完整见证出口；新增两项实际负面输入验证。未审阅general全部历史改动，也未对含既有dirty浮点改动的工作树进行功能签收。

## P2：非法数值字符串触发panic

`[initial_state] x1 = "中"` 调用get_initial_state → parse_u64_value，config.rs:258的`&s[0..2]`切在UTF-8字符中，release进程退出134。这个切片是既有helper的问题，新入口复用后同样触发。建议用strip_prefix("0x")替代按字节切片，并增加此负例；应返回带initial_state.x1的配置错误。

## P2：不支持的寄存器类型校验太晚

`[initial_state] pma_regions = "?"`：IR中zpma_regions是List(Struct(PMA_Region))。setup_pre_state先将其加入reg_names，再调用symbolic，得到Poison，于target.rs:129 panic，release退出134；后面的“仅支持位向量”校验没有机会运行。用户不支持的配置类型不是内部不变量破坏。建议在将配置寄存器加入符号化集合前，依据shared_state.registers/type_info校验类型和位宽，然后返回ExecError::Type。原内部Poison断言可以保留。增加list/非向量AnyBits/多字段struct负例。

## 可选精简

位模式目前生成Vec<(Option<(u32,u32)>,Option<u64>)>，保留了取消字段表后不再对外使用的任意范围结构，具体位逐个Assert。可后续复用已有位向量或mask表达，减少嵌套Option与逐位约束；不是本轮确证的语义错误，也没有性能退化测量，不必为此引入新框架。

复现命令（工作树.worktree/isla-initial-state-20261029）：将configs/riscv64_difftest.toml复制到临时文件，追加上述initial_state表，然后执行`ulimit -c 0`及`./target/release/isarch -A rv64d.ir -C <临时配置> -T 1 solve-state --clause=MRET`。两次均退出134。日志：[unicode](evidence/review-unicode.log)、[type](evidence/review-type.log)。源码/IR/二进制未修改。

修订：以上两项P2已于ef882f0修复并合入general，原复现证据保留。现行验证见[状态](status.md#复审修复2026-10-29)。
