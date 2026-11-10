# 浮点最终限定签收

**用户授权的本轮浮点收敛验收通过，无剩余阻断。** 签收范围是[终验矩阵](final-exit-scope.md)：77处已批纯数据回退等价，NaN/trap保持，OPEN按用户决定冻结并延期memory；本轮不继续扩展研究，也不把延期OPEN改成永久KEEP。

模型：`0f7b8fbc6724103f91f929ef6918f123df75d6c9`。集成Isla：`591693df2bc32019ea300511509ed683df09522e`，Git树`8ea0df2093dcd379b408154057ca391ee8ceb7cd`。完整机器签收与全部证据SHA见[final-signoff.json](final-signoff.json)，逐项审查见[结果报告](model-converged-results-review.md)。父仓最终gitlink提交由主agent后续refseal，以下受测组件和内容不因此改署。

| 验收 | 最终实际结果 |
| --- | --- |
| 源码/IR | 77处精确回退；ordinary+四配置SYMBOLIC strict；四IR数值DAG不变，独立返回比较276,672组通过 |
| 永久检查与安装 | 8项正控、104负变异拒绝、安装五入口绿；完整run-all 26/26步骤通过 |
| 新定向数值/状态 | flags300、转换819helper+282scalar+183vector、315实际JSON全部独立复算通过，来源/seed/约束IR/所列保持状态分别核对 |
| 汇编与Make | 新1104前向输出、5824指令字节检查通过；25个GNU能力拒绝保留且有精确替代；真实Make8JSON/48检查通过 |
| 两正式完整入口 | FLEQ_S 48条/27.67秒，C_ADDI4SPN 1条/2.038秒；原完整符号域、T1/qffp/seed17/双7200，均自然exit0、finished/partial0；word/数值/后态/trace独核 |

运行程序仍是由`42000be47596ec088623881d03c0eadc5cf0ba27`构建的`acda0dceb259205fe0c43a3785484ffcafbef26b3194de3b9f67ad38eccbcf7d`。集成591只改下列六生成文件和四测试文件，146个Rust/Cargo/.cargo文件与420逐字一致；不声称591重新构建了该程序，不重写历史source manifest。新回归helper/state程序实际链接官方Z3哈希亦已独核。

最终315的summary于2026-11-03 09:27:52.557142 UTC全部完成；根Isla591提交在其后3.44秒，float两clone快进分别晚120.44/128.44秒。无任务受clone快进影响，且batch私有binary/baseIR与launch哈希相同，无需为该时序复验，见[时序证据](final-execution-timeline-independent.json)。

集成manifest SHA256为`6caab4ef6b1a2b95b2e78691dc6b23e6acecca708fca41f4f036834c866a7093`。精确十文件内容如下；V128与默认入口为同一产物。

| Isla内路径 | SHA256 |
| --- | --- |
| `ir/provenance/manifest.json` | `6caab4ef6b1a2b95b2e78691dc6b23e6acecca708fca41f4f036834c866a7093` |
| `ir/rv64d_v128_e64.ir` | `0fb0897e028803155108ec59f8289d4f89bafa98deb063bfa7f016a3d29f0786` |
| `ir/rv64d_v256_e64.ir` | `47ba73418d6dcb1b1e86db7680ce4df9508e7885a02096e25e213c2c3b2c05e1` |
| `ir/rv64d_v512_e64.ir` | `2bdea17d36c64545254f50cc5a6902e570a1fea682de3f7c062bf641a85a62a9` |
| `rv32d.ir` | `e17c4fe18552f8ce219b35f846c4c1a2c530dcad0ac9fc8f10d0da2604c3fa4e` |
| `rv64d.ir` | `0fb0897e028803155108ec59f8289d4f89bafa98deb063bfa7f016a3d29f0786` |
| `test/float_ir/README.md` | `d22a5f296534f4fbd44151dabbcb337eac7c1b9e766c653881c3c63caf010b87` |
| `test/float_ir/check_float_closure_branches.py` | `9ebd0d937edc805e49103984bffbb507470115d349d7262553b6943b9e2763cf` |
| `test/float_ir/check_special_semantic_branches.py` | `af14d3cbd4762bbaba5b6c80e16ea093c9ddba83e3d8e8d9364bea6db52e9d93` |
| `test/float_ir/run.py` | `d78fe01d66a542d26b531dfda4214d8a8a460c92bc0932c571d1c8a4332092cb` |

旧214批49PASS/28FAIL、e9批52PASS/25FAIL的53项失败逐一核实均是约7200秒外限124、没有完整JSON，不能算语义错误实证或PASS。原始证据迁存并保留逻辑symlink/哈希清单；独审核全部文件集合/大小、871个非trace SHA和迁前53失败结果相同，owner另核全部大trace SHA。

本次**没有宣称新版本全77Clause预算通过**，也不承诺全输入/调用者、全向量域、所有FMA变体、Zfinx、硬件差异测试或动态反解析。changed、29个finite/valid gate、2个ROD模式及既有f16→I16外overflow等OPEN保持，策略议题按用户决定延期memory。本签是本轮限定范围完成，可以据此收敛float。
