# Isla 合流源码合同独审

当前结论：实施前合同检查完成；候选仍处合并中，尚未给源码或动态验收 PASS。固定输入为 memory Isla `bdd047bc` 与 float Isla `591693df`，共同基准 `0008fae76`。审查者只写本议题 review/core 证据与独立探针，不修改生产候选或原工作树。

## 合同表

| 观察面 | 必须保留的合流合同 | 独立验证要求 |
| --- | --- | --- |
| JSON 并集 | 保留 memory 的 `memory-events`、`pre-memory`、`post-memory`、value-hint/encoding-slice、skip/diagnostics，以及 float 的完整寄存器前后态、requested-instruction、path-signature、三表示、state-domain；FPR/fcsr 不因合流缺失 | 真实 collector JSON 明确断言字段集合；无访存例也保留空数组字段 |
| 最终求解模型 | 具体指令、编码、汇编所用前态、寄存器前后态、返回值、访存事件及重放结果来自同一最终可满足约束和同一个 Z3 `Model` | 让前态、后态、返回值、读写数据互相关联；使用能在拆模型时暴露分歧的探针，并审源码作用域 |
| 字段失败 | 必需值任一维失败则整例不进入 `gen`；错误和 partial 仍有统计/诊断；不得用 null、空串或掩码占位代替可重放值 | 分别注入前态、后态、返回值、访存地址/数据/结果失败；校验 gen 为空且错误不被吞掉 |
| ExecuteAs | 同一 frame 的寄存器、内存、lets、路径身份、累计时间、执行预算与 trace 延续，checkpoint 携带原约束；所有轮次结束才导出状态 | 原请求先写状态和内存，payload 再读写；校验两轮副作用及最终返回，并检查 task_id 不重置 |
| 编码可行域 | float 的 encoding_paths 在完整执行约束下验证候选；压缩 fallback 仅进入普通 mapping 正常拒绝域；真正 assertion/类型错误不能作为正常拒绝吞掉 | 编码/状态守卫相关探针、多个编码、部分 assembly 拒绝和 assertion 测试 |
| 枚举生命周期 | 同 Context 的 solver/重放共享一致 enum sort，所有 solver 析构后 checkpoint 仍能重放；缓存与 solver 引用各自正确释放；成员数冲突/空枚举硬失败 | 单/多成员、struct 字段、同 Context 及跨 Context、全部 solver drop 后重放，已有生命周期测试实际执行 |
| tactic/种子 | CLI 缺省 `Default`，保留 qffp/qfaufbv/smt；使用指定官方 Z3 探测实际 tactic 与 seed 参数能力，初始化不支持时不可静默跳过 | 初始化独立进程测试、选项测试与实际库链接核对 |
| memory/非冲突接口 | 保留 memory 数组、区域/PMA/CSR、固定输入及 witness 批次；保留 float initial_state/宽向量/三表示；不以整边选择删除已有功能 | diff 两侧和自动合并文件，访问调用链，复跑原两侧相关测试；旧 F1–F5 外树补丁不自动纳入 |
| illegal/partial | 合法完成的 Illegal_Instruction 仍可输出；未完成/字段失败不能伪装 finished；原有配额/采样保持 partial 标识 | 完成结果类别、错误结果、采样与配额测试；无编码非法路径须有明确状态而非悄悄丢失 |

## 实施前发现

1. 自动合并的 `isla-lib/tests/smt_tactic.rs` 仍要求 `Tactic::default() == Qfaufbv`，而新增 `smt_init.rs` 要求 `Default`。已通知 owner，最终按用户已有 CLI 默认 Default 同步测试，保留 qffp。
2. memory 旧 `ExecuteAsContinuation` 只保存指令和 checkpoint，并从初态重建 frame、使用新 task_id；float 已通过 `frame.new_call` 保留真实 frame。合流应采用后者，并将 memory 数据和初态合同接入。
3. memory 旧事件格式化使用 Option、终值超时以空字段构建候选再由最终层滤除；本轮用户已明确 Schema Union 的原子失败要求，不能继续产生成功的部分见证。
4. 合流配置的同名组合必须检查：`setup_pre_state` 的 float `initial_state` 先约束原符号，memory `apply_symbolic_csrs_to_registers` 若重建符号并覆盖 pre_state，则前约束孤立；具体 fixed-prestate 与 initial_state 同名时原宽度查询也只支持符号值。已通知 owner 最小保留同变量与具体位宽；独立最终回归须包含同名组合。

