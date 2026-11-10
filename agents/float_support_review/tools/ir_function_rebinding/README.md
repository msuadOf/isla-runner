# 实际IR函数级严格重绑合同

目标是为旧1dcc与新56cc提供可复用的**整函数结构身份**证明及Name/PC映射。输入和输出均为证据，不修改模型、运行器、旧报告或覆盖状态。

## 权限与证明边界

- 代码仅在本目录；运行证据仅在 `isla/target/float-support-review/final-coverage/integration/p1-56cc69/independent-function-rebinding/`。
- PASS只表示列定整函数在显式前提下结构相同。动态case、caller/root参数、phase、初始化约束、不可达排除和完整coverage均不自动继承。
- `zexecute` 必须按整函数核查，不裁剪未知路径。四个V4纯判断及AMO变化函数应正常拒绝，由单独语义合同接管。
- 禁止进入或读取memory-consistency工作树，保留全部已有dirty。

## 输入与现有接口

复用 `solve_scalar_coverage/runtime_binding.py` 的 `read_sidecar`，验证实际SharedState指令全集、Name表及IR/config/runtime manifest绑定。新模型另显式复验 `runtime_binding_v3.py` 的四路径来源桥；不得只读其PASS标签。

为避免从函数名模式猜局部变量，`export.rs` 直接复用冻结 Isla 的 `IrParser`、`initialize_architecture` 与公有 `install_solve_wrapper`，导出真实SharedState完整typed正文，包括Init/Monomorphize类型、Call external标志及primop元数类别。另保存原IR完整typed正文与签名/global/名义类型元数据。运行时指令逐项与已有实际sidecar核对；不解析Debug补类型，不用原IRPC代替运行时PC。

CLI输入配置JSON包含旧/新IR、实际runtime sidecar、模型source manifest与目录、runtime manifest及目录、生成记录、实际配置、新v3桥接，以及明确的函数列表。所有输入与导出器/验证器依赖重新核hash并记入输出。

## 名字与结构规则

1. 函数参数仅按签名参数位置规范化为 `param:N`；返回槽单列。局部变量必须由该函数实际Decl/Init引入，按声明顺序确定binder。每个使用点检查到达的声明及作用域；名字重复声明、参数shadow、全局shadow、未声明未知名字均拒绝或列为未覆盖，不凭名字字符串补猜。
2. 全局寄存器、let、enum成员、callee、字段、constructor和名义类型名保持各自命名空间的精确身份。形如 `z3zE数字` 的名字也必须先由真实binder证明为局部。字段与callee绝不参与局部alpha替换。
3. 保留全部指令、Decl与类型、Jump条件/target/fallthrough、Goto、调用外部标志、callee、参数顺序、读写位置、常量、异常原因及退出次序。仅去除SourceLoc和进程地址；primop用实际sidecar的完整语义别名集合与元数标识，不把未知地址当相同。
4. 第一版不重排指令、不删除无效代码、不消去Decl、不做CFG同构。整函数指令序列对应时PC映射为逐位置双射；分支target必须在该双射下相同。绑定器及所有SSA读写身份必须一致。不同布局正常FAIL。
5. 函数签名、引用到的global声明/类型、名义类型定义、调用签名和实际primop映射均精确比对。函数正文结构相同不证明callee语义相同；输出明确callee依赖清单，消费方必须逐项关闭依赖，不能把本地结构PASS当递归语义等价。

## 源码与诊断信息

源函数正文必须在两个实际冻结源中逐字相同；若所在文件有其它函数修改，则定位真实完整函数声明/正文及预处理上下文，保存旧新字节范围、正文hash和实际SourceLoc归属。无法唯一定位或跨mapping/clause的函数列为未覆盖。源码不同但IR恰同，不直接PASS，另需独立证书。

第一版**不接受任何extern alias或诊断常量豁免**：extern拼写、签名或映射改变正常拒绝；assert/internal_error中的字符串和数字逐项保持。这样不需要新引入泛化的alias或抹除规则。后续若某实际批确有必要，应增加逐调用点、逐实参、双方实际源码行、实际runtime映射及签名的独立合同，并先审查该扩展。

