# A/B 相同workload交叉五重复

目标：比较发布版本A953e433与Bae64857，使用冻结二进制A-revised/z3、B/z3，核对manifest SHA256。同一workload的输入字节完全一致，调用check-sat-using default。六项历史输入（NaN、flags、最小例及6/512/1024构造器×256枚举变量）及两项超过60秒的真实flags-dump-7/11，共八项。

每项顺序AB/BA/AB/BA/AB，即每版本各五次，无额外预热/不计旧数据。每项固定同一CPU，八项选择不同物理核并行；不在A/B间更换亲和性。启动前采样CPU及SMT同胞空闲程度；机器共享，无法宣称独占CPU。记录拓扑、负载、开始结束时间、墙钟/user/sys/RSS、stdout/stderr/返回码及输入和二进制SHA256。每次新进程，保持默认随机参数和线程参数一致。

显式Z3限时7200000ms，进程外限7210秒；超时/UNKNOWN不按成功耗时计入加速比。只测独立SMT查询，不是完整Clause。CPU选择只依据启动前采样，不在运行中调整。对每workload汇报五次原始墙钟、中位/均值/范围及配对B/A；检查两臂均SAT才比较。

脚本run.py写各次日志与JSON，summary.json/report.md随每次结束原子更新。源码/生产组件/PR不修改。未获本轮更新外部评论指令，先交付本地实验结果。
