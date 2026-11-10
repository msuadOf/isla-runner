# 浮点纯数据比较修复（2026-09-26）

用户授权继续收敛浮点 `make solve` 路径。Astra architecture/performance 审定后，本包仅修改 `sail-riscv/model/core/ieee_fp_exceptions.sail` 和 `model/extensions/FD/softfloat_symbolic_f16.sail`、`softfloat_symbolic_f32.sail`、`softfloat_symbolic_f64.sail` 的 SYMBOLIC 纯数据比较；不修改舍入模式、IEEE 数值/异常算法、五 Bool 事实结构、架构 guard 或全局 Isla primop。

## 原因与修改

Isla `eq_bits/neq_bits` 及 `eq_bool` 使用 `try_concretize_bool_exp`，会主动查询 SMT。浮点结果再次进入分类或饱和方向判断时，这种提前查询可能把尚在构造的复杂 FP 表达式送入求解器。通用 `eq_anything` 对 Symbolic 参数只定义相等式；配合 `not_bool` 与 strict Bool 可以保留表达式语义而省去这类提前查询。真实指令超时诊断和整体性能由 performance 工作包另行记账，本包不据局部测试宣称官方批次已收敛。

具体修改：

- 五个分类函数继续调用 Sail `float_decompose`、使用 `float_bits` 字段；exp/mantissa 全零、全一以及 sNaN quiet 位改为 `eq_anything`。未恢复各格式硬编码切片，也未新增重复分类函数。
- f16/f32/f64 Add/Sub 的无穷符号关系、Sqrt 的输入 sign、FMA 的乘积与加数 sign 比较使用纯等值表达式。
- 三种格式的四个整数转换包装只改饱和方向的 sign 等值，共 12 处；返回值、flags 和合法性规则保持原样。

FMA 的外层 Bool 不等需要额外处理：直接 generic Bool 相等、显式 `: bool`、调换参数顺序及 Bool ITE 均在 Sail 0.20.1 触发 singleton Bool 类型约束失败。退回 `eq_bool` 仍会主动查询。Astra 批准用 `strict_or_bool(strict_and_bool(p, not_bool(c)), strict_and_bool(not_bool(p), c))` 表达相同 XOR，局部 `c_negative` 保留原 sign 判定。小 IR 已确认三种 FMA 函数体没有被重新专化成主动比较或条件分支。

## 先红后绿与旧新等价

专属工具见 [测试说明](../../sail-riscv/test/solve_pure_compare/README.md)。修改前先冻结四份实际生产源，再从这些真实文件生成小 IR。结构测试在旧 `is_all_ones` 的 `eq_bits` 调用处失败；没有把手写伪造旧逻辑作为红例。修改后用真实新生产文件生成旧新同模型探针，严格编译通过，分类调用闭包的 7 个函数没有 `eq_bits/neq_bits`；24 个 sign/整数饱和函数体没有 `eq_bits/neq_bits/eq_bool/neq_bool` 或分支。按具体位宽选择格式的 `float_decompose` 分支仍保留。

外部证据目录名为 `isla-float-pure-compare-20260926`：`old/` 为冻结源码，`red/` 为结构红例，`green/` 为成功候选及逐项日志。实际执行使用 Sail 0.20.1 和 D 候选插件；动态 runner 依赖删除旧浮点分发的 D 隔离 `isla-lib`。该候选和当前主执行器的通用比较实现相同；最终主候选的 277 helper 与完整测试由集成人另跑。

成功命令参数为：

```sh
python3 sail-riscv/test/solve_pure_compare/prepare.py \
  "$PURE_COMPARE_OUTPUT/old" "$PURE_COMPARE_OUTPUT/green"
python3 sail-riscv/test/solve_pure_compare/run.py \
  "$PURE_COMPARE_OUTPUT/green" "$ISLA_PLUGIN" \
  --isla-lib "$D_STAGE/isla-candidate/isla-lib"
```

两种模式的 `--strict-var --strict-bitvector --strict-exponentials --just-check` 均退出 0。27 个比较入口全部退出 0，合计执行 7.221 秒，逐入口约 0.26–0.29 秒：

| 范围 | 输入域 | 检查与结果 |
| --- | --- | --- |
| 五类分类，f16/f32/f64 | 原始位串完全未知 | 五个分类 Bool 同时比较；3/3 SAT、差异 UNSAT、唯一完成路径 |
| Add/Sub/Sqrt/MulAdd，三种格式 | 浮点位串完全未知，RM 符号映射覆盖 0–4 | 完整结果位和五 flags 同时比较；12/12 SAT、差异 UNSAT、唯一完成路径 |
| ToI32/ToUi32/ToI64/ToUi64，三种格式 | 原始位串完全未知，RM 符号映射覆盖 0–4 | 包含 NaN、无效饱和值及 NV/NX 优先级的完整输出；12/12 SAT、差异 UNSAT、唯一完成路径 |

这 27 项证明的是本次替换前后等价，不是独立 IEEE 正确性证明；RM 编码检查、全部 67 helper、真实指令和官方 `make solve` 结果不能由这组局部通过代替。源码冻结后仍须以最终生成的完整 IR 重验。

## 冻结哈希

| 文件或证据 | SHA-256 |
| --- | --- |
| 新 `core/ieee_fp_exceptions.sail` | `6a53eb013721787194a4fb370974e785fd0751f35f9d6cb66bb360ff82d6faeb` |
| 新 `softfloat_symbolic_f16.sail` | `94f728cbd3f560c6c71f84072ff87f4cdffce2ade7dcd136590b257e7422c61c` |
| 新 `softfloat_symbolic_f32.sail` | `31a36c513ac58ad05c2248d965898507d11e0aca832c912b25df14d72cdcbfc7` |
| 新 `softfloat_symbolic_f64.sail` | `af79ba96fcc1e7a597c8104283436a1bcaa8749ddb6a0d570d5dbc99e9a5fbf9` |
| `green/manifest.json` | `c688b87a8b554bfb0589002483a0255f7edbc7a7df8cb62acaefb5b8cac29d83` |
| `green/probe.ir` | `a529bc743fe4b3a170b06f0fbd754da184a44f96f79a8d47c4df49eb885030a3` |
| `green/results.json` | `0c7bf69a52eccf71e89aeef82d273a43f855af64e2c2550dcb6a9b6e45683273` |

旧四源哈希持久保存在 `test/solve_pure_compare/before-manifest.json`，反向补丁支持只在外部目录还原相同旧源码；还原后必须全部匹配才可运行比较。四个生产文件在此交付后不再由本包继续修改；其他模型文件、内存工作树和已有 dirty 内容均保留。
