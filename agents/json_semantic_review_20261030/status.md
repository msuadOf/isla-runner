# JSON语义独立复审状态

2026-10-30完成只读独立审阅：float bb9d271（Isla b0138b7/模型18389a89），memory1731207（Isla47ac90c/模型1fa93117）。两套都具备有用专项支持，尚不能按“JSON覆盖所固定源码控制流语义”验收。

确证问题：memory运行IR未含寄存器组越界/vstart非陷阱两项源码修复，两个新负例分别成功退休越界寄存器组／错误Illegal；float FLI文本仍旧索引形式，GNU接受6/32但6条全错码，LLVM拒绝；两分支MRET采样4→1、退出均0且JSON不声明partial。另静态确认memory终值查询超时空壳保留而不序列化不完整标记；SC默认具体reservation只含成功路径，测试副本符号化后恢复成功/失败两条。

正面限定验证：float五IR helper1615、state180、guard20通过；memory数组30测试通过，ld/sd/c.ld/AMO定向事件与前后内存自洽。FVFTYPE45秒探针外限124无JSON，未全77/硬件/整体覆盖验收。生产源码、分支、gitlink均未修改，根/子模块工作树干净。

[详细问题/代码位置/建议](report.md)、[计划](plan.md)、[精确版本](versions.json)、[18项新探针命令/hash/结果](all-probe-summary.json)。所有PASS仅指列定命令与输入，不推广到所有模型路径。
