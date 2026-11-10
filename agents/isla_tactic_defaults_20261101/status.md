# 默认策略与Make Clause配置：已修改，限定验证通过

用户最终确认：直接CLI缺省default，Makefile中为每Clause写好具体策略即可，不增加缺失配置报错。实现范围：根isla/feat/float-support及其runner-float检出；memory-consistency及runner-memory检出。开始前四者均干净，现有修改仅属本任务；未commit/push/移动父gitlinks。

- float：Tactic的derive默认值移到Default，新增Qffp解析/CStr，帮助默认改default，原seed能力检查保持。README同步。
- memory：CLI原本已default、字符串支持qffp，不重复改其SMT结构，仅Make和README。
- 两条源码与两快照Make：复用ALL/FD_FLOAT/MEMORY，ALL目标先显式qfaufbv，非访存FD_FLOAT目标显式qffp；不加策略报错，不加自动探测/回退。命令行TASTIC=smt或其他合法值覆盖照常。

TDD：先添加default_and_explicit_tactics，在原源码Qffp不存在处失败（red.log）；实现后smt_init测试2/2通过（green.log），涵盖已有初始化fail-fast/线程/SMT场景以及default与qffp解析。cargo fmt及四源码diff-check通过。

Make验证：四检出各347个ALL Clause逐项make -n，实际命令均且仅含一个--tastic qffp或qfaufbv，MRET/LOAD/LOAD_FP=qfaufbv、FLEQ_S=qffp，命令行TASTIC=smt覆盖有效（make-dry-run.json）。未声称这些Clause均完成执行或该策略均最优。

运行验证：根isla使用cargo rustc编译debug isarch，仅在最终链接指定已校验Release5292580e5的lib目录/RPATH（未修改全局库/环境）。readelf确认DT_NEEDED=libz3.so.5.3。使用相同生产float IR/config、T1、显式SMT7200秒：
1. CLI不传--tastic：FLEQ_S退出0、13.72秒、gen10/status finished/errors0/timeouts0。
2. make solve-FLEQ_S：实际使用已编译新debug程序的独立执行目录，跳过重复build-isarch，Make目标本身决定qffp；退出0、15.73秒、gen10/status finished/errors0/timeouts0。命令/结果见runtime-results.json；输出各自独立，未覆盖生产output。

debug时间非受控性能对照，不与此前release4秒比较。未全77/全memory/全Clause回归。源分支及runner快照改动未提交，旧target/release程序不会因源码改动自动变化；本轮实际新程序为根isla/target/debug/isarch。正式make默认Z3_PREFIX仍按既有配置，欲消费fork default需指定新库并重新链接，不能仅改PATH。主工作区原IR/模型/父gitlink未动。