以上为两侧固定源码事实和当前候选观察，尚不代表最终实现状态。源码 ready 后记录哈希、实际 cargo 命令及独立错误注入结果，再判断签收。

## 空值与失败的边界（用户裁决）

| 现象 | 是否允许进入 gen | 理由与所需证据 |
| --- | --- | --- |
| 完整执行没有访存，三项 memory 数组均为空 | 允许 | 事件账本为空，没有要求查询访存值 |
| read 事件的 data 为 null | 允许 | data 仅适用于 write；read 的 value/address 必须具体 |
| write-first 字节的 pre-memory.value 为 null | 有条件允许 | 事件账本证明首触是写，原合同未观察/请求该字节初值；不得用此解释实际 Model 查询失败 |
| 普通写返回 false | 允许并提交写 | Bool 对普通写不表示提交成败；独占写按 Bool 判定 |
| 独占写返回 false | 允许且不提交写 | 成败 Bool 必须查询成功；不能以 null 代替失败 Bool |
| 某字段不在当前目标寄存器集合中 | 只按两侧既有合同判断 | 本轮不另建全架构观测能力；FPR/fcsr 等原必需集合不可因合流漏掉 |
| 实际请求的前/后态、地址、读写数据、写结果、返回值、编码查询失败或类型错误 | 不允许 | 整例拒绝，统计/诊断保留；不能降级为 null、默认值、空串、掩码占位或静默删除字段 |

验证中须配对检查合法 free-null 和失败分量，防止“只要有 null 就拒绝”或“所有 null 都可重放”的错误实现。

## 中间快照探针记录

首个可编译快照记录于 [probe2 清单](core/probe2/source-manifest.json)。独立探针仅附加在临时源码副本；独立 target 链接指定官方 Z3，启用 tracetool 和 smt-thread-interrupt。

- 四项正控实际通过：字段并集与 GPR/FPR/fcsr/编码/返回值/事件关联；七维必需查询失败原子拒绝；write-first 自由初值 null；无访存空数组。日志见 [正控](core/probe2/cargo-test-lib-fixed-import.log)。
- 三项可编译错误变异均被拒绝：删除 memory-events 字段、从剥离执行与编码约束的独立 solver 取最终 Model、吞掉必需前态错误并输出空 map。变异恢复后四项正控仍通过，见 [错误变异清单](core/probe2/mutations.json)和[恢复正控](core/probe2/post-mutation-restored.log)。
- 两个额外真实反例 RED 已交 owner：嵌套 `Poison` 返回值仍进入 gen；decoder `Run::Exit` 被静默当普通 guard 拒绝，见 [Poison](core/probe2/nested-poison-red.log)与[decoder 提前退出](core/probe2/decoder-exit-red.log)。这是待修问题，不计 PASS。
- ExecuteAs 两阶段的寄存器、具体内存修改及前后阶段事件续接独立通过，见 [续执行探针](core/probe2/execute-as-memory.log)。
- 独立 SMT 单元组为 25/26：枚举生命周期、模型缓存及 checkpoint 隔离通过，旧 `deadline到期中断check返回超时错误` 预期 1ms 必超时但实际 Sat。该乘法式未限制非平凡因子，不能保证超时；已交 owner 修正测试，不能据此宣称生产 watchdog 失效。六组集成测试合计 19/19，通过宽位向量、混合位串消费者/访存、tactic 及独立进程初始化，见 [SMT 日志](core/probe2/smt-tests.log)与[集成日志](core/probe2/integration-tests.log)。

真实 IR 回环的额外调查：严格拒绝 Poison 后，旧 `real_ir_env` 的合法 lb 测试暴露 `get_xLPE(cur_privilege)` 在 VirtualSupervisor/VirtualUser 抛出未支持 Hypervisor 的内部异常。该 fixture 使用 `use_model_init=false`，未设 cur_privilege，因此辅助执行探索五种权限。直接绕到 `zencdec_backwards` 也产生同样 Poison。独审要求保留 wrapper 和 failclosed，在 fixture 中提供本次真实前态（例如 Machine），不得把模型内部异常吞成正常守卫拒绝；生产 collector 已按最终 Model 将记录的 cur_privilege 放入具体寄存器表。最终结果仍待 owner 修订与复验。

该阶段只适用所列源码哈希；owner 仍在修订，最终源码、IR、来源及根 metadata 未签收。首轮副本遗漏编译期资源、错误选择 bin 测试入口和探针缺显式 IR Exp import 的失败日志原样保留；它们属于审查运行准备，不是生产候选缺陷。
