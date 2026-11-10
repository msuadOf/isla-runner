# std-gaps 合入状态

2026-11-09：独立候选已合并并完成限定实测；原仓库引用导入及源分支删除待沙箱外执行。

模型合并提交 `cbb4766f` 的双亲为旧 isarch `34903a1e` 与 std-gaps `7d7e76f3`；完整保留x0与Svnapot/Svpbmt历史，额外纳入4份V源码及24份配置。7项VVTYPE预算1→0沿用源提交。

实测结果：普通/SYMBOLIC严格类型检查均exit0；当前v128 IR及别名严格重生exit0；path merge 6/6、executor396通过/5忽略、Python153通过/210子测试、向量22项定向、原生fuzz20/20认证与20次变异/判定，均exit0。79份workaround、130个region与22处注释锚点校验通过。

向量定向覆盖segment组界（含分数EMUL）、普通/indexed load/store合法性、vstart边界，以及全寄存器LOAD/STORE早退清零且不访问内存。初版探针存在初值类型与结果格式解析错误，修正探针后22项通过；中间日志保留，未记作模型PASS。

限定：原生探索采用60秒路径预算，存在excluded memory修剪与局部超时，不声明全路径覆盖；未执行硬件测试或其他IR配置回归，其他IR保留历史来源。本轮7项预算只核对继承与区域，不声明向量全覆盖或性能提升。

原工作区与备份保留。候选提交、bundle、精确命令与日志位于 `.worktree/isarch-std-gaps-merge-20261109/`；实际原仓库导入状态见其中 `finalize-result.json`。

[方案](plan.md)、[验证摘要](verification/summary.json)、[向量探针](run_vector_probes.py)、[原生认证](verification/reconfirm.json)。
交付候选：模型cbb4766f、Isla79d0e335、runner fb9916b9。三个bundle和收尾脚本已生成；真实预检通过，隔离三仓实际快进/删除及脏源工作树保全通过。原仓实际--apply因.git只读在写入前停止；终核原分支、HEAD、索引、未提交代码及worktree注册不变。详见[交付说明](../../.worktree/isarch-std-gaps-merge-20261109/README.md)。


2026-11-09外部执行后回读：finalize-result.json为complete；三仓实际isarch已分别为cbb4766f/79d0e335/fb9916b9，模型本地feat/sail-std-gaps已删除。上述“原仓待导入”是本环境交付时状态，不代表当前引用。后续origin删除单列于[远端清理议题](../origin_branch_cleanup_20261109/status.md)。
