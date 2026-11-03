# 新版本 JSON 的 GCC/Clang 三表示验收

输入冻结清单为 `validation/inputs.model-8ad5e8e.json`（SHA-256 `25a1a624cb5dcac76a2261c470e198c64a75b20259322a1c7ee5d0572b83ec24`）：模型 `8ad5e8e9e0fc2a567a3b989a3738698f5c520bde`、Isla `42000be47596ec088623881d03c0eadc5cf0ba27`、rv64 VLEN128 IR `5ecea3717205dda77bc3cdbaf7a6b677415152e1f5cd09e541d0530519e25017`、启用单次 SMT interrupt 的新程序 `fe4bdcebd1d970d6f026c0f81ccd22f807f5cb4729da27ef67e20b2c08d09d80`。运行器先核两源码树清单、IR/程序/配置/官方 Z3 与实际动态链接哈希。脚本版本已由独立审查签于 `review/acceptance/harness-reviewed-hashes.json`。

命令为 `python3 agents/float_review_closure_20261102/validation/representations/run.py --inputs agents/float_review_closure_20261102/validation/inputs.model-8ad5e8e.json --batch model-8ad5e8e --cpu 36`。每组固定初态另列，不计完整域 Clause 完成。每次实际执行新程序，`-T 1 --tastic qffp --smt-timeout 7200s`，外层 `timeout 7200s`，`LD_PRELOAD` 拦截 seed 并逐行核 `fixed=17`。运行期间 PID 为 `663365`，已退出。逐组命令、环境、输入/输出哈希、完整 summary、工具版本和汇编日志见 [批次目录](model-8ad5e8e/)。

11 组共 111 条新 JSON，均 `finished`，八项 partial 计数逐项存在且为零，seed 均固定 17。GCC/Clang 的助记符、精确小端 bytes 与 `.insn` 共 666 次实际汇编核对，**648 通过、18 失败**；因此整组三表示 **FAIL**，不把部分组通过改称全通过。

| 分组 | JSON | 三表示核对 | 结论 |
| --- | ---: | ---: | --- |
| FLEQ H/S/D 的 qNaN 定向三组 | 24 | 144/144 | PASS |
| sqrt S | 12 | 72/72 | PASS |
| VFNUNARY0 的 f16→i8/ui8、合法 SEW8 | 2 | 12/12 | PASS |
| BF16 的 vl0/vl1 | 12 | 72/72；其中 4 次 Clang 对非法布局助记符按合同拒绝 | PASS |
| C_ADDI4SPN | 1 | 6/6；退休后态核对通过 | PASS |
| sqrt H/D Clause 的全部生成项 | 60 | 342/360 | FAIL：18 次 GNU 助记符拒绝 |

失败全来自同 Clause 中的拓宽转换 `fcvt.s.h`、`fcvt.d.h`、`fcvt.d.s` 附带 `rne/rtz/rdn/rup/rmm/dyn` 的 JSON 助记符。例：`fcvt.d.h f0, f0, rne` 对应字节 `53002042`，GCC 报 `illegal operands`。Clang 对这 18 项接受且字节相符；两工具链的精确 `.byte` 和 `.insn` 也与 JSON 字节相符。原始逐项失败、命令及 stderr 在 `sqrt-H/toolchains/results.json` 与 `sqrt-D/toolchains/results.json`。H/D sqrt 本身的负数/正数结果及 flags 经复用的语义检查器读取本轮新 JSON 另核通过，见 [补充观察](model-8ad5e8e/sqrt-semantic-observation.json)；它不消除同 Clause 的三表示失败。独立审查的无 RM/显式 RM 探针说明简单删 RM 会把非零编码规范成 `rm=0`，不能作为此证据的静默修正。

这组定向固定状态只验证列出的操作和汇编表示，不代替全部异常原因、全部 SEW/LMUL/VLEN、完整 Clause 预算或硬件差异测试。失败是 JSON 助记符与 GNU 工具链的表示兼容问题；本轮未改生产实现或放宽检查。
