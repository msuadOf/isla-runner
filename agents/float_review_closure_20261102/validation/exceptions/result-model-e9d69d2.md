# e9d69d2 候选模型异常、ROD、BF16定向复验

## 实际结果

正式冻结输入 `validation/inputs.model-e9d69d2-itrace.json` SHA-256 `eb830e77f6d31e88574e018ef08e1eb1d5f47f2e9369169d9fd4613877e6973a`，模型 `e9d69d2f28586c089244c8e37ee4c904c5114458`、Isla `42000be47596ec088623881d03c0eadc5cf0ba27`、V128 IR `661fd6e443a690f5b1c2a0ccfd1a5b84c908baba5e1b6cea786a1e0696a022ad`、Release isarch `acda0dceb259205fe0c43a3785484ffcafbef26b3194de3b9f67ad38eccbcf7d`，官方Z3 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。执行器 `run_directed.py` SHA-256 `8475d90d35d3d52195bbeb6bab4ab5cfe28d669536cb82aa61610c55e2efe311`，独立SoftFloat预期 `expected.json` SHA-256 `6ed44d0afba816a709fe6f4f18f0e34505c8b3202aaed6e1ad306e5aea135891`。

`--dry-run` 退出0，核上述完整来源、模型提交/父提交/差异、配置和官方动态链接；随后用CPU17/29各一个串行队列、T1/qffp/seed17、单例及单SMT外限各600秒启动独立目录 `runs-model-e9d69d2-itrace/`。PID和精确命令在 `launch-pid-model-e9d69d2-itrace.json`，资产/模型差异哈希在该批 `launch.json`。批次自然结束，**315/315 PASS**，每条退出0、1条Retire_Success、summary finished，错误、超时、遗漏、排队与采样计数均0，seed17日志有效。单例耗时1.106–28.330秒、中位1.607秒；计时仅是本固定输入批的观察值。

`python3 agents/float_review_closure_20261102/validation/exceptions/audit_model_e9d69d2.py` 退出0：逐条重读实际JSON、命令、seed、初后态和来源哈希，并从冻结base.ir和固定字段重建315份临时约束IR，其SHA逐条匹配命令与JSON provenance。**33566/33566** 已记录断言通过。机读账本 `audit-model-e9d69d2.json` SHA-256 `e9ab45a465960afa0c8cfe4f24da32b0069918f593f772fac0779175ab1108e3`，列逐例原始输出、约束IR、配置和seed日志SHA。临时约束IR按受签执行器合同在执行后删除，可由账本所列base IR与fields重建；没有将已删除文件称为在盘归档。

独立审查者从新批实际机器字与JSON初态重新调用SoftFloat，315/315数值和flags一致、零跳过；另独立重建315份临时约束IR哈希并核6566项初态值、30870项保持字段、seed和33566项已记录断言，给出[候选限定签收](../../review/acceptance/modele9-results-review.md)。

## 预期复用与范围

`expected.json` 原来源模型 `8ad5e8e`；候选直接父模型 `21418d0`，214→e9仅 `model/core/ieee_fp_exceptions.sail` 变化，完整Git diff SHA-256 `9dbf13575b7b32f48adb05f40c392bdbd520f77a980cea4d7594946808a1e9dd`。版本门预审见 `guard-e9d69d2.md`；执行器对候选完整SHA、父提交、唯一变动文件和diff哈希作固定检查。复用的是不依赖受测模型计算的SoftFloat预期，**本页315条实际结果全部来自候选新IR重新执行**，不继承 [21418d0结果](result-model-21418d0.md)。

固定矩阵为H/S/D标量165、ROD6 24、普通窄化转换70、H/S/D向量30、BF16 VV/VF 26，详见 [矩阵入口](README.md) 与 `expected.json`。逐例检查实际结果位串、五位flags、fcsr、FS/VS/SD、完整目的寄存器、其他FPR/VR/GPR保持和32位编码字段完整性。本批固定输入与600秒定向预算不代替完整Clause和单次SMT的7200秒预算，也不关闭全部调用入口、宽化、归约、估算、FMA四变体或任意vl/LMUL/VLEN条件。

