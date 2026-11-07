# ecfg3：新 IR 的 P0 重放结果（2026-11-07）

**结论：步骤1–6完成；四场景2836类/584形状与来源REPORT一致；E3 584/584 PASS；定向用例4/4、补充非叶隔离对照2/2 PASS；E4 587/587 验收PASS；unittest 100/100 PASS。E4正例均与Isla期望一致；NEMU的独立判断限于定向与隔离对照输入。**

| 步骤 | 状态 | PASS / FAIL / 阻塞 |
| --- | --- | --- |
| 输入核对、profile/lock | 完成 | 固定 isarch 与 REPORT SHA 一致，新 IR/配置/受测环境逐次核对 |
| 四场景 class_cap=1 导出 | 完成、限定 PASS | 4 / 0 / 0；2836类、584形状；解码错误/地址违规/代表拒绝均0 |
| E3 每形状最小 sample_id | 完成、PASS | 584 / 0 / 0；另有定向4/4＋隔离2/2，单独计数 |
| 三个指定定向用例＋PBMT对照 | 完成、PASS | 4 / 0 / 0；补充隔离对照2/2；emu 与独立 NEMU 与 Isla 一致，mismatch=0 |
| E4 首批20条→全代表及负对照 | 完成、PASS | 首批20/20；全批587/587；正例584，负对照3 |
| unittest discover | 完成、PASS | 100 / 0 / 0 |

本结论只覆盖当前 class_cap=1 的场景、形状代表和定向/隔离对照输入。Svpbmt 的 NEMU 结论限于本轮 PBMTE=0；PBMTE=1 的01/10行为未测。类内具体值穷举、源码分支全集和设备响应不在本批签收范围。

## 固定输入与实现

本轮直接复制 sail-std-gaps 工作树 output/ecfg3/final 的冻结 IR/配置，使用其 output/ecfg3/bin/isarch；没有生成 IR、修改 Sail 或初始化子模块。来源 REPORT 的只读副本见 [source-REPORT.md](../../output/ecfg3/source-REPORT.md)，逐文件核对见 [input-verification.json](../../output/ecfg3/input-verification.json)。

| 输入 | SHA-256 |
| --- | --- |
| 新 IR | `3f16d5e73c3295b594f04f45c7b532d2f7b9c12cead83d64f5d044aec5f0a67b` |
| config-xs.toml | `a6625f05fd680fc621f646e67b87b8ac027d8c79fcb8f2f1e9808a9ff167e0bd` |
| isarch 固定副本 | `610df5395219d4202a0dc347d05104737f521562d85dd47a70fbe25d8d31a3db` |
| emu | `871416926352103051fce0efac7bf219602547c0852d5aa24af0c01a35ea85ee` |
| NEMU SO | `9188e7dda30709962f0bfbc1dd87cea73d88a18c92c30892f93ed529c22def43` |
| platform_gen_sha256 | `d2820d0f918373af6ace0cd71c67d6d2a8b413dc65f6b3db0b711c69a293451b` |
| platform_env_sha256 | `8a6ae7197518cd649d9bae47142125a7ceec4ab7426a6127e8a1d02519722147` |
| 定向只读观察器 | `adf49655fdffd79f0b9d431792ab2a53ca99ebf76a3816c1f7880ada8f6a30e6` |

profile/lock 沿用 ecfg2 的规范化规则，在导出前生成；样本清单绑定 lock 全文和 samples SHA。IR provenance 直接复制真实生成记录，不把本轮复制冒充重新生成。完整文件身份见 [profile.json](../../output/ecfg3/profile.json)、[profile.lock.json](../../output/ecfg3/profile.lock.json)、[generation.json](../../output/ecfg3/generation.json)。emu/NEMU 哈希与 ecfg2 相同，XiangShan 身份沿用已核实 a13efc8775。

paging_replay.py 增加显式 standard_paging 解码适配：按新模型顺序检查非叶保留位和 N 保留编码，并用64KiB页计算 NAPOT 地址。外部 pt_decode 保持只读；相同形状键字段保留。新 profile 启用标准语义，停止使用旧 R4/R7/R8 拒绝规则，原始 PTE 保留，差异交给重放分类；历史 E0/ecfg2 入口仍沿用原行为。实现文件身份同时绑定到运行侧 profile。

## 四场景、E3与旧 IR 对照

旧 IR 为 `4e9fb66ecb42a7ca8464af56159ac5efdfe3b5a71b6b7e24fbe6cbd8941b91e2`，下表旧列及 ecfg2 的474条 E3、477条 E4结论仅适用该旧版本。新列均在本轮重新生成和验证，不迁用旧PASS。

