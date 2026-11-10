# Isla接入fork Z3 A的隔离验证

目标：核实GitHub Release5292580e5的Linux共享库与当前float Isla兼容，并确认是否能启用default策略从而消费A。先只读源码与版本，使用现有isarch的隔离副本指定新共享库，保留源二进制/工作树与系统Z3；复制ELF后用patchelf替换DT_NEEDED并指定RUNPATH，只用于API加载/初始化验证，不冒充正式重新编译。

核对Release校验和/BUILD-INFO、共享库导出API、ldd -r和Isla --version；分别试qfaufbv/default初始化，若seed能力检查阻塞则明确报告，不悄悄跳过/删除随机种子。短Clause可运行则做MRET/FLEQ_S smoke并记录命令、IR/配置/二进制哈希；不把单query结果外推完整Clause。不修改生产代码/父gitlinks。
