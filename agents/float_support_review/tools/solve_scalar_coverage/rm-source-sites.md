# RV64 scalar RM / guard 源码 site 清单

状态：**当前源码静态清单**，没有 Sail 或 IR 的插桩 branch trace。`rm-source-sites.json` 是机读全集；本文件只说明计数口径、配置边界和关键 site。49 个 clause 是 27 个类型化 clause 加 22 个 Zfa clause；90 个 enum 加 22 个 Zfa op 对应 112 个译码映射。BF16、RV32 专属 Zfa 和访存不在范围内。

## 版本冻结

本清单在一次读取中冻结以下源码字节，生成后再次核对文件未变。路径以仓库根目录为基准。d012 IR 的旧冻结 `zfa_insts.sail` 哈希是 `7759b83d…`，当前为 `804b002f…`；本清单不能当作 d012 的源码重建或 trace 证据。

| 源码 | SHA-256 |
| --- | --- |
| `sail-riscv/model/extensions/FD/fext_insts.sail` | `d32c4741bc63f7e850f469412d05a0288e48a415bfb4b5c19870988f8fc6bfd6` |
| `sail-riscv/model/extensions/FD/dext_insts.sail` | `3419798f019c2dc2646cca3193360f2124799140bfdc380f6221ed7b0d1295d0` |
| `sail-riscv/model/extensions/FD/zfh_insts.sail` | `1f589078f69f127ec9af63fd0bd32c52eac09a4b8e37e59a6bd334b0950841fc` |
| `sail-riscv/model/extensions/FD/zfa_insts.sail` | `804b002f96e7be22f6fd3173a143b545d7802f4979b5d68f65280b947f186ca0` |
| `sail-riscv/model/extensions/FD/fdext_control.sail` | `ba32768c933b97b3416fcfda895ab7cc3dec52dee213c151e26443cf57b6a8e6` |
| `sail-riscv/model/extensions/bfloat16/zfbfmin_insts.sail` | `2cd483db1f59379ac46efd3d7a165ed3ec8e24c89f283df90acaf6834530b82b` |
| `sail-riscv/model/extensions/V/vext_control.sail` | `2fdf5f777f5e1b9023c62291d6a6cd7617a101b577634269a7a1a89c038949e2` |
| `sail-riscv/model/extensions/Zicsr/zicsr_insts.sail` | `9a797cf8c5a2a92b670bbff7d909ce608951ea9e3c9526e926149ab29dc19848` |
| `sail-riscv/model/core/extensions.sail` | `d9f17ada13e2da6bc6af26bbd18a18213c048aba4414d77aa26fb1205f8ee26f` |
| `sail-riscv/model/core/sys_regs.sail` | `d8d71b7feb3703d656dc23ddc14b57cff228324f19d25770ac3e16306bff3de8` |
| `sail-riscv/config/config.json.in` | `7ea028d0d049a26f0d7a1a1b95685722c227560b7face1f1f129b27aa0e95890` |

IR 参照哈希：`d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`。运行配置前提：RV64/FLEN64；`F/D/Zfa/Zfh/Zfhmin/Zfbfmin/Zicsr` 编译支持；`Zfinx/Zdinx/Zhinx/Zhinxmin` 编译关闭；`Fcsr_RM_Illegal`。`config/config.json.in` 是配置模板证据，最终可执行配置/IR 应单独绑定；不把模板哈希等同于生成产物。

## 分母与来源

| 唯一源码位置 | 数量 | 计数方法 |
| --- | ---: | --- |
| `mapping clause encdec ... when` | 112 | 逐 op 的真实映射行：H 32、S 28、D 30、Zfa 22；每行 `when` true/false 作为候选臂。 |
| `match (select_instr_or_fcsr_rm(rm))` | 45 | 每个源码 match 只有一个 site 与 `Some`/`None` 两臂，共 90 个 site+arm。H 15、S 11、D 13、Zfa 6。 |
| 带 RM 的 op 关联 | 63 | 57 个 typed enum + 6 个 Zfa round op，**仅作为消费者索引**；共享的 MADD/BIN execute match 不按 enum 复制。 |
| 共享映射与 helper/谓词 | 26 | `shared_sites` 每个源码 site 只列一次，臂在其下列出。 |
| 映射 guard 固定不可达子条件 | 40 | 14 个 `xlen >= 64` 的 false 与 26 个 `validDoubleRegs` 的 false；不等于整个 `when` false 不可达。 |

