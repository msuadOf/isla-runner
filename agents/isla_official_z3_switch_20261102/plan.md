# 正式Isla切换官方Z3

用户授权：根目录、float/memory Isla正式使用已编译官方1fd1d3613。保留原有CLI默认default、Make各Clause具体tactic和全部未提交改动。安装到用户级版本化前缀~/.local/opt/z3-official-1fd1d3613（不改系统包或全局PATH），所有检出Make默认Z3_PREFIX改该前缀并显式native链接/RPATH；内存分支补齐同样的链接参数。

实际源码：根isla/feat/float-support、isla/.worktrees/memory-consistency/feat/memory-consistency；runner-float和runner-memory独立检出也同步Make。注意runner-float target软链至另一既有worktree的target，runner-memory target软链至memory-consistency target，只对共享target串行/单次构建，避免并发覆盖。根与runner-float分别构建；memory使用runner-memory源码构建共享target。执行make build-isarch（各8个Cargo job）并核对--version/DT_NEEDED/RUNPATH/ldd -r均指向官方SHA。根debug亦重链接新库，不使用ELFpatch伪装正式编译。

验证：既有smt_init，Make实际FLEQ_S和C_LD smoke（独立输出、7200秒显式预算），CLI不传参数的默认入口smoke；不覆盖已有output。保留源码/IR/hash和结果，如发现基线已有partial如实分开。未请求提交/推送或改父gitlink，保持工作区改动可review。
