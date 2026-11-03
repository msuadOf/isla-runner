# 组合模型验收

本轮不修改生产源码或IR，不提交；只验证已经独立审阅并提交的组合模型。监督进程等待 `../implementation/generation/rv64d_v128_e64/generation.json` 自然生成、退出0且产物hash一致后，才复制输入并运行。

- 程序冻结自 Isla `09678a737743d87057df8138fb321658a52aee20` 的 Release，包含本轮汇编表示和ExecuteAs修复；二进制hash和官方Z3版本见 `launch.json`。
- 七个完整Clause，每Clause一次；qffp、T1、外限7200秒、SMT7200秒，不设更短path限时。固定实验seed17拦截器与上一轮相同。
- 六worker使用CPU98、100、116、120、121、73，各为不同物理核；启动准备时 `/proc/stat` 一秒采样忙率依次0%、1%、1%、1%、1%、3%。同时排除仍运行单变量实验的40–51逻辑核及其所有SMT sibling；共享机器非独占。
- minmax/minm/maxm用原FD配置；NaN、mask、reduction、class用此前消融配置的字节相同副本。初态中vtype/vl/vstart约束等见 `inputs/*.toml`，结果统计实际见证值。
- 只有退出0、JSON summary=finished、无errors/SMT超时/执行超时/截断/未完成且seed拦截成功，才记单Clause PASS。
- JSON数不是fork数；见证类别与flags转移分别记录。旧A/单项B是三种seed的并集，组合模型单次缺少旧类别只能说明未见证，需定向检查，不能直接认定语义回归；旧程序与当前修复不同，亦不能作净性能归因。

入口为 `report.md`、`summary.json`；逐Clause命令/日志/JSON路径/hash/初态/有效NaN-boxing后操作数分类/flags转移/历史类别对照均在 `runs/<name>/`。监督进程每30秒增量写状态，全部结束自动写最终状态；超时保留partial而不冒充完成。
