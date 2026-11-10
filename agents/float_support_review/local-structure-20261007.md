# 浮点未提交改动的局部结构修整（2026-10-07）

## 目标与范围

按用户要求修改上一轮只读审查发现，保留功能、原注释及必要的数据顺序，不提交，不调整原索引。热点为isla/src/isarch/{exec.rs,mod.rs,target.rs}及isla-lib/src/primop/float.rs。内联单调用浮点见证逻辑和mapping拒绝判定，去掉编码空转发；指令文本递归归属现有JSON条目，hart能力探测归属Rv64Domain，浮点参数检查归属Val方法。MappingCollector保留真正复用的错误记录方法，单调用new/finish就地展开；编码match恢复原块结构。

## 验证计划

先把直接调用待删除helper的测试改为真实collector/mapping入口回归，在旧实现上验证基线，再做结构修改。复验isarch库/bin、浮点primop及默认feature编译/fmt，make solve MRET。核对原生产注释保留、无多余文件修改、索引逐项不变。证据位于isla/target/local-structure-20261007/。纯结构修改的基线应通过，不虚构红例；出现失败据实记录。

## 状态

已完成，修改仅在工作区未暂存层，HEAD及原索引逐条未变；未提交。

## 实施

- exec.rs内联prefer_enabled_float_witness，保留SAT时加入偏好、UNSAT/Unknown保留原路径、错误经原诊断早退的行为；删除仅供直接helper测试的bool结果。
- mapping拒绝判定并入run_mapping的错误分支；删除get_assembly_encdec_forwards空转发，编码两入口直接复用run_mapping。MappingCollector的new/finish就地展开，复用的record_error方法保留。
- 原stable_instruction_text递归实现归属既有AssemGenJsonItem::instruction_text关联方法，专门构造requested-instruction输出，不新增类型。
- hart能力探测移为Rv64Domain::probe_hart_support关联方法，三处生产调用保留；fp_arg/rm_arg/bv_arg改为Val实例方法，仍复用原类型查询和转换机制。
- 编码match按HEAD原分块恢复，增加一行说明以保留rustfmt下的分块；原生产区行注释逐项核对均保留，pre-state先于model completion的必要顺序不变。

## 验证（限定PASS）

先改测试入口再改实现：原直接helper的FS/VS测试并入真实collector用例，用官方浮点clause检查16种约束组合及无约束时FS/VS=3；mapping错误用例改经try_get_assembly_name真实执行。旧实现基线82项通过，重构后相同库82项通过。未新增红例，因为目标是等价结构修改。

命令均在isla目录执行：

- `cargo test --offline -q -p isla --lib --features itrace,smt-thread-interrupt -- --test-threads=1 --skip isarch::target::tests::rv64_target_trait`：基线82通过。
- `cargo test --offline -q -p isla --lib --bin isarch --features itrace,smt-thread-interrupt -- --test-threads=1 --skip isarch::target::tests::rv64_target_trait`：修改后82库＋25bin通过。已知x0测试仍过滤。
- `cargo test --offline -q -p isla-lib --lib --features itrace,smt-thread-interrupt primop::float:: -- --test-threads=1`：10项通过。
- `cargo check --offline -q -p isla --bin isarch`、`cargo fmt --all -- --check`、`git diff --check`：通过。
- `make solve ALL=MRET THREADS=1 ITRACE=1`：退出0，4 gen；保留运行前后产物。该结果属于完整工作区，未跑全量浮点、全库或硬件。

受测HEAD为7b7337b加原暂存浮点改动及本次四文件修改，完整文件哈希、IR/配置/binary哈希和原索引核账见证据目录audit.json；日志为baseline.log、green-isla.log、green-float.log、default-check.log、fmt.log、smoke.log。本轮结束原暂存补丁不变，不将历史整批PASS迁记到新代码。
