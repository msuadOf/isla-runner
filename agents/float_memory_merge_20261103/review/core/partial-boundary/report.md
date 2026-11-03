# Make partial 边界独立分类

STORE 的 P3/主执行及 C_LD 主执行三个代表的新旧同输入复证已完成：P3 代表是既有模型异常，新版使用同一最终 Model 后拒绝该见证符合合同；主执行 Poison 代表也是继承边界。该结论不外推全部 922 条错误、112/7 条未完成，原域 Make 保持 partial。

## 原域账本

独立读取 `validation/dynamic/runs/merge-make-full-v2/make/{STORE,C_LD}` 的实际 JSON、命令与日志，见 [机器记录](original-full-accounting.json)。

| Clause | gen | errors | unfinished | 其他 |
| --- | --- | --- | --- | --- |
| STORE | 130 | 922，全部为 `Unreachable: zext_decode 译码回环返回非具体值: Poison` | 112 | assertion-filtered=1；无超时、采样、待处理批次或配额删除 |
| C_LD | 89 | 0，diagnostics 为空 | 7 | 无超时、采样、待处理批次或配额删除 |

`exec.rs` 的 collector 在 ExecuteAs 续执行入队之后、具体化之前，把顶层 `Run::Finished(Val::Poison)`、`Run::Exit`、`Run::Suspended` 统一计入 unfinished。实际日志中 STORE 的顶层 Poison 警告恰 112 次、C_LD 恰 7 次，Exit/Suspended 均 0；因此这两个数的代码来源已核实为主执行顶层 Poison，不能称求解超时或 P3 编码失败。

## 独立探针位置审查

owner 的临时副本 `.worktree/fm-store-probe-20261104/source` 不修改正式候选。P3 捕获点在 collector 的 `encdec_guard_roundtrip_ok` 返回错误处，精确匹配“译码回环返回非具体值: Poison”，已经取得最终 Model、具体原请求、具体编码及门所用 concrete_regs；它与上述 922 类逐字相同，不是 startup decode 或主执行的 Poison。

辅助译码 callback 额外记录实际 `frame.get_exception()` 和 throw 位置；collector 捕获 path-signature、requested、编码、具体前态/完整门寄存器和具体返回值后以预设 86 停止。额外模型求值不新增约束。主执行 Poison 另有独立捕获点与预设 87，使用本路径 SAT Model 的完整前态/原请求及 frame 异常；两类证据不得混记。

## 分类条件与同输入复证

1. 保存首次 P3 失败的编码、最终具体 cur_privilege/mstatus/misa 及全部 helper 实际可读取寄存器，并记录哪项仍未初始化；不要仅打印稀疏前态。
2. 在新/旧 IR 和对应程序中对同一个编码及完全相同的具体 helper 环境直接执行译码。记录全部可满足终态、构造子、Poison/异常、异常文字和 throw 位置，不依赖 callback 的最后一个结果。
3. 若旧/新辅助域均含同一异常而旧收集器忽略错误或用后到成功覆盖，则新拒绝是用户要求的 failclosed，旧更多 gen 不能称更完整；仍应保留完整 Make partial。
4. 若只有新辅助域因环境丢失/多出自由符号失败，而旧同一完整状态正常译码，则属合流回归，不能以 failclosed 为由关闭。
5. 主执行 unfinished 用其实际具体请求/前态重放新旧主执行；相同异常可证明该代表输入的继承边界。单个代表不能自动证明全部 112/7 路径或全部 922 错误的原因相同。

捕获阶段两类代表已取得，随后完成的完整同输入复证见末节 v4；本记录不签完整原域 Make PASS。

## 已捕获的两类代表

已独立审读 owner 临时程序的实际输出，原样副本和哈希见 [捕获收据](captured/receipt.json)。程序分别按预设 86/87 退出，属于诊断成功条件，不是正式求解 PASS。

