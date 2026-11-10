# 浮点数据条件覆盖核账（2026-11-02）

**仍有未核完的条件；不能把 helper 回归、恢复 boxing 分支或新 Z3 接入当成全覆盖。** 本轮核对当前模型 `9c339044b07e235fe48d5bc585cbd3975ceeba5a`，建立 [25 项义务账本](coverage-matrix.json)：18 项数据条件/集成义务，7 项交主消融负责，不重复启动求解。第一阶段为静态与已有 JSON 离线核账；后续追加6次定向求解，见文末。无生产修改、无新二进制，任务现均已结束。

## 当前可确认的见证

对官方 Z3 `1fd1d3613` 接入时的 `float-cli-default-FLEQ` 现成产物重新分类：10 条 FLEQ_S 中，两个源位置各观察到 boxed sNaN、boxed qNaN、正常数、零和无效 boxing；其中一条新增 NV，九条无新增 flags。新增 NV 的一条是**两个源同时 sNaN**，qNaN 一条同样是两个源同时 qNaN，故不能据此关闭左源独立/右源独立的条件义务。

这修订了旧 `afff3822` 模型/旧 Z3 报告中“FLEQ 默认批没有 NV”的适用范围。当前默认批已有该见证；旧批结论按旧版本保留。新数据支持 FLEQ_S 这一批次，不代替 H/D、其他关系操作或其他 Clause。

[离线导出](observed-witnesses.json)还保留旧定向 sNaN 两条作历史对照。独立按 IEEE 位模式检查 8 个分类边界；12 条 FLEQ JSON 的 NV 与 FRM 保持关系全部符合所查代码，25 个源码定位/hash匹配。[验证结果](export-checks.json)。这不是新求解或全源分支 PASS。

## 不与本轮消融重复的优先缺口

| 义务 | 当前源码与证据 | 最小后续验证 |
| --- | --- | --- |
| 静态 rm=5/6 与动态 FRM 非法值 | `fext_insts.sail:31` 的枚举根本没有静态5/6；`:51` 才处理 DYN 读取 FRM。旧 d012 解码负例只覆盖部分指令族 | 对 RM-bearing 每个编码族从 raw word 走 decode→execute；静态5/6期望 ILLEGAL，DYN+FRM5/6/7期望执行 Illegal；不要互相代替 |
| qNaN/sNaN 独立源位置 | `ieee_fp_exceptions.sail:79/85` 区分 quiet/signaling；当前 FLEQ_S 只闭合部分组合 | 单独将 rs1 或 rs2 设为 boxed qNaN/sNaN，另一源1.0；逐 EQ/LT/LE/LTQ/LEQ、H/S/D检查结果和 NV |
| 算术无效原因与五类异常 | 同文件 ADD/SUB/MUL/DIV/SQRT/FMA 的 invalid 原因不同；flags changed 不能代表五个 flag 和全部原因 | 分开0/0、Inf/Inf、1/0、0×Inf、异号无限和、负数sqrt、FMA无限抵消；正常对照；旧 flags0，逐格式/操作记录 |
| vfrec7/vfrsqrt7 估算正常路径 | `vext_fp_utils_insts.sail:584/675` 有查表与次正规归一化；旧指令审计只验证+0→Inf/DZ，当前未找到同版本普通路径指令见证 | `VFUNARY1` 按 SEW16/32/64，用1.0/2.0、次正规、指数/查表索引边界；核对 lane 写回和flags，不能只测 helper |
| BF16三个异常源角色 | `zvfbfwma_insts.sail:155` 标量转换，随后向量源转换及 f32累加器FMA分别产生异常；旧56cc/d012大包是历史证据 | scalar BF16/vs2 BF16/累加器 f32分别放 sNaN，逐活动/无活动对照；full destination group；BF16不得按 f16位宽语义分类 |
| BF16真正融合边界 | 旧大包提供能区分融合和分步运算的输入，但不能迁作当前模型 PASS | `a=b=0x5f80,c=0xff7fffff` 及 `a=b=0x1780,c=1.0`，VV/VF五RM；独立FMA oracle对照结果/OF/UF/NX |
| lane布局与混合异常累计 | 小 vl mask/归约消融不关闭全部LMUL、tail、prestart、重叠、不同lane异常 OR | 独立lane分别触发NV及OF|NX，单独/同时/屏蔽；旧flags0；观察完整寄存器组和vstart |