## 输出与消费API

输出 `report.json` 以函数名索引，给出 `PASS` / `FAIL` / `UNCOVERED`、具体拒绝原因、旧/新typed规范体SHA、参数列表、source函数正文SHA与范围、实际PC映射、Name与Decl/binder映射、引用的globals/types/callees/primops及未关闭的前提。另给全部输入/工具hash、PASS/FAIL/UNCOVERED列表及未请求函数列表。

公开Python入口为 `run.compare_function(old_snapshot, new_snapshot, function)`，snapshot必须来自同模块 `load_snapshot` 的实际来源/sidecar复验。返回纯数据，不改磁盘；CLI批量调用同一入口并写证据。低层 `rebinding.compare_typed` 只比较本地结构，不能替代公开入口。消费方按函数键读取映射，不依赖输出列表次序。输出带 `dynamic_cases_transferred=false`、`premises_transferred=false`、`coverage_transferred=false`。

首批包括 `zassert_vector_num_elem_upto_128`、`zvalid_widening_fp_conversion`、`zvalid_narrowing_fp_conversion`、`zinit_masked_source`、`zget_start_element`、`zget_sew`、`zget_lmul_pow`、`zcurrentlyEnabled`，再由各owner提供完整list。变化函数允许FAIL，不能为提高PASS数量放松身份规则。

## 验证步骤

先写负控和最小fixture，再实现规范化。负控至少修改常量、global写目标、调用payload顺序、Jump极性与target、类型、重复局部声明/参数shadow、未声明名，并验证同形假局部callee/global不能被alpha吞掉。正控只改真实参数/局部名字及SourceLoc应PASS；一切非绑定名字改变均应FAIL。

随后在真实1dcc/56cc运行首批未改函数与必拒V4/AMO/zexecute样例，保存决定性输入hash、确定性映射与完整失败原因。报告显式区分局部函数结构通过与尚未关闭的callee/root/phase/config前提。

架构已批准此边界并完成首版实现。词法源正文边界按真实括号深度和顶层token确定，内层let与预处理指令不得截断函数。源码身份比较包含同名函数的全部声明（含inactive正文），不会静默忽略缺少SourceLoc命中的声明；至少一个实际SourceLoc锚定函数归属。这个规则有意比只比较active代码保守。

## 复跑与最小消费

实际批配置位于上述证据目录的 `input.json`。从仓库根目录运行：

```sh
python3 -B -m unittest discover -s agents/float_support_review/tools/ir_function_rebinding -p test_rebinding.py -v
python3 -B agents/float_support_review/tools/ir_function_rebinding/run.py \
  --input isla/target/float-support-review/final-coverage/integration/p1-56cc69/independent-function-rebinding/input.json \
  --output isla/target/float-support-review/final-coverage/integration/p1-56cc69/independent-function-rebinding
```

首次构建使用 `build.py --input INPUT --output BUILD_DIR --z3-library Z3_LIB_DIR`；可加 `--lock` 指定已有Cargo.lock以冻结依赖。`run.py --reuse-exports` 只复用同源码/二进制hash的typed导出，仍重验全部快照、来源桥和sidecar。改变函数清单需重新导出。

```python
import json
from pathlib import Path

report = json.loads(Path("isla/target/float-support-review/final-coverage/integration/p1-56cc69/independent-function-rebinding/report.json").read_text())
entry = report["functions"]["zget_sew"]
assert entry["status"] == "PASS"
pc_map = dict(entry["local_structure"]["pc_map"])
name_map = entry["local_structure"]["name_map"]
# 仅使用身份映射；callee闭包与具体caller/phase/config前提仍另验。
assert entry["semantics_status"] == "NOT_PROVED"
```

报告对 `init_masked_source` 的源行号诊断literal差异保留FAIL，即使运行时typed正文相同。V4四函数变化按FAIL处理；缺旧AMO函数或无法关闭全部声明/命名空间的整 `zexecute` 列UNCOVERED。以上都是预期拒绝，不能用新旧PASS数量代替语义验收。
