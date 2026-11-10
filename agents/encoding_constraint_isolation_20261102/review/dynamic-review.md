# 动态产物独立复核（初版 de00adb）

状态：初版 de00adb 的新模型、定向验证及新旧两条完整 flags 已签收；旧 eager sat 诊断最终TIMEOUT。初次待办状态保留为历史，后续 flags 结果见末节。本文件不适用于保留指令断言的新源码。

受测正式 Release 为 Isla `de00adb`，程序 `e95fa842…533ab`，官方 Z3 `1fd1d3613`/库 `899cbc70…9970`；新模型 `6202e23` 的 V128 IR 为 `a877e245…f97e`。完整哈希由各结果文件和独立复核 JSON 保存。后续 Isla `8e5a3f7` 仅同步 IR 及永久回归，已审两份 Rust 源码未改变。

## 完成性及语义

- 新模型 VFUNARY0 使用原 sat 配置，seed17、T1、qffp、进程与 SMT 预算各7200秒；自然退出0，墙钟37.16秒，46条见证（22退休/24非法），summary 为 finished，采样、错误及各 partial 字段均0。该配置完整 Clause 完成；不外推未测配置或全域源码覆盖。
- 独立 [check_sat_json.py](check_sat_json.py) 使用 Python 精确有理数和五种舍入公式检查实际 f16→i16 见证，覆盖正溢出、负溢出、范围内及不活动 lane；检查数值、flags、目标寄存器其他位、不相关向量寄存器保持。全部46条见证的初始 vtype/vl/vstart 和机器码、opcode、字段与字节表示也一致。结果见 [sat-json-checks.json](sat-json-checks.json)。这批见证不保证穷尽 f16 NaN/Inf 等全部数值类别；出口公式本身的全 sig32 等价检查另见源码审查。
- 56项定向完整 Clause 共156条 JSON 的来源、最终状态及3518条语义检查独立重算通过；另核9272个具体初态字段值，未发现隔离候选约束使初态配置失效。定向 wrapper 的全部假设均从本轮新 IR 正确附加，其余内容逐字一致。BF16 FMA 及 flags 再次由独立 SoftFloat oracle 检查，源角色、NaN、mask/vl≤2 范围保持原验收边界。
- BF16两批和压缩例共13条 JSON，GCC/Clang三表示78项证据逐项复核；成功项的实际 `.bin` 字节与 JSON 编码完全相同，4个 Clang 非法布局助记符拒绝符合记录，精确位串和 `.insn` 仍有字节对应。C_ADDI4SPN 的实际编码解出目标寄存器和立即数，后态等于初始 x2 加立即数，返回已退休。
- 正式 Make 入口退出0、3.51秒、8条 JSON；原 qNaN 左右角色检查重算通过，48项 GCC/Clang 实际字节与编码相等。共计上述三表示和 Make 126项工具链检查。详见 [directed-results-checks.json](directed-results-checks.json)。

五处安装 IR 的25步完整回归记录均退出0，日志存在并保存独立哈希于 [ir-regression-evidence.json](ir-regression-evidence.json)。该项为检查原命令和日志，未重复运行全部25步。

## 初次签收时的待办（历史）

旧 flags B 与旧 sat B 原 IR/配置的哈希已核实，使用相同新程序、官方库、seed17及7200秒预算。二者最终结果未到前，不从新饱和完成或单路径速度推导旧完整输入已提速、已消除超时或 flags changed 可以恢复。

## 初版 de00adb 完整 flags 结果补充

上节“尚待结果”是初次签收时的历史状态。后续原旧 flags 显式 B 与当前生产 IR 的完整 flags 均已自然完成，现签收这两项结果；旧 sat 仍待。以下只适用于程序 `e95fa842…533ab`（de00adb），不迁用于保留指令断言的新源码。

|完整 Clause 输入|墙钟秒|JSON|退休／非法|退休 flags 改变／不变|新增 NV|
|---|---:|---:|---:|---:|---:|
|原 flags 显式 B，原 IR `c450a442…f09`|2884.43|328|280／48|120／160|103|
|当前生产 IR `a877e245…f97e`|1615.96|728|680／48|338／342|320|

两项使用相同原配置 `20851fdb…3d0`、seed17、T1、qffp、完整 Clause 和单次 SMT 7200秒。退出0，完整 JSON summary finished，采样、错误、超时和各 partial 字段均0。输入、输出、seed 拦截及日志哈希逐项核实。

独立 [check_flags_json.py](check_flags_json.py) 检查全部1056条编码字段、助记符寄存器及字节表示；对960条退休见证逐条按实际 RM 和初始 FPR 做 NaN-boxing、SoftFloat 算术与异常位核对，并检查其他 FPR 保持。对96条非法见证检查 FPR/fcsr 不变。共41088项检查通过，详细来源与计数见 [flags-json-checks.json](flags-json-checks.json)。

原 flags 显式 B 在本配置已经低于7200秒预算，不能继续把它描述为“本版未解决的2h超时”。历史旧程序达到外限的记录仍成立，但这里只签收本版单次完整结果，不计算删失样本的精确提速倍数。两份 IR 的控制流不同、见证集合不同，不用1615.96与2884.43计算等覆盖加速比。当前生产模型仍不包含恢复 flags changed 显式分支的新修改，不能从当前生产 IR 完成推导那项恢复已验收。


## 旧 eager sat 诊断最终结果

初版de00adb的旧 eager-lane sat B 诊断最终为TIMEOUT：7200.20秒进程外限退出124、无完整JSON/summary，不计PASS。原IR/config、程序/官方库来源、seed和计时已核，详见 [终态元数据](old-sat-diagnostic-terminal.json)。前文旧sat“仍待”是当时历史状态；修订版cf1aa14的新模型正式验收结论见最终报告。
