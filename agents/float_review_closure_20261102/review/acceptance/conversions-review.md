# 整数转换动态独立签收

模型 `8ad5e8e`、Isla `42000be`、新V128 IR `5ecea371…` 上，819个helper和465条直接执行指令的限定动态结果签收，无阻断。实际输出的结果位、五flags、机器字、观察寄存器状态均已独立核对；本批不算isarch JSON或完整Clause预算PASS。

受测配置 `8247c8d4…`、直接helper程序 `669c727e…`、指令程序 `9e1bc98f…`、官方Z3 `899cbc70…` 与seed17，均由 [run.json](../../validation/conversions/runs/rv64d-v128-attempt2/run.json)记录。源清单固定166个模型文件和1029项Isla tracked文件；新IR与正式inputs `25a1a624…`相同。两个旧直接runner硬编码Qfaufbv，配置也与正式FD完整域不同，见[正式输入绑定](../../validation/conversions/runs/rv64d-v128-attempt2/formal-input-binding.json)。这些差异不能省略。

独立重核命令：

```sh
python3 agents/float_review_closure_20261102/review/acceptance/audit_conversion_expected.py
python3 agents/float_review_closure_20261102/review/acceptance/audit_conversion_results.py
```

[独立结果](conversions-results-independent.json)不读取owner提供的expected位来计算数值：按实际机器字重解源/目的/格式/舍入模式，读取被观察源寄存器和冻结初态，以精确有理数解码FP和整数舍入重新计算结果/flags。282条scalar和183条vector全部相符；W/WU的RV64符号扩展、NV压制本次NX、旧flags OR、完整目的组、活动/屏蔽/前序/尾部、LMUL2源对齐与观察寄存器保持均按实际用例核实。六个窄helper和十二普通包装均在所列固定输入中执行；没有将不可表示的整数端点或f16有限正overflow虚列为可达。

819条helper的独立FP输入预期另用精确有理数全量重算。真实helper日志的逐例函数名/次序与归档TSV完全对应，三段实际退出均0，seed日志均记录random_seed固定17；helper实际返回位/flags断言及差异UNSAT由已审Rust程序执行。所有指令均实际Retire_Success，且有SAT、差异UNSAT、译码/执行/反编码路径与机器字证据。

输入14文件预运行快照与归档hash逐项核对，见[归档核账](../../validation/conversions/runs/rv64d-v128-attempt2/input-archive-verification.json)。scalar结果SHA为 `903a4c7d…`，vector为 `547a4482…`。源码、完整命令、日志与输出hash均在原批次保留。旧attempt1确有806条helper实际通过，但启动器将汇总PASS误计为807后停止；该准备错误已修，旧批不算新版整体完成，且旧fixture未随批复制的限制保留。

本签收只覆盖列明FP位串、舍入、源/目的寄存器、vl≤2、LMUL1/2和观察域。未逐项检查所有无关寄存器，不证明全部输入、全部调用者、VLEN变体或完整控制流已覆盖；正式64条受影响Clause及13条兼容回归结果仍由另一账本单独验收。
