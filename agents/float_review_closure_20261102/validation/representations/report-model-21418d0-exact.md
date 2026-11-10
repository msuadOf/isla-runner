# 修后新 IR 的 JSON 三表示复验

本批使用新冻结清单 `validation/inputs.model-21418d0-itrace.json`（SHA-256 `44641223d4541b042a337c9adab6ac902f34d3af82f3835213f28b39cc247b19`），模型提交 `21418d0b0d4942fae20061ed580ee04aff4a8a61`、Isla 提交 `42000be47596ec088623881d03c0eadc5cf0ba27`、rv64 VLEN128 IR `5514e98ee5566dbbcfa4f6dbafa9dbb1851c72dce4b52ca0c0a95a1c7fafff4a`、启用单次 SMT interrupt 与 trace 的程序 `acda0dceb259205fe0c43a3785484ffcafbef26b3194de3b9f67ad38eccbcf7d`。所有来源清单、配置、官方 Z3 与动态链接先经 `common.frozen_inputs` 逐哈希核对。旧 `8ad5e8e` 批次的 GNU 助记符 FAIL 仍保留在 [旧报告](report.md)，不覆盖。

命令：`PYTHONDONTWRITEBYTECODE=1 python3 agents/float_review_closure_20261102/validation/representations/run.py --inputs agents/float_review_closure_20261102/validation/inputs.model-21418d0-itrace.json --batch model-21418d0-exact --cpu 36`。每组固定初态，`-T 1 --tastic qffp --smt-timeout 7200s`、外层7200秒、`LD_PRELOAD` seed17；实际 runner PID `1315068` 已退出。程序、IR、配置、命令、环境、seed 日志、JSON 和工具链版本/哈希见 [批次 provenance](model-21418d0-exact/provenance.json)及各组 `run/command.json`、`result.json`。

12组生成 **135条新 JSON**，均自然退出0、`summary.status=finished`、八项 partial 计数逐项存在且为0，seed日志逐行确认 `fixed=17`。GCC/Clang 对助记符、精确字节、`.insn` 的 **810次实际汇编**均有原始记录：其中 25 次 GNU 非零 RM 精确转换助记符被拒，原 `toolchains/results.json` 保持失败；新消费器逐项选择已实际编译且与原机器字逐字相同的 GNU `.insn`，并要求同次 `.byte` 和 Clang 原助记符也精确匹配。选择记录见各组 `toolchains/selection.json`。按用户允许的精确表示合同，**810/810均有可用的精确工具链表示，12/12组 PASS**；不把25次 GNU 助记符失败改写成成功。

| 实际范围 | JSON | 精确工具链结果 |
| --- | ---: | --- |
| FLEQ H/S/D qNaN 定向 | 24 | 144项，原助记符与两精确形式均通过 |
| sqrt H/S/D Clause | 72 | 432项；D.S/D.H/S.H 的非零RM有15次 GNU `.insn` 精确选择 |
| f16→i8/ui8 合法 SEW8 | 2 | 12项通过 |
| 新增 F_UN_RM_XF_TYPE_D 固定 `x1=1, rd=f0` | 24 | 144项；D.W/WU非零RM有10次 GNU `.insn` 精确选择；D.L/LU全部严格助记符通过 |
| BF16 vl0/vl1 | 12 | 72项；4次 Clang 对非法布局助记符按原合同拒绝，精确形式保字 |
| C_ADDI4SPN | 1 | 6项，退休后态通过 |

五种精确转换 `FCVT.D.S/D.H/S.H/D.W/D.WU` 各有 RM0/1/2/3/4/7 的实际 JSON；RM0五条均是无 RM 的 canonical 助记符，GCC 和 Clang 都汇编成功且机器字相同。`FCVT.D.L/LU` 各有六RM实际 JSON，保留显式 RM 并由两工具链助记符精确通过。`FCVT.S.W` 负对照没有进入本次12组，但已在独立112次工具链探针和消费器18种负对照组合中严格验证；本报告不称其有新 JSON 见证。新增整数到双精度组还核原机器字 `rs1=x1/rd=f0`、输入x1=1、输出双精度1.0和flags0的24种组合。独立审查从实际机器字和前态用 SoftFloat 重算24条数值与 flags，并逐项复核工具链选用，见 [修后结果审查](../../review/acceptance/model214-results-review.md)。

这属于列明的固定初态 JSON 与工具链表示复验，不代替全部异常原因、SEW/LMUL/VLEN、完整 Clause 两小时预算或硬件差异测试。
