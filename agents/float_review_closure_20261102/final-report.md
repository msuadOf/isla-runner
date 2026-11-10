# float收敛交付

本轮77处纯数据选择回退已完成并通过GPT-6.1 Sol独立源码、IR和限定回归复核。OPEN实现保持现状，通用配置和必要性策略按用户要求延期至memory合流。当前交付模型 `0f7b8fbc6724103f91f929ef6918f123df75d6c9`，Isla `591693df2bc32019ea300511509ed683df09522e`；根float提交同时固定两者，远程发布状态另记。

## 最终实现

33处仅返回NV/DZ的异常原因判断、8处窄结果选择、12整数包装36处嵌套选择恢复原生Bool/ITE；core/V/FD分别为三个职责提交。NaN真实结果传播、NaN-boxing、原生trap/合法性控制保持。changed、29 finite/valid gate、2 ROD mode及既有f16→I16外overflow均未继续展开。Isla保留同Context枚举重放修复并同步五IR/来源及永久控制/数据流回归；最终Isla相对受测程序源码42000be只改六生成文件和四测试文件，生产Rust逐字相同。

## 最终验收

| 项目 | 实际新版本结果 |
| --- | --- |
| 源码/严格生成/IR | 精确77回退与其余161模型文件保持；普通严格检查、四配置SYMBOLIC生成成功；276672组旧新IR值流比较通过 |
| 永久回归 | 四IR及special共8正控、104独立错误变异全拒；安装五入口真实run.py全26步通过，RV64各327、RV32 307 helper用例及state/guard通过 |
| flags状态 | 300/300；独立按实际old/incoming/pre-state复算fcsr/mstatus |
| 转换 | 819helper+282scalar+183vector；实际机器字/初态与独立Fraction全符 |
| 异常/ROD/BF16 | 315/315新JSON；SoftFloat独立数值/flags全符，33566条记录断言及315约束IR来源复核 |
| 汇编/Make | 正向1104；GNU/Clang独立5824字节检查；真实Make8JSON/48检查通过，25次GNU非零RM拒绝保留并用相同机器字.insn验证 |
| FLEQ_S完整域入口 | 自然exit0，27.67秒，48条Retire，finished且所有partial计数0 |
| C_ADDI4SPN完整域入口 | 自然exit0，2.038秒，1条Retire，独立核pre.x2+imm后态及ExecuteAs完成边界 |

完整入口保持原FD域、T1/qffp/seed17、Clause和单次SMT各7200秒；定向315使用600秒固定输入预算，不混计完整域。运行程序明确来自42000be（acda0dce），与最终591的146个受控Rust/Cargo/.cargo文件逐字相同，不伪称重新构建。审查者核实315全部完成后才提交并更新子模块检出，运行输入未被中途改动。

来源与实际新数据见[动态独审](review/acceptance/model-converged-results-review.md)、[IR独审](baseline-0008fae/converged-ir-review-20261103.md)、[最终限定签收](review/acceptance/final-signoff.md)。根版本/远程引用的最终封存随后追加到publication，不改变受测程序和结果署名。

## 验收边界与合流

旧214与e9全77预算分别49/77、52/77通过，53次未通过均已核为7200秒外限124/无完整JSON；不重署精简版PASS。约28GB历史证据迁移后逐文件哈希和大小一致，原逻辑路径保留。本轮是上表限定回退验收，不宣称全77预算、全输入控制流覆盖、动态字符串反解析或硬件差异验证。

本轮无未关闭的新增源码/IR/定向正确性阻断；用户已接受的OPEN策略项不改成KEEP，其后续范围见[memory交接](handoff-to-memory.md)。准备合流所需提交/来源/回归及延期清单已留存，本轮不执行memory合并。