112 个 `when` false 可以由 FS Off 或相应 misa F/D 关闭触发。`xlen >=64` 的 false 与 `validDoubleRegs` 的 false 是**同一映射内的特定子条件**，在此 IR 中不可达；JSON 把它们单列，避免把 guard 总体可拒绝误写成每个子条件都有见证。`rm_guards.py` 的 630 正向/549 负向 d012 结果已由主 agent 报告动态通过，但只证明输入与预期行为，不能证明源码臂插桩命中。

## 共享 site 与臂

| Site | 条件或映射 | 臂分类摘要 |
| --- | --- | --- |
| `sail-riscv/model/extensions/FD/fext_insts.sail:31-38` | encdec_rounding_mode | `RM_RNE`=input_reachable, `RM_RTZ`=input_reachable, `RM_RDN`=input_reachable, `RM_RUP`=input_reachable, `RM_RMM`=input_reachable, `RM_DYN`=input_reachable, `unmapped_5`=input_reachable, `unmapped_6`=input_reachable |
| `sail-riscv/model/extensions/FD/fext_insts.sail:49` | valid_rounding_mode | `true`=input_reachable, `false`=input_reachable |
| `sail-riscv/model/extensions/FD/fext_insts.sail:52` | instr_rm == RM_DYN | `true`=input_reachable, `false`=input_reachable |
| `sail-riscv/model/extensions/FD/fext_insts.sail:55` | valid FRM and FRM != RM_DYN | `true`=input_reachable, `false`=input_reachable |
| `sail-riscv/model/extensions/FD/fext_insts.sail:57-60` | fcsr_rm_reserved_behavior | `Fcsr_RM_Fatal`=config_unreachable, `Fcsr_RM_Illegal`=input_reachable |
| `sail-riscv/model/extensions/FD/fext_insts.sail:56` | dynamic Some | `Some`=input_reachable |
| `sail-riscv/model/extensions/FD/fext_insts.sail:63` | static Some | `Some`=input_reachable |
| `sail-riscv/model/extensions/FD/fdext_control.sail:18` | currentlyEnabled Ext_F | `true`=runtime_reachable, `false`=runtime_reachable, `hartSupports_F_false`=config_unreachable, `Zicsr_false`=config_unreachable |
| `sail-riscv/model/extensions/FD/fdext_control.sail:19` | currentlyEnabled Ext_D | `true`=runtime_reachable, `false`=runtime_reachable, `hartSupports_D_false`=config_unreachable, `flen_lt_64`=config_unreachable, `Zicsr_false`=config_unreachable |
| `sail-riscv/model/extensions/FD/fdext_control.sail:20` | currentlyEnabled Ext_Zfinx | `true`=config_unreachable, `false`=config_fixed |
| `sail-riscv/model/extensions/FD/fext_insts.sail:28` | currentlyEnabled Ext_Zfh | `true`=runtime_reachable, `false`=runtime_reachable, `hartSupports_Zfh_false`=config_unreachable |
| `sail-riscv/model/extensions/FD/fext_insts.sail:29` | currentlyEnabled Ext_Zfhmin | `true`=runtime_reachable, `false`=runtime_reachable, `hartSupports_Zfhmin_false`=config_unreachable |
| `sail-riscv/model/extensions/FD/fext_insts.sail:253` | haveSingleFPU | `F_route`=runtime_reachable, `Zfinx_route`=config_unreachable |
| `sail-riscv/model/extensions/FD/dext_insts.sail:212` | currentlyEnabled Ext_Zdinx | `true`=config_unreachable, `false`=config_fixed |
| `sail-riscv/model/extensions/FD/dext_insts.sail:214` | haveDoubleFPU | `D_route`=runtime_reachable, `Zdinx_route`=config_unreachable |
| `sail-riscv/model/extensions/FD/dext_insts.sail:220` | validDoubleRegs RV32Zdinx condition | `true`=config_unreachable, `false`=config_fixed |
| `sail-riscv/model/extensions/FD/dext_insts.sail:223` | validDoubleRegs odd register | `true`=config_unreachable, `false`=config_unreachable |
| `sail-riscv/model/extensions/FD/dext_insts.sail:224-225` | RV32Zdinx reserved behavior | `Zdinx_Fatal`=config_unreachable, `Zdinx_Illegal`=config_unreachable |
| `sail-riscv/model/extensions/FD/zfh_insts.sail:9` | currentlyEnabled Ext_Zhinx | `true`=config_unreachable, `false`=config_fixed |
| `sail-riscv/model/extensions/FD/zfh_insts.sail:10` | currentlyEnabled Ext_Zhinxmin | `true`=config_unreachable, `false`=config_fixed |
| `sail-riscv/model/extensions/FD/zfh_insts.sail:155` | haveHalfFPU | `Zfh_route`=runtime_reachable, `Zhinx_route`=config_unreachable |
| `sail-riscv/model/extensions/FD/zfh_insts.sail:158` | haveHalfMin | `Zfh_or_Zfhmin_route`=runtime_reachable, `Zhinxmin_route`=config_unreachable |
| `sail-riscv/model/extensions/FD/zfa_insts.sail:9` | currentlyEnabled Ext_Zfa | `true`=runtime_reachable, `false`=runtime_reachable, `hartSupports_Zfa_false`=config_unreachable |
| `sail-riscv/model/extensions/bfloat16/zfbfmin_insts.sail:11` | currentlyEnabled Ext_Zfbfmin | `true`=runtime_reachable, `false`=runtime_reachable |
| `sail-riscv/model/extensions/V/vext_control.sail:25` | currentlyEnabled Ext_Zvfh | `true`=state_dependent, `false`=state_dependent, `sole_FLI_H_enabler_when_Zfh_false`=config_unreachable |
| `sail-riscv/model/extensions/Zicsr/zicsr_insts.sail:12` | currentlyEnabled Ext_Zicsr | `true`=config_fixed, `false`=config_unreachable |

