# 枚举重放独立审查结论

**限定签收：实现方向与本次枚举/API 回归通过，未发现阻断问题。** 同 Context 重放原测试应保留；问题属于 Isla 在 Solver 层缓存了 Context 层类型声明的实现缺口。修复没有删除失败测试、放宽模型断言、任意改名或增加后备行为。

## 审查版本与结果

基点 Isla `cf1aa1431d5f2d05584c78c0e7c84862a9a9b1fa` 加本轮 `isla-lib/src/smt.rs` 未提交修改；最终受审文件 SHA256 `aa3cb973102299707fc2d87c94369136daed8b88944e47b48ff3ee9e9ec1f9cc`。审查者不参与生产实现，只写本目录。

独立直接运行实施者独立 target 中的 Release 测试程序，SHA256 `1ebb556f1c09b669f83701c23afec98b6ad6dee746e47fded6010d5bf7422209`。`smt::` 过滤器 **29/29 通过**，包括旧单/多成员和结构体枚举重放、新生命周期与冲突测试、辅助 checkpoint/完整 checkpoint 回接，以及三项 SMT-LIB2 dump 测试。命令统一固定一个 CPU、`--test-threads=1`，测试共 0.45 秒；未重复编译或覆盖生产 binary。原拟 CPU53 出现竞争，改用抽样负载较低的 CPU37；该结果只判功能，不作为性能数据。

独立检查 `ldd`、`readelf`，并以 `LD_DEBUG=libs` 实际运行多成员重放测试，确认装入官方 `libz3.so.5.3`，真实库 SHA256 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。详见[机器记录](green-independent.json)、[单测原始输出](smt-independent.log)、[实际装载日志](runtime-loader.log)。

修前同一官方库下旧三项枚举重放均独立复现退出 1、`enumeration sort name is already declared`，见[基线记录](baseline-independent.json)。C API 探针进一步证实：全部引用释放后同 Context 仍不能重新声明同名类型；不同类型可使用相同构造器符号，类型身份仍不同；新 Context 可声明同名类型。见[探针](api_probe.py)和[结果](api-probe-result.json)。

## 代码核对

- Context 按实际 Z3 sort 符号的整数/字符串值缓存枚举，避免仅按成员名或错误地混合整数、字符串命名。Solver 与 Context 各持一份 Z3 引用；缓存命中克隆指针列表后增加引用，Solver 销毁仅释放自己引用。Context 销毁先排空缓存释放引用，再调用 `Z3_del_context`，没有悬空引用或引用循环。
- 同 Context 相同类型复用原 sort、构造器、识别器；旧单/多成员测试额外核对 `Z3_is_eq_sort`。不同枚举即使成员符号相同也保持不同 sort，新测试分别具体化回正确 `EnumId`/成员。
- `get_enum` 本地命中时只核对成员数量，不增加 trace；首次定义经 `DefineEnum` 消费原有 fresh 编号，Context 缓存命中也不跳过该过程。`from_checkpoint` 的最终 `next_var` 恢复未改，辅助域与完整域的声明、定义和后缀回接逻辑未改。
- `get_enum` 与直接 `DefineEnum` 两条入口均拒绝同名不同成员数量；跨 Solver 经 Context 缓存同样拒绝；空枚举硬失败。没有静默换类型或选择任意值。
- 新生命周期测试先销毁来源 Solver，再连续三次在同 Context 重放且销毁全部临时 Solver，最后在新 Context 重放；单/多成员约束和模型回读均通过。已有结构体模型回读原断言保留。
- SMT-LIB2 dump 的整数/字符串命名使用现有独立 Context，三项 dump 单测通过。模型回读仍以模型值自身 sort 的识别器辨认成员，再按整数 sort 名映射 `EnumId`，映射约定未改。

## 边界与未决项

本签收针对上述文件哈希和测试程序，不替代后续正式 `make solve`、模型 IR 同步、完整 Clause 预算或全仓验收；由主 agent 集成阶段完成。当前默认 feature 构建不含 `tracetool` 单测，一次该过滤器运行零项，已在机器记录标为未执行，未计入通过数。未运行引用泄漏检测工具；引用平衡由静态逐分支核对及多次销毁/重放测试支持。对本次枚举修复没有发现需要保留的阻断项。
