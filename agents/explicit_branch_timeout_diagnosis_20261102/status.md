# 当前状态

首轮300秒诊断已完成，原因已区分：flags是显式异常条件带来的大量慢SMT查询累积；sat还存在旧VFUNARY0循环对7个不活动lane提前运算、连续8次overflow分叉的结构性问题。不能统一称单次查询卡两小时或统一称路径爆炸；没有Z3求解错误证据。

[详细报告](report.md)、[固定300秒查询计数与耗时](first-300s.json)、[计划](plan.md)。B带fork日志的7200秒观测继续后台运行，仅定位，不混算耗时。两种solver状态dump均解析失败，重放结果已明确判无效。只新增本目录实验工具与证据，未改生产。

追加：不活动7lane固定0、活动lane低16仍符号化的控制已自然finished，22JSON、2667check/256.686秒Z3累计、4个overflow fork，见报告及sat-B-inactive-zero/result.json。仅方向性因果证据，不是同域性能验收。
