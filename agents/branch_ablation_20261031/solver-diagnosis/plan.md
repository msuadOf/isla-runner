# 超时路径性能定位

目标：解释flags与NaN显式分支上的单次CheckSatAssuming为何超过60秒，区分SMT公式、tactic与执行器重复查询。只写本目录，不改生产和既有结果。先核对超时SMT/源码位置，再独立重放同一query、比较tactic与等价条件表达；短query探针与完整Clause验收分开。保留命令/版本/hash/资源/输出，不用改输入域后的快速结果宣称原Clause修复。
