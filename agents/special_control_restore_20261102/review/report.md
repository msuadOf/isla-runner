# 特殊值控制分支独立语义审查

当前结论：10文件源码、四配置新 IR、安装五路径及56项定向结果的独立审查均通过，无阻断，可以提交。审查基线为模型 `fd71c9ab58fe6f41b97c976a5f7e470318c708a8`，实际受审文件哈希见 [source-evidence.json](source-evidence.json)。本 agent 只写本审查目录，不修改生产源码，不启动子代理。

## 已核对的源码行为

- 新 `ieee_operand_invalid(signaling, raw)` 对每个操作数先分 NaN/非 NaN，再分 sNaN/qNaN。EQ 和 quiet 比较只令 sNaN 产生 NV，ordered 比较令任一 NaN 产生 NV；两源均分别求值，最后 strict OR。算术两源与 FMA 三源也通过 strict 函数参数分别求值，不因前源成立而短路。底层纯分类谓词保留 strict Bool；新 IR 已核实每个角色调用及 helper 内两个真实谓词 Jump。
- f16/f64 及跨格式、BF16 NaN 出口改为同条件、同 canonical 常量的 if。非 NaN 的 IEEE 位串未改；boxing 不在本补丁内修改。ROD 模式选择与最低位奇数化保留原数值公式，窄化 flags 与结果原配对不变。
- 20个剩余运算循环将纯转换/运算、lane 写回及 flags OR 放进实际活动 mask；结果仍以 initial_result 开始，不活动 lane 保留其 prestart/tail/mask 初值。比较目的 mask 位仍保留不活动初值。归约 RFWVVTYPE 仍按 lane 递增更新 sum，先宽化再相加，不重排浮点加法。
- BF16 VF 的标量纯转换移入活动 lane，故 vl0/全屏蔽不会进入该新增特殊值分类；标量、向量、累加器的转换/FMA flags 仍只合并在活动 lane。BF16 quiet bit 仍是尾数 bit6。VV/VF 仍单次调用 riscv_f32MulAdd，内部单次 native fp32_fma；没有把融合运算拆为乘加。
- 审查发现初版同时删除普通模式 VFWMACCBF16_VF 的标量绑定，造成引用未定义；实施方已恢复。修后五个 V/BF16 文件的所有 `$else` 普通实现与基线逐字一致。共用 IEEE helper 的 strict_or_bool 是普通函数，c extern 仅供 Isla 绑定；新增 helper 本身有普通 Sail body，未引入新的外部接口。

## 独立辅助核算与限制

以 IEEE 指数/尾数字段独立计算，穷举65536个 f16 位模式、f32/f64各50个边界模式，在 signaling 两取值下，新 helper 与原 `sNaN OR (signaling AND NaN)` 相同。穷举65536个 BF16 位模式，新三分支的 flags/canonical/位拼接与原二 ITE 相同。四 lane 各取10种 flags、16种活动组合，共160000组，受 mask 的原 OR 与活动 if 后 OR 相同。这些是字段真值和组合代数核算，不是 Sail/IR 动态执行 PASS。

完整 Clause 外限和 SMT 均须7200秒；定向输入与默认域分开，实际源位置与分类以生成 JSON 核实。缺 JSON 先检查退出账与 trace，不能据此断言没执行。

## 明确保留的义务

本轮范围由主 agent 确认为独立源 NaN 类别、同构 NaN 出口、20个真实活动 gate。非 NaN 的 add/sub 无穷抵消、mul 0×Inf、div 0/0、Inf/Inf、finite_nonzero/0、sqrt 负非零、FMA 0×Inf/无穷抵消及最终 NV/DZ/OF/UF/NX 位打包仍有 strict 组合。它们仍是特殊行为分界，不能称其覆盖已闭合；本轮未把最终五位全部展开，原因是须先定位相关超时，不能否认其控制语义。

accrue_fflags 的 changed 与窄整数 sat overflow 本轮暂不恢复。BF16 真正融合舍入边界只做 oracle 验证，不制造算术分支。实施前完整分类与20个入口清单见 [classification.md](classification.md)。

## 永久回归与验证器准备

新增生产永久检查 `isla/test/float_ir/check_special_semantic_branches.py`，由主 agent 接入总回归。旧五 IR 均在“缺少独立源 NaN 行为 helper”处红测，见 [旧五 IR 红测](permanent-old-five-red.json)。新 IR 已核20个真实活动 gate 的 CFG、24个异常 helper 的源角色与 quiet/ordered 模式、helper 两个 NaN/sNaN 谓词 Jump、15个规范化出口及单次 fp32_fma；三代表 gate 的运算前移与非活动泄漏六个结构负变异全部被永久检查拒绝，见 [负变异核对](mask-cfg-negative-checks.json)。