| 场景 | 旧类/形状 | 新类/形状 | 新路径 | E3 PASS / FAIL | 导出 / E3 秒 |
| --- | ---: | ---: | ---: | ---: | ---: |
| sv39-load | 490/107 | 728/136 | 26 | 136 / 0 | 313.240 / 32.712 |
| sv39-store | 250/95 | 380/120 | 26 | 120 / 0 | 160.628 / 23.429 |
| sv48-load | 788/144 | 1122/174 | 35 | 174 / 0 | 543.350 / 58.043 |
| sv48-store | 416/128 | 606/154 | 35 | 154 / 0 | 303.242 / 47.289 |
| 合计 | 1944/474 | 2836/584 | 122 | 584 / 0 | — |

新 IR 比旧 IR 增加892类、110形状。四路最多同时运行，每路-T32；独立Sv39 LOAD count=728，与samples一致。全部2836条样本严格解码并逐字节核对：PTE/数据访问在DRAM、避开harness/设备，AF目标在hole。机器统计见 [analysis.json](../../output/ecfg3/analysis.json)。

**原始摘要保持partial，不改成finished。** 导出和E3各有errors=5/5/7/7；执行、SMT、终值查询超时与unfinished-paths均0。两阶段各24次终止均逐查询证明：原查询UNSAT；仅去掉当前excluded条件、保留历史断言与读值等式后SAT；harness重叠UNSAT。另列excluded_filtered_paths=24、其他已核实执行错误=0。证据为 [filtered-proofs.json](../../output/ecfg3/filtered-proofs.json)、[e3-filtered-proofs.json](../../output/ecfg3/e3-filtered-proofs.json)；不按错误文本或相同错误数直接豁免。

E3每形状取最小sample_id，不搬地址、不改PTE；STORE未知初值填为后态逐字节反码，PTE旁保留既有诱饵槽。后态仍只包含实际访问足迹。每条均accepted_paths=1、consistent_paths=1、inconsistent_paths=0；输入SHA与同一config/IR/isarch绑定。E3无ELF和退出PC，PASS依据是成员检查计数，见 [e3-summary.json](../../output/ecfg3/e3-summary.json)。

## 定向验证：emu与独立NEMU

以下顺序先完成三个指定用例，再跑PBMT对照。合法NAPOT取本轮形状代表；三条故障用例采用来源已冻结的PTE；非叶位另用下文隔离对照排除下级错误掩盖。四个具体输入先在当前lock下重新check-samples，4/4恰好一条一致路径；另有5次excluded终止证明，见 [directed-membership/manifest.json](../../output/ecfg3/directed-membership/manifest.json)。

| 输入 | Isla cause | emu退出PC | 独立NEMU退出PC | 精确符号（emu / NEMU） | 结论 |
| --- | ---: | --- | --- | --- | --- |
| 合法 NAPOT，L0、PPN[3:0]=1000 | 0 | 0x80000344 | 0x80000344 | good_trap_ins / good_trap_ins | PASS，双方与 Isla 一致 |
| 非法 N 编码，L0、PPN[3:0]=1001 | 13 | 0x80000348 | 0x80000348 | good_trap_ins / good_trap_ins | PASS，双方与 Isla 一致 |
| 非叶根 PTE，A=1 | 13 | 0x800001d8 | 0x800001d8 | good_trap_ins / good_trap_ins | PASS，双方与 Isla 一致 |
| 叶 PBMT=01、PBMTE=0 | 13 | 0x80000348 | 0x80000348 | good_trap_ins / good_trap_ins | PASS，双方与 Isla 一致 |

例如合法NAPOT的原始叶PTE为`0x80000000200420c3`：PPN低4位是1000；VA=0x20000000使实际PA从编码PPN对应的0x80108000替换为0x80100000。emu/NEMU均读出Isla期望值，说明本例执行了地址替换。非法编码`0x80000000200c24c7`、非叶根PTE`0x20080441`（A=1）、PBMT叶`0x20000000200c00c7`均PF13，mtval=0x20000000。emu和NEMU都与Isla一致，没有屏蔽或修改Sail。

DiffTest的页异常强制同步不算独立NEMU证明。本轮先用原SO正式运行，再用只读转发观察器保留真实emu初始化；在payload前fork，子进程继承完整NEMU状态，直接调用difftest_exec执行至ELF登记出口，**不调用guided_exec**。父进程照常转发原API，未改寄存器或guide。各份native-nemu-trace.jsonl记录初态、逐步PC/CSR和精确出口；初始mnstatus=8。含下文补充隔离对照，正式与观测运行共12次emu，独立NEMU子进程6次，均与上述结论一致；这些运行不混入E4分母。结果见 [directed/results.json](../../output/ecfg3/directed/results.json)。

### 非叶位检查的隔离对照

