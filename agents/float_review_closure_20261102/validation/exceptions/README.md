# 异常、ROD 与 BF16 独立数值 oracle

当前状态：最终模型 `0f7b8fbc` 的新IR已在固定输入、600秒定向预算下重新执行315条，**315/315 PASS**；独立Sol已从实际机器字和初态重算数值与flags，并核来源、seed、完整状态及315份约束IR，见[最终结果](result-model-converged-0f7b8fbc.md)和[独立限定审查](../../review/acceptance/model-converged-results-review.md)。这不替代完整Clause的7200秒预算。候选模型 `e9d69d2` 的[结果](result-model-e9d69d2.md)及[当时签收](../../review/acceptance/modele9-results-review.md)、模型 `21418d0` 的[结果](result-model-21418d0.md)及[当时签收](../../review/acceptance/model214-results-review.md)、更早 `8ad5e8e` 的[结果](result.md)与[当时签收](../../review/acceptance/exceptions-review.md)均保留原版本署名。最早 `rv64d.ir` SHA-256 `a877e245…` 只用于构造器字段结构预检。

## 已准备的固定输入

运行 `python3 agents/float_review_closure_20261102/validation/exceptions/prepare_expected.py` 生成 `expected.json`，从独立 Berkeley SoftFloat oracle 逐条取得原始 result bits 和五位 flags；NaN 结果按架构 canonical NaN 规范化，原 oracle bits 另存。`expected.json` 的 SHA-256 为 `6ed44d0afba816a709fe6f4f18f0e34505c8b3202aaed6e1ad306e5aea135891`，记录 oracle 程序、源码和 libsoftfloat.a 的哈希及每条实际命令。

| 类别 | 数量 | 具体义务 |
| --- | ---: | --- |
| H/S/D 标量 | 3×55 = 165 | 加减 Inf 抵消与有效对照、零×Inf 两源及负符号、0÷0／Inf÷Inf／有限非零÷±0／Inf÷0、sqrt 负数／±0／sNaN／qNaN、FMA 两乘源和加源 sNaN 与 Inf 抵消；五 RM 下有限 OF、UF、NX 与融合对照。 |
| f32→f16、f64→f32 ROD 与普通 | 24 + 70 = 94 | ROD6 精确低位0/1、非精确 RTZ 低位0→1/原1、负值、tiny/OF、±0/Inf/sNaN/qNaN；普通五 RM 数值边界及 RM0 特殊值对照，结果与 flags 成对。 |
| H/S/D 向量 `FVVTYPE` | 30 | 两 lane 的 Inf 抵消、NV 与有限 OF\|NX、0÷0 NV 与有限÷0 DZ；mask0/1/2/3 分别核目的组与 flags OR。 |
| BF16 VV/VF 融合 | 26 | 五 RM 融合与乘后加分离反例、三来源 sNaN、vl0、mask0/1/2/3 的 `NV\|OF\|NX` 累计及未活动 lane 保持。 |

`run_directed.py` 使用最终 `validation/inputs.<批次>.json` 冻结清单，强核模型/Isla commit 与源码 manifest、IR/config/binary/官方 Z3/seed17 拦截库哈希和动态链接；将实际资产复制到本目录的新 run 子目录。每个样例保存初态配置、约束字段、命令、受测哈希、seed 拦截日志、原始 JSON、完整后态断言与输出哈希。每个 CPU lane 串行执行，用户指定独占 CPU；单例默认外限及 SMT 均600秒，属于固定域定向预算，**不替代完整 Clause 的7200秒预算**。

启动示例（最终路径和独占 CPU 由主任务提供）：

```sh
python3 agents/float_review_closure_20261102/validation/exceptions/run_directed.py \
  --inputs agents/float_review_closure_20261102/validation/inputs.<批次>.json \
  --output agents/float_review_closure_20261102/validation/exceptions/runs-<批次> \
  --workers 2 --cpus <独占核1>,<独占核2>
```

`run_directed.py` 对旧 IR 完成全部315项 Clause 字段/类型/约束文本生成预检；其结果解析器另只读复核旧批次20项 BF16 原始 JSON，20项逐条断言均一致。这两项仅检查工具。最终 IR 的真实执行已记录在 [两批结果](result.md)：仅当退出0、严格 summary/provenance、有效 seed17 日志及逐条位串/flags/状态断言全绿才记单例 PASS；首批配置解析失败保留FAIL。

本批未准备 `Recip7/Rsqrte7` 十类 H/S/D 查表、顺序/无序及宽化归约、其它向量算术 Clause（如 VF、宽化和 FMA）的全组合；旧56项结果仅作历史方法，不迁为本批 PASS。H/S/D 标量和 `FVVTYPE` 向量的定向成功也不能外推为全部24条异常调用闭包已见证。
