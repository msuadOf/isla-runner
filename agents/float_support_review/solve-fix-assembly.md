# 官方 solve 浮点汇编文本修复

2026-09-26，按用户已授权的“根据审计全部调通”实施汇编文本工作包。仅修改 Sail 汇编映射；数值、flags、执行 guard 和已有 BF16 工作树修改均保留。本工作包没有生成或替换主 IR。审计原结论见[日志与 JSON 语义复核](solve-audit-log-semantics.md)，实施边界见[修复架构](solve-fix-architecture.md)。

## 实施

| 文件 | 修改 |
| --- | --- |
| [zfa_insts.sail](../../sail-riscv/model/extensions/FD/zfa_insts.sail) | 三个 FLI `assembly` 共用新增 `fli_constant_mnemonic : bits(5) <-> string`，按编码索引打印标准立即数。前置 `val` 替换原第 12 行空白；mapping 定义追加文件末尾，原 execute 行号未移动。 |
| [zvfbfmin_insts.sail](../../sail-riscv/model/extensions/bfloat16/zvfbfmin_insts.sail) | 两种向量转换移除 `maybe_vmask` 前的多余 `sep()`；复用已有 `maybe_vmask` 负责可选逗号和 `v0.t`。 |
| [zvfbfwma_insts.sail](../../sail-riscv/model/extensions/bfloat16/zvfbfwma_insts.sail) | VV/VF MACC 的第二、第三寄存器之间由 `spc()` 改为既有 `sep()`。两文件原行数保持不变。 |
| [assembly_text 测试](../../sail-riscv/test/assembly_text/README.md) | 直接抽取生产映射为可执行 Sail 小模型，验证 FLI 与 BF16 标准文本、LLVM 编码和 FLI 字面值映射双向往返。 |

这里没有把立即数命名从实际浮点结果反推。Zfa 常量表的 32 个编码拥有 32 个独立文本：索引 1 使用 `min`，由指令格式决定对应最小正规数；30、31 使用 `inf`、`nan`。索引 29 使用 `65536.0`，即使 H 的数值结果与索引 30 都是 `0x7c00`，二者文本仍不同，因此逆向映射不歧义、不丢编码。其余普通值使用 LLVM 接受的精确十进制字符串，三个格式共用同一映射。

真实 LLVM 实测 `fli.h f0, 65536.0` 编码为 `f41e8053`（索引 29），`fli.h f0, inf` 为 `f41f0053`（索引 30）；没有将两者合并，也没有改变对应数值表。使用现有 Sail `mapping` 机制自动生成正反方向，不引入同名函数或手写 parser。

## 红绿验证

受测 Sail 为 0.20.1 (`446fb477c508853595ccc937ed60765aa685ae31`)，LLVM 为 22.1.8。以下目录名指调用者保存的仓库外证据目录。

| 阶段 | 证据目录 | 结果 |
| --- | --- | --- |
| 修改前红测试 | `isla-solve-fix-assembly-red` | 真实 Sail 小模型编译及正向打印完成；104 条原文本全部与规范文本不同，LLVM 汇编失败；`summary.json` 记录 104 个文本失败及 1 个汇编器汇总失败。 |
| 修改后绿测试 | `isla-solve-fix-assembly-green` | 104/104 标准文本、LLVM 机器码一致；32/32 FLI 立即数映射在 Sail 中 `index → token → index` 往返通过。 |
| 复用接口回归 | `isla-solve-fix-assembly-green-final` | 为 replay 工作包从同脚本抽出 `assemble_texts`/`decode_encodings` 接口后复跑，仍为 104/104 文本/编码与 32/32 立即数往返通过；生产映射未再改动。 |
| 完整模型 strict 检查 | 同绿测试目录 `full-check.log` | PASS，退出 0；SYMBOLIC、V128/ELEN64/RV64、全部模块及三项 strict 开启，只有既有 effect 注释弃用警告。 |

104 条为 FLI.H/S/D 的 96 条，加上两个 BF16 转换和 VV/VF MACC 各自有掩码/无掩码的 8 条。FLI 每个格式的目标寄存器遍历全部 32 个编号。测试源码不复制生产映射为另一份实现，而是从当前源文件提取真实映射；Python 预期文本/编码表与标准 LLVM 汇编器共同构成独立检查。

复跑命令（从工作区根目录）：

```sh
: "${ASSEMBLY_TEST_OUT:?set a fresh external output directory}"
python3 sail-riscv/test/assembly_text/check.py "$ASSEMBLY_TEST_OUT"
```

完整模型检查（`FORMAL_CONFIG` 为已冻结 V128 配置，SHA-256 `89923ebff21718bb382df38bf246207cbb1eb5ae0cd314d078d87c0ab2b9f625`）：

```sh
: "${ASSEMBLY_TEST_OUT:?set an external output directory}"
: "${FORMAL_CONFIG:?set the frozen rv64d_v128_e64.json path}"
cd sail-riscv/model
sail -D SYMBOLIC --strict-var --strict-bitvector --strict-exponentials \
  --require-version 0.20.1 --memo-z3-path "$ASSEMBLY_TEST_OUT/full_sail_smt_cache" \
  --all-modules --just-check --config "$FORMAL_CONFIG" riscv.sail_project \
  > "$ASSEMBLY_TEST_OUT/full-check.log" 2>&1
```

绿测试源文件 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `zfa_insts.sail` | `804b002f96e7be22f6fd3173a143b545d7802f4979b5d68f65280b947f186ca0` |
| `zvfbfmin_insts.sail` | `460bbdd197fb4a87c614c8556cc4c6701f16b2b7e7b7832a8ddf31f0b4ee5a1a` |
| `zvfbfwma_insts.sail` | `936f99356860180f94041d489ae79a6bebad900c2c1120d547dc71ce86233fad` |

## 工具边界与集成

Sail 0.20.1 将完整 `assembly_backwards` 标为 `not executable`，在 C probe 中调用 `assembly(text)` 被检查器拒绝。`assembly_backwards_matches` 虽可编译，但所生成 C 函数只有 `sail_match_failure` 分支，运行也立即失败；红测试目录的 `effects.log` 记录前者。故本次验证明确分为“真实 Sail 正向打印 + LLVM 整条汇编解析/编码”和“纯字面值 FLI mapping 的 Sail 正反往返”，没有声称完整 Sail assembly 反解析通过，也没有手写替代解析器掩盖限制。

下一步由主集成工作包重新生成冻结 IR、同步严格配置哈希并核对全部 region 锚点，再以官方 `make solve-*` 验证输出文本。虽然原执行代码行号保持不变，IR 结构和哈希仍会变化，不能仅凭行号未变跳过严格绑定复验。当前主 `d0123541…` IR 仍含旧映射，不能拿本次源码绿测试代替新 IR 验证。
