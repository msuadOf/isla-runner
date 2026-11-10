# RV64 scalar assert 源码排除预备清单

机器可读逐项清单见 [assertion-exclusions.json](assertion-exclusions.json)。本清单从当前 `source_catalog.py.generate(repo_root)` 的 **239 site / 713 arm** 中抽出 **39 个 assert site / 78 个 holds/fails arm**。旧 if/match/mapping 边界是 **635 arm**，没有被本表改写。每项保留 catalog 的 `global_site_key`、`site_id`、源码哈希、原表达式、两臂状态和证据。

## 分类口径

所有条目均为 `constraints_pending_final_ir`：源码、配置和类型支持的结论需与最终候选 IR 的源码哈希、编译配置和调用图绑定后才能扣除。没有使用 runner PASS 或缺少 trace 来证明不可达。**39 个 site 的 assert 条件没有未决真假项**，但每个 site 是否实际保留和被调用仍待最终 IR；可达条件的 `holds` 也仅表示“若调用则成立”。

- **35 个条件固定成立的 site**：`fails` 拟排除，`holds` 在实际调用时可达。固定条件包括 RV64 XLEN、FLEN64、Ext_F=true、Ext_Zfinx=false 和 SYMBOLIC `accrue_fflags` 的恒真后件。
- **4 个整个 site 不可达**：`rF` 的 `_` wildcard 内 `assert(false)`、`float_classify` 最后穷尽类别后的 `assert(false)`、`rF_or_X_D` 与 `wF_or_X_D` 的非F/RV32嵌套偶数寄存器断言。两臂都拟排除。
- 因此拟排除 **43 arm**（35 个 `fails` + 4×2），其余 35 个 `holds` 只有条件可达，不能声称执行 trace 命中。

| 证明类 | assert site |
| --- | ---: |
| `bounded_fregno_wildcard` | 1 |
| `dominated_by_fixed_f_extension` | 2 |
| `exhaustive_fp_classification` | 1 |
| `fixed_extension_xor` | 8 |
| `fixed_f_extension` | 7 |
| `fixed_flen` | 6 |
| `fixed_xlen` | 12 |
| `fixed_xlen_flen` | 2 |

| 来源文件 | assert site |
| --- | ---: |
| `sail-library/float/classify.sail` | 1 |
| `sail-riscv/model/extensions/FD/dext_insts.sail` | 6 |
| `sail-riscv/model/extensions/FD/fdext_regs.sail` | 24 |
| `sail-riscv/model/extensions/FD/fext_insts.sail` | 4 |
| `sail-riscv/model/extensions/FD/zfh_insts.sail` | 4 |

## 证据边界

- 编译配置以 `sail-riscv/config/config.json.in` 的源哈希（见 JSON）和 RV64/FLEN64 前提记录；最终 IR 配置仍须单独核对。当前 `fdext_regs.sail` 与早先 d012 冻结源码不同，JSON 绑定的是本次读取的哈希。
- `assert` 的 `fails` 是断言失败结果，不等于指令 `Illegal_Instruction`；`rF` wildcard 和分类器尾断言的 `holds` 同样不可达，因为断言所在语句本身不可能进入。
- `get_F` / `set_F` 的 Ext_F 断言条件固定真，但其 `fregno` 重载是否存在于最终候选 IR 仍需确认；这两个 site 的 `holds` 不计为动态命中。
- JSON 中每个 site 的 `global_site_key` 含文件、源码 SHA-256、assert token 的字节起止、kind 与 subcondition ordinal；该键可用于最终 IR SourceLoc/源码重定位，行列号只作阅读辅助。

未决项：**39 个 site 的最终 IR 绑定及调用可达性**；其中 `get_F`/`set_F`、被预处理/优化处理的共享包装尤其需要函数定义和调用图证据。条件真假本身没有因本轮缺少动态 trace 而被臆断为未决。
