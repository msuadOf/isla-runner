# 向量数值定向义务：本轮结果

本文件只记新增的有限输入。逐项精确分母和独立预期来源在 [numeric-obligations.json](numeric-obligations.json)，生成器在 [numeric.py](numeric.py)。受测版本：完整 IR SHA-256 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`；配置 SHA-256 `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`；成功 runner SHA-256 `bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425`。额外独立 oracle：Berkeley SoftFloat CLI SHA-256 `0bb63bc72889502ef6a36cb739589745987a0788eb73d57e0570815a3c228bc6`；Spike estimate CLI SHA-256 `5df09858c896ffeff02fb170dd07372114071a93bafe604cba23c95c2cfe6833`，其 `libsoftfloat.so` SHA-256 `f1592214d4845ba004aaa487f3f3285e6cbd0909597e126e5438c2f4ae614b41`。

## 原始证据与判定

仓库外运行目录在本轮记为 `$NUMERIC_STAGE`。其中 `inputs-caseid.json` SHA-256 `39534dfb1e2f5eb53ed69a3316305666449a883c9b1e39edc78ce5de5e01d3ac`；原始 runner 输出 `results-caseid-runner.json` SHA-256 `31fb5edd0ec098430e84b7901976da1392d9670e31768d0dc1e039c9fe9e1db9`；`run-caseid.log` SHA-256 `e46cad86d42f4907b62c79f44495bd1e23761d7efe3be1a6d4987d99ffc73891`。生成器 SHA-256 `057387abbaf898578d68c3602b47416ab987db74c236f30a493ec9402c08bfb9`；义务清单 SHA-256 `b997caf86620951761d6cf6cac368337c16e37cce8de44f9d8e6ce8277f94ce8`。实际运行退出码 0，输入及结果均为 **1498 条、1498 个唯一 name**。

核对结果逐项满足：`sat=true`、`difference_unsat=true`、`structural_ok=true`；真实字经 `zext_decode` 的两条完成路径，构造器及字段符合输入；`zencdec_forwards` 唯一结果等于原字；`zexecute` 唯一完成路径返回 `Retire_Success`；对**完整目标寄存器**、`fcsr`、`vstart`、`mstatus` 的任意差异 UNSAT。宽目标和刻意预置的 `vr5` 还观察下一物理寄存器。该检查由 runner 实施，另从归档 JSON 独立逐行复查了上述字段。每条输入的 `case_id` 是 UTF-8 `name` 的 SHA-256 前 8 字节按 big-endian 解作无符号 64 位整数；1498 个 ID 均唯一并逐项重算相等。当前 runner 输出以 `name` 对应输入，未回写 `case_id`。

复跑命令；调用者提供仓库外目录和固定 IR、配置、runner：

```sh
python3 agents/float_support_review/tools/solve_vector_coverage/numeric.py \
  --output "$NUMERIC_STAGE/inputs-caseid.json"
"$RUNNER" "$IR" "$CONFIG" \
  "$NUMERIC_STAGE/inputs-caseid.json" "$NUMERIC_STAGE/results-caseid-runner.json"
