# 原生环境选择附层

## 目标与边界

本步骤续接已授权的完整源码闭合工作，验证实际 typed 环境中的声明选择及模块可见性。已有 `has_val_spec`／`is_mapping` 分类只测试全局名字存在；本附层不能沿用该分类直接签可见性。

冻结 `attempt-006`、原生类型工具、各族图及已审来源合同均保留。新工具和测试使用 `native_env_resolution*` 文件名；证据写入 `source-ast-full/environment-resolution-preparation-v1/`。不修改模型、编译器或旧 exporter。审查队列由架构 owner 协调。

## 实际接口与热点

- 冻结 Sail `type_env.ml` 的 `item_in_scope`、`get_val_spec_opt`、`get_val_spec_orig`、`get_union_id` 与 `lookup_id`。
- 复用冻结 `support.ml`、`serializers.ml` 和 target 能力。新 metadata 包装 `E_app`／`P_app`／`MP_app`／`LE_app` 及变量读取，只在真实节点环境上查询。
- 底层 `Type_env.get_val_spec_opt` 返回声明位置并执行可见性检查，但 `Type_check.Env` 公开接口没有导出它，首轮构建已失败并保留。第二轮明确改用公开 `get_val_specs` 的实际 scope 过滤集合、`get_val_spec` 和 `get_val_spec_orig`，同时保存可见 map key 的位置及原始／freshened 类型；map key 位置不是直接读取 `item.loc`，二者关系须另核所有写入及 OCaml map 规则。
- `lookup_id` 对全局 let 和局部变量都返回 `Local`。本附层保留这个限制，不仅凭名字或该分类签唯一局部 binder。

## 步骤

1. 先用测试约束新增 metadata 的提取和剥离、旧树逐节点守恒、路径、失败状态和权限边界。
2. 新插件只附加实际环境查询结果。已知类型错误记录为明确失败；意外错误停止，不回退到按名字配对。
3. 按旧完整 argv、宏域、source/config/compiler 与 `skip_initial=true` 导出两个后端。复制 memo 并使用新输出路径，不运行待测模型指令。
4. 剥离新增字段后与旧 AST 完整字段比较，再按实际结构路径输出附层；显式列出查询失败、缺签名、不能唯一联声明的项。
5. 对成功项核声明位置、原生类型与实际 `DEF_val` 或构造子声明，保存 compiler API 规则与完整依赖。类型相等、位置相等分别列出；多候选不授唯一选择许可。
6. 冻结后交独审，公共严格消费者及三族精确应用另立版本。

## 验证与许可

真实编译执行、每域完整 AST 对照、带 shadow／private／同名声明的负控、全部输入 hash 重核和独立复审分别记录。只验证所查环境中的声明选择；callee 语义、caller 可达、extern 效果、未覆盖类型引用与完整分母仍 OPEN。`source_branch_closed=false`、`denominator_complete=false`，动态观察与静态排除增量为 0。历史 live457 的三项漂移 FAIL 原样保留。

## 未决问题

- 实际环境可能经 compiler 的 `open_all` 重写；本证只描述该 hook 上的实际选择，不能还原更早阶段可见性。
- 初始重写可能改变 module metadata；本步骤使用 `skip_initial=true` 的准确旧阶段，不能将其选择直接当作后端 post-initial 阶段的环境。
- 生成声明的未知／共享位置、重复 val 与原始／规范化类型关系须单列，不用近似匹配吞掉。
- 局部 shadow 的唯一 binder 身份及 outcome/undefined 等生成规则继续保持专门义务。
