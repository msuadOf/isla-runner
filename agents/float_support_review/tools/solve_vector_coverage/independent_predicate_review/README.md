# 31 个向量 predicate/body 候选的独立审定

2026-09-27，限定 `1dcc8081…` 冻结 IR、`aa069e7f…` actual SharedState 与原 31 个候选。没有改生产源码、IR、输入域或全局分母。工具为 [review.py](review.py)，冻结摘要为 [evidence.json](evidence.json)。全量证书在 `isla/target/float-support-review/final-coverage/vector/independent-predicate-review/report.json`。

## 结果

| 项目 | 结果及边界 |
| --- | --- |
| 静态谓词、极性和 body 对应 | **31/31 PASS**：22 illegal guard、2 VL0、1 overlap alignment、1 extra-ops dispatch、5 mask |
| 有区分力负控 | **11/11 拒绝**：错误 if/短路极性、错误 callee/参数、删除 CFG 分支、错误 return、VL0/mask 常量，以及错误 caller/config/context |
| default-FD 直接 execute site | **27 项各有双向真实终态见证**，另 2 项见下述真实译码不可达证明 |
| shared `valid_reg_overlap:68` | default-FD **9 个精确 caller context 各有双向见证**；另三种分派配置每种 9 个 context 只观察到 false |
| shared `init_masked_source:44` | 8 个已观察 caller/config scope；FD、VPR、FPR 各 2 个 context 仅 true，lanes 2 个 context 仅 false。固定配置排除义务由向量 owner 的 `default-fixed-cfg.json` 管理 |
| 全局源码分支闭合 | **仍为 false**；未把本审定扩大为全体 caller、所有配置或数值语义的证明 |

动态前沿绑定 6 种配置、3105 个输入、9045 个终态，逐一复核其所引 7 份 audit 的 SHA。`default-lanes` 与 `default-fpr` 各有 3 个直接 site 双向命中；`default-vpr` 尚无双向直接 site。关闭 F/D 的配置没有本组 execute 见证，不能跨配置借用 default-FD 命中。

## 静态规则

- constructor 参数按实际 `Kind`、`Unwrap`、tuple 字段顺序绑定；getter 的 callee/参数及派生 SEW/LMUL 运算另核实际 AST，并检查变量未被重定义。
- 以源码条件生成有限布尔原子表，对 actual CFG 的**全部原子组合和内部指令**核对。源码 token span 仅用于定位；callee、参数身份、整数转换、比较常量、短路写回及 true/false 后继必须一致。
- 26 个提前返回或配置分派 site 逐指令检查 true 路径的实际返回值及 `End`，false 必须是 unit 加绕过 then 的 `Goto`。编译器生成的 return 赋值不依赖其虚拟 SourceLoc。
- 5 个 mask site 验证同一个 tuple 的 `mask` 字段、循环 induction variable 或 index0、`vector_access`、一位常量1及 equality 极性。对 then 内全部 CFG 边分类，允许已识别的外置 assertion handler 和提前返回；证明 then 入口与 false 绕过关系，不声称 then 的浮点数值运算均已证明。
- overlap 的寄存器编号来自 `unsigned(vregidx_bits)`，范围0..31；group 为正幂或1。因此余数0..31，相关数学整数到 i64 转换精确。SEW/LMUL 的派生量亦在 i64 范围内，不无条件消去截断。

## 两个 mask 的真实译码不可达性

`VFWUNARY0:938 / zexecute:27188` 由 `SEW==8` 与五个 FP→int/FP→FP 枚举的外层 true edge 支配；`VFNUNARY0:1251 / zexecute:28180` 由 `SEW==8` 与四个 int→FP/FP→FP 枚举的外层 true edge 支配。工具验证外层实际布尔 CFG，再删除该 true edge，确认从 clause 入口不再能到达 mask site。

实际 `valid_widening_fp_conversion` 与 `valid_narrowing_fp_conversion` 分别穷举 **5×32=160**、**4×32=128** 个“枚举×扩展开关”组合。将 `get_sew()` 固定为外层必需的8，其所有正常返回均为 false；扩展开关独立枚举覆盖了相关性的超集。实际 `zencdec_backwards` 的 guard 参数与 constructor 枚举字段相同，false 走 `None`，不能产生这两个 constructor。

到外层检查的 execute 前缀及 `get_sew/currentlyEnabled` 的传递闭包各审查88个名字，确认无 `vtype` 写入或未审写引用；记录全部 primop 别名、构造器、只读寄存器 builtin 与配置常量 reset，绑定冻结 `executor.rs`、`primop.rs` SHA。配置常量 reset 仅接收不可变 memory，最终赋给已核目的地。`isla_read_vreg/isla_init_mask` 的 frame 参数不参与实现。

**适用入口：成功真实译码与执行使用相同 vtype、期间没有外部状态改写，且译码没有异常。** 直接构造 constructor 执行不适用；这两个 site 保持零动态命中，静态不可达不折算成动态命中。

## 动态消费契约

每个 `certificates[]` 只登记一次 `global_site_key`，并分列：

- `predicate_proof`、`body_proof`：静态对应证明；
- `caller_unreachability`：仅上述两个 site 的带前提不可达证明；
- `dynamic_caller_configuration_obligations[]`：精确 configuration、clause、phase、context、双方向代表；代表保留 input/terminal case ID、trace block、path signature、terminal ordinal 和 audit；
- `both_directions_dynamically_witnessed`：只对该具体 scope 生效。

共享 helper 的列表仅是**已观察 caller**。没有出现在前沿的 caller/config 仍需与独立 typed-call 闭包合并，不能把有限列表当完整分母。源码分支、异常数值、全模型 decoder 和官方 solve 的其余义务仍由各自证据负责。

## 复跑

将 `IR_STAGE` 指向冻结目录 `isla-float-solve-fix-final-20260926.GThshy`，`CATALOG_STAGE` 指向 `isla-directed-final-coverage-20260926/vector`，`SIDECAR_STAGE` 指向 `isla-directed-final-runtime-catalog-20260926`。输出目录为仓库内独占产物目录：

```sh
REVIEW_STAGE=isla/target/float-support-review/final-coverage/vector/independent-predicate-review
python3 agents/float_support_review/tools/solve_vector_coverage/independent_predicate_review/review.py \
  --sidecar "$SIDECAR_STAGE/official-fd.jsonl" \
  --catalog "$CATALOG_STAGE/source-branch-catalog.json" \
  --candidates "$CATALOG_STAGE/lowering-candidates-minimal12.json" \
  --model-root "$IR_STAGE/model" \
  --frontier isla/target/float-support-review/final-coverage/vector/full-source-frontier.json \
  --output "$REVIEW_STAGE/report.json"
```

冻结执行 exit0，输出 `sites=31, proven=31, negative_controls_rejected=11, real_decode_unreachable=2`。早期开发报告留在原临时目录，最终仅以 `evidence.json` 所指报告 SHA 为准。