初版非叶A=1只初始化根PTE；即使实现忽略A，也可能因下级V=0而报相同PF。因此初版的GOOD只证明该输入结果一致，不单独证明NEMU检查了A位。本轮补充同一组可成功的下级页表和数据，两例前态与harness初始化写入只差根PTE的A位（0x40），没有修改其他PTE或数据：

| 输入 | Isla cause | emu / 独立NEMU退出PC | 精确符号 | 验收 |
| --- | ---: | --- | --- | --- |
| nonleaf-a-valid-lower | 13 | 0x80000320 / 0x80000320 | good_trap_ins / good_trap_ins | PASS |
| nonleaf-valid-control | 0 | 0x80000308 / 0x80000308 | good_trap_ins / good_trap_ins | PASS |

两例先在当前IR/config/isarch下check-samples，2/2恰好一条一致路径，5次excluded终止另有消融证明。额外的合法下级表只加入前态与harness回读表，故障样本后态仍只含实际读取的根PTE。A=0对照成功；A=1时emu和未经引导的NEMU均PF13，说明本组下级条件不会掩盖非叶位检查。E4的emu池结束后才串行运行补充用例，全程总emu并发不超过8。见 [隔离输入与成员证明](../../output/ecfg3/nonleaf-isolation/manifest.json)、[隔离重放结果](../../output/ecfg3/nonleaf-isolation/results.json)。本补充不计入584个形状或587条E4分母。

## E4：先20条，再全批

首批覆盖四场景成功、未对齐超级页、PBMT非零、非法N编码与N1–N3，20/20符合预期后扩全。全批587条包含584个正例代表及3个负对照，emu并发最多8，每例120秒外限；每例核对ELF哈希和精确出口符号。

原始桶：`{'agree': 584, 'xs!=expected': 3}`。正例agree=584/584；正例其他桶为0。timeout、limit、framework-abort、xs!=nemu均0。

| 负对照 | 原始桶/原因 | 退出PC | 精确符号 | 验收 |
| --- | --- | --- | --- | --- |
| N1 | xs!=expected(unexpected_trap) | 0x80000310 | fail_unexpected_trap_trap | PASS |
| N2 | xs!=expected(unexpected_trap) | 0x80000310 | fail_unexpected_trap_trap | PASS |
| N3 | xs!=expected(rd) | 0x80000328 | fail_rd_trap | PASS |

N1翻叶V，N2清叶A，仍保留成功期望；N3翻期望rd一位。它们是故意错误期望，不计真实模型分歧，也不冒充经过E3的新正例。失败归因：重放缺陷0、配置未对齐0、真实RTL/NEMU与模型分歧0、待查0；预设负对照3，全部正确检出。详见 [failure-attribution.json](../../output/ecfg3/failure-attribution.json)、[首批20条](../../output/ecfg3/e4/first20.json)、[E4汇总](../../output/ecfg3/e4/summary.json)。

## 命令、边界与中间失败

以下从工作树根目录执行。各阶段完整argv、环境、耗时、退出码在done.json/case.json/result.json；禁止覆盖本批运行目录，复现须换输出目录并同步脚本BASE。

```sh
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$PWD/output/ecfg3/tmp"
export XDG_CACHE_HOME="$PWD/output/ecfg3/cache"
python3 output/ecfg3/prepare.py
python3 output/ecfg3/export_all.py
python3 output/ecfg3/run_scenario.py --scenario sv39-load --out output/ecfg3/sv39-load-count --count
python3 output/ecfg3/finish_ecfg_e3.py
python3 output/ecfg3/run_directed.py
python3 output/ecfg3/run_e4.py
python3 output/ecfg3/strengthen_nonleaf.py
python3 output/ecfg3/run_nonleaf_isolation.py
PT_DECODE_DIR="$(realpath ../isla-enumerate/agents/path_merge_call_support/pt_decode)" \
  python3 -m unittest discover -s difftest-xiangshan/tests -v
python3 output/ecfg3/audit.py
```

unittest为100/100 PASS，见 [unittest.log](../../output/ecfg3/unittest.log)。新增回归覆盖合法NAPOT的PPN替换与原PTE保留、非法N编码、非叶U/A/D在下级读取前报PF。最终核账见 [final-audit.json](../../output/ecfg3/final-audit.json)：旧ecfg/ecfg2全部文件清单与SHA不变，来源final/isarch未变，当前ELF、样本和lock逐项一致。所有产物、缓存和临时文件均在本树/data1；没有Git写操作，没有改锁定二进制、emu、NEMU SO或其他工作树。

