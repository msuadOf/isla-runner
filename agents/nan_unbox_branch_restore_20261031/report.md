# 恢复NaN-boxing显式分支（2026-10-31）

按用户要求，将`model/extensions/FD/fdext_regs.sail:50`从ITE恢复为原来的Sail if。模型提交9c339044，Isla提交80231ce9。保留boxing有效/无效的显式控制流，不以缺乏整Clause性能数据支撑的提速承诺合并两侧。

```sail
if x['n - 1 .. 'm] == ones()
then x['m - 1 .. 0]
else canonical_NaN()
```

本轮只恢复这一行，其他ITE及既有独立review问题未修。boxing有效的输入仍可能包含低位NaN、Inf等，这些条件不能因本次恢复而视为全部覆盖。

## 实施与验证

- 修改前新增分支回归失败：旧IR的nan_unbox只有1个Jump，boxing判断被ITE合并。新IR五份均有等宽与boxing两个显式Jump，检查通过；测试已接入`test/float_ir/run.py`。
- 四配置完整SYMBOLIC严格IR生成均退出0，五个交付IR文件全部更新；普通模式完整严格类型检查退出0，162.79秒。模型、配置、工具与IR哈希见`isla/ir/provenance/manifest.json`。
- 五IR数值/状态回归共23步全部通过：1615项helper、180项状态、20项guard及分支结构检查；不外推完整源码控制流覆盖。
- 使用同一二进制和FD配置做有限预算前后探针。FLEQ_S由4条变10条，退休见证覆盖两个源的四种boxing组合；F_BIN_RM_TYPE_S由52条变208条，退休由40变160条，四种boxing组合各40条。有效boxing且源为有限数的退休见证由0变40条。
- 单次FLEQ_S耗时3.62→4.57秒，单次四算术Clause耗时9.78→55.70秒。每次内部路径预算30秒、外限60秒，均自然退出0；并发背景负载未控制、未做重复统计，且生成集合扩大，不能作为相同覆盖工作量的严格性能比。保留这些实测数据，不宣称恢复分支提速。
- 新FLEQ的GCC/Clang文本编码核对20/20，新四算术JSON核对416/416通过，仅限这些生成见证。BF16非法布局等既有双工具链缺口仍待独立处理。
- 79份workaround、132个region和22处锚点检查通过；Sail行数和坐标未变，按约定保留基准IR哈希的advisory告警。
- 根float独立检出执行`make solve-FLEQ_S THREADS=1 ISA_CONFIG=./configs/riscv64_difftest_fd.toml OUTER_TIMEOUT=60s SOLVE_TIMEOUT=30s SMT_TIMEOUT=20s TASTIC=qfaufbv`退出0、10条JSON，两侧见证检查通过。

## 历史性能依据与边界

原441c与nan86f的FVFTYPE对照均在约7200秒外限退出124，没有最终完整JSON；局部退休终态分别21、27，不能据此推算总fork数量或完成时间加速比。恢复显式判断的依据是用户的覆盖与性能证据取舍，未声称原ITE算错。

完整IR生成和本轮回归的可复现入口：`isla/scripts/regenerate_ir.py`、`isla/test/float_ir/run.py`、`isla/test/float_ir/check_nan_unbox_branches.py`。本轮不包含完整77 Clause、硬件重放或其他review缺陷的验收。

## 本机证据入口

[前测红测](branches-before.log)、[IR结构绿测](branches-after.log)、[实际JSON分支检查](json-branches-after.log)、[前测](before/summary.json)、[后测](after/summary.json)、[普通严格检查](ordinary-strict.json)、[23步回归](float-regression/checks.json)、[算术双工具链](arithmetic-assembly.json)、[FLEQ双工具链](fleq-assembly.json)、[区域检查](workarounds.log)、[make日志](make-fleq.log)。各probe的result.json保留精确argv、退出、IR/config/binary哈希。
