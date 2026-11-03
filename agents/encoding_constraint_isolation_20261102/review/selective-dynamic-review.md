# 保留指令字段断言版：动态独立复核

状态：修订版约定的正式验收全部通过，含新饱和、新生产IR完整flags、旧显式B完整flags、56项定向与三表示/Make。此前待办状态保留为历史；最终旧显式B结果见末节。初版 de00adb 的独审证据独立保留在 `dynamic-review.md`，不能当作本版通过结果。

受测源码 `cf1aa1431d5f2d05584c78c0e7c84862a9a9b1fa`，冻结程序 `abce451a11e0e4a8a3c9658d4a8462634f284085f219cca79f439ca176853a1a`；实际文件及官方 Z3 库 `899cbc70…9970` 核实一致。两份 Rust 受审源码与 `selective-source-manifest.json` 一致。模型/IR 未改变：Sail-RISC-V `6202e23`，V128 IR `a877e245…f97e`。

## 已签收结果

- 新饱和 VFUNARY0 使用原 sat 配置、seed17、T1、qffp、完整 Clause/SMT 均7200秒，自然退出0、22.33秒、46条JSON（22退休/24非法），所有 partial/error/sample 计数0。独立精确有理数计算、flags、机器码/字段与前后态共662项检查通过，含正/负溢出、范围内及不活动 lane；见 [selective-sat-json-checks.json](selective-sat-json-checks.json)。
- 56项定向完整 Clause/156条JSON全部 finished，3518项语义断言独立重算通过，并核对9272个具体初态值。全部定向 wrapper 的原假设来自本版同一IR，程序/IR/config/output 的哈希一致；没有把初版产物迁记成本版结果。见 [selective-directed-results-checks.json](selective-directed-results-checks.json)。
- BF16两批和压缩例共13条JSON的78项 GCC/Clang 三表示证据复核通过；成功项的实际 `.bin` 字节与机器码相等，4个Clang非法布局助记符拒绝符合预期。C_ADDI4SPN 的寄存器和立即数从机器码独立解出，续执行后态与初始 x2 相符。
- 正式 Make 入口自然退出0、3.19秒、8条JSON；15项语义断言独立重算，48项三表示实际字节复核通过。与上一项合计126项工具链检查，见 [selective-representation-results-checks.json](selective-representation-results-checks.json)。

当前限定域验证未发现依赖筛选改变可达编码、初态配置、数值/异常位或续执行状态。特殊值验收仍是原固定域及 vl≤2；不能据此宣称整个模型控制流或全部具体编码覆盖完整。

## 初次签收时的待办（历史）

本修订版的旧 flags 显式 B 与当前生产 IR 完整 flags 正在运行。待实际退出、完整JSON、原输入哈希及数值检查完成后再签性能。初版的2884.43秒与1615.96秒仅属于 de00adb，不沿用到 cf1aa14。

## 当前生产 IR 完整 flags：后续签收

`validation/runs/selective/new_flags` 已自然退出0、1127.51秒（user1118.55/sys7.71），728条JSON，680退休/48非法，summary finished，所有 partial/error/sample 字段为0。冻结程序仍为 `abce451a…53a1a`，实际官方库及 seed17 复核一致；原 IR `a877e245…f97e` 与配置 `20851fdb…3d0` 未变，T1/qffp/7200秒预算。上节“两项待结果”仅适用于初次签收时；本节签收当前生产IR这一项，旧显式 B 仍待。

全部680条退休见证的实际 NaN-boxing、SoftFloat 数值、舍入模式、flags 累积及其他FPR保持均正确；48条非法见证的FPR/fcsr保持正确。连同全部编码/字段/字节核对，共28344项检查通过。退休见证 flags 改变338、不变342、新增NV320。精确来源及逐条见证见 [selective-flags-json-checks.json](selective-flags-json-checks.json)。

