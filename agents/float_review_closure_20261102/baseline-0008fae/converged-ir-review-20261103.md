# 最终0f7b模型的严格生成与实际IR独审

**源码、严格生成来源、四配置IR及永久检查器限定签收，无当前源/IR阻塞。** 实际模型为`0f7b8fbc6724103f91f929ef6918f123df75d6c9`；77处纯数据选择回退已独审，延期OPEN按用户决定保留。本审查不把旧e9/214的动态或预算结果迁给新版本。

实际源码的三提交/五文件及其余161模型文件边界见[源码签收](converged-source-review-20261103.md)。严格生成独立复核166个模型源、149个工具/配置文件；ordinary及四配置SYMBOLIC均exit0，使用指定named模型、严格选项和各自memo。五份memo是独立inode副本，输入输出记录有效，旧e9源/memo/IR未改。真实Sail二进制SHA256为`373a37c268779bad65381b98c3dc13d56c3db9db90102d28d6f410278b23d45a`，编译Z3 CLI为`a7eac84c5493ac5766c2179620c3a4628b151198af9e6e9c488163c84561b3e9`；完整来源见[机器报告](converged-provenance-review-20261103.json)和[复核脚本](converged-provenance-review-20261103.py)。

| 生成配置 | 最终IR SHA256 |
| --- | --- |
| rv64d_v128_e64及默认别名 | `0fb0897e028803155108ec59f8289d4f89bafa98deb063bfa7f016a3d29f0786` |
| rv32d | `e17c4fe18552f8ce219b35f846c4c1a2c530dcad0ac9fc8f10d0da2604c3fa4e` |
| rv64d_v256_e64 | `47ba73418d6dcb1b1e86db7680ce4df9508e7885a02096e25e213c2c3b2c05e1` |
| rv64d_v512_e64 | `2bdea17d36c64545254f50cc5a6902e570a1fea682de3f7c062bf641a85a62a9` |

对e9比较，RV64仅36个目标函数变化：18个异常helper、6个窄转换及12个整数包装；RV32为34个，因为其工程本来没有f16→I64/Ui64。函数集合/数量无增减；`zexecute`、汇编及其他函数规范化后不变。`zrecip7/zrsqrt7`的断言诊断字符串只移动源码行号，规范化单独移除此非语义差异。逐指令记录赋值依赖，全部原生FP、舍入及exact操作序列和完整上游表达式DAG签名一致；[结果](converged-ir-review-20261103.json)、[脚本](converged-ir-review-20261103.py)。

另用不导入永久检查器的独立IR解释器比较旧、新实际返回值，四配置共276672组通过：异常helper对每操作数12类正负normal/subnormal/zero/Inf/sNaN/qNaN组合并遍历8种OF/UF/NX；窄转换核32位上游转换值在各端点前后及0/1/16/31四种上游flags；整数包装遍历12类源、全部32种五flags及3种候选整数。所有NV/DZ/facts、端点/原值、flags实际返回结果一致。解释器将原生FP作为相同不透明表达式，数值表达式由前述DAG独立绑定；这是分类/选择合同验证，不是全数值域证明。[结果](converged-ir-values-20261103.json)、[脚本](converged-ir-values-20261103.py)。

永久检查器冻结在SHA256 `9ebd0d937edc805e49103984bffbb507470115d349d7262553b6943b9e2763cf`。独立代码审阅及正负控见[检查器签收](converged-checker-review-20261103.md)：四配置closure/special共8绿，旧a877/e9红，104个定向语义错误全部拒绝；根Isla安装后的五份IR另以同一冻结检查器全部通过。安装已按主agent授权放行；`run.py --mode all`、新动态oracle、assembly/Make及两正式完整入口由其各自负责人单列验收，不由本静态签收替代。冻结214/e9旧77项预算只作历史。