| 类别 | 同路径具体状态 | 实际异常 |
| --- | --- | --- |
| P3 回环错误 | path-signature `3705594432398073476`；`32'h01ff_b023`，`sd x31,0(x31)`；最终 Model 的 cur_privilege=VirtualSupervisor，mstatus=0，misa=0x800000000034112f，x31=1；主执行返回 Memory_Exception(地址1，E_SAMO_Addr_Align) | 辅助 zext_decode 的 Error_internal_error：`extensions/cfi/zicfilp_regs.sail:31: Hypervisor extension not supported`；throw `prelude/errors.sail:21.41-21.106` |
| 主执行顶层 Poison | path-signature `662382735639519740`，SAT；cur_privilege=VirtualSupervisor，mstatus=0x21000；STORE 的 imm=0，rs1/rs2=31，原载荷 width=1 | Error_internal_error：`core/types.sail:78: Invalid privilege level or virtual mode`；同一 errors.sail throw 入口 |

这两类异常不同，不能合并解释。主执行的原符号载荷 width=1，不能拿 P3 的 sd 机器字重新译码后替代同 Ctor 复证。首次 main 诊断因 P3 探针环境变量未设置而 panic 134，失败保留；改为只在设置对应捕获路径时启用 P3 退出后，main-v2 才得到上述实际 87 证据。

相关模型源 `extensions/cfi/zicfilp_regs.sail`、`postlude/decode_ext.sail`、`sys/sys_control.sail` 与 bdd 固定模型 c70482a7 逐字相同，新旧 IR 的 zext_decode/压缩 wrapper 去除 SourceLoc 后也逐字相同，见 [源码等价记录](relevant-model-source-equivalence.json)。这证明相关规则不是本轮新增；捕获时尚待的完整同具体 helper 环境旧/新动态复证现已在 v4 完成；不把一个代表的原因外推到全部 922 或全部 unfinished。

主 Poison 代表的 mstatus=0x21000 进一步指向 MPRV=1、MPP=0b10（保留值）：`effectivePrivilege` 为数据访问取 `privLevel_bits(MPP,0)`，落入 core/types 的无效 privilege 默认错误。`core/types.sail` 也已核对与 bdd 固定模型逐字相同；它与 P3 的 zicfilp Hypervisor unsupported 是两项不同继承规则。

## bdd 计账与门环境的源码差异

已独立封存 [bdd 门环境与错误分支源码](bdd-gate-error-source.json)。bdd collector 在未配置 symbolic_csrs 时，把原始 `ctx.regs` 直接传给汇编和回环门，未用最终 Model 将 cur_privilege 等前态全部具体化。当前合流实现按用户合同传最终同一 Model 的具体前态，因此不能用 bdd 在另一个自由辅助权限下的结果直接证明同一机器状态合法。

此外，bdd `encdec_guard_roundtrip_ok` 的 Err 分支仅记录日志并 return，不调用 record_error；回环收集器还只保留最后一个 callback 结果。故 bdd 较少的 errors 可能是静默丢路径或后到成功覆盖错误，不证明新 922 是合法路径回归；同样不能未逐例证明就说旧版本把所有 922 都写成错误 gen。新旧完整同输入复证需要同时观察全部辅助终态和实际 gen/诊断，分开说明“旧不完整输出”与“旧静默丢错”。

## 完整门寄存器捕获补充

第二轮 P3 捕获已保存于 [v2 收据](captured-v2/receipt.json)：门所用寄存器总计 183 项，其中 145 项已初始化、38 项明确未初始化；另有 102 项完整前态输出。直接复放必须保留这一区分，跨 IR 按寄存器、字段和 enum 名重建值，不得复用 Name ID 或以默认值补齐未初始化项。该 v2 收据只证明实际捕获；后续新旧同输入复放见下节独立 v4 收据。

## 新旧同输入复证（v4）

