# flags changed 动态独立签收

新模型 `8ad5e8e` 与 Isla `42000be` 上，直接helper的300项状态结果限定签收，无阻断。五个逻辑IR入口各60项均实际退出0；其中rv64-default与rv64-v128使用同字节IR，不将它们说成五份独立IR。

受测Rust probe SHA `ded63f435…`，qffp、CPU15、官方Z3 `899cbc70…`、seed17；正式isarch `fe4bdceb…`只作来源绑定，本项实际执行独立probe。完整资产/命令见 [result.json](../../validation/flags/runs/model-8ad5e8e/result.json)，SHA `7fca0668…`。

独立执行 [audit_flags_results.py](audit_flags_results.py)，结果见 [flags-results-independent.json](flags-results-independent.json)：忽略owner日志中的expected字段，从实际old/incoming、初始FS/SD和完整状态重算，300项fcsr/mstatus均相符。每个逻辑入口36项changed真、24项假，覆盖旧位相同、零flags、首次增加、已有异位再增加及多位OR；FS Initial/Clean/Dirty、SD初值0/1、其他mstatus位哨兵取完整笛卡尔积，RV32检查SD31、RV64检查SD63。运行/seed/oracle日志SHA逐项匹配，五份seed日志实际fixed17。

SYMBOLIC实际IR的两个CSR callback（fflags后fcsr）只签静态调用合同；其空函数体未提供动态callback事件观察。普通Sail helper changed真臂另有mstatus callback，状态规则相同不等于回调事件完全相同。Ext_F定向初态含用于位保持验证的人工哨兵，不证明这些mstatus组合全部能由完整指令路径到达，也不覆盖Zfinx。未用目标FPR写回造成的Dirty替代changed假臂证据。

首次dry-run因源manifest排除8项旧IR/provenance/test fixture而失配，未开始动态；owner收窄为精确8项差集并逐项对git show字节核验，实际依赖冻结runner-float/isla-lib，134项Rust源均列入清单。修后dry-run与本批动态通过。初始化三个未用primop提示未触发错误出口，未影响这300项实际调用。

完整64受影响Clause的预算、实际指令多lane状态及全部数值输入仍按各自证据单列，本签收不替代它们。
