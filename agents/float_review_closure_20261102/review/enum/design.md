# 枚举重放独立设计审查

本审查只读生产源码，由独立 reviewer 完成；审查基点 Isla `cf1aa1431d5f2d05584c78c0e7c84862a9a9b1fa`。实施与测试最终结果另记，不以设计意见代替验收。

## 当前判断

同一 Context 重放枚举会重复声明 Z3 枚举类型，是 Isla 可以修复的实现缺口。把原三项枚举重放测试改成新 Context，能够验证目前主要生产调用方式，但不能据此认定原测试无效。`Solver::from_checkpoint` 未声明只能接收新 Context，现有 `tracetool/tests.rs::ftrace_projects_existing_events_in_execution_order_across_forks` 也直接在同 Context 重放。禁止同 Context 是新的 API 限制，需要单独理由，不能从 Z3 底层限制直接推出。

官方 Z3 `1fd1d3613` 的 `src/api/api_datatype.cpp:107` 明确检查 `is_declared(sname)`，同 Context 重复调用 `Z3_mk_enumeration_sort` 返回 `Z3_INVALID_ARG`。枚举类型属于 Context，而现实现的 `Enums` 缓存属于 Solver；新 Solver 忘记 Context 已声明的类型，因此重复调用。新建类型名称会改变 `Model::get_ast_with_timeout` 按整数 sort 名映射回 `EnumId` 的约定，也没有必要。

## 最小正规方向

在 Context 保存枚举原始 sort、构造器和识别器，Solver 按同 `EnumId` 和相同成员数量复用；同名不同成员数量直接终止。缓存须持有 Z3 引用直至 Context 销毁，不能仅保存弱引用，因为全部 Solver 销毁后，Z3 的同名声明限制依然存在。Context 销毁顺序须保证先释放缓存引用，后 `Z3_del_context`。

重放仍须消费 `DefineEnum` 原有的 fresh 编号，保持变量编号和 checkpoint 的 `next_var` 一致。普通整数命名与 SMT-LIB2 dump 命名的缓存身份须一致，或以当前 dump 独立创建 Context 的实际不变量说明边界；不能将字符串命名类型冒充整数命名类型。不同枚举的构造器即使具有同名符号，仍须按实际 sort 保持类型身份；模型回读不能仅比较成员名称。

## 已核对调用者

- `executor.rs` 三个生产重放入口在创建新 Context 后调用 `from_checkpoint`。
- `src/isarch/exec.rs` 在每个编码候选中创建新 Context；`src/isarch/encoding.rs` 的辅助域回接完整执行域也创建新 Context。
- `src/isarch/args_yaml.rs::sym_solve_str` 和 `src/footprint.rs` 两处调用各自创建新 Context。
- 现有同 Context 的三项枚举重放测试保留了来源 Solver；另有上述不含枚举的 trace 分叉测试。

因此目前没有证据表明正式 Clause 被该问题阻断；本修复恢复的是 API 在同 Context 的一致行为，不声称改变浮点 Clause 性能。

## 最终审查义务

保留原失败断言，核对同/异 Context、多次重放、来源 Solver 已销毁、全部 Solver 已销毁后再次声明、单/多成员、多枚举及同名成员、冲突拒绝、类型身份、模型回读和声明一致性。辅助域和完整域重放须保留现有检查。实际测试库必须为 SHA256 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`，不能以系统 `libz3.so.4` 结果代替。
