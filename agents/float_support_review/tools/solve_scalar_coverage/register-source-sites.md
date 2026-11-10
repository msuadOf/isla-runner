# Scalar 共享函数源码分母（只读）

2026-09-26。机器可读逐 site 清单见 [register-source-sites.json](register-source-sites.json)。清单按 file+line+id 去重后有 **44 个 site、261 个列示结果/索引项**，从 49 个 RV64 非 BF16 scalar clause 向共享函数追踪固定配置下的可达性。这些项混合了结果叶子、寄存器索引和条件取值，**不计入 `source_arm` 分母**，也不是执行 trace。主聚合工具当前报告的 49 constructor、94 execute 定义、125 `if` 和 62 `match` 属于 execute 与部分 shared 的词法统计；精确源码 `if/match` 分母由其 `source_catalog.py` 扩展计算，不能与此语义清单相加。

## 版本边界

动态 550 条使用冻结 IR `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`。该 IR 绑定的 `fdext_regs.sail` SHA-256 为 `b71d9da2208ab0591ea676b52fd9280ab455faace1250980d157ef2e5562f948`。只读审查时当前 [fdext_regs.sail](../../../../sail-riscv/model/extensions/FD/fdext_regs.sail) SHA-256 已为 `393abf4daf6ad5fc190517dcd4cd93df955a51cb029bb86e3eba899902588301`：生产 owner 修复了 SYMBOLIC `get_F_bits/get_F/set_F_bits/set_F` 的向量读写契约并修改 `accrue_fflags`。以下行号以**当前源码**为准；旧 d012 的动态 PASS 不自动转给新源码。当前 [regs.sail](../../../../sail-riscv/model/core/regs.sail) SHA-256 是 `913197b8efb5382b0ccb17979268ba57a34524b3462763fc2833c014be59db55`。

固定输入域是 RV64、XLEN=64、FLEN=64、Ext_F/D/Zfh/Zfa 可用、Ext_Zfinx/Zhinx/Zdinx 不可用。`__isla_vector_fpr`/`__isla_vector_gpr` 是运行时开关，默认 false；需要单独设 true 才能触及向量寄存器路径。`hartSupports` 是模型支持配置，不能仅靠清 `misa.F` 当作 Ext_F=false。

## 寄存器、boxing 与固定配置排除项