精确源码锚点、SHA、适用版本、状态、剩余域和具体下一步均在 JSON。账本为候选义务分组，**不是穷尽分母，不能把18或25当覆盖率分母**。

## 边界与使用方法

主消融负责 flags更新、min/max/minm/maxm、mask/归约、分类、NaN规范化、转换饱和及合法性聚合。这里将它们标记 `owned-by-current-ablation`；其结果需主agent后续关联，不在本包重复运行。

`export_witnesses.py` 只读 JSON，按被读源寄存器的**原始位值和 boxing 后实际类别**导出，不能将全部初态 FPR 的取值算成被该指令使用的输入。输出只称“观察到”，不推断不可达或分支闭合。`newly_visible_fflags=post & ~old` 只反映新增可见位：旧NV已置位时，不能据其保持判断本次是否产生NV。向量/mixed-width转换/`.insn`显式标记不支持，需要按实际指令类型另写提取器，不猜类型。

```sh
python3 agents/float_review_completion_20261102/data-conditions/export_witnesses.py \
  agents/isla_official_z3_switch_20261102/float-cli-default-FLEQ/output/rv64_zFLEQ_S.json \
  agents/independent_topic_review_20261030/float/fleq-clean-snan/output/rv64_zFLEQ_S.json \
  --out agents/float_review_completion_20261102/data-conditions/observed-witnesses.json
python3 agents/float_review_completion_20261102/data-conditions/build_ledger.py
python3 agents/float_review_completion_20261102/data-conditions/verify_export.py
```

后续真求解统一使用冻结官方Z3与正式Isla，完整 Clause 外限7200秒、显式 SMT7200秒；固定输入定向测试与默认全域批分开，不能把修改初态后的一组输入当默认域穷尽证明。本包没有运行求解，故不制造新的2h性能结论。

## 定向补验（本轮追加，官方 Z3）

后续授权运行6次完整但固定初态的Clause：4次FLEQ_S、2次VFUNARY1，40条JSON全部finished，错误/执行超时/SMT超时/未完成均0。冻结二进制为 `agents/branch_ablation_official_z3_20261102/bin/isarch`，使用现行 `isla/ir/rv64d_v128_e64.ir`；hash、版本、配置、实际argv与日志分别保存在 [首4次manifest](directed/manifest.json)及[后2次manifest](directed-rhs/manifest.json)，每Clause外限7200秒、SMT显式7200秒、T1/qffp、最多2并发。**这些是定向域，不能当默认全域覆盖。**

- **FLEQ_S左源独立通过**：rs1为boxed `0x7f800001` sNaN、rs2为boxed1.0，NV从0变16、比较结果false；rs1为boxed `0x7fc00013` qNaN时NV保持0、结果false。另一源为1.0，两源FPR保持；另有1.0≤1.0的true对照。
- **FLEQ_S右源独立仍缺见证**：将低/高半FPR的NaN/1.0分配交换后，求解器仍选左源NaN、右源normal。不能因写了该配置就声称右源被测。指定冻结binary没有固定机器码参数，本轮未另造执行语义。
- **估算正常/次正规活动lane已补**：SEW32/LMUL1/vl1/vstart0，1.0输入下 `vfrec7.v` 与 `vfrsqrt7.v` 均输出`0x3f7f0000`；次正规`0x00400000`分别输出`0x7eff0000`、`0x5f340000`，四例flags均0。独立IEEE位串解码＋90位Decimal算术检查相对数学倒数/倒平方根误差≤2^-7，且7位估算低16尾数位为0；目的尾部96位、其他VR、vl/vtype保持，vstart归0。这个算术界不证明查表逐项精确正确，SEW16/64、完整查表索引与异常值仍未闭合。

[逐条断言](directed-checks.json)状态为`PARTIAL`，明确列出缺少的两项右源义务。`check_directed.py` 可重复离线核对。首4次调度脚本同类两任务共享CPU（后两次分CPU35/33）；不将本轮耗时当性能比较，不与主消融数据混算。
