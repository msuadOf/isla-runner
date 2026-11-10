# 饱和分支 IR：独立签收

结论：四配置严格生成、普通严格检查、实际 CFG 与五处安装来源审查通过，无阻断。完整 Clause 与 JSON 结果在后续单独签收。

独立 [check_ir.py](check_ir.py) 逐项核对了四份 `generation.json`/`driver.json`：均退出0，起止模型提交均为 `6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a`，干净源码，生成前后源码不变。每份166个源文件的哈希同时与 Git 提交内容和实际源码核对；Sail launcher、插件及配置哈希与实际文件一致。结果见 [ir-checks.json](ir-checks.json)。

四配置与上一轮正式生成 IR 逐函数比较，去除位置和临时/形参的改名后，仅 `zriscv_f16ToI16_pure` 改变。新 helper 的唯一 Jump 检查 `not(sig32 == sign_extend(sig32[15..0]))`；真臂计算 NV 并使用正负饱和值，假臂保留原 flags 和低16位。符号位选正负限幅的数值 ITE 保持。永久回归在四份新 IR 全部通过，20个活动 gate、源 NaN、NaN 出口及 FMA 检查保持有效；VFUNARY0 的活动 gate 仍支配 helper 调用。

新增永久测试的旧 ITE 红例与显式 if 参考绿例已独立重跑；将符号扩展改成零扩展、改反 overflow 谓词、改错真臂目标的三个负变异均被拒绝，见 `ir-regression-pilot.json` 和 `ir-regression-mutations.json`。

普通严格检查在 `a9fd947` 加未提交补丁时启动，检查途中把相同字节提交为 `6202e23`。其初始记录 `driver.initial.json` 保留；全部166个源文件与最终提交及四配置生成字节一致，故这一检查适用于最终源码。未把起始提交误写成干净 `6202e23`。

五处安装 IR 的实际哈希与四份生成产物和安装 manifest 全部相同，manifest 模型及166个源文件哈希、配置和插件也逐项匹配；Sail 实际编译器的哈希亦核实。见 [installed-ir-checks.json](installed-ir-checks.json)。未因本轮仅改变该 helper 的源码而移动任何 workaround 区域。
