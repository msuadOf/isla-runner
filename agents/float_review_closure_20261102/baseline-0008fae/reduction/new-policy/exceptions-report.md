# 算术异常原因分支的数据流候选

本文件只记录可审阅的源码候选。生产模型 `e9d69d2f28586c089244c8e37ee4c904c5114458`、冻结的 runner-float 214 源码、IR 和输入均未修改。候选只针对 `model/core/ieee_fp_exceptions.sail` 的 H/S/D 共 18 个算术异常 helper；来源文件 SHA-256 为 `866f85a607b112d57a0ea8c6d9a85c1befb36ef11ea39b7058a252606df257cd`。Isla 的 `0008fae` 是另一仓库的共同参照，不是本候选模型源码版本。

[候选整文件](candidate-ieee_fp_exceptions.sail) SHA-256 为 `7ed9529baac57717875ea49e8fff5130d3ec611f824aa71483b2b856d67c96b4`；[相对 e9 的精确差异](exceptions-source.diff) SHA-256 为 `c004552a66db697d984c193dbde6e25ad6f46c3091bfbc4af5f7389502f2c6dd`。[构造脚本](exceptions-build-candidate.py)以固定来源文件哈希为前提，只写本目录的候选和差异；重新执行得到同一候选哈希。

| 操作 | H/S/D 回退的原因 `if` 数 | 恢复的数据流事实 |
| --- | ---: | --- |
| add/sub | 6（各宽度各 1） | `invalid_nan OR invalid_inf`；无 DZ。 |
| mul | 6（各宽度各 2） | 零乘无穷的两个方向先 OR，再与 `invalid_nan` OR；无 DZ。 |
| div | 9（各宽度各 3） | `0/0`、`Inf/Inf` 与 `invalid_nan` 合成 NV；有限非零数除零独立置 DZ。 |
| sqrt | 3（各宽度各 1） | 负且非零、非 NaN 的输入与 `invalid_nan` 合成 NV；负零仍按原有效输入处理。 |
| FMA | 9（各宽度各 3） | 零乘无穷两个方向和无穷乘积与加数抵消合成 NV；每源 `invalid_nan` 继续独立求值。例如 `0 × Inf + sNaN` 仍置 NV。 |
| **合计** | **33** | 原 NV/DZ 原因谓词与五位 flags 保留。 |

候选保留每个 helper 原有的 `finite/valid` gate：普通 `lo`、`hi`、`rounded` 及融合 FMA 的原生 FP 计算仍只在原真臂执行；假臂的 OF/UF/NX 为 false。原生计算行和 FMA 调用次数未改。NaN 分类、结果传播和最终状态写回不在本候选改动范围。依[正式架构裁决](../../architecture-decision-20261103.md)，33 个仅选择 NV/DZ 返回位的原因分支为 REVERT，而这 18 个 gate 为 OPEN；本候选保留 OPEN 项，不把“保留”解释为已通过新增分支的证据门。

`python3 agents/float_review_closure_20261102/baseline-0008fae/reduction/new-policy/exceptions-audit-candidate.py` 退出 0。[审计脚本](exceptions-audit-candidate.py)逐函数断言原生 FP/lo/hi/rounded 行一致、每函数保留一个 gate、按操作精确减少 1/1/2/3/1/3 个原因 `if`，合计 33；[机器结果](exceptions-source-audit.json)记录 18 个函数、55,584 组局部 flags 对照。对照输入按每源正负零、normal、subnormal、Inf、qNaN、sNaN 共 12 类，并让 OF/UF/NX 三位取全部 8 种组合；它验证原因合成与 flags 选择，不执行 Sail 数值计算、IR 或完整 Clause。生产模型树核对为干净的 `e9d69d2`。

本候选尚未应用于独立模型树，也未运行候选版严格检查、IR 生成、动态数值或 7200 秒预算验收。旧 e9 或 214 的动态 PASS 不迁署给该候选；若后续实施，须以新源码与 IR 哈希重新验证。
