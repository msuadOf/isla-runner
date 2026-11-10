# 29 个 foreach 的独立复核

承接已批准的最终覆盖议题。本目录和 `isla/target/float-support-review/final-coverage/vector/independent-loop-review/` 为独占输出；生产源码、原 loop producer 与共享报告只读。

输入为固定 `loop-structure-and-witnesses.json`（SHA256 `c69ae41e2b19c3a7fd002c6c824f7f4f71daa3c97492063513fe982728abcb21`）。先按实际 sidecar 重核 29 个 header、初始化、步长、唯一支配定义、回边、跨区入口和写集；再独立按每次调用的有序 header 片段复核 407 个 witness。所有配置、源 site、clause、phase、root context 和 runtime PC 保留。

长度证明分别处理 execute 的实际长度 SSA、helper 的实际形参与支配断言、write helper 的 group_size 和 elem_per_reg。检查 int→i64 窄化、最后索引及增量范围。VL0 不作为 foreach 零次证据。两个未观测转换循环只在成功真实 decode 的 outer 条件证书和实际 CFG 均绑定后才能排除。

验证需保存完整命令、受测版本、证书与工具哈希；长度或配置不能闭合时明确保留 pending。

## 最终复验

追加已执行的 default-lanes `01-legal-lmul` 组后，固定 v2 输入 SHA256 为 `57689d641ef515de985916b578352070d9023cea9eb075296f12a57ceb237683`。原 29 个结构没有变化，新增 9 条继续见证。最终独审 39.668 秒，exit 0，stderr 空：

- 29 个结构及源 token、29 个正长度域、int→i64 转换与最终索引增量安全均通过。
- 416 条实际时序见证逐项复核：139 enter、138 continue、139 exit；两份配置分别绑定。
- 99 个已观察 helper context 的实际 root、逐层 Call 和形参重新绑定。仅 VFMVSF 的 `zexecute:31547 > zwrite_vreg:1`、PC114 循环长度恒为 1，排除该 context 的 continue。
- 5 个结构/算术/断言负控通过。另对两个 outer false 的静态排除核 actual CFG；改为 true 后均能到达 header。两个整循环排除只按默认 FD 证书范围消费。

execute 循环长度为 `get_num_elem` 的实际结果：22 个长度域包含于 2..128；VFMVSF 初值 1、长度 2..16。四个 helper 的实际 num_elem 断言正常返回域为 `{1,2,4,8,16,32,64,128}`；write helper 两层长度分别为 `{1,2,4,8}` 与 `{2,4,8,16}`。这些都是到达循环时的条件域，不代表完整指令已可达。

证据目录中 `certificate.json` SHA256 为 `9fee8e68312bbe784bf68b5874723f423c3f781af89511ffcad267fab2caa183`；`run-pass.json` 保存完整命令，`review.json` 保存摘要。原 407 条见证的结果保留为 `certificate-v1.json` 和 `run-v1-pass.json`。

共享 `runtime_binding.py` 在本轮新增源码重封接口。工具严格核旧完整源 ac44e5 和新源 4a0dcd，逐个比较除 `verify_source_snapshot` 外的原函数 AST；本次使用的 `read_sidecar`、`normalize_instruction` 和 `verify_runtime_catalog` 均不变。模块层只新增 importlib 与已有 trace 模块的异常别名。这个依赖桥显式写入证书；本 1dcc 审计不调用新增重封接口，旧 P2 证书保持冻结。

```sh
python3 agents/float_support_review/tools/solve_vector_coverage/independent_loop_review/review.py \
  --freeze "$FREEZE" \
  --input isla/target/float-support-review/final-coverage/vector/loop-structure-and-witnesses-v2.json \
  --domain isla/target/float-support-review/final-coverage/vector/independent-domain-review/certificate.json \
  --fixed isla/target/float-support-review/final-coverage/vector/default-fixed-cfg.json \
  --outer isla/target/float-support-review/final-coverage/vector/independent-predicate-review/report.json \
  --output isla/target/float-support-review/final-coverage/vector/independent-loop-review/certificate.json
```

`FREEZE` 指向冻结 1dcc 模型/runtime 目录；完整路径及哈希见运行记录。该工具不执行 solve、不改变 owner 分母或共享状态表。