| 源码 site | 精确 arm / 可达性 |
| --- | --- |
| [fdext_regs.sail:21](../../../../sail-riscv/model/extensions/FD/fdext_regs.sail#L21) `canonical_NaN` | `match` 16/32/64 可由 H/S/D 结果取到；128 不在 49 项中。 |
| [fdext_regs.sail:49](../../../../sail-riscv/model/extensions/FD/fdext_regs.sail#L49) `nan_unbox` | 有**两个嵌套 `if`，各有 true/false 两个源码臂**；清单中的同宽、合法 upper 全 1、非法 upper 非全 1 是三个最终结果叶子，不能算作三个源码臂。本次 H/S 从 FLEN64 读，可达后两个结果叶子。D 的 `F_D` 直接读，不调用该函数；同宽叶子在此 49 项不可达。FMV.X.H/W 原位读低位，也不调用 unbox。 |
| [fdext_regs.sail:122](../../../../sail-riscv/model/extensions/FD/fdext_regs.sail#L122) `rF`、[:163](../../../../sail-riscv/model/extensions/FD/fdext_regs.sail#L163) `wF` | 各 32 个显式索引臂 0…31，均可由 5 位字段选择；`rF` 的 `_` 非法号因 `fregno` 范围 0…31 不可达。当前 550 只选了部分编号，不能算 32/32 动态命中。`wF` 普通臂还执行 callback 与无条件 dirty。 |
| [fdext_regs.sail:253](../../../../sail-riscv/model/extensions/FD/fdext_regs.sail#L253) `get_F_bits`、:262 `get_F`、:273 `set_F_bits`、:284 `set_F` | 各有 `__isla_vector_fpr` true/false 两臂。true 用 vector primop，当前源码还执行 Ext_F 断言、类型转换，写路径另有 callback/dirty；false 走 `rF/wF`。冻结 d012 IR 有 `zget_F_bits/zset_F_bits` 定义，**没有 `zget_F/zset_F` 定义**，故其 `fregno` 重载已在该 IR 编译消除，不能列入 d012 实际分母；当前候选 IR 仍需验证。旧 d012 true 写臂缺 Dirty，版本不同。 |
| [fdext_regs.sail:327](../../../../sail-riscv/model/extensions/FD/fdext_regs.sail#L327) H、:339 S、:351 D 的读写包装 | H/S `nan_unbox` 与 `nan_box`；D 同宽直接取/写。`flen`/Ext_F 断言成功臂固定可达，失败臂被本配置排除。 |
| [fdext_regs.sail:368](../../../../sail-riscv/model/extensions/FD/fdext_regs.sail#L368) `rF_or_X_H/S/D`、:398 `wF_or_X_H/S/D` | Ext_F=true 的 F 路由固定可达；Ext_F=false 的 X 路由在本配置不可达。D 的 X 路由内部还有 XLEN≥64 与 RV32 偶数寄存器对、零寄存器对分支；它们均处于已排除的 X 路由，RV32 臂另由 XLEN64 排除。 |
| [regs.sail:151](../../../../sail-riscv/model/core/regs.sail#L151) `rX`、:190 `wX` | 各 0…31 显式臂；读 0 返回 `zero_reg`，写 0 是 no-op 且 :226 跳过 callback。`x0` 不作为 runner 可观察寄存器读回；x0 源以另一目的的 0 结果见证，x0 目的只观察其他状态不变。 |
| [regs.sail:281](../../../../sail-riscv/model/core/regs.sail#L281) `get_X/get_X_bits`、:294 `set_X/set_X_bits` | 各有 vector flag true/false；true 额外分 r=0（常数 0/no-op）与 r≠0（vector primop），false 走 `rX/wX`。默认 false 的用例不能证明 true 臂。 |

## 数值辅助函数的传递闭包

- [zfh_insts.sail:37](../../../../sail-riscv/model/extensions/FD/zfh_insts.sail#L37)、[fext_insts.sail:165](../../../../sail-riscv/model/extensions/FD/fext_insts.sail#L165)、[dext_insts.sail:124](../../../../sail-riscv/model/extensions/FD/dext_insts.sail#L124) 的 `negate_H/S/D` 各有 sign=0→1 和 sign=1→0。后者由 FMSUB rs3、FNMSUB rs1、FNMADD rs1/rs3 负输入定向见证；这里只映射输入，不称 trace。
- [zfh_insts.sail:119](../../../../sail-riscv/model/extensions/FD/zfh_insts.sail#L119)、[fext_insts.sail:217](../../../../sail-riscv/model/extensions/FD/fext_insts.sail#L217)、[dext_insts.sail:176](../../../../sail-riscv/model/extensions/FD/dext_insts.sail#L176) 的 `fle_H/S/D`：结果链按双正、正负、负正、双负分流；同号两臂各再分指数相等/不等；flags 先分 `is_quiet`，再分对应 sNaN/任意 NaN 真/假。当前 49 项只有 MIN/MAX 与 MINM/MAXM 调用 `fle_*`，且都传 `is_quiet=true`；false 分支及其任意 NaN 检查在该调用域不可达。FEQ/FLT/FLE、FLEQ/FLTQ 调用独立 IEEE helper，不能拿它们的输入给 `fle_*` 记命中。NaN 时 `fle_*` 仍可能计算数值比较，但 MIN/MINM 后续选择会覆盖该布尔结果。
- `fsplit_H/S/D` 是固定位切片，`fmake_H/S/D` 是拼接；三份源码的 `f_is_*`（sign、normal、subnormal、zero、inf、sNaN、qNaN、NaN）是布尔位测试，定义体没有显式 `if/match`。它们的 true/false 可作为条件输入域，不能另算函数内部控制流 arm。`fregval_from_freg`/`fregval_into_freg` 和 `regval_from_reg`/`regval_into_reg` 是类型恒等包装，无内部条件臂。
- FCLASS.H/S/D 分别在 [zfh_insts.sail:812](../../../../sail-riscv/model/extensions/FD/zfh_insts.sail#L812)、[fext_insts.sail:912](../../../../sail-riscv/model/extensions/FD/fext_insts.sail#L912)、[dext_insts.sail:846](../../../../sail-riscv/model/extensions/FD/dext_insts.sail#L846) 调用 **Sail 安装库** `float_classify`；模型 [core/float_classify.sail:10](../../../../sail-riscv/model/core/float_classify.sail#L10) 只把十种 enum 映射到 one-hot。实际分类器来自 `model/prelude/prelude.sail:21` 包含的 `float/interface.sail`→`float/classify.sail:27`，库文件当前 SHA-256 `5b73810b001aa95908dfec313172b8c3fbb4cbdd81e2a01556848b23522d8636`。分类器按 sNaN、qNaN、zero±、subnormal±、normal±、inf± 有**十个结果类别**；这是嵌套 `if` 链的结果叶子数，不能当作十个 `if` 的源码臂数，后者交由聚合 catalog 逐条件统计。尾部 `assert(false)` 对合法 IEEE 16/32/64 位串不可达。其 `float_is_*` 来自库 `float/{nan,zero,normal,inf,sign}.sail`，定义体为布尔测试；`float_decompose` 在 `float/common.sail:62` 有 16/32/64/128 四种宽度 `match`，FCLASS 本域只可到前三种。这里没有名为 `fp_classify` 或 `_classify` 的额外模型实现。

清单中的可达性仅依据源码与固定配置；d012 运行结果由主 agent 汇总。当前源码变更后需要重新生成 IR 才能对其写入、状态及 callback 分支作动态判断。
