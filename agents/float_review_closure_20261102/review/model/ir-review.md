# 四配置 IR 独立审查

模型 `8ad5e8e9e0fc2a567a3b989a3738698f5c520bde` 的 ordinary 严格检查、四配置 SYMBOLIC 严格生成及实际 IR 控制关系通过。六个受审模型文件与源码签收哈希完全一致。永久 CFG 检查器的候选实现仍有已复现的误绿，待修复后单独签；动态 oracle、条件见证与完整 Clause 预算由另一个独立审查者验收，本文不签动态结果。

| 配置 | 新 IR SHA-256 | 目标函数实际 CFG |
| --- | --- | --- |
| RV64 VLEN128（亦为 default 别名） | `5ecea3717205dda77bc3cdbaf7a6b677415152e1f5cd09e541d0530519e25017` | 54项通过 |
| RV32 default | `df3dfd02cecd184e8ed2adfcdab4c4d3a4e15afba274ab51c0c2d63041744eb0` | 52项通过 |
| RV64 VLEN256 | `fbc1f8953810f63b1f092929e26802f816bc7f5e354e170afae35a51d71c2922` | 54项通过 |
| RV64 VLEN512 | `a699d34c4c9c52da15d6924f6788d641880b2c7f331b0f55fce42bddc576bbdc` | 54项通过 |

[生成来源审计](generation-provenance.json)独立回读166个已跟踪模型输入、149个实际 Sail 二进制/标准库/插件/配置/生成 driver 文件。全部命令含 strict-var、strict-bitvector、strict-exponentials 与版本0.20.1约束，SYMBOLIC 含实际 `-D SYMBOLIC`；五个生成/检查进程退出0且源未变。原记录误把忽略的 `model/sail_smt_cache` 计入文件列表，后补审计保留原记录并将它与166输入分开。编译时实际 Z3 CLI 为4.16.0，仅用于 Sail 类型约束；运行时官方 Z3 库另有哈希，不把两者混写。

新旧同配置函数比较去掉源位置、assert 位置与按签名位置变化的生成参数名后，RV64 仅54个目标函数体变化，RV32 仅52个；`zexecute` 和所有活动 lane gate 保持。RV32 主项目不调用 f16→I64/Ui64，旧新均未输出这两个函数。新 IR 不再输出无主项目调用的 `riscv_f32_to_f16_normal_rm_bits`，源码定义为现有独立测试探针保留。记录见 `ir-delta-*.json`；原始未规范化差异另存，未掩盖算式变化。

独立 CFG 审计分为 [原因与舍入出口](audit_cfg_relationships.py)及[窄化、包装和 ROD](audit_remaining_cfg.py)，每配置结果在 `cfg-relationships-*.json`、`cfg-remaining-*.json`。检查实际 Jump 条件、真/假独占可达节点及支配，不以总 Jump 数替代：

- changed 的比较确实来自 old 与 old|flags，changed 和 Ext_F 两个真臂支配唯一 mstatus.bits 写；原两个 CSR callback 在合流后。
- 六窄适配器的 overflow 追到同一32位候选的精确低位符号扩展或高位零比较；正常臂保留原 flags/低位，饱和真臂只用 NV，signed 正负位31与两个端点相符。
- 18个算术异常 helper 均先做各源 NaN 分类；Inf 抵消、两位置零×Inf、0÷0、Inf÷Inf、DZ、负非零 sqrt 和 FMA 抵消的独立真臂只返回相应 flags，后续原因仅在前因假臂。finite/valid 真臂支配全部更宽转换、两个 directed 运算与 rounded helper，特殊路径绕过它们。
- 四个 rounded helper 的 OF、UF、NX 三层出口返回对应实际 flags；未用 OF⇒NX 或 OF/UF 互斥删原事实。整数核心的 finite/范围/NX 层级及转换、round、mask 的有限值门控保持。
- 12个 FP→整数包装按 invalid、NaN、符号分支；NaN（含负 NaN）优先选最大值，合法臂保留候选。两个 ROD wrapper 的模式真臂只用派生 ROD，假臂才解码普通 RM；两个 ROD helper 在 inexact 真臂对原 base OR 1，假臂保留 base，二者 flags 相同。

除架构相关 F1 外，V256/V512 的53个目标函数及 RV32 的51个共有目标函数与 V128 去源位置后逐字一致，见[跨配置核对](ir-crossconfig-targets.json)。这支持四份实际 CFG 关系一致，不替代不同静态配置的动态预算。

[workaround 来源审计](workaround-source-audit.json)核79配置、132region、22注释锚点通过；六个改动文件未被任何 region 引用，因此无需坐标迁移。旧基准 IR 哈希只按原 strict=false 契约告警，未改成新控制的跳过机制。

永久检查器当前误绿的五个具体负变异见 [记录](checker-negative-controls-intermediate.json)：changed 改成 old==old、SD写0、0÷0条件换Inf÷Inf、finite条件换0÷0、signed overflow改成候选自比较。它们说明候选测试需要加强，不表示实际生成 IR 存在这些错误。永久检查器源码/红绿与负变异修复另行签收，不能由本文实际 IR 通过代替。
