# E 阶段 RV64 浮点向量非访存 clause 样例

2026-09-26 完成 22 个具体输入的验证，覆盖 clause-matrix #35–46（排除 #40）、#75–76、#78–81、#84–85、#89，共 20 个不同 clause。`cases.json` 每个 clause 至少一条真实 OP-V 编码；`VFUNARY0` 和 `VFUNARY1` 另有一条产生 NX 的输入。此结论只覆盖列明的子操作、输入、SEW=32、VL=1、LMUL=1，不代表其余 enum、SEW、mask/vstart 情况通过。

## 证据与重跑

- `generate.py` 以独立的 Python 浮点/整数计算构造写回与完整 `fcsr` 预期；调用 GNU `riscv64-linux-gnu-as -march=rv64gcv_zvfh` 生成机器码，再与 Sail OP-V 字段拼接核对。调用者须以 `--output-dir` 指定仓库外汇编临时产物目录。源汇编见 `assembly.txt`，GNU 反汇编见 `cases.objdump`；其文件头已规范化为 `cases.o`。
- `cases.json` 是 runner 输入，`results.json` 是实际输出，`run.log` 保存退出码为 0 的一次 `/usr/bin/time -p` 日志（real 5.91 秒）。
- 固定 runner SHA-256：`bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425`；IR：`c9e1bfe29e75452568d61fc3b3407e707eb1bd7e48193e212495ec21b885bc75`；配置：`8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`。归档的 `cases.json` SHA-256 为 `c5c91bc4c2d7d14f95efc2dc72d00b2dac2786f836ff8e94bffc6ce2483e20cc`，`results.json` 为 `ffa69f354fbeb734d9ab689b34903e5e59de72aa4ca301f348eea56a6dcd0a39`，规范化 `cases.objdump` 为 `86fd5ab3abc3e8f5d2ccf3ac0f214b923c6cea69903ada1a61a0402d31cd7933`。重跑时先核对前三个执行输入文件哈希，在本目录以路径变量执行：

  ```sh
  python3 generate.py --output-dir "$OUT_DIR"
  /usr/bin/time -p "$RUNNER" "$IR" "$CONFIG" cases.json results.json
  ```

22/22 项均有 `sat=true`、`difference_unsat=true`、`structural_ok=true`：每项 `zext_decode` 为 2 条 SAT 完成路径，constructor 与 tuple 字段符合预期；`zencdec_forwards` 唯一反编码与输入相同；`zexecute` 唯一完成路径返回 `Retire_Success`；所观察的完整目标寄存器、`fcsr` 和 `vstart` 与独立预期任意差异不可满足。`vfcvt.x.f.v` 的 1.5→2 与 `vfsqrt.v` 的 √2 两项分别验证 NX=`0x1`。

`run.log` 中配置寄存器与未调用 primop 的解析提示在本次退出码 0 的完整执行中存在；它们不是验证失败。源文件或 IR/配置改变后，这份结果需要重新验证。

首次试跑在 `FWVVMATYPE` 的 `expected_fields` 索引 2/3 写反处停止；Sail 该 tuple 顺序是 `(funct6, vm, vs1, vs2, vd)`，已修正生成器并全批重跑。该次失败属于样例元数据错误，不是执行语义差异。

## 扩展批次（同一 IR、配置与固定 runner）

首轮 22 条证据原样保留。后续使用同一 runner/IR/配置哈希分别运行三个输入批次，均由 `verify.py` 对输入与归档证明逐项检查（包括真实编码、完整 tuple、`Retire_Success`、唯一路径、SAT 和状态差异 UNSAT）：

| 批次 | 输入与证明 | 结果 | 独立预期与边界 |
|---|---|---|---|
| 映射×格式 | `expanded-cases.json` / `expanded-results.json` | 227/227 PASS | 80 个 enum 成员的全部合法 SEW 共 215 条，另四个固定编码各 SEW16/32/64 共 12 条；包括两条 SEW8→FP16。观察目标、完整 `fcsr`、`vstart`、`mstatus`，宽目标另观察下一物理寄存器。 |
| 状态 | `state-cases.json` / `state-results.json` | 49/49 PASS | 14 个普通 clause 各有 vstart 跳过有 mask 位的 sNaN、另一 sNaN 被 mask 屏蔽、活动有限元素、tail、旧 flags；另测比较 NaN、两元素 slide payload、归约多 lane/vl0/全 mask、move/merge、FMA 融合低乘积、H/S 非法 boxing 和 LMUL2 跨寄存器。 |
| 舍入 | `rm-cases.json` / `rm-results.json` | 564/564 PASS | 14 个 rm 路由族的 34 条格式路径；正/负/奇中点×frm0–4 为 510 条，旧 flags OR 34 条，固定 RTZ 在非 RTZ frm 下 20 条。SQRT 的三个 shape 都用 √2，故 564 条记录对应 534 个不同完整输入。 |

