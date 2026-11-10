# 最终模型0f7b8fbc的异常、ROD与BF16定向结果

## 实际新批次

冻结输入 `validation/inputs.model-converged-0f7b8fb-itrace.json` SHA-256 `5147af93ecd9cfb5cd6c0607d8073fa997b608dc9993f8c81dee8e739f1e631e`，模型 `0f7b8fbc6724103f91f929ef6918f123df75d6c9`、Isla `42000be47596ec088623881d03c0eadc5cf0ba27`、V128 IR `0fb0897e028803155108ec59f8289d4f89bafa98deb063bfa7f016a3d29f0786`、Release isarch `acda0dceb259205fe0c43a3785484ffcafbef26b3194de3b9f67ad38eccbcf7d`、官方Z3 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。执行器 `run_directed.py` SHA-256 `12ea69e349660ccdb79d129f41968d35657a67502c70b028082a2053c9325cf7`，独立SoftFloat预期 `expected.json` SHA-256 `6ed44d0afba816a709fe6f4f18f0e34505c8b3202aaed6e1ad306e5aea135891`。

`--dry-run` 先退出0，核完整源码manifest、最终提交链/五文件范围/差异哈希、IR、程序、配置、官方动态链接和seed库。随后在CPU17/29各一串行队列、T1/qffp/seed17、单例及单SMT各600秒外限运行独立目录 `runs-model-converged-0f7b8fbc-itrace/`。精确后台命令、PID与哈希在 `launch-pid-model-converged-0f7b8fbc-itrace.json`，冻结资产及预期来源在该批 `launch.json`。批次自然结束，**315/315 PASS**：每条退出0、1条Retire_Success、summary finished，错误/超时/遗漏/排队/采样计数均0，seed17日志有效。单例耗时1.415–80.990秒、中位3.613秒，仅是本固定输入批的观察值。

`python3 agents/float_review_closure_20261102/validation/exceptions/audit_model_converged_0f7b8fbc.py` 退出0：逐条重读原始JSON、命令、seed、初后态、来源哈希，并从本批冻结base.ir与每例clause/fields重建315份临时约束IR，其SHA与命令及实际JSON provenance相符；**33566/33566** 条记录断言通过。机读账本 `audit-model-converged-0f7b8fbc.json` SHA-256 `6d076a4dcdfa9bf94410e44c8e3c9b5e2c3224e90e7945e6b116287a7d12f906`，逐例列输出、约束IR、配置与seed日志SHA。临时IR按受签执行器原合同在执行后删除，可从上述冻结内容确定性重建。

## 固定范围与版本

315例沿用原fixture，不增加覆盖：H/S/D标量165、ROD6 24、普通窄化转换70、H/S/D向量30、BF16 VV/VF 26。每例核实际结果位串、五位flags、fcsr、FS/VS/SD、完整目的寄存器、其他FPR/VR/GPR保持及32位编码字段完整性。`expected.json` 来源模型为 `8ad5e8e`，但本页所有实际输出均由最终模型新IR重新执行；旧[候选e9结果](result-model-e9d69d2.md)不继承为最终PASS。

最终模型相对e9有三提交收敛链，仅变core异常文件、三个FD整数wrapper及V窄转换文件；Git差异 SHA-256 `01ad2e7f97de170aa7e400979b5c00af49e3f473e8b65946d16faa2fe39c74ae`。执行器对精确提交链、五文件集合和该差异哈希固定核对，见[版本门](guard-final-0f7b8fbc.md)。复用独立数值预期不等于继承旧模型验收。

独立Sol审查从本批实际机器字与初态重算SoftFloat，315/315条数值和flags相符、无跳过；另逐条核seed、来源与完整状态，并独立重建315份约束IR，其SHA与命令及provenance一致。6,566项初态及30,870项状态保持字段核对相符，owner的33,566项记录断言也由审查重核。见[独立审查](../../review/acceptance/model-converged-results-review.md)、[数值账本](../../review/acceptance/exceptions-converged-independent.json)和[来源账本](../../review/acceptance/exceptions-converged-evidence-independent.json)。

本批固定输入与600秒定向预算不替代完整Clause和单次SMT的7200秒预算，也不关闭全部调用入口、宽化、归约、估算、FMA四变体或任意vl/LMUL/VLEN条件。
