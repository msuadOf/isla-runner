# E 阶段 FVVTYPE 逐 enum 与 SEW 定向验证

日期：2026-09-26。本目录只对 `FVVTYPE` 做隔离候选的定向证明；没有修改共享 runner、IR、配置或 Isla/Sail 源码。

## 固定受测产物与预期来源

- runner binary SHA-256 `bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425`；完整 V128 IR SHA-256 `c9e1bfe29e75452568d61fc3b3407e707eb1bd7e48193e212495ec21b885bc75`；RV64 E 配置 SHA-256 `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`。接口和此三个产物的来历见同级 `e_nonmem/RESULTS.md` 以及隔离 runner 的 `RUNNER.md`。
- Sail 映射经当前 `sail-riscv/model/extensions/V/vext_fp_insts.sail:16–98` 核对。`FVVTYPE(funct6,vm,vs2,vs1,vd)` 的编码 guard 分别是 Zvfh/SEW16、Zve32f/SEW32、Zve64d/SEW64。执行映射：add/sub/min/max/mul/div 使用对应 FP 函数；sgnj/sgnjn/sgnjx 为位串符号操作。预期数值**未由待测 Sail 生成**：有限输入用 Python 标准库 `struct.pack` 的 IEEE16/32/64 编码及显式算术、符号位公式；边界输入用明确列出的 IEEE 位串和 RISC-V FFLAGS 定义，见两个 `make_*.py`。旧 FFLAGS=NX，精确操作保留 NX；sNaN/无穷乘零令 NV 累计，除零令 DZ 累计。所有预期均包括完整 `vr3`、32 位 `fcsr`、`vstart`、64 位 `mstatus`。
- 编码来自 GNU assembler 2.46 的 `inputs/fvvtype.s`，`inputs/fvvtype.objdump` 保存 GNU 反汇编，头部以稳定名称 `fvvtype.o` 呈现。源 SHA-256 `51fcf71eae9f08c9b12c4185b056dcb2e08a5c869b31498bf9e9f9996b2f41d0`，反汇编 SHA-256 `7b57442a156479172d52e6b2add0b156d78f5539c22453f15a`，`.text` 原始二进制 SHA-256 `83992cffea39bfd68ea475812f47f28bb8fd90533838af784ef0d42e7d11b97e`。每个真实指令字被三档 SEW 使用，`vtype` 分别固定为 `0x8/0x10/0x18`，`vl=2`、`LMUL=1`、`vstart=0`，源为 `v2/v1`、目的为 `v3`。`vta=0`，高于 `vl` 的目标位从零初值保留。

| enum | GNU 指令字 | SEW16 | SEW32 | SEW64 |
| --- | --- | --- | --- | --- |
| `FVV_VADD` | `0x022091d7` | PASS | PASS | PASS |
| `FVV_VSUB` | `0x0a2091d7` | PASS | PASS | PASS |
| `FVV_VMIN` | `0x122091d7` | PASS | PASS | PASS |
| `FVV_VMAX` | `0x1a2091d7` | PASS | PASS | PASS |
| `FVV_VSGNJ` | `0x222091d7` | PASS | PASS | PASS |
| `FVV_VSGNJN` | `0x262091d7` | PASS | PASS | PASS |
| `FVV_VSGNJX` | `0x2a2091d7` | PASS | PASS | PASS |
| `FVV_VDIV` | `0x822091d7` | PASS | PASS | PASS |
| `FVV_VMUL` | `0x922091d7` | PASS | PASS | PASS |

## 可复现命令与逐批结果

从仓库根目录运行。预先将 `E_STAGE` 设为隔离目录 `isla-float-e-nonmem-20260926` 的绝对路径、`D_STAGE` 设为 `isla-float-d-20260926` 的绝对路径，`CASE_STAGE` 设为仓库外工作目录的绝对路径。哈希必须与上节一致。GNU 汇编和预期生成的实际步骤由脚本固定，其中反汇编在对象文件所在目录以文件名调用，以免写入本机路径：

```sh
WORK=agents/float_support_review/tools/e_fvvtype_cases
sh "$WORK/make_inputs.sh" "$CASE_STAGE"
```

本次对象文件和二进制暂存于仓库外工作目录；JSON 和 GNU 反汇编是保留证据。两批执行命令相同，只把 `TAG` 分别置为 `finite`、`edges`：

