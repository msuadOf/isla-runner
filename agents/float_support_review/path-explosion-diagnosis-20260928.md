# 73df 全域 FVFTYPE 超时机理核账（2026-09-28）

## 入口口径：译码为何进入符号执行

先前[求解审计方法](solve-audit-method.md#2-真实入口与输出的含义)描述的入口确实直接调用 `zexecute`，结果物化时才具体编码；它符合“先求 execute，再用具体编码得到字符串”的理解。**本次 73df/77 浮点目标没有走那个入口。**冻结运行器的 `SolveEntryMode::for_clause` 对 `official_float77.txt` 中的 FVFTYPE 选 `FullEncoded32`，`run_symbolic_execute_with_target` 随后选择 `zisarch_solve_wrapper`，而非直接 `zexecute`。该 wrapper 在同一个符号 frame/solver 中依次调用 `zencdec_forwards → zext_decode → zexecute`；[实际trace入口证明](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-2h-20260928/evidence/entry-mode-proof.json) `0e9c36d1…42744`中的译码分支带有 `zisarch_solve_wrapper:4 > zext_decode:0` 调用栈。因此下面的2544个译码fork由**运行器入口选择＋全模型decoder生成顺序**造成，不是 Sail 的 FVFTYPE `execute` 自己调用译码，也不是末尾输出字符串的具体编码。冻结运行器见 `isla/target/float-solve-evidence/num-elem-order-rm-eq-2h-20260928/stage/src/isarch/exec.rs:42–49, 77–85, 1061, 1102–1106`。

后来[架构方案](solve-fix-architecture.md#22-明确三个阶段)明确选择符号编码、译码、执行同路，以约束机器编码可达性并把无法编码、译码拒绝及执行非法分账；这解释了实现动机，**并不证明这项额外符号译码成本是当前目标必须承担的最优方案**。若改回仅求 `execute`、结束后具体编码/译码，本次全模型decoder的fork会离开求解热路径，但原先 wrapper 在符号域提供的编码存在性、decoded/requested一致性及拒译分类须另行补证，不能把两种入口的完成数或覆盖证据直接互换。

## 版本、输入和退出

隔离 IR SHA-256 为 `73dfb2e17bfbd67686442cc59bfd69e2ca84a497db345d04abb2916bfb671d2a`；Sail 来源是 `isla/target/float-solve-evidence/num-elem-order-rm-eq-candidate-20260928/sail-riscv/`，关键文件 `model/extensions/V/vext_fp_insts.sail` `2417a6bc…576e6`、`vext_utils_insts.sail` `e1401308…15a9`、`vext_control.sail` `ffb8d575…cef6`。诊断运行器 `e7ba503a…10f81`，冻结 `executor.rs` `d758a3e5…c8dd`、solve wrapper `exec.rs` `a1a40078…b534`；77 活跃 strict 配置绑定本 IR，输入仍为完整符号域、完整 ITRACE、j1×T2、7200/7140/30 秒、`qfaufbv`、`thread_interrupt`。正式主 IR 仍为 `d012`。

[两小时 stage](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-2h-20260928/evidence/exit-audit.json) `78a07ed4…ee72e` 在 7201.319 秒外限 child124、make2；无 supervisor signal、资源止损或最终 `rv64_zFVFTYPE.json`。残缺日志 2212 终态＝33 Retire＋2176 Illegal＋3 non-encodable；trace 2,687,990,476 字节仅封哈希，不签完整守恒。旧 `56cc` 的 57/77 完成数不变。另 19 个候选目标各 30 分钟也全部外限124、无最终 JSON，见[20项汇总](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-candidate-20260928/target20-exit-summary.json) `89922cad…6327be`；19项使用 b42 运行器，不与 FVFTYPE 的 e7ba 性能计数混用。

## 单次 SMT 查询与总量

[完整 Z3 配对统计](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-2h-20260928/evidence/z3-duration-audit.json) `63ea5bcd…e49e` 对 609,782,038 字节 JSONL 逐个 begin/end 配对；与独立 v2 [结构汇总](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-2h-20260928/evidence/z3-final-summary.json) 的 790352 条已完成操作一致，末尾 2 条未完成不补耗时，0 残行。

| 操作 | 已完成次数 | FFI 总秒 | p50 秒 | p99 秒 | 最大秒 | ≥5 秒 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CheckSat | 22871 | 4875.168 | 0.00352 | 1.2363 | 4.3982 | 0 |
| CheckSatAssuming | 72808 | 9218.938 | 0.00310 | 1.0013 | 3.0566 | 0 |
| ModelEval | 694673 | 2.226 | 0.00000233 | 0.0000412 | 0.000701 | 0 |

两类 SAT 检查合计 95679 次、14094.107 秒 FFI；已完成 FFI 总量 14096.333 秒占对应 worker 窗口 14382.102 秒的约 98.0%。12 个十分钟窗口均有 5012–14339 次已完成 SAT 检查、约 1158–1181 秒合计检查 FFI（T2 两 worker），没有单个数十秒／数分钟查询主导的证据。末尾两条查询在外限前开始，没有 end，不能给它们推定 FFI 时长或结果。`SourceLoc=unknown` 的 CheckSat 有 11019 次／3562.060 秒，冻结 runtime 的物化与 witness 路径存在多个无位点调用；现有 v2 记录不足以将这些秒数精确归给某一调用点。

## 实际路径分叉来自哪里

[分叉账本](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-2h-20260928/evidence/fork-audit.json) `a8dda7ff…13bb62` 从残缺日志读出 **6828 个实际 fork、39 个来源位置**。冻结 `executor.rs` 第 1594–1658 行先检查真假两向 SAT，随后才记录 `FORK` 并向 `fork_sink` 提交另一条路径，因此这些不是仅看见符号条件的静态计数。它们不能与 2212 个终态相减并直接宣称精确排队数，因为还存在死亡路径与外限中的 worker。

| 来源 | 实际 fork | 约占总量 | 源码/IR 对应 |
| --- | ---: | ---: | --- |
| 全模型反向译码 | 2544 | 37.3% | 生成 IR `zencdec_backwards` 的 `33365`/`33236`/`33279` 分别 862/822/293，映射 Sail `VFUNARY1`、`VFUNARY0`、`VFWUNARY0` 的 encdec 条款；`zbool_bit_backwards_matches:1080` 另 567 |
| 寄存器组正负 LMUL 判断 | 1449 | 21.2% | `vext_utils_insts.sail:53` 的 `if EMUL_pow > 0`，符号来源 `vtype` |
| FVFTYPE execute 非法 guard | 1305 | 19.1% | `vext_fp_insts.sail:1904–1908`，复合 `illegal_fp_normal`、两次组对齐及 slide overlap；taint 为 `vtype`＋`fcsr` |
| vstart 上界 | 356 | 5.2% | `vext_utils_insts.sail:284–286`，taint 为 `vstart` |
| num_elem 合法集合 | 至少 330 | 至少 4.8% | `vext_control.sail:139–159` 的外层范围及 match 分区，taint 为 `vtype` |
| 特权态 LPE 选择 | 402 | 5.9% | `zicfilp_regs.sail:25–26`，taint 为 `cur_privilege` |

冻结 IR 在 `VFUNARY0` 反向译码分支先运行 `encdec_vfunary0_vs1_backwards_matches`（PC 27942，生成位置 33236），随后才检查固定 opcode、`funct3=001` 与 funct6；`FVFTYPE` 的 `funct3=101`。`VFWUNARY0` 与 `VFUNARY1` 对应 PC 28107/28319 同类。因 solve wrapper 实际顺序为 `zencdec_forwards → zext_decode → zexecute`（冻结 `exec.rs:63–88`），这些生成 decoder 的早期子字段匹配在本 clause 的完整符号编码路径上真实分叉，尽管后续固定字段可排除相应其它 clause。这是跨条款译码分叉的具体来源，不是 FP 数值循环慢查询；本轮 `vext_fp_insts.sail:1928–1950` 循环区域只有 48 个实际 fork，且局部成功终态仅 33 条。guard、LMUL、vstart 与其它状态维度随后继续组合分叉。

**判断：当前外限主要由路径分叉及其累计 SAT 检查造成；单次 SMT 查询未呈现失控。** 其中最大一组可见分叉来自运行器选择的符号编码/译码入口，不能归咎为 Sail `execute` 自身的必要成本。该判断限 73df、e7ba、FVFTYPE 两小时残缺前缀。它没有证明完整路径总数，也没有证明只优化任何一个位点即可使目标自然完成。下一步先审定求解入口究竟需在符号域保证哪些编码/译码关系，再选对应的最小验证方案；所有候选仍须保持完整符号输入域与版本隔离，并分别重做严格配置、C++/Isla 重放及完整求解核账。

在用户要求先诊断后，未再启动模型求解；先前隔离寄存器组 bit 测试候选的两次类型错误日志保留。第三次构建的交互会话在停止操作后返回130，但[构建报告](../../isla/target/float-solve-evidence/reg-group-bitmask-build-v3-20260928/model-build.json) `54979da3…491f7`已落盘为PASS，生成 C++、模拟器与 IR `fa36a733…366a1`等七件输出的实际 SHA 均与报告一致。因此仅签**隔离构建产物**，尚无严格配置重绑、helper/整指令回放或新求解证据；该候选未进入生产 Sail 或正式主 IR。末尾追加 helper 的另一副本未构建。