`expand.py` 从 Sail 映射取得 enum、编码和助记符，用 GNU assembler 生成 `expanded.objdump`，再按每个子操作独立计算结果位。`state.py` 的 LMUL2 编码有独立 GNU 反汇编 `state-lmul2.objdump`；`rm.py` 的中点预期由目标格式精度、正负方向和 tie 规则算出，SQRT 以精确有理数平方夹逼相邻结果。重跑顺序：

```sh
python3 expand.py --output-dir "$OUT_DIR"
"$RUNNER" "$IR" "$CONFIG" expanded-cases.json expanded-results.json
python3 state.py --output-dir "$OUT_DIR"
"$RUNNER" "$IR" "$CONFIG" state-cases.json state-results.json
python3 rm.py
"$RUNNER" "$IR" "$CONFIG" rm-cases.json rm-results.json
python3 verify.py
```

归档 SHA-256（运行时耗时字段可随重跑变化）：

| 文件 | SHA-256 |
|---|---|
| `expanded-cases.json` | `bdcbe69ca2e869d108879485c7424bbe9e135d80553de9d71b2d97c9898eb2f3` |
| `expanded-results.json` | `6efd13c7e614da3f168c042ba482ae21ee1446bbc88d79506ca6a8d966d766d7` |
| `state-cases.json` | `63a3af23ec3e9a337cea9e3edc76cf32b72dc7fb792a303533c4b20d8accadaa` |
| `state-results.json` | `4e74717ffc88780d0aca9a6e68e446d1beec3fa9538052dfddc48c7d2362225e` |
| `rm-cases.json` | `7ffa85cf0ff72b00efe1f543a42fe5221ee7799b4f2d412986faa5f277740ad4` |
| `rm-results.json` | `4d9988387df41ae0fc4540a782588b442401324d572a0379babb493d200c7a22` |

中间试跑曾把 `mstatus.SD` 误设为 0；活动指令会从 FS/VS Dirty 形成 SD=1，已修正并把目标 CSR 纳入观察。归约 `vl=0` 的早返回则保持初始 `mstatus=0x6600`，状态样例据此给出不同预期。状态批次初稿的 v0=`0x4` 无法区分前缀是被 `vstart` 跳过还是被 mask 屏蔽；现改为 v0=`0x5` 并全批重跑。

## 负控：非法舍入字段

使用固定的独立负控 runner：执行阶段版 SHA-256 `e265b79839c1e3b6721342b435d1c974574c7424d47b2edda92246d9f41802b3`（源码快照 `illegal-runner.rs`），译码拒绝版 SHA-256 `db2c6a686328b43219fb5aee5a76db0a38fd5b58d66465de62ebca22d1802eda`（在前者基础上增加 `ILLEGAL` 译码结果及译码后状态差异检查，源码 `decode-negative-runner.rs`）。均与上述候选 `isla-lib` 链接；二进制复制在仓库外证据目录。调用：

```sh
python3 negative.py
"$ILLEGAL_RUNNER" "$IR" "$CONFIG" negative-cases.json negative-results.json
python3 negative_decode.py --output-dir "$OUT_DIR"
"$DECODE_NEGATIVE_RUNNER" "$IR" "$CONFIG" negative-decode-cases.json negative-decode-results.json
python3 verify.py
```

`negative-cases.json` / `negative-results.json` 的 21/21 项在七个典型向量族上分别测试动态 frm5/6/7：真实 OP-V 编码仍正确反译和反编码，`zexecute` 唯一路径返回 `Illegal_Instruction`，目标、完整 `fcsr`、`vstart`、`mstatus` 均与初始状态差异 UNSAT；其中归约例设 `vl=0`，验证非法 frm 仍先于早返回检查。`negative-decode-cases.json` / `negative-decode-results.json` 的 4/4 项把 GNU assembler 产生的 FADD.S、FCVT.S.W 原编码中的 rm 字段改为 5/6；`zext_decode` 两条 SAT 完成路径均返回 `ILLEGAL(raw_word)`，译码后目标、`fcsr`、`mstatus` 差异 UNSAT。由于在译码阶段拒绝，这四项没有反编码或执行路径，不能记作执行阶段非法。

| 负控文件 | SHA-256 |
|---|---|
| `negative-cases.json` | `363210e5cad8c35f3b0902856481e76f4709c56f97ba036c727b582ab06a17a7` |
| `negative-results.json` | `52b08a7ba593cdd859eb82262b013f0bb02ed3816a2b3a52bf95bf2a1c78f590` |
| `negative-decode-cases.json` | `76f6f5f5b6adfa5d1d0f75ad2a673beb991efe18d0f08bb7a880354e4be0497a` |
| `negative-decode-results.json` | `6d306f329dad767cb782d755fc1ceab48529115918d4cdd43b5631b6a8e7c731` |

上述 PASS 只针对列明的有限输入，不能替代任意符号输入证明；BF16、`FVVTYPE`、`VFNUNARY0` 由其他批次验收。