## 配置不可达与状态边界

- `fext_insts.sail:31–38` 仅映射静态 0–4 与 DYN 7；编码 5/6 无臂，在译码阶段拒绝，不到达 `select_instr_or_fcsr_rm`。
- `fext_insts.sail:52/55/57–60/63` 是**一套共享函数**：静态 0–4 到 :63；DYN 的 FRM 0–4 到 :56；FRM 5/6 的 `valid_rounding_mode` 为 false，FRM 7 与 RM_DYN 相等，三者经当前 `Fcsr_RM_Illegal` 到 :60 `None`。`:58` 的 `Fcsr_RM_Fatal` 需另一生成配置。
- `fdext_control.sail:18–19` 的 F/D 运行开关由 misa 和 FS 决定；`hartSupports`、Zicsr 与 FLEN 在固定 IR 内不能靠改 misa/mstatus 关闭。D 的 `currentlyEnabled` 不读取 misa.F。直接注入 misa.F=0、D=1 是 runner 状态测试；普通 misa 写路径见 `core/sys_regs.sail:111`，会按 F 位约束 D。
- `haveSingleFPU`、`haveDoubleFPU`、`haveHalfFPU`、`haveHalfMin` 中 Zfinx/Zdinx/Zhinx/Zhinxmin 替代路由在本配置关闭。`dext_insts.sail:220–225` 的 RV32Zdinx 寄存器奇偶与 Fatal/Illegal 分支因此不可达。
- `FLI_H` 的 Zfh/Zvfh OR、H 搬运的 Zfhmin/Zfbfmin OR 在固定支持配置下不能用 misa 位单独关闭任一编译扩展。`Zfa/Zfh` 不是运行时 misa 位；如需验证某扩展支持为 false，须另生成模型/IR。

## 证据解释

JSON 的 `runtime_reachable` / `input_reachable` 表示源码条件允许且有定向输入映射；`config_unreachable` 表示本生成配置排除；`state_dependent` 表示本批 scalar 输入未隔离该条件。它们均不是 trace 统计。49 个 clause 的数值分支、寄存器状态及其他 helper 的完整分母不在此专项清单中，不能把本表各类计数相加当作全模型 branch coverage。
