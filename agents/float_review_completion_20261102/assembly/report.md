# 三种指令表示：模块完成，等待主 agent 接线与 CLI 验证

## 改动

新增 `isla/src/isarch/representation.rs`，保留助记符，按最终已核对编码同时构造精确位串、定宽十六进制、小端字节和 `.insn`。不修改指令模型、执行结果、可达路径或原有 `test-ins` / `test-ins-encdec` 字段。

建议新增 JSON 字段：

```json
"instruction-representations": {
  "mnemonic": "vfwmaccbf16.vf v1, f14, v1",
  "encoding": {
    "status": "complete",
    "bit-length": 32,
    "bits": "11101110000101110101000011010111",
    "hex": "0xee1750d7",
    "bytes-le": "d75017ee"
  },
  "insn": {"status": "complete", "text": ".insn 4, 0xee1750d7"}
}
```

FmtVal 的 BitVal 位/掩码无公共读取接口。因此复用已有定宽显示格式，而非修改 isla-lib 或重复具体化；支持下划线、16/32位，保持前导零。掩码值、空值或不支持的长度明确返回 `incomplete`，不生成假编码；不合法的内部格式或越界值直接 panic，绝不截断。没有调用外部汇编器的生产路径，因而没有添加未经验证的“工具接受”状态。

`wiring.patch` 是供主 agent 应用的最小接线：mod 声明、AssemGenJsonItem 增量字段及构造调用。serde default 允许旧 JSON 缺少新增字段。已运行 `git -C isla apply --check ../agents/float_review_completion_20261102/assembly/wiring.patch` 通过；没有直接修改共享 exec.rs/mod.rs。

## 新测试

TDD：先写五项断言，首次编译因模块不存在失败（red.log）；模块实现后五项通过（green.log）。边界包括压缩16位、非法BF16原助记符保留、未具体化掩码、缺失/不支持位宽、越界禁止截断。测试在新模块内部，正式 cargo test 接线后会收录。

独立测试命令（借用已有依赖 rlib，不编译共享 target）：

```sh
rustc --edition=2021 --test agents/float_review_completion_20261102/assembly/representation_tests.rs -L dependency=isla/target/debug/deps --extern serde_json=isla/target/debug/deps/libserde_json-3d448c38313c35eb.rlib -o agents/float_review_completion_20261102/assembly/representation-tests
agents/float_review_completion_20261102/assembly/representation-tests
rustfmt --edition 2021 --check isla/src/isarch/representation.rs
```

实际运行新模块生成 fixtures.jsonl，然后运行：

```sh
rustc --edition=2021 agents/float_review_completion_20261102/assembly/representation_fixture.rs -L dependency=isla/target/debug/deps --extern serde_json=isla/target/debug/deps/libserde_json-3d448c38313c35eb.rlib -o agents/float_review_completion_20261102/assembly/representation-fixture
agents/float_review_completion_20261102/assembly/representation-fixture > agents/float_review_completion_20261102/assembly/fixtures.jsonl
/usr/bin/python3 agents/float_review_completion_20261102/assembly/check_toolchains.py
```

36/36 项符合预期：6样例 × GCC/Clang × 原助记符/精确.insn/由精确位串生成的.byte。三条非法BF16原助记符在Clang仍被拒绝，GCC接受；两种精确表示在两工具均接受，字节均与模块输出一致。合法BF16 `vfwmaccbf16.vf v31, f0, v10, v0.t`、c.nop、addi也均匹配。

工具版本 GCC 14.2.0+19、Clang 22.1.8；逐项命令、stderr、对象字节、源码 SHA256 见 toolchain-results.json。初次测试误用 .option norvc 导致压缩例被拒绝，已改为16位用rvc、32位用norvc；初次失败证据保留 toolchain-initial-results.json，不作为代码失败隐藏。

## 限制与交付边界

这是模块和新表示的定向验证，不是生产 JSON 端到端验收、全指令双工具链回归或硬件重放。必须由主 agent 接线、cargo 检查及 CLI 生成，并确认非法模型条目仍在后才能关闭该 review 项。`.insn` 接受与机器编码字节一致，不会将 Illegal_Instruction 变成合法退休。

## 端到端脚本准备

`run_e2e.py` 使用官方新库、默认策略，单次路径/SMT预算均显式7200秒，整个Clause外限7200秒。输出目录必须新建，保留所有旧证据。真实模式调用方式：

```sh
/usr/bin/python3 agents/float_review_completion_20261102/assembly/run_e2e.py --binary isla/target/release/isarch --output production-e2e
```

等待主 agent 通知新 binary，尚未运行真实新CLI。已用 `--offline --output offline-simulation` 将旧 JSON 经新模块补字段后，仅核对表示和工具链；BF16-vl0/vl1各6条（其中2条Illegal），C_ADDI4SPN 1条，共78项工具检查符合预期，包括4项预期Clang助记符拒绝。此结果明确标记 `simulation: true`，不声称新程序生成或ExecuteAs修复通过。模拟仅证明检查脚本和表示函数能处理旧审阅样例。

## 新 CLI 端到端完成（2026-11-02）

主 agent 接线并编译后，将实际 Release 复制为本目录 `isarch-tested` 冻结。SHA256 `ec4e1c436ec32f8b55b2c1d0e1def0f3c44b96c3113b390dcbb9fe9ed5f137fe`；本 binary 包含三表示与ExecuteAs续执行，但不含随后单独追加的SMT统计快照补丁。IR SHA256 `10bea88ca9bc2938cc9f8d303fc3f851c0a256a31ef894bd84d5c7e2e8142bbf`。

真实运行 `run_e2e.py --binary agents/float_review_completion_20261102/assembly/isarch-tested --output production-e2e`：

| Clause配置 | 墙钟秒 | JSON数 | Illegal数 |
| --- | ---: | ---: | ---: |
| VFWMACCBF16_VF vl0 | 31.77 | 6 | 2 |
| VFWMACCBF16_VF vl1 | 11.80 | 6 | 2 |
| C_ADDI4SPN | 3.68 | 1 | 0 |

三批均退出0、finished、errors/执行超时/SMT超时/未完成/最终模型超时均0。所有13条JSON三表示字段与原机器编码一致；GCC/Clang各验证助记符、精确.insn和精确.byte，共78项符合预期。四条非法BF16助记符仍被Clang拒绝，其精确.insn/.byte在两工具均通过且字节一致；非法模型记录和原助记符均保留。

压缩例仍输出 `c.addi4spn x8, x2, 0x3fc`、原编码 `16'h1fe0`、精确 `.insn 2, 0x1fe0`，最终返回 `Retire_Success(())`，x8后态为 `64'h0000_0000_0000_0403`（7+1020=1027），不再是未执行payload时的7。

[逐批摘要](production-e2e/summary.json)，各批run.json记录精确命令、版本哈希、墙钟和退出；toolchains/results.json记录全部工具调用与字节。此为指定三批定向端到端PASS，不代替全77/全压缩指令或硬件验收。