定向观测首次重新链接同一汇编时，随机临时对象名导致ELF符号表字节不同，SHA断言停止；没有运行该观察ELF，也不计模型失败。已改成复制正式ELF，保留首次日志directed-first-attempt.log和legal-napot-observed-build-attempt目录。另有辅助NEMU直接启动诊断未到出口，保留inspect-native.log；该诊断不计语义结果，最终结论来自真实初始化状态的独立子进程。没有触发15分钟无进展停止条件，也未遇到需要改变设计的新增语义问题。

用户将写范围限定在本议题与重放代码/output；因此不修改范围外的specs/TODOs、docs/RESULTS、agents/findings。本报告及本议题status是本轮现行入口。[ecfg2结果](ecfg2-results.md)已明确标注旧IR适用范围与新入口。

## 先前阻塞记录（历史，已解除）

先前任务要求在本树生成IR，但sail-riscv子模块为空；禁止Git写操作时无法准备独立检出，因此当时停止。当前任务提供另一工作树的冻结final/IR，直接解除该前提，未初始化或修改本树子模块。以下保留原文，原文“阻塞/未测”只描述前次任务。

<details>
<summary>先前阻塞原文</summary>

# E-cfg3 结果（2026-11-07）

**结论：前置检查发现阻塞，尚未修改 Sail、生成 IR 或执行验证。** 本工作树的 `sail-riscv/` 是空目录，子模块未初始化；恢复独立的子模块检出需要 Git 写操作，与本轮“不做 git 写操作”的限制冲突，因此按用户要求停下报告。

| 步骤 | 状态 | 结果 |
| --- | --- | --- |
| 读取方案与版本边界 | 完成 | 已读 sail-gap-design、ecfg2-results、ir-workflow、GIT 及项目入口；执行顺序以用户要求的 Svnapot → Svpbmt → 非叶检查为准，改动保持未提交 |
| 检查本工作树的 Sail 子模块 | 阻塞 | 父仓库 gitlink 是 `4f2ac293654a02db26dac5055be7f93fd6e3141e`，但本地尚无检出 |
| 检查上游参考对象是否存在 | 完成 | 主仓库 Sail 对象库中 `6cc81f28`、`cb8e870e`、`9c3fd5b8` 均为 commit；未移植、未 cherry-pick |
| Sail 最小测试先红后绿 | 阻塞／未测 | 无本地 Sail 源码，未创建测试或运行模拟器 |
| 三阶段 IR 与 Sv39 LOAD 类数／形状数 | 阻塞／未测 | 三份 IR 均未生成，无新哈希和耗时 |
| 最终四场景、ecfg3 lock、E3 | 阻塞／未测 | 未生成输入或 lock |
| NEMU 三个定向用例、E4 | 阻塞／未测 | 无 PASS 或 mismatch 判断，未屏蔽任何样本 |
| unittest | 未测 | 本轮未运行，不迁用旧版本 PASS |

## 阻塞证据与影响

从本工作树根目录执行的只读命令：

```sh
ls -la sail-riscv
git ls-tree HEAD sail-riscv
git submodule status -- sail-riscv
git -C sail-riscv rev-parse --show-toplevel
```

`ls` 仅列出 `.` 和 `..`；`git submodule status` 输出：

```text
-4f2ac293654a02db26dac5055be7f93fd6e3141e sail-riscv
```

前导 `-` 表示未初始化。在空目录里执行 `git -C sail-riscv rev-parse --show-toplevel` 会向上找到 replay-p0 父仓库，所以它报告的 HEAD 不是 Sail HEAD，不能当成子模块版本不符的证据。

主工作区的 `sail-riscv` 虽然有源码且 HEAD 为上述 gitlink，但带有大量已有暂存修改；它在本轮范围之外，没有改动。也没有把旧 `output/ecfg2/model` 冻结副本冒充本工作树的 Sail 子模块。

完整只读输出见 [preflight.json](../../output/ecfg3/preflight.json)。解除阻塞需要先准备 replay-p0 内独立、版本正确的 Sail 子模块检出；这一步涉及 Git 写操作，本轮没有执行。

## 修改摘要与历史证据

- Sail diff：无，未修改任何 Sail 源码、配置或测试，未推进 gitlink，未做 Git 写操作。
- 新增本文及 `output/ecfg3/preflight.json`，并在 [ecfg2-results.md](ecfg2-results.md) 标出旧 IR 适用范围与 ecfg3 待复验状态。
- `output/ecfg`、`output/ecfg2` 保持只读；isarch、emu、NEMU 未运行或修改。
- ecfg2 的历史结果仅适用 IR `4e9fb66ecb42a7ca8464af56159ac5efdfe3b5a71b6b7e24fbe6cbd8941b91e2`，对本次计划中的新模型／IR 均为**待复验**。本轮没有产生新 IR，不能给出类数变化或沿用历史 PASS 作为 ecfg3 结果。

</details>