BF16 oracle 调用直接使用 Berkeley SoftFloat f32_mulAdd；独立CLI进程每次重置 RM/flags，tininess after rounding，NV16/DZ8/OF4/UF2/NX1 与 RISC-V 一致，未共享线程内全局状态。独立两边界各五 RM 的10组结果表明融合与分步 `(result,累计flags)` 全部不同，见 [oracle核对](fusion-oracle-audit.json)。小数边界两者结果位可以相同，但融合只有 NX，分步有 UF|NX，不能只对比结果位。

初版验证器只有上界 RNE，经审查建议已扩为两边界×VV/VF×五 RM；修订56任务含48个约束包装。对旧IR独立逆变换48包装均全文件逐字还原，原 zexecute body 完全不变，见 [验证器核对](validation-harness-audit.json)。新模型48份实际包装也已逆变换逐字还原；定向结果的独立核对见下文。


## 四配置 IR 与安装签收

模型固定于 `a9fd9476fc1bf471070a38e01ee9233d10d742d3`，四个分类提交为 `350a072`、`f263774`、`eb17b05`、`a9fd947`，工作树干净。四配置 SYMBOLIC 严格生成及普通严格检查均退出0，全部使用相同166件模型文件；源码、配置、launcher、真实 Sail 二进制、插件和实际标准库文件哈希已复核。普通模式新增 helper 有 Sail body，strict_or_bool 的函数求值没有引入新外部依赖，普通严格检查通过。

四份 IR 均核实20个新增 mask Jump 支配原转换/运算，false出口绕过这些调用；BF16 VF 的两次转换及单次 FMA 均在活动分支内。24个异常 helper 的1/2/3源调用数与角色顺序、quiet/ordered参数已核。前轮 FVVTYPE/RFVVTYPE 仍通过原永久检查。去除源码位置及SSA临时名差异后，原2053函数增为2054，且仅54个预期函数发生变化（包括新增源helper），没有无关函数变化。

[四配置独立核查](ir-cfg-audit.json)、[安装manifest核查](installed-manifest-audit.json)确认五路径与四生成记录同源。新永久检查旧五 IR 红、新五 IR 绿，见 [新五 IR 绿测日志](permanent-new-five-green.log)。首次全四配置审计早于 V256 产物出现，因文件尚未生成而停止；其余三配置先单独通过，四配置齐备后完整重跑通过。这是审计启动时机，不是模型生成失败。负变异驱动初版对故意篡改 goto 的报错种类期望不符，经明确变异结构后六项按目标拒绝；未修改生产模型以迁就负对照。

## 56项定向结果独立复核

[最终定向核账](validation-final-audit.json)核实56/56任务退出0、156条JSON均finished，错误、执行/SMT超时、未完成、遗漏、pending与采样均0。所有命令外限和SMT都为7200秒，T1/qffp；输出、配置、冻结binary、基础IR与wrapper哈希一致。48个实际新IR包装的完整逆变换与基础IR逐字相同，仅约束原constructor字段后调用原body。

- H/S/D 的六个 FLEQ s/qNaN 任务各8条，两源单独、双NaN及双normal四组合都实际出现；NV符合s/q类别，非x0比较结果与源FPR保持已核。右源独立见证缺口在这些定向任务中关闭。
- BF16 两融合边界×VV/VF×五RM共20任务与独立SoftFloat结果/flags相同，并均与分步结果或累计flags不同；FRM保持。
- VV/VF各自mask0/1/2/3共8个混合异常任务分别得到flags0/NV/OF|NX/NV|OF|NX；逐活动lane独立oracle相符，不活动lane不贡献。标量源、向量源、累加器单独sNaN及vl0对照均通过；完整目的组尾部和其他VR保持、vstart归0已核。
- 半/双精度sqrt、代表比较/转换/宽化归约gate及BF16两转换的定向检查通过。

这是固定初态、字段约束、SEW及vl≤2的定向验收；不代表默认全域完成、全部20个循环的所有格式/LMUL/VLEN组合，或剩余异常原因/flag分界闭合。主agent的25步整体回归另行汇总，本独审不以其尚未结束时刻宣称通过。

正式 `make solve-FLEQ_S` 入口的8条新JSON已独立重核四种左右qNaN组合、非x0结果和flags。10条实际JSON指令、GCC/Clang×三表示的60项记录，其来源JSON哈希和真实提取二进制字节均复核相同，见 [入口及编码独审](entry-encoding-audit.json)。这确认正式入口和表示的列定样例，不扩大为全指令集的汇编验收。
