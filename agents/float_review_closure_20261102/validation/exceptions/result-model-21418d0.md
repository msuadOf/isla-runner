# 21418d0 新IR与新isarch定向数值复验

## 实际结果

最终冻结 `validation/inputs.model-21418d0-itrace.json` SHA-256 `44641223d4541b042a337c9adab6ac902f34d3af82f3835213f28b39cc247b19`。模型 `21418d0b0d4942fae20061ed580ee04aff4a8a61`、Isla `42000be47596ec088623881d03c0eadc5cf0ba27`、V128 IR `5514e98ee5566dbbcfa4f6dbafa9dbb1851c72dce4b52ca0c0a95a1c7fafff4a`、Release isarch `acda0dceb259205fe0c43a3785484ffcafbef26b3194de3b9f67ad38eccbcf7d`、官方 Z3 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。执行器 SHA-256 `613e0441923a42650165da75a14bed730704bb16d08f09cda056c65008d12cd9`，独立 SoftFloat 预期 `expected.json` SHA-256 `6ed44d0afba816a709fe6f4f18f0e34505c8b3202aaed6e1ad306e5aea135891`。

`--dry-run` 先退出0并核上述资产、全部源码清单、官方库链接和seed拦截库；随后单独目录 `runs-model-21418d0-itrace/` 用CPU17/29各一个串行队列、T1/qffp/seed17、单例和单SMT均600秒外限后台运行。PID和精确argv见 `launch-pid-model-21418d0-itrace.json`，资产哈希、expected来源提交与模型差异哈希见该批 `launch.json`。后台批次自然结束，`summary.json` 为 **315/315 PASS**，每条退出0、1条Retire_Success、summary finished、错误/超时/遗漏/排队/采样计数为0，seed17日志有效。

`python3 agents/float_review_closure_20261102/validation/exceptions/audit_model_21418d0.py` 退出0，逐条重读新批实际JSON、命令、初后态断言、seed日志与来源哈希，并从冻结base.ir和固定字段重建315份临时约束IR核其SHA，共 **33566/33566** 已记录断言通过。账本 `audit-model-21418d0.json` SHA-256 `5c794b808be11c96f3d140f98d0bd725119bfe0967df544f4ac07b0b71441673`，列每个样例的原始输出、约束IR、配置和seed日志哈希。单例耗时最短1.211秒、中位1.614秒、最长28.046秒；计时只是本固定输入批的观察值。

独立审查从新批实际机器字译码并读取对应实际初态，逐条调用独立 SoftFloat 重算，315/315数值与flags相符、零跳过；另独立重建315份约束IR哈希并复核来源、seed、6566项初态值、30870项保持字段及33566条记录断言，给出[新版限定签收](../../review/acceptance/model214-results-review.md)。

覆盖分组与具体输入见 [固定矩阵](README.md) 和 `expected.json`：H/S/D 标量165、ROD6 24、普通窄化转换70、H/S/D向量30、BF16 VV/VF 26。逐例核结果位串、五位flags、fcsr、FS/VS/SD、完整目的寄存器、无关FPR/VR/GPR保持和编码字段完整性。旧模型 `8ad5e8e` 的305+10两批证据仍见 [旧版结果](result.md)，**不作为本页315项的通过来源**。

## 预期复用边界

`expected.json` 原绑定 `8ad5e8e`；新模型相对它仅在 `dext_insts.sail` 和 `zfh_insts.sail` 增加20行 `mapping clause assembly`，整份Git diff SHA-256 `305d826ee485b4803ffe8cb747cc9e20f815897c3b2714415a51c00867459bd7`。执行器对新模型固定提交和这份差异作显式校验，`launch.json` 同时记录实际受测提交与预期来源提交。这里复用的是独立数值预期，**实际结果全部来自新IR与新程序重新执行**。

本批固定输入域与600秒单例外限不替代完整Clause和单SMT的7200秒预算，也不证明所有调用入口、宽化、归约、估算、FMA四变体或任意vl/LMUL/VLEN条件闭合。