同IR初版de00adb与本修订版的 `(path-signature, ret_val)` 多重集合完全一致，均有692个键、728项；见 [selective-flags-path-comparison.json](selective-flags-path-comparison.json)。这是本输入下没有少掉已输出路径见证的检查，仍不代表穷尽同路径下每个数值、寄存器编号或机器码。两版同输入墙钟分别为1615.96与1127.51秒，均为一次运行记录，不宣称稳定提速比例，也不把本次结果迁用于旧显式B。

## 逐条语义字段比较补充

独立从原始JSON重新构造多重集合，确认初版与修订版的56项定向156条、新饱和46条、新flags728条，共每版930条，均在 `test-ins`、`test-ins-encdec`、`isa-state-complete`、`isa-state-post`、`ret_val` 五个字段上逐项相同，重复次数也相同。原始JSON哈希、同任务两版IR/config哈希及各自程序版本均已核；实施方三个 `semantic-comparison.json` 的逐项计数与独立重算完全一致。见 [semantic-comparison-checks.json](semantic-comparison-checks.json)。

该比较排除了文件顺序和运行来源元数据，只确认本批已生成见证的具体语义字段未变；不把有限集合相同扩大为未生成数值、所有机器编码或全域源码覆盖相同。此前数值/flags与配置核验仍使用各自批次的独立结果；本补充未重复跑Clause、oracle或Rust测试。修订版旧显式B在本次补充时仍未结束，未预判其结果。

## 旧显式 B 完整 flags：最终签收

最后一项 `validation/runs/selective/old_flags` 已自然退出0、2626.07秒（user2582.16/sys40.43），328条JSON，280退休/48非法，summary finished，所有 partial/error/sample 字段为0。冻结旧IR `c450a442…f09` 和原配置 `20851fdb…3d0` 不变，程序 `abce451a…53a1a`、实际官方库 `899cbc70…9970`、seed17/T1/qffp及7200秒预算全部核实。

独立核全部编码、NaN-boxing、SoftFloat数值、flags、其他FPR保持及非法FPR/fcsr保持，共12744项检查通过。flags改变120、不变160、新增NV103。结果见 [selective-flags-json-checks.json](selective-flags-json-checks.json)。本版与初版这328条见证的五个具体语义字段多重集合完全相同；最终56项定向156条、新饱和46条、新flags728条、旧flags328条，合计两版各1258条相同，见 [semantic-comparison-checks.json](semantic-comparison-checks.json)。

本任务约定的正式验收现已全部通过，无剩余源码或正式结果阻断。最初旧 eager-lane sat B 的初版2h任务是单独诊断，不作为修订版正式验收项目；其最终TIMEOUT记录见末节，不计PASS。完整验证结论仅限记录的输入/配置；有限见证集合一致不证明全域具体输入覆盖，现有特殊值固定域与其他宽度控制流义务保持原边界。

实施方随后保存的旧flags `semantic-comparison.json` 与 `coverage.json` 也已逐项核对，原始文件哈希、例子及计数与独立原始JSON重算相同。覆盖字段的 `NVTrue` 表示本指令新增NV（`post & ~pre`），不是后态NV绝对值；结果见 [selective-old-flags-coverage-checks.json](selective-old-flags-coverage-checks.json)。


## 旧 eager-lane sat：诊断终态

初版 de00adb/e95fa842 程序对冻结旧 sat B IR `d29e971b…46bf`、原配置 `da35c576…326f` 的诊断任务已在7200.20秒进程外限退出124，user7119.08/sys71.91，无完整JSON、无summary，结果为TIMEOUT，不能记PASS。官方库、输入文件、seed17、T1/qffp、双7200秒参数、日志及计时均只读核实，见 [old-sat-diagnostic-terminal.json](old-sat-diagnostic-terminal.json)。

这是旧模型仍对不活动lane提前做转换的初版诊断输入，不能写成修订版cf1aa14的新模型失败。本次未重跑测试；修订版三条正式Clause及其他已签收结果保持不变。此前进行中表述只适用于原记录时点。
