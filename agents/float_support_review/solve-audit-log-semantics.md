# 官方 solve 日志与 JSON 的语义复核

2026-09-26，只读检查官方批次 `isla-float-official-d012-20260926-150048` 的 `stage{,2,3,4}/output/`；没有修改被测源码、IR、配置、输出或运行进程，也没有访问独立内存 worktree。受测 IR 为 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`。入口和证据解释遵循[审计口径](solve-audit-method.md)。

## 1. 本次能回答的问题

官方 JSON 的 `ret_val` 只表示 Sail 返回的退休类别，`isa-state` 为输入状态；没有目的寄存器结果、post-state 或输出 fflags。故本次核对的是输入、编码、文本和退休类别是否自洽，不能从日志给出数值、五 flags 或全部副作用正确的结论。

77 个目标全部收尾后，直接读取 4 个输出目录中的 41 份完整 JSON，共 3,474 条记录：3,350 条 `Retire_Success`、124 条 `Illegal_Instruction`。必需字段 `arch/test-ins/test-ins-encdec/isa-state/ret_val` 均非空；没有其他退休类别。存在 JSON 不代表 clause 完整通过，返回错误的 clause 也可能写入已经完成的部分路径，退出分类以本批主审计结果为准。

最终复核结果：

- 3,474 条编码都是合法格式的 32 位位串；寄存器编号、存在的 rm 字段与汇编文本一致。
- 除 FLI 的 96 条外，1,169 个唯一汇编文本覆盖 3,378 条记录，使用 LLVM 22.1.8 `llvm-mc` 重新汇编，编码逐条一致。
- 96 条 FLI 文本不能被标准汇编器解析，见第 3 节；其编码与 Sail 常量表索引一致。
- 全部 3,474 条都没有 `fcsr`，也没有 `mstatus`。443 条显式 `dyn`（350 成功、93 Illegal）均因此缺少决定舍入/合法性的具体值。`fcsr` 缺失是已确认的独立重放缺口；`mstatus` 缺失要结合直接 constructor 执行的边界解释，不能单独认定数值错误。
- 逐条计算 `vtype/vl`：全部满足 `RV64::constrain_pre_state` 的合法 SEW/LMUL/VLMAX 或 `vill => vl=0` 约束；没有向量 Success 使用 SEW8 或 vill=1。
- 扫描 77 份日志未发现 `Z3Unknown`、`unknown` 或 panic 文本，且现有 JSON 没有空字段记录。这个观察不能消除 collector 的潜在错误收集缺口，详见[审计口径](solve-audit-method.md)。

将 41 个 JSON 按其 `stage*/output/*.json` 路径字典序排序并拼接文件内容，SHA-256 为 `bea6a46b44f2fbb328a7496f7d397405e88d29563f2f73372a5a6bd12d495963`。复核命令使用只读 Python `json.load`、正则字段检查及 LLVM 的 stdin 文本汇编；没有覆盖官方产物。

## 2. 正常 Illegal 与尚不能独立重放的状态

### 标量/BF16 动态舍入

`FCVT_S_BF16` 为 39 条：36 成功、3 Illegal，其中 33 条 `dyn`。`FCVT_BF16_S` 为 36 条：30 成功、6 Illegal，其中 21 条 `dyn`。六个 `FROUND{NX}_{H,S,D}` 中，H/S 各 36 条（30 成功、6 Illegal），D 各 23 条（20 成功、3 Illegal）。后续 `F_UN_RM_FF_TYPE_S` 为 16 条（10 成功、6 Illegal）、`F_UN_RM_FX_TYPE_H` 为 344 条（320 成功、24 Illegal）、`F_UN_RM_XF_TYPE_H` 为 144 条（120 成功、24 Illegal）。全体标量 JSON 的 93 条 Illegal 全部使用 `dyn`，没有观察到静态合法 rm 返回 Illegal 的矛盾样例。

这与 [fext_insts.sail](../../sail-riscv/model/extensions/FD/fext_insts.sail) 的 `select_instr_or_fcsr_rm` 相符：静态 rm 直接返回 `Some`；`dyn` 读取 `fcsr[FRM]`，在本批 `Fcsr_RM_Illegal` 策略下，frm 为 5/6/7 时返回 `None`，clause 再返回 Illegal。BF16 两个执行入口分别位于 [zfbfmin_insts.sail](../../sail-riscv/model/extensions/bfloat16/zfbfmin_insts.sail) 第 20、45 行。

例如 `FCVT_S_BF16` 的 `gen[0]` 是 `fcvt.s.bf16 f30, f8, dyn`，编码 `40647f53`，返回 Illegal，却没有记录能决定该分支的 frm。源码中这一 clause 唯一的显式 Illegal 条件就是上述 `None`。因此此记录可解释为正常非法 frm 路径，但使用者不能只凭 JSON 独立重放这个判定。

[target.rs](../../isla/src/isarch/target.rs) 第 413 行的 RV64 `reg_list` 没有 `fcsr`；`solve_pre_state` 只遍历这份清单建立的 `PreStateCtx`。现有日志有 `fcsr` taint 并不补足其具体初值。此外 fflags 的旧值也没输出，不能验证累计副作用。没有参与路径约束的其他寄存器按既有设计可省略，不把这种省略计为本问题。

### 向量移动、vill 与 vstart

| Clause | 完整 JSON | 成功 | Illegal | 判据与解释 |
| --- | ---: | ---: | ---: | --- |
| `VFMVFS` | 16 | 3 | 13 | `illegal_fp_vd_unmasked` 检查 vill、SEW 和 frm；另检查 SEW ≤ FLEN。3 条成功分别 SEW16/32/64。 |
| `VFMVSF` | 38 | 20 | 18 | 同样先检查 vill/frm，再由 `init_masked_result` 检查 vstart；没有观察到 SEW8 成功。 |

源码为 [vext_fp_insts.sail](../../sail-riscv/model/extensions/V/vext_fp_insts.sail) 第 891–927、1433–1486 行，辅助条件为 [vext_fp_utils_insts.sail](../../sail-riscv/model/extensions/V/vext_fp_utils_insts.sail) 第 16–36 行和 [vext_utils_insts.sail](../../sail-riscv/model/extensions/V/vext_utils_insts.sail) 第 274 行。

- `VFMVFS gen[6]`：`vfmv.f.s f10, v2`，`vtype=8000000000000000`、`vl=0`，Illegal 符合 `valid_vtype() = vill == 0`。
- `VFMVSF gen[7]`：`vfmv.s.f v5, f0`，`vtype=9`（SEW16）、`vstart=8000000000000000`，Illegal 符合 `get_start_element` 的上界检查。
- `VFMVSF gen[17]`：`vstart=32`、`vl=7`、SEW16，却成功，不是自相矛盾。当前 Sail 的 `get_start_element` 上界是 `2^(3 + vlen_exp - SEW_pow)-1`，VLEN128/SEW16 时为 63，允许这个值；活动 lane 为空时仍可正常退休。该源码已带上界可能不正确的 TODO，本次不把它升级为浮点改动引入的数值反例。
- 标量成功记录中也有 vill=1；标量指令不依赖向量类型，这是正常无关状态，不能因 `vtype` 高位非零判错。

`VFMVFS/VFMVSF` 的若干 Illegal 记录为 SEW8；它们不满足这两个 clause 正向 `encdec` 的 SEW16/32/64 守卫。执行器从 constructor 直接调用 execute，再逆向物化编码，所以会出现这类可执行 constructor 状态。这不能当成覆盖了一个真实可译码的 SEW8 浮点指令，也不能当成浮点算术错误。

向量指令即使助记符没有 `dyn` 后缀，当前模型也会读取 frm。仅统计文本 `dyn` 会漏掉向量 JSON 的 `fcsr` 重放缺口。

## 3. 已确认的汇编文本问题

这三类格式问题在当前 Sail HEAD `f8ce849` 中已经存在；本轮工作树 diff 没有修改相应 `assembly` 映射。它们是现行交付的缺口，不能归为 C1 浮点数值迁移新引入的回归。

### FLI 输出表索引，标准汇编要求浮点立即数

[zfa_insts.sail](../../sail-riscv/model/extensions/FD/zfa_insts.sail) 的 FLI H/S/D `assembly` 映射分别在第 19、69、119 行使用 `hex_bits_5(constantidx)`。3 份 JSON 各有 32 条，完整覆盖索引 0–31；编码与索引一致。但如 `FLI_S gen[16]` 输出：

```text
test-ins:        fli.s f0, 0x10
test-ins-encdec:  32'hf018_0053
ret_val:         Retire_Success(())
```

LLVM 22.1.8 的以下验证拒绝第一行，第二行产生 JSON 中的 `f0180053`，第三行产生不同的 `f01c8053`：

```sh
llvm-mc -triple=riscv64 -mattr=+f,+d,+zfh,+zfa -show-encoding <<'EOF'
fli.s f0, 0x10
fli.s f0, 1.0
fli.s f0, 16.0
EOF
```

96 个 FLI 原文全部得到 `invalid floating point immediate`。结论是标准汇编文本重放失败；原始编码可使用 `.word` 等方式重放，编码与数值模型没有因此被证明错误。

### BF16 向量转换的额外逗号

[zvfbfmin_insts.sail](../../sail-riscv/model/extensions/bfloat16/zvfbfmin_insts.sail) 第 62、113 行在 `maybe_vmask(vm)` 前额外拼接 `sep()`；[vext_utils_insts.sail](../../sail-riscv/model/extensions/V/vext_utils_insts.sail) 第 14–17 行的 `maybe_vmask` 已经包含所需逗号，未掩码分支则为空。因此日志实测生成：

```text
vfncvtbf16.f.f.w v12, v3,
vfwcvtbf16.f.f.v v31, v3, , v0.t
```

第一条来自 `VFNCVTBF16_F_F_W.log` 第 29 行，同一日志编码为 `4a3e9657`。`llvm-mc -triple=riscv64 -mattr=+f,+d,+v,+zvfbfmin -show-encoding` 拒绝原文；删掉末尾逗号后正常产生 `[57,96,3e,4a]`。两类错误均已在官方日志观察到；这些外限 clause 当前没有完整 JSON，不能把日志中看到的局部输出算作完整验收。

### BF16 MACC 寄存器之间缺逗号

[zvfbfwma_insts.sail](../../sail-riscv/model/extensions/bfloat16/zvfbfwma_insts.sail) 第 62、121 行在第二、第三寄存器之间拼接 `spc()`，漏了分隔逗号。两个官方日志的第 29、34 行给出：

```text
VFWMACCBF16_VV: vfwmaccbf16.vv v16, v12 v3   / ee361857
VFWMACCBF16_VF: vfwmaccbf16.vf v16, f12 v3   / ee365857
```

LLVM 22.1.8 `llvm-mc -triple=riscv64 -mattr=+f,+d,+v,+zvfbfwma -show-encoding` 对两条原文都报 `unexpected token`；补上逗号后分别产生 `[57,18,36,ee]`、`[57,58,36,ee]`，与日志编码一致。此项已经动态观察，结论同样只针对汇编文本重放。

四个 BF16 向量 clause 最终均无完整 JSON，但日志已有以下局部结果。日志多线程输出可能交错，不能用相邻文本强行绑定每个终点、汇编和输入状态；表中的计数分别来自对应字段的实际出现次数。

| Clause | 汇编文本条数 | 日志 Success | 日志 Illegal |
| --- | ---: | ---: | ---: |
| `VFNCVTBF16_F_F_W` | 189 | 0 | 189 |
| `VFWCVTBF16_F_F_V` | 201 | 8 | 194 |
| `VFWMACCBF16_VV` | 204 | 3 | 201 |
| `VFWMACCBF16_VF` | 197 | 3 | 194 |

相应 `assembly` 映射对成功和非法路径都适用。局部 Success 没有 post-state，不能证明这些路径的 BF16 结果和 fflags 正确；没有 Success 的 `VFNCVTBF16_F_F_W` 也只能说本预算未观察到成功，不推导为合法路径不可达。

### 与正常非法汇编的区分

日志中另有被 LLVM 拒绝的 `vd=v0` 掩码、`vfmerge vd=v0`、禁止源目的重叠等编码。这些与 Sail 的 `valid_rd_mask`、`illegal_fp_vd_masked`、`valid_reg_overlap` 或特定 slide guard 相对应，属于正常 Illegal 候选。标准汇编器拒绝保留/非法编码不等于打印语法错误，也不证明执行器错误；仍需按其 Sail 返回和 guard 判断。

## 4. 元数据与真实译码边界

[exec.rs](../../isla/src/isarch/exec.rs) 第 51 行将每条记录的 `arch.ext` 固定为 `IMACFD`。因此 BF16、Zfa、Zfh、V 的输出没有完整表达扩展需求，不能靠这一字段选出正确重放 ISA。

执行后的 `try_get_assembly_encdec` 不等价于将编码在输入状态下正向译码。`mstatus` 虽在 `reg_list` 中，但未进入路径条件时被 `solve_pre_state` 省略；当前完整 JSON 均未输出它。真正的 F/D 启用由 [fdext_control.sail](../../sail-riscv/model/extensions/FD/fdext_control.sail) 第 18–19 行要求 FS 非 Off，向量启用在 [vext_control.sail](../../sail-riscv/model/extensions/V/vext_control.sail) 第 17–21 行还要求 VS 非 Off。故当前 JSON 的 constructor 退休结果不能独立证明真实机器状态的译码使能；重放工具需要外部约定扩展、FS/VS 等启动状态。

## 5. 当前判断

已检查记录未显示编码寄存器/rm 与原模型文本矛盾，也未发现可以仅由这些输入字段证明的错误退休类别。正常 Illegal 不计执行器失败。但存在明确的 `fcsr` 重放状态缺失、FLI/BF16 汇编文本不可被标准汇编器使用、扩展元数据不完整，以及全体输出不含结果状态的证据边界。此次语义复核完成，不构成浮点全输入或完整数值验收 PASS。
