# default/smt 策略追加比较（2026-11-01）

在与此前相同的两个完整超时dump上，分别用default/smt/qfaufbv/qffp，每组3次独立命令并行、单CPU、探针限时60秒。只有check-sat-using后的策略不同，未删约束或固定输入。时间只对本轮样本有效，不混算前轮不同并发/初始状态；这仍是单查询probe而非Clause验收。

| 查询 | 策略 | 墙钟中位秒 | 三次输出 |
| --- | --- | ---: | --- |
| nan | default | 28.033 | sat, sat, sat |
| nan | smt | 45.849 | sat, sat, sat |
| nan | qfaufbv | 41.444 | sat, sat, sat |
| nan | qffp | 0.210 | sat, sat, sat |
| flags | default | 60.363 | unknown, unknown, unknown |
| flags | smt | 60.369 | unknown, unknown, unknown |
| flags | qfaufbv | 60.367 | unknown, unknown, unknown |
| flags | qffp | 5.116 | sat, sat, sat |

flags上default与smt均三次60秒unknown，并不解决慢查询；NaN上default较当前qfaufbv略快，但远慢于qffp。不能据此建议全局改成default或smt。优先测试浮点预处理后接现有策略的通用组合（前轮该组合flags13.92秒SAT、NaN0.208秒SAT），保留模型显式分支；还需完整Clause和数组/枚举/模型求值验证。

另做当前isarch的default初始化探针：`--tastic default` 在Z3 4.16.0.0下实际panic于smt.rs随机种子能力校验，原因是该tactic未暴露seed/random_seed。stderr在default-initialization/stderr.log。这是当前接入能力限制，不是数学求解失败；不能把配置字符串直接切到default。没有修改生产代码或源分支。
