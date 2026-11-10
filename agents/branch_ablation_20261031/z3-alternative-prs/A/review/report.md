# 候选 A 独立审查

结论：**当前提交存在一个应在上游 PR 前修复的功能回退，暂不建议按原样提交为可用备选。** 简单枚举的域约束、模型恢复、假设、增量以及 proof/core 保护在本轮探针中未发现错误；全局加入 `dt2bv` 会额外覆盖 lambda 和无 FP 枚举任务，已有实证回退。

受审提交 `4e6105c2830a4b6ebaef1a7b340e6dea602bafa2`，基线 `8fbb275aba0472e862e289c7af1331b3bd5d512c`。使用 A 的冻结独立可执行文件和库；精确哈希见 [provenance.json](provenance.json)。未切分支、未修改源码、未编译共享 build、未阅读 B 或其他 reviewer 结论。写入限于本目录。

## P2／阻断：枚举 lambda 的绑定变量被错误改写，合法输入 UNSAT 变 UNKNOWN

入口是 A 的 `src/tactic/portfolio/default_tactic.cpp:48`：对所有无 proof/core 的 goal 先执行 `dt2bv`，没有 lambda 适用性保护。

已有 `src/tactic/bv/dt2bv_tactic.cpp:84–90` 将枚举 bound variable 所属 sort 加入可转换集合，但 lambda 回调不排除该 sort。`src/ast/rewriter/enum2bv_rewriter.cpp:146–148` 将 body 的变量改为 BV；同文件 `:200` 对 lambda 直接返回 false，保留原来的枚举 binder。于是产生类型不一致的内部表达式。

完整最小例在 [lambda-array-true.smt2](lambda-array-true.smt2)：

```smt2
(declare-datatypes () ((E A B C)))
(declare-const arr (Array E Bool))
(assert (= arr (lambda ((y E)) (= y A))))
(assert (= arr ((as const (Array E Bool)) true)))
(check-sat-using default)
(get-info :reason-unknown)
```

预期 UNSAT：lambda 在 B、C 处为 false，不能等于全 true 数组。基线返回 UNSAT；A 立即返回 UNKNOWN，原因明确为：

```text
Sort mismatch at argument #1 for function
(declare-fun = ((_ BitVec 2) (_ BitVec 2)) Bool) supplied sort is E
```

对同输入执行 `(apply (then simplify dt2bv))`，可直接看到错误形式：

```smt2
(= arr (lambda ((y E)) (= y #b00)))
```

完整输出见 [lambda-transform.stdout](lambda-transform.stdout)，双侧结果见 [independent-results.json](independent-results.json)。这不是相同限时下的搜索性能差异；无资源限制即可稳定触发。尚未观察到 SAT/UNSAT 互换，不声称已有错误求解答案。

最小修复方向：默认入口在 lambda 存在时跳过该转换，或先修复 `dt2bv` 对 lambda 所用枚举 sort 的适用性判定；不能只保护原 FP 枚举测试中的类型。修复后必须补入上述回归，重验其他新增路径。

## P2／性能边界：无 FP 的纯枚举任务也会增加预处理开销

同一入口在枚举只有自由常量和 distinct 时也执行转换。`enum2bv_rewriter.cpp:163–181` 为每个新枚举常量立即创建覆盖所有构造器的模型恢复 ITE，成本随“常量数 × 构造器数”增长，即使没有请求模型。

独立生成的纯枚举 SAT 查询，32 个自由常量且两两不同；相同 CPU 112–115，各三次，进程墙钟中位数为：

| 枚举构造器数 | 基线 | A | 比值 |
| --- | ---: | ---: | ---: |
| 1024 | 0.0466 s | 0.1044 s | 2.24 |
| 8192 | 0.0951 s | 0.4832 s | 5.08 |

输入见 [wide-8192-32.smt2](wide-8192-32.smt2)，各次原始结果见 `independent-results.json`。此项是稳定的本地开销实证，不外推为所有枚举任务退化；本轮未测 RSS，也未制造内存耗尽。它可作为上游设计取舍，但 PR 必须说明 A 扩大了无 FP 任务的影响范围，不能只宣称 FP 分发修复而无旁路成本。

## 适用性与保护核对

- **一般 datatype**：`dt2bv_tactic.cpp:45` 仅允许 `is_enum_sort`，有字段或递归 ADT 不直接转换。ADT selector 返回枚举会使该 sort 进入排除集合（`:64–66`）。独立 selector 反例返回预期 UNSAT。
- **UF、数组、枚举 ITE**：有参数的枚举结果，或作为其他应用参数的枚举，会通过 `:64–81` 将整个枚举 sort 排除；同 goal 中另一个安全枚举 sort 仍可能转换。枚举 UF 参数和数组值域探针均保持预期；不能把这描述为完整支持任意 UF/数组枚举转换。
- **forall/exists**：该预处理并不一概排除量词。`enum2bv_rewriter.cpp:204–240` 改 binder sort，forall 加域蕴含、exists 加域合取。独立三值枚举穷尽域 UNSAT 与嵌套 forall/exists SAT 通过。lambda 的处理与它们不同，产生上面的阻断。
- **有限域**：自由常量通过 `:73–87,163–167` 增加范围约束，非二次幂排除多余编码；单构造器固定为 0。模型恢复通过 `dt2bv_tactic.cpp:148–153` 隐藏 BV 辅助声明并添加原枚举定义。三个独立 C API SAT 查询共 14 次原断言/假设求值，全部 true。
- **假设与增量**：本轮用 A 的 `libz3.so` 和 `Z3_mk_solver_from_tactic(default)`，依次检查无假设、p、非 p、push 矛盾、pop 恢复，状态符合预期。另 CLI 增量为 SAT/UNSAT/SAT，模型 x=B。脚本和结果见 [api-independent.py](api-independent.py)、[api-independent-results.json](api-independent-results.json)。这不是全量增量/取消/多线程验证。
- **proof/core**：`tactical.cpp:1229–1254` 的两个 wrapper 在相应 goal flag 开启时返回原 goal，跳过 `dt2bv`。独立 named-core 输出 `(finite)`，proof 返回完整证明，与基线一致。它们保护了 `dt2bv` 本身不具备的完整 proof/依赖转换能力；不应删去 wrapper。
- **参数与资源**：没有添加自定义参数；`dt2bv` 本身参数处理基本为空。新预处理在非枚举任务仍会遍历表达式，在枚举任务会改变资源预算消耗和后续分类；不能承诺相同 rlimit/timeout 的 UNKNOWN 状态保持。

## 本轮独立验证与复现

在仓库根目录执行：

```sh
/usr/bin/python3 agents/branch_ablation_20261031/z3-alternative-prs/A/review/independent.py
/usr/bin/python3 agents/branch_ablation_20261031/z3-alternative-prs/A/review/api-independent.py
```

`independent.py` 包含 11 个语义/模式用例的双侧执行，以及两组纯枚举性能查询的各三次双侧执行，共 34 次进程执行。1 个用例发现上述类型回退；其余 10 个用例状态符合预期，12 次性能执行均 SAT。较早 5 个探索探针及原始结果另保存在 `probe.py`、`probe-results.json`，不与 34 次重复计数。未把作者既有 90-query/18-API 结果计作本轮独立覆盖。

本轮未复跑真实 25 个慢 dump，未验证完整 Clause，未构建 debug/ASan，未验证内存峰值。提交备选前至少需要关闭 lambda 回退；纯枚举成本则需在上游讨论中明确接受或限制范围。
