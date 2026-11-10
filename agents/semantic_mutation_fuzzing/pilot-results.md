# E1 首轮生成侧 pilot 结果

2026-10-22。已运行两个目标、两种模式、各三次，共 12 次命令；全部正常退出 0，合计输出 168 条记录，整批约 34.76 秒。此结论限生成侧，不是模型全路径、DUT、RTL 覆盖或检错 PASS。

## 配置与证据

- 源码工作树：`isla/.worktrees/witness-pure`，HEAD `2fefa7274d6e84bef46e5c25b1a06b662d69aa29`，运行前后干净。
- 二进制 SHA-256：`0baf7eb09c3e1ae7bc39c781568cb237bfac4b1a6355696460878ddedc5a087c`。
- 自带 IR SHA-256：`6fc39efd0f72b0ee8eae247d9965e680b6874f9954334c20d748b42c0987792c`。
- FD 配置 SHA-256：`01229f5ff91a54ed632739d422d6fffa83f3dc87165b55d13b65c5c3d89c5bfb`。
- 使用既有二进制，没有重编，不新增源码与二进制精确对应证明；不能外推当前内存／浮点集成版本。
- 单 worker、`qfaufbv`、内部 45 秒、单 SMT operation 10 秒、外部 60 秒；每目标三对 off/on，on seed 为 1234、4321、20261022。第二对调换执行顺序，整批顺序执行。
- [命令、退出、耗时及逐输出哈希](evidence/e1-20261022/manifest.json)、[共同字段汇总](evidence/e1-20261022/analysis.json)、[执行脚本哈希及初次错误记录](evidence/e1-20261022/execution-source.json)。原始 JSON 和日志与 manifest 中的相对目录对应。

## 观察结果

以下并集均来自每组的三次运行；取值来源为输出 `isa-state`，不是随机化尝试元数据。

| 观测 | VFMVFS 关闭 → 开启 | VSETIVLI 关闭 → 开启 |
| --- | --- | --- |
| 每次记录数 | 16 → 16 | 12 → 12 |
| 每次 verdict | 13 Illegal＋3 Retire，全部六次一致 | 12 Retire，全部六次一致 |
| 每次不同 vl 数 | 4／5／4 → 8／6／5 | 1／1／1 → 4／3／3 |
| 不同 vl 并集 | 5 → 13 | 1 → 8 |
| 仅 Retire 的 vl 并集 | 1 → 5 | 1 → 8 |
| 不同 vstart 并集 | 1 → 12 | 1 → 16 |
| 命令中位耗时 | 3.971 → 4.373 秒（约 +10.11%） | 1.567 → 1.668 秒（约 +6.43%） |

在这两组小负载上，随机化确实增加记录上下文的取值多样性，并有小幅端到端耗时增加。但没有测得新语义分支、RTL 行为或 bug 检出变化，不能据此认定 fuzzing 有效性提升。

## 测量限制与下一步

1. 该早期版本 off 输出的初态只含五类上下文键；on 的部分条目还输出 GPR/FPR/VPR 和 mstatus。因此整份 JSON 的去重数、文件体积和寄存器字段数不能直接作为组间多样性指标。分析器只按共同字段比较；缺失字段是未观测，不当作零。
2. VSETIVLI 会覆盖旧 vl；旧 vl 变多不证明指令输出或硬件活动变多。后续 E1 应以指令实际消费的输入切片、目标条件保持率和实际 DUT 行为作主指标。
3. 每组仅三次，未做统计显著性推断。耗时含启动、IR 加载、求解与额外字段导出，不是纯求解器开销。
4. 日志包含旧配置未知 `__isla_always_aligned` 和未注册 primop 警告。命令退出和非空 JSON 不消除这些兼容性限制，也不证明覆盖所有语义。
5. 本轮没有 E0 负对照或 DUT 重放，没有证明旧 witness 可以独立恢复完整状态。不能用 NEMU／硬件复位状态补齐缺失输入后仍称同一完整 witness。
6. 第一次分析误以为旧 JSON 必含源向量寄存器，遇到缺失字段退出；已修正为显式未观测并用新目录重跑全部 12 次。原始失败目录 `.tmp/semantic-mutation-pilot-20261022` 保留，未计入上表。

复算已保存结果：

```sh
python agents/semantic_mutation_fuzzing/analyze_pilot.py \
  agents/semantic_mutation_fuzzing/evidence/e1-20261022
```

重新执行使用新的、尚不存在的输出目录：

```sh
python agents/semantic_mutation_fuzzing/pilot.py \
  --output .tmp/semantic-mutation-pilot-new
```

下一步按 [实验矩阵](experiments.md) 先选定可完整重放的向量访存种子和 E0 观测范围，再开发 E2/E3 共同变异器；不得把本 pilot 当作普通变异或约束修复实验。