```

| 新增义务 | 输入名称模式（完整名称均在输入 JSON） | PASS/分母 | 独立预期 |
| --- | --- | ---: | --- |
| class 十类 | `numeric_class_e{16,32,64}_bit{0..9}` | 30/30 | IEEE 位字段、RISC-V one-hot |
| rec7/rsqrt7 | `numeric_{rec7,rsqrt7}_e{16,32,64}_{normal,minsub,negative,negzero,posinf,qnan,snan}` | 42/42 | 固定 Spike SoftFloat API |
| 归约顺序 | `numeric_{rfvvtype,rfwvvtype}_{enum}_{forward,reverse}` | 8/8 | 精确整数幂逐步舍入；unordered 为当前模型选择的顺序算法 |
| 归约屏蔽 | `numeric_{rfvvtype,rfwvvtype}_{enum}_mask_lane1` | 4/4 | IEEE ties-to-even，旧 flags OR |
| VV 各 enum 边界 | `numeric_vv_{enum}_e{16,32,64}_edge` | 27/27 | SoftFloat 算术及 ISA min/max/sign |
| VF 非 slide 各 enum 边界 | `numeric_vf_{enum}_e{16,32,64}_edge` | 33/33 | 同上，并检查 NaN boxing |
| 四类 FMA 特殊值 | `numeric_{fvvmatype,fvfmatype,fwvvmatype,fwvfmatype}_{enum}_e{SEW}_{inf,zero,snan,qnan}` | 256/256 | SoftFloat fused fma，独立符号/操作数角色 |
| 三类 FP→整数边界 | `numeric_{vfunary0,vfwunary0,vfnunary0}_{enum}_e{SEW}_{minusone,posinf,neginf,qnan}` | 112/112 | ISA 有/无符号饱和及 NaN 结果 |
| ROD 特殊值 | `numeric_rod_f{32,64}_to_f{16,32}_{poszero,negzero,minsub,negminsub,maxfinite,posinf,qnan,snan}` | 16/16 | SoftFloat ROD=6 |
| VV 舍入 | `numeric_rm_vv_{add,sub,mul,div}_e{16,32,64}_rm{0..4}` | 60/60 | SoftFloat 五种 RM |
| VF 舍入 | `numeric_rm_vf_{add,sub,rsub,mul,div,rdiv}_e{16,32,64}_rm{0..4}` | 90/90 | SoftFloat 五种 RM |
| 四类 FMA 中点舍入 | `numeric_rm_{fvvmatype,fvfmatype,fwvvmatype,fwvfmatype}_{enum}_e{SEW}_rm{0..4}` | 320/320 | SoftFloat fused fma 五种 RM |
| 三类 FP→整数舍入 | `numeric_rm_{vfunary0,vfwunary0,vfnunary0}_{enum}_e{SEW}_{positive,negative}_frm{0..4}` | 280/280 | SoftFloat，固定 RTZ 输入保持动态 frm |
| VV/VF 比较 | `numeric_cmp_{fvvmtype,fvfmtype}_{enum}_e{16,32,64}_{finite_true,finite_false,qnan,snan,posnegzero,negposzero}` | 180/180 | SoftFloat eq/lt/le 及交换操作数 |
| REDMIN/MAX | `numeric_red{min,max}_e{16,32,64}_{qseed,sseed,qlane,slane,negposzero,posnegzero}` | 36/36 | ISA NaN、NV、±0 选择 |
| 全 mask sNaN seed | `numeric_{rfvvtype,rfwvvtype}_{enum}_allmask_snan_seed` | 4/4 | 无活动 lane 原样复制 seed 和旧 flags |

新包 1498 项按 `expected_fflags & ~initial_fflags` 统计：不新增 584，NX 528，NV 371，DZ 6，OF 5，UF 4。此处只表示这些输入生成的标志，不代表所有产生标志的路径或全部 enum 都已覆盖。

## 边界与初次试跑

现有编码格式矩阵由主 agent 统一核对：`expanded-cases.json` 227 + `fvvtype-finite.json` 27 + VFNUNARY0 的 seven/sew32/sew8/ROD 20 = 274 条，涉及 97 个 enum 名及 4 个固定编码；它是格式触达分母，**不并入本轮1498条数值输入**。本新增包涉及 14 个 clause，未新增 FWVVTYPE、FWVTYPE、FWVFTYPE、FWFTYPE 的普通数值特殊值，也未新增四个 move/merge clause 的数值样例；`FVFTYPE` 两个 slide enum 未纳入 33 条边界组。`VFUNARY0`、`VFWUNARY0`、`VFNUNARY0` 的整数→FP 和普通 FP→FP enum 未系统补特殊值。估算查表只选 normal=1.0 和最小 subnormal，未穷举 128 个索引、其它归一化深度及全部舍入溢出组合。归约顺序只选择一组可辨识的整数幂，比较关系只选六种输入形状。所有例均为 LMUL1、`vta=vma=0`，主要 `vl=1`；源寄存器、非目标寄存器和全部 CSR 未统一加入不变性观察。因此不能写作 source branch PASS 或完整机器状态等价。

首次 84 条试跑中，`RFWVVTYPE` 全保留目标的 mask 样例期望 `fcsr=0x4`，实际 `0x5`。原因是 seed=`2^53` 加 `1` 的结果仍是 seed，但舍入不精确，必须置 NX。已按独立 ties-to-even 规则修正预期并重跑，全批通过；初次失败原始输入 `inputs-initial-failed.json` SHA-256 `b9b0b60c66e870896ca90b3c3338d340776d522c91bb6fbb15e5979af0282b22`，原始日志 `run-initial-failed.log` SHA-256 `1875772e5495222448f1101279b24436b0c0c61e85ad63007612e56146697093`，均在 `$NUMERIC_STAGE` 保留。该失败是预期标志错误，没有目标写回差异证据。
