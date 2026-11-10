# Sail V mapping 成员谓词收敛

日期：2026-09-26。状态：局部实现与验证 PASS；真实全模型 decoder 对照待集成新 IR。

## 范围与冻结

本包只改 `sail-riscv/model/extensions/V/vext_arith_insts.sail` 中 `encdec_nreg`、`vext_vs1` 两个 mapping。在 `SYMBOLIC` 下使用 Sail 原生 `val name : A <-> B` 及四个显式函数；原 value 表按原顺序成为部分 match，bits5 成员谓词由 `eq_anything` 与 `strict_or_bool` 组合。`encdec_nreg_backwards_matches` 和 `vext_vs1_forwards_matches` 对各自有限输入类型返回 true。普通分支仍保留原 mapping，两段 `$else` 内容分别与修改前 120/209 字节逐字相同。没有改外层 mapping、指令 guard、执行函数或其他生产文件。

生产文件修改前 SHA-256：`1353b775d0efc4c6b6edb5028d4cd70da0f8e5c8890cddc5b11e89679b0583db`；修改后：`60c1f6f2ec6809bbba39151b44fbeeaa2a5c071d78b0f4ab44d6401ff768d927`。原件、副本、小 Sail IR、runner、日志、哈希和命令清单位于 `isla/target/float-solve-evidence/mapping-matches/20260926-2330/`；`manifest.json` 记录 Sail、插件、Isla 库、V128/E64 配置、fixture 和二进制哈希。源版本为 Sail-RISC-V `f8ce8490981eac6396a31013180a2e718615757d` 与 Isla `f4f8e4584a70588c66c9e7a6286cc20211618f18`，两者已有其他未提交修改，HEAD 不能替代本次源码哈希。

## 验证

从 `sail-riscv/model/` 使用 `--all-modules --strict-var --strict-bitvector --strict-exponentials --require-version 0.20.1 --just-check` 和 V128/E64 JSON，各运行普通与 `-D SYMBOLIC` 全模型类型检查，均退出 0。`SYMBOLIC` 有两条预期部分 match 警告，普通模式没有这些新警告；完整日志为 `typecheck.symbolic.log`、`typecheck.default.log`。`git diff --check` 通过。

`test/symbolic_fp/solve_mapping_matches/build_fixture.py` 从冻结前后源码抽取两个 mapping，生成同一小 Sail IR；旧原生 mapping、新显式函数和相同顺序的外层 32 位 VMVR/VEXT mapping 均在其中。`runner.rs` 用 Isla 真实 IR 执行器在独立 QFAUFBV solver 上运行，每个路径核 SAT，拒绝 ReadReg、WriteReg、ReadMem、WriteMem、Abstract、采样、执行错误或未完成。小 IR 成员函数检查：两个新 bits5 `*_matches` 各为 0 Jump、0 `eq_bits`，分别含 4/6 个 `eq_anything` 与 3/5 个 `strict_or_bool`；原 value 函数仍有分支。

| 检查 | 实跑结果 |
| --- | --- |
| 32 个 bits5 的两个成员谓词，旧新各一 | 128 次逐值真假均与原表一致；每次 1 完成路径 |
| 无效 bits5 直接调用旧新 value 函数 | 108 次均为 `MatchFailure`，没有默认值 |
| 有效值和 roundtrip | 四个 nreg 与六个 enum 的旧新双向值均正确；新函数 10 个双向 roundtrip 正确 |
| 未知 bits5 的成员谓词 | 旧 nreg 5 路、旧 vext 7 路，逐路 SAT；新各 1 路；组合 Bool 差异在旧全部 5/7 路 UNSAT |
| synthetic 32 位 decoder | 整字未知输入，完整 AST/全部 payload 旧新差异在 41 路 UNSAT |
| synthetic 16 位邻近 mapping | 整字未知输入，完整 AST/payload 差异在 2 路 UNSAT |

runner 完整执行退出 0，294 行 PASS，详见 `runner.log`。执行命令从仓库根目录为：

```sh
timeout 300s isla/target/float-solve-evidence/mapping-matches/20260926-2330/runner \
  isla/target/float-solve-evidence/mapping-matches/20260926-2330/fixture.ir
```

这只证明小模型和成员函数；完整真实 decoder 的 R1 域、浮点 VV/VF 指令相关未知 rs1/vs1 对照须由集成新 IR 单独运行。新 IR 生成后应按新哈希重新绑定严格配置，旧 IR PASS 退为历史证据。