```sh
TAG=finite
/usr/bin/time -v "$E_STAGE/target/debug/isla-float-e-nonmem-runner" \
  "$D_STAGE/ir/rv64d_d.ir" "$E_STAGE/inputs/rv64-e.toml" \
  "$WORK/inputs/fvvtype-$TAG.json" "$WORK/results/fvvtype-$TAG.json" \
  > "$WORK/results/fvvtype-$TAG.stdout" 2> "$WORK/results/fvvtype-$TAG.stderr"
```

| 输入 → 输出 | 条数 | 输入 SHA-256 | 输出 SHA-256 | wall / RSS |
| --- | ---: | --- | --- | --- |
| `inputs/fvvtype-finite.json` → `results/fvvtype-finite.json` | 27/27 | `8cabe018732e3ecffd8b7ebcdfbc2176653bb3d02b8c83335c05cbc53094fd80` | `b4b8e5a117c2c179a1bdaf1700808647727f6ac0501c5fb1dd1bb28d333725ff` | 6.13 s / 136224 KiB |
| `inputs/fvvtype-edges.json` → `results/fvvtype-edges.json` | 24/24 | `c3e1a613c3770cd3c21549d7f4ecf92db92c4deff9ecd3be14888b5222f034ca` | `0fbac17ebcced2e2d2a5a1f2ca6a2e728d99ea2240f8323ff414e4143f83e67b` | 6.09 s / 136036 KiB |

51/51 条均为 `FVVTYPE`，`zext_decode` 有 2 条相同合法路径，`zencdec_forwards` 反编码 1 条，`zexecute` 有 1 条完成路径且为 `Retire_Success`；每条 `sat=true`、`difference_unsat=true`、`structural_ok=true`。结果 JSON 逐例保存编码、构造器、全部 5 个 tuple 字段、执行状态与耗时。runner 首先确认可达 SAT，再将**目标或任一观察状态与独立预期不等**作析取差异查询并要求 UNSAT。当前 runner 的 `calls=[]` 是未启用调用 trace，不能据此判断未执行普通 Sail 体。`time -v` 原始日志的命令行含隔离工作目录的本机路径；归档的 `.stderr` 只把这些目录前缀替换为 `$E_STAGE`、`$D_STAGE`，其余诊断和测量值不变。

24 个边界例按三档 SEW 各 8 条：min/max 的 ±0 选择、min/max 的 sNaN+有限数（返回数值并置 NV）、min 的 qNaN+有限数（不置 NV）、div 的 1/0（+∞ 与 DZ）、mul 的 ∞×0（canonical NaN 与 NV）、sgnj 的 sNaN payload/符号位保留（不置 NV）。这些辨识例可在 `inputs/fvvtype-edges.json` 查到每个确定位串。

负控制：`inputs/negative-control.json` 将 SEW16 VFADD 正确结果最低位故意翻转，runner 退出 `101`；`results/negative-control.stderr` 显示实际 `vr3=0xbe004380`、错误预期 `0xbe004381` 且差异为 SAT，未误记通过。该故意失败不计入 51 条通过样例。早先测试脚本曾试图使用 zsh 只读变量 `status` 保存退出码，shell 在赋值处报错；随后改为 `run_exit` 重跑，保存的 `results/negative-control.exit` 为 `101`。证明批次本身无失败或预期修正历史。

负控制的实际调用：

```sh
"$E_STAGE/target/debug/isla-float-e-nonmem-runner" \
  "$D_STAGE/ir/rv64d_d.ir" "$E_STAGE/inputs/rv64-e.toml" \
  "$WORK/inputs/negative-control.json" "$CASE_STAGE/negative-control-result.json" \
  > "$WORK/results/negative-control.stdout" 2> "$WORK/results/negative-control.stderr"
run_exit=$?
printf '%s\n' "$run_exit" > "$WORK/results/negative-control.exit"
```

## 适用边界

这是一组具体输入及所列观察寄存器的定向证明，涵盖 9/9 enum×3/3 合法 SEW 格，不代表各格的全部 FRM、NaN payload、mask/vstart、tail policy 或所有输入域等价。`VFADD.VV` 的独立 mask/vstart/sNaN 例见同级 `e_nonmem/RESULTS.md`。此组无硬件运行，也不替代公共 `make solve` 的整库验收。
