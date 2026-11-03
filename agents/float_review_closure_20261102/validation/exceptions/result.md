# 异常、ROD 与 BF16 定向数值结果

## 结果与受测范围

固定模型 `8ad5e8e9e0fc2a567a3b989a3738698f5c520bde`、Isla `42000be47596ec088623881d03c0eadc5cf0ba27`；正式冻结输入 `validation/inputs.model-8ad5e8e.json` SHA-256 `25a1a624cb5dcac76a2261c470e198c64a75b20259322a1c7ee5d0572b83ec24`。受测 V128 IR `5ecea3717205dda77bc3cdbaf7a6b677415152e1f5cd09e541d0530519e25017`、Release isarch `fe4bdcebd1d970d6f026c0f81ccd22f807f5cb4729da27ef67e20b2c08d09d80`、官方 Z3 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。完整哈希和命令见两批 `launch.json` 与逐例 `command.json`；预期值来自独立 SoftFloat，`expected.json` SHA-256 `6ed44d0afba816a709fe6f4f18f0e34505c8b3202aaed6e1ad306e5aea135891`。

**315 条固定输入定向样例均有通过证据：首批305条，修正初态表示后的第二批10条。** 合并证据审计 `python3 agents/float_review_closure_20261102/validation/exceptions/audit_combined.py` 退出0，逐例重核原始输出哈希、seed17拦截日志、命令资产哈希、完整退出状态和结果断言，共 **33566/33566** 项断言。每条实际输出为1条 `Retire_Success`、summary `finished`、无错误/超时/omitted/pending/sampled；位串、五位flags、fcsr、FS/VS/SD、目标全寄存器、其他FPR/VR/GPR保持符合期望，编码字段完整且为32位。逐例清单、输出及seed日志SHA见 `combined-audit.json`（SHA-256 `52f833319c9e6daa07d09aed48cdb12fe0b9bafc89c9b6a5454cb22dc3984e8b`）。

独立审查者从实际机器字、实际初态和独立 SoftFloat 重算全部315条结果与flags，零skip，并重核上述来源、seed、summary和33566条断言，给出[限定动态签收](../../review/acceptance/exceptions-review.md)。该签收仅适用本页列明的模型、IR、程序和固定输入域。

| 类别 | 实际通过 | 结果义务 |
| --- | ---: | --- |
| H/S/D 标量 | 165 | Inf抵消、两源零×Inf、0÷0、Inf÷Inf、有限÷±0、Inf÷0、sqrt负数/±0/NaN、FMA三源特殊值；五RM下有限OF/UF/NX与融合数值反例。 |
| ROD6 + 普通格式转换 | 24 + 70 | f32→f16、f64→f32；精确/非精确低位、tiny/OF、负值、零、Inf、sNaN/qNaN；普通五RM作数值与flags对照。 |
| H/S/D向量 `FVVTYPE` | 30 | 两lane的NV、DZ、OF/NX和mask0/1/2/3 flags OR、目的组保持。 |
| BF16 VV/VF融合 | 26 | 五RM的单次融合与乘后加反例、三来源sNaN、vl0、mask0/1/2/3的异常累计。 |

实际输出例子：H `+Inf + -Inf` 得 canonical `0x7e00`、NV=`0x10`；S `1.0 ÷ -0` 得 `-Inf=0xff800000`、DZ=`0x08`；D 的融合输入 `0x3ff0000000000001 × 同值 + 0xbff0000000000002` 得 `0x3970000000000000`、flags=`0`，独立乘后加则为 `0`、NX=`1`。ROD 的 f32 `0x3f800001`→f16 得 `0x3c01`、NX=`1`，f64最小次正规→f32 得 `0x00000001`、UF\|NX=`3`。D向量两活动lane分别产生NV与DZ时，目的低/高lane为 canonical NaN/`+Inf`，累计flags=`0x18`；BF16两活动lane的NV与OF\|NX累计为`0x15`。每个例子的源位串、原始JSON与完整后态断言保留在对应 `runs/<name>/`。

## 首批失败和定向复验

首批 `runs-model-8ad5e8e/summary.json` 为315条：305 PASS、10 FAIL。10个失败全部为 `VD-*` 双精度向量两lane初态：十六进制128位 `vr2/vr4` 被 Isla 配置按64位整数读取，进程在求解前退出1，未生成JSON或seed日志。保留原始FAIL，不把它记作模型计算错误或通过。

第二批 `runs-model-8ad5e8e-vd-retry/summary.json` 仅复验这10条，10/10 PASS。只将D向量 `vr2/vr4` 初态改成配置已支持的 `0b` 加128位逐位模式，并在结果检查时按二进制解析；数值位模式未变。首批脚本 SHA-256 `6c24b0da54defa58cac14456b65ce1a313fffabab010e239924ed7938eafbfbd`，复验脚本 `43c967d0e212aedfea1b50b97e144440598b2dec99ad328dd38cb1596c8f1752`。SoftFloat预期、模型、Isla、IR、binary、Z3、seed拦截库及配置母本哈希在两批一致。改动范围与独立复签见 `vd-retry-scope.md` 和 `../../review/acceptance/harness-review.md`。首批成功项用原脚本原结果签，复验项用新脚本原结果签，不写成“单批315全PASS”。

首批通过项单例耗时1.212–2.620秒，复验10项为2.014–28.241秒；两批均使用CPU17/29各一个串行队列、T1/qffp/seed17、单例与SMT外限600秒。该预算和固定输入域只证明列明的315条实际数值/状态；不是完整Clause的7200秒预算，也不关闭其它宽化、归约、估算、VF、FMA四变体及全部输入域的覆盖义务。
