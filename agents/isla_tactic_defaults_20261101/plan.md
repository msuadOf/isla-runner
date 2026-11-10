# Isla命令行默认策略与Make Clause策略

用户要求：直接Isla不传--tastic使用default；Makefile写明各Clause的非default具体策略，不额外加缺配置报错。命令行TASTIC覆盖继续允许。

实际源码入口：根isla/feat/float-support80231ce（干净），内存isla/.worktrees/memory-consistency/bdd047b（干净）。float为类型化Tactic，仅default/qfaufbv/smt，需把derive默认改到Default，并加入Qffp解析/CStr与帮助；memory已缺省default且支持任意字符串，无须改其CLI。两分支Make的ALL/FD_FLOAT/MEMORY分组已有，复用组名写target-specific TASTIC：非访存浮点qffp，其余qfaufbv，无新验证层/错误/策略回退。保留solve目标/参数入口/预算和原结构。

按TDD先加float纯策略默认/解析测试并观察失败，然后改源码；Make按全部ALL目标dry-run核对每项实际--tastic、MRET/FLEQ/LOAD代表与命令行override。格式化、针对性测试，新forkZ3下不带--tastic的FLEQ实际smoke与make指定qffp smoke（独立输出；不覆盖旧产物）。默认策略只变入口选择，不删除seed能力检查，不更新系统Z3。必要时在make smoke指定Z3_PREFIX为已下载fork包。根float/memory固定快照gitlink不自动变更，是否提交/同步按实际边界记录。
