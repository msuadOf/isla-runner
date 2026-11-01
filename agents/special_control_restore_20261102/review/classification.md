# 特殊值控制分界独立审查：实施前分类

当前结论：NaN 规范化、各操作数独立的 NaN/sNaN/qNaN 行为及活动 lane 是必要控制分界；BF16 真正融合边界与多 lane 异常 OR 的数学组合需要验证，不应制造算术分支。以下以模型 `fd71c9ab58fe6f41b97c976a5f7e470318c708a8` 为基线，只读生产源码。

## 建议恢复的最小边界

| 区域 | 当前边界与建议 | 不变量 |
| --- | --- | --- |
| `model/extensions/FD/softfloat_symbolic_f16.sail` | 六算术、roundToInt、ToF32/ToF64 共九处 NaN 规范化 ITE 改 if | 常量和 IEEE 编码不变；整数转换饱和本轮不改 |
| `model/extensions/FD/softfloat_symbolic_f64.sail` | 统一 result_bits、ToF16、ToF32 NaN 出口显式；ROD 模式独立选择 | 不改 ROD 数值公式、奇数最低位或五种 RM |
| `model/extensions/FD/softfloat_symbolic_f32.sail` | ToF64、ToF16、ToBF16 的 NaN 出口显式 | 原 f32 算术出口已有 if；窄化保留 ROD 与普通路径的精确 flags 配对 |
| `model/core/ieee_fp_exceptions.sail` | 比较的六个 eq/lt helper、各格式 add/sub/mul/div/FMA/sqrt 的 signaling 行为应按源独立分类 | 底层 ieee_is_nan/is_snan 保持 strict 纯谓词；每个源先绑定行为 helper 结果，再 strict OR，不能 OR 后只分两路或短路漏过后源 |
| `model/extensions/bfloat16/zfbfmin_utils.sail` | SYMBOLIC bf16_to_f32 区分 sNaN、qNaN、非 NaN | BF16 指数8位/尾数7位，quiet bit6；sNaN 单独 NV，所有 NaN canonical f32，非 NaN 保留 v@16零 |
| FP/BF16 的剩余20个运算循环 | 见下表，全部纯转换/运算、写 lane、OR flags 由真实活动 mask 支配 | 初值、prestart/tail、vstart、位宽和目的寄存器组不变；不活动 lane 不求运算、不贡献异常 |

最小行为 helper 可表达为：`if ieee_is_nan(raw) then if ieee_is_snan(raw) then true else signaling else false`。比较 ordered 传 true，quiet/EQ 与算术传 false。两个源均先绑定，FMA 三个源均先绑定，最后使用 strict OR。它在 quiet 比较中令 qNaN 不置 NV，在 ordered 比较中令任一 NaN 置 NV；把两个源合在同一 OR 条件上只能保证任一源成立，不能保证右源单独成立。单源 round/widen/convert 中的 sNaN 行为也要按实际调用点审，不能把 helper 存在等同于所有调用已覆盖。

## 剩余20个运算循环的实际入口

- `model/extensions/V/vext_fp_insts.sail`：FVVMATYPE、FWVVTYPE、FWVVMATYPE、FWVTYPE、VFUNARY0、VFWUNARY0、VFNUNARY0、VFUNARY1、FVFTYPE、FVFMATYPE、FWVFTYPE、FWVFMATYPE、FWFTYPE，共13个。
- `model/extensions/V/vext_fp_vm_insts.sail`：FVVMTYPE、FVFMTYPE，共2个；mask 目的位写回应保留 initial_result 的不活动位。
- `model/extensions/V/vext_fp_red_insts.sail`：RFWVVTYPE，共1个；sum 按原 lane 递增更新，宽化 flags 和相加 flags 仅活动 lane 合并。
- `model/extensions/bfloat16/zvfbfmin_insts.sail`：VFNCVTBF16_F_F_W、VFWCVTBF16_F_F_V，共2个。
- `model/extensions/bfloat16/zvfbfwma_insts.sail`：VFWMACCBF16_VV、VFWMACCBF16_VF，共2个。

已恢复的 FVVTYPE/RFVVTYPE 不重复记新增。VFMERGE/VFMV 的 vector_select 是搬运数据选择，没有异常运算；不能仅凭出现 vector_select 就机械纳入20个运算 gate。后续若审其活动/未活动写回覆盖，应单独说明目标。

BF16 VF 的 scalar 纯转换原在循环之前；新增 s/q 分支后应移入活动 lane，或首次活动 lane 缓存。不能在 vl=0/全 mask 情况执行一个新增的源分类控制并据此宣称实际执行了异常操作；更不能在循环前 accrue scalar flags。

## 只验证、不修改数值的项目

- BF16 源转换精确嵌入 f32，MACC 继续一次 `riscv_f32MulAdd`，底层继续一次 `fp32_fma`；独立以 `a=b=0x5f80,c=0xff7fffff` 和 `a=b=0x1780,c=1.0` 的 VV/VF、五 RM 对照融合 oracle。禁止改为乘后加，禁止按这些测试值增分支。
- 多 lane OR 继续逐 lane 合并，OR 自身无须按值拆分。应以独立 lane NV、OF|NX，分别活动/同时活动/分别屏蔽，旧 flags0 对照；检查完整目的组及 vstart。不活动 lane 的 flags 必须为零贡献。
- `ieee_*_rounded_exceptions` 的上下界、lower/upper 幅值、nearest/outward/inward 和 ROD 奇数化均是原数值方法，不因 ITE 存在就改。
- `accrue_fflags` 的 changed 和窄整数 sat overflow 本轮暂不恢复；此前三次7200秒证据不能改写为不需要控制或已覆盖。

## 未闭合项目必须继续记账

独立源 helper 与 NaN 出口不会自动给出非 NaN 的所有特殊原因见证。当前 add/sub 无穷抵消、mul 0×Inf、div 0/0、Inf/Inf、finite_nonzero/0、sqrt 负非零、FMA 0×Inf/无穷抵消及 NV/DZ/OF/UF/NX 最终位打包仍有 strict 组合。它们按用户原则属于异常行为分界；若本补丁不拆，应明确保留义务，不能写成全特殊值控制恢复完成。最终 flag pack 每位 if 可分异常类别，但会使算术查询组合增加，须与主 agent 明确范围后实测，不能顺带扩大。

## 签收要求

审实际 patch 的函数级数学表达、源顺序、flags、boxing、融合、宽度与归约顺序；新 IR 要检查真实 Jump/CFG 支配，不只数 Jump。source/IR/manifest 同源且所有配置哈希一致；普通及 SYMBOLIC 严格检查。动态默认完整 Clause 与定向输入分开记，每 Clause 外限及 SMT 均7200秒，无 JSON 先检查退出账和 trace，不能直接判没执行。新增分类实际操作数位置、单独 s/qNaN 和多 lane flags 需从 JSON 原始源位值确认。
