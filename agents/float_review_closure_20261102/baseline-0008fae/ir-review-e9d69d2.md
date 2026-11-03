# e9d69d2严格生成与实际IR独审

**普通严格检查、四配置SYMBOLIC严格生成来源及实际IR通过独审。** 模型为`e9d69d2f28586c089244c8e37ee4c904c5114458`，来源是独立named模型树；冻结runner-float的214模型、旧IR与memo源文件均未改变。本结论不含新版永久checker或动态/完整Clause预算验收。

- [来源与memo证据](model-review.provenance-e9d69d2.json)／[脚本](model-review.provenance-e9d69d2.py)：166个受控模型文件、149个工具/配置文件逐项匹配现场；ordinary与四SYMBOLIC均exit 0、源码未变，严格参数/配置/真实Sail及编译Z3保持。五个memo目的文件与旧源分别为独立inode，旧源未变；新生成确实读取named树和每配置独立memo路径。
- [IR范围与数值表达式证据](model-review.ir-e9d69d2.json)／[脚本](model-review.ir-e9d69d2.py)：四配置对214逐函数比较，均仅14个预期函数变化、删除`ieee_mask_exact_exceptions`，无新增函数。其余函数、zexecute和汇编映射不变。对14函数的每个FP/舍入/exact计算按指令顺序构建上游表达式DAG签名，全部与214相同，支持同变量多次赋值。
- [实际返回值与保留gate证据](model-review.values-e9d69d2.json)／[脚本](model-review.values-e9d69d2.py)：四配置×14项通过。从旧IR实际Jump条件核新facts的OF/UF/NX字段、round/整数核心的NX及原finite/valid条件；四转换/BF16有限臂直接返回原exact facts。ROD逐一核两条非SSA flags赋值、原RTZ base及同flags NX选择的`base|1/base`，不以“出现了OR/ITE”代替来源核对。

| 配置 | 新IR SHA256 |
| --- | --- |
| rv64d_v128_e64 | `661fd6e443a690f5b1c2a0ccfd1a5b84c908baba5e1b6cea786a1e0696a022ad` |
| rv32d | `c619a2b803ba719505118793d72bb906d74f85acb06d457f8dc687680fdc1e88` |
| rv64d_v256_e64 | `76d658edb9bb92ade750161a9f782bb4f908aec9a2ff3951a82a1b476126dc71` |
| rv64d_v512_e64 | `44657bfff823e33c66326cff0b7a6b27f4fd1715440653299462135fd9880006` |

纯flags/jam返回已回到数据流，不再要求生产代码为这些结果位制造fork；NaN/Inf/零、invalid原因、finite/valid、饱和、changed写回及ROD模式控制保持。源码签字见[候选源审查](model-review.candidate.md)。旧214动态结果和正在运行的77项长跑继续绑定214，不迁作e9通过；新版永久checker待其固定哈希、四配置及独立负控完成后另签。

后续签收补记：新版永久checker `053b48b3b588c58f87d74a72c7a5d5097a610ccea37700d94380142fede5ad16`已完成独立四配置/special绿、旧a877红及31项负控全拒，正式记录见[永久检查器独审](model-review.checker-e9d69d2.md)。前述动态/完整预算边界不变。