实际文件及哈希见 [独立收据](replay-v4/receipt.json)，逐项比较见 [机器核对](replay-independent-checks.json)。新程序源于 Isla `4d085b14`，旧程序源于 `bdd047bc` 的完整 archive；810 个旧 tracked 文件逐项核对，只有本次诊断的 `src/isarch/exec.rs` 不同。新副本也只有该诊断文件有 tracked 修改。两侧补丁均已独审，保留各自原 helper 聚合逻辑，增加完整状态快照、SAT/异常日志和预设退出；不修改生产树。

- P3 两侧各用对应 Rust 程序及 IR，机器字均为 `0x01ffb023`。141 项 CLI pin 加初始化默认值形成实际 183 项门寄存器；独立规范化逐项比较与原 capture **零差异**。145 项已初始化值（包括 CLI 不能表示的两个 Unit、PMA List 和 TLB Vector）及 38 项未初始化状态均相同。
- 两侧观察到的 Finished 终态均仅一条、均 SAT，均为 Poison 和同一个 `zicfilp_regs.sail:31: Hypervisor extension not supported` 异常。旧 helper 返回“译码结果不是指令构造子: Poison”，新 helper 返回“译码回环返回非具体值: Poison”；文本不同，实际异常相同。v4 逐条日志覆盖 Finished callback，其他 callback 分支尚未逐条记日志，故不以此声称已枚举所有类型的 callback。
- 主执行两侧直接重建原 STORE 构造子：imm=0、rs1=rs2=31、width=1；width 按名义 `%i64` 类型构造为 I64(1)，与原最终 Model 输出的 64 位值1一致，不通过 sd 机器字重译。102 项完整前态与捕获逐项相同，两侧 SAT、顶层 Poison，实际异常均为 `core/types.sail:78: Invalid privilege level or virtual mode`。预设退出87/88为诊断完成，不记正式求解 PASS。

因此，**该 P3 代表不是合流新增的合法路径回归**：在最终见证的同一完整具体状态，旧 IR/旧解释器也触发相同模型内部错误。新版 failclosed 拒绝该见证合理；旧程序原 collector 在另一自由门环境中成功、或静默丢弃 P3 错误，均不能证明该具体见证合法。主执行 width1 代表也已经实证为继承的 MPRV/保留 MPP 边界。

v4 时尚未逐例分类全部 922/112，C_LD 的7条未完成当时也未捕获异常代表；后续 C_LD 补证见 v5。不能据有限代表宣称全量错误都已解释、旧版全部输出都错或完整原域 Make 通过。旧原域完整运行尚未结束，另由动态验证记录其外限/结果，不以有限诊断替代。

## 最终 v5：全部 callback 与 C_LD 代表

后续补证的 [v5 收据](replay-v5/receipt.json)和[逐项机器核对](replay-v5-independent-checks.json)保留新阶段版本，不改署 v4 历史。v5 两侧诊断 callback 已覆盖 MatchFailure、其他执行错误、Finished 和其他 Run；实际每侧均只有一条 callback，Finished、SAT、Poison，仍为同一个 zicfilp Hypervisor unsupported 异常。新旧实际 183 项门寄存器各与原 P3 capture 零差异，因此 v4 的非 Finished 日志限制现已关闭。

C_LD 新捕获的原请求三字段均0（5/3/3位），path-signature=`9876273536327509654`，SAT，cur_privilege=VirtualSupervisor，mstatus=0x21000。诊断在两侧直接重建该原构造子，102 项完整前态分别与捕获逐项相同，返回值均为顶层 Poison；异常文字与 throw 位置均为 `core/types.sail:78: Invalid privilege level or virtual mode` / `prelude/errors.sail:21.41-21.106`。该代表与 STORE 主执行同属 MPRV=1、MPP=0b10 保留编码导致的继承模型边界。

最终分类限于三个代表：P3 在同一完整 gate state 的继承模型异常已证，拒绝该代表符合单最终 Model 与 failclosed 合同；STORE/C_LD 顶层 Poison 代表的继承异常也已证。没有修改生产代码、扩大配置域或加入状态过滤策略。尚未逐例分类全部922条错误、112/7条未完成，因此两项完整原域 Make 继续如实标 partial。
