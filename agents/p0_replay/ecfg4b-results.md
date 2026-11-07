# ecfg4b：同一香山配置下的新模型重放结果（2026-11-07）

**结论：本批范围内通过。新模型使用 ecfg3 完全相同的 Sail 配置重建后，四场景仍为 2836 类、584 形状、122 路径；J1 2836/2836，E3 584/584，E4 587/587。指定 Python 单测 124/124 通过。**

四场景类数、形状数和形状键集合均与 ecfg3 相同。本批未发现模型/Isla 相关结果失败或新的 emu/NEMU 分歧。ecfg4 用了官方发布配置，与 ecfg3 的香山专用配置不同；不能把 ecfg4 的失败认定为新模型缺陷。其原始失败记录保留，开头已追加更正。

本结论限于四场景 `class_cap=1` 种子、每形状代表和下列定向/隔离输入。没有签收类内全部具体值、源码分支全集或设备响应。E4 的普通 DiffTest 不单独证明页异常时 NEMU 的独立判断；独立 NEMU 证据限于四个定向和两个隔离对照，与 ecfg3 口径相同。

## 新 IR、配置和生成来源

| 项目 | ecfg3 | ecfg4b |
| --- | --- | --- |
| IR SHA-256 | `3f16d5e73c3295b594f04f45c7b532d2f7b9c12cead83d64f5d044aec5f0a67b` | `97199a835168371fec2e4d0cae4145e186c4b1f74232e3d5d3dc4017c4b41b91` |
| Sail JSON SHA-256 | `0d3caae71c6e6e71fdfd9a313d9c047222ddd27ff98e5f160b6cc854e7957618` | `0d3caae71c6e6e71fdfd9a313d9c047222ddd27ff98e5f160b6cc854e7957618` |
| CLINT base / size | 33554432 / 0 | 相同 |
| Svrsw60t59b | false | 相同 |
| Svnapot / Svpbmt | true / true | 相同 |
| config-xs.toml SHA-256 | `a6625f05fd680fc621f646e67b87b8ac027d8c79fcb8f2f1e9808a9ff167e0bd` | 相同 |
| isarch SHA-256 | `610df5395219d4202a0dc347d05104737f521562d85dd47a70fbe25d8d31a3db` | `a7d715b1d2ca7cf38b5d0f27f907847bc912b0f8aebcb8a484f85f8a69a7cc89` |
| emu SHA-256 | `871416926352103051fce0efac7bf219602547c0852d5aa24af0c01a35ea85ee` | 相同 |
| NEMU SO SHA-256 | `9188e7dda30709962f0bfbc1dd87cea73d88a18c92c30892f93ed529c22def43` | 相同 |

Sail JSON 直接取只读来源 `../sail-std-gaps/output/ecfg3/final/sail-config.json`；与本树 ecfg3 冻结副本也相同。**逐字节相同，逐项比较 151 项，差异 0。** [完整逐项对照](../../output/ecfg4b/config-comparison.json)保留全部字段。PMA、设备排除区和枚举参数使用原 `config-xs.toml`、`enumeration.toml`、`count.toml`，没有重新设计地图或调整 PMP 参数。

新模型只读使用 `../sail-std-gaps-on-float`，提交 `d79d8b320beec68b596e5e01e69cc353eb78f7a4`，开始时工作树清洁；将 `model/` 复制到本轮输出目录后编译，生成前后来源源码哈希一致。与 ecfg3 冻结模型比较，页表遍历和相关标准扩展检查文件相同；28 个变化文件主要涉及浮点、向量及构建入口，完整清单与差异在 [model-comparison.json](../../output/ecfg4b/model-comparison.json) 和 [model-comparison.diff](../../output/ecfg4b/model-comparison.diff)。

使用 `../runner-memory-enum/output/memory-enum-20261107/toolchain/` 的浮点扩展快照，只读使用工具：

- `Sail 0.20.1 (feat/float-support @ f4f8e4584a70588c66c9e7a6286cc20211618f18)`；launcher SHA `2e89d5f5467195ea0a2fb4b072133a0ee73933db3e8808b8a6518c7ef59ec807`；实际 Sail SHA `373a37c268779bad65381b98c3dc13d56c3db9db90102d28d6f410278b23d45a`。
- Isla 插件 SHA `c4eccb06af9f85820c28bd67556ae0f191361c93cbe1afb334900f9e1f0e22f6`，与 ecfg3 相同。
- Isla 源码只读使用 `../runner-memory-enum/isla` 的 `ae1a33550c6d06ecbf85ac2e2daa85d196bd3e53`；复用 ecfg4 release isarch，使用前校验完整 SHA。
- 运行期动态 Z3 与 ecfg3 相同，SHA `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。

emu 与 NEMU 分别沿用根目录相对路径 `../../difftest-xiangshan/xiangshan/build/emu`、`../../difftest-xiangshan/xiangshan/ready-to-run/riscv64-nemu-interpreter-so`；开始与结束均核对上表完整哈希，未重建或修改。见 [input-verification.json](../../output/ecfg4b/input-verification.json)。

编译参数逐项核对一致，只替换工具副本、配置副本、缓存与输出路径。保留 `-D SYMBOLIC`、三项 strict、`--require-version 0.20.1`、全部 preserve 参数及相同输出名 `rv64d`。生成耗时 **461.479 秒**、退出 0；IR 实际常量也已核对 CLINT=0、Svrsw60t59b=false。精确 argv、源码逐文件哈希与编译工具身份见 [generation.json](../../output/ecfg4b/generation.json)、[alignment-verification.json](../../output/ecfg4b/alignment-verification.json)。本轮没有修改生成后的 IR。

## 四场景对照

表中数量顺序为“类数/形状数/路径数”，场景间形状分别计数。

| 场景 | ecfg3 | ecfg4b | 本轮导出秒 |
| --- | ---: | ---: | ---: |
| sv39-load | 728/136/26 | 728/136/26 | 326.386 |
| sv39-store | 380/120/26 | 380/120/26 | 179.553 |
| sv48-load | 1122/174/35 | 1122/174/35 | 472.918 |
| sv48-store | 606/154/35 | 606/154/35 | 321.710 |
| 合计 | 2836/584/122 | 2836/584/122 | — |

四场景数量差异均为 0；形状键集合新增 0、消失 0。全部 2836 行种子逐条解码，解码错误、地址违规、代表拒绝均为 0。实际 PTE/数据读写逐字节落在 DRAM 并避开 harness/device；AF 目标归 hole。每个守卫类恰有一个种子，文件行数、唯一样本数、类数一致。证据见 [analysis.json](../../output/ecfg4b/analysis.json)、[comparison.json](../../output/ecfg4b/comparison.json)。独立 Sv39 LOAD count 模式仍为 728 类；四场景导出 argv 除绑定文件路径外也逐项相同，见 [scenario-command-comparison.json](../../output/ecfg4b/scenario-command-comparison.json)。

前态、指令、枚举配置与 ecfg3 相同：`x1=0x20000000`，Supervisor，`mstatus=0x0000000a00040000`，`menvcfg=senvcfg=mseccfg=0`，SATP 为 `0x8000000000080200` 或 `0x9000000000080200`，指令 `0x0000b103` 或 `0x0020b023`。四路最多同时运行，各 `-T 32`；单独 count/定向检查用 `-T 64`。每次 isarch `--smt-timeout 5 --timeout 890`，外限 **900 秒**，未加时；本批没有超时。

**原始执行状态没有改为 finished。** 导出四组均为 `partial/errors=5/5/7/7`，新 isarch 原始退出码均为 1。全部 24 项终止都有逐查询证明：原查询 UNSAT；只移除当前 excluded 条件、保留历史断言与读值等式后 SAT；harness 重叠 UNSAT。执行/SMT/终值查询超时、未完成路径和待处理批次数均为 0。按 ecfg3 原验收口径，另列 excluded_filtered_paths=24、其他已核实执行错误=0。没有仅凭相同错误文本或数量豁免错误。证据见 [filtered-proofs.json](../../output/ecfg4b/filtered-proofs.json)。

## 全种子 J1

对全部原始种子运行 `--check-samples`，没有选择可解码子集。每场景完整核对 sample_id 集合、报告分母与绑定的种子文件 SHA。所有样本都满足 `(accepted_paths,consistent_paths,inconsistent_paths)=(1,1,0)`。

| 场景 | 通过/总数 | 原始 errors / 有证明的排除终止 | 秒 |
| --- | ---: | ---: | ---: |
| sv39-load | 728/728 | 5 / 5 | 95.899 |
| sv39-store | 380/380 | 5 / 5 | 46.787 |
| sv48-load | 1122/1122 | 7 / 7 | 317.097 |
| sv48-store | 606/606 | 7 / 7 | 106.551 |
| 合计 | 2836/2836 | 24 / 24 | — |

J1 原始退出码 1、partial 和 errors 保留；逐查询排除证明与零超时/未完成检查全部通过。见 [j1-summary.json](../../output/ecfg4b/j1-summary.json) 及各 `*-j1/filtered-proofs.json`。

本轮观察器只修改产物目录内的副本：[observe.c](../../output/ecfg4b/observe.c)。依据 `nm -S -C`，读地址范围由 `[0x336be0,0x3374f7)` 改为 `[0x2dc970,0x2dd27d)`，写范围由 `[0x337500,0x337bdd)` 改为 `[0x2dd280,0x2dd95d)`；仅更新四个地址常量。ecfg3 原件未改。新观察器 SHA `7e04f36c373e1806784d745dddbf1d9c631486e6c4890921b8f86970f0bad95e`，构建命令、符号与精确差异见 [observer-build.json](../../output/ecfg4b/observer-build.json)、[observer-symbols.txt](../../output/ecfg4b/observer-symbols.txt)、[observer.diff](../../output/ecfg4b/observer.diff)。

## E3、定向与 E4

E3 每形状选最小 sample_id；保持原地址和 PTE，STORE 未知初值与诱饵槽处理沿用 ecfg3。全部代表在同一新锁下再次满足唯一接纳且后态一致。

| 场景 | E3 通过/总数 | 有证明的排除终止 | 秒 |
| --- | ---: | ---: | ---: |
| sv39-load | 136/136 | 5 | 32.287 |
| sv39-store | 120/120 | 5 | 24.753 |
| sv48-load | 174/174 | 7 | 52.598 |
| sv48-store | 154/154 | 7 | 39.916 |
| 合计 | 584/584 | 24 | — |

E3 原始 partial/errors 和退出码 1 同样保留；全部错误均有排除证明。E3 不运行 ELF，PASS 根据成员检查结果，见 [e3-summary.json](../../output/ecfg4b/e3-summary.json)、[e3-filtered-proofs.json](../../output/ecfg4b/e3-filtered-proofs.json)。

四个定向用例（合法 NAPOT、非法 N 编码、非叶 A=1、PBMT=01 且 PBMTE=0）先在新 IR 下检查成员资格，再跑正式 emu 和独立 NEMU；**4/4 通过**。补充非叶 A=1/有效下级表与 A=0 对照，输入只差根 PTE A 位，**2/2 通过**。独立 NEMU 子进程继承真实 emu 初始化后执行，未用 guided_exec。结果见 [directed/results.json](../../output/ecfg4b/directed/results.json)、[nonleaf-isolation/results.json](../../output/ecfg4b/nonleaf-isolation/results.json)。这些输入单列，不混入 E4 分母。六次独立观测还用现有 `observe_run` 复核三方 cause、起止 PC、子进程正常退出和无 guided_exec，见 [independent-nemu-audit.json](../../output/ecfg4b/independent-nemu-audit.json)。

E4 先跑含四场景成功、未对齐超级页、PBMT、非法 N 编码与三个负对照的20条，**20/20** 符合预期后扩全。最终 **587/587** 符合预期：584 个正例 `agree`，三个负对照正确检出。原始桶为 `{'agree': 584, 'xs!=expected': 3}`。emu 最多八路，每例外限120秒；逐例校验 ELF SHA 和精确退出符号，没有只凭退出码或 GOOD 文本签收。正例 timeout、limit、framework-abort、xs!=nemu 和其他失败均为0。

| 负对照 | 原始桶 / 原因 | 退出 PC | 精确符号 | 验收 |
| --- | --- | --- | --- | --- |
| N1 | xs!=expected / unexpected_trap | 0x80000310 | fail_unexpected_trap_trap | PASS |
| N2 | xs!=expected / unexpected_trap | 0x80000310 | fail_unexpected_trap_trap | PASS |
| N3 | xs!=expected / rd | 0x80000328 | fail_rd_trap | PASS |

N1 清叶 V、N2 清叶 A、N3 翻期望 rd 一位；它们保留故意错误期望，单独计数，不算新模型分歧。逐例日志和输入在 `output/ecfg4b/e4/`；[首批20条](../../output/ecfg4b/e4/first20.json)、[E4汇总](../../output/ecfg4b/e4/summary.json)。

## 失败分类与已知分歧规则

| 类别 | 本轮结论 |
| --- | --- |
| 模型/Isla 变化导致的结果失败 | 0；类数/形状/路径数相同，全部种子与代表检查通过 |
| 重放链问题 | 初版驱动只接受退出0，遇新 isarch 的 excluded 退出1而停止；已在本轮副本中按原逐查询证明口径修正。旧观察器地址也已在本轮副本修正。定向脚本还残留不存在的 ecfg4 输入路径，启动前失败；已改回 ecfg3 冻结定向输入 |
| 新发现的 emu/NEMU 分歧 | 本批0；独立 NEMU 判断范围限于上述定向/隔离对照 |
| 预设负对照 | 3，全部正确检出 |
| 尚未分类的实际失败 | 0 |

所有原始退出状态和中间驱动日志保留。`pipeline-initial.py` 和 `pipeline-driver.log` 记录原驱动的退出码假设；[continuation-status.json](../../output/ecfg4b/continuation-status.json) 记录后续各阶段的实际返回值；[post-e3-status.json](../../output/ecfg4b/post-e3-status.json) 记录修正定向输入路径后的执行。允许继续的条件仍为完整产物、无超时/未完成、全部错误可逐查询证明、J1/E3 唯一接纳，不是把退出1改成退出0。

已知表原样复制 ecfg4 的两条精确输入键，加当前 `paging_fuzz.py` 中原有 `xs_leaf_ppn_af_over_permission_pf` 规则，逐项核对相同。没有新增、删除或放宽规则；[known-mismatches.json](../../output/ecfg4b/known-mismatches.json)。本批正例原始分歧为0，因此过滤命中0，不用过滤掩盖 J1、解码或重放基础设施问题。

## 平台锁变化

| 字段 | ecfg3 | ecfg4b |
| --- | --- | --- |
| platform_gen_sha256 | `d2820d0f918373af6ace0cd71c67d6d2a8b413dc65f6b3db0b711c69a293451b` | `3bad2bb24cca00b5f607bc098c730981c21276d3b876f257fc29efed5bd738f7` |
| platform_env_sha256 | `8a6ae7197518cd649d9bae47142125a7ceec4ab7426a6127e8a1d02519722147` | `d87467ec5034326bd8685f2734c74232effdb423b5784902f950810c11a6458a` |

profile 只变四项：`ir.ir_sha256`、`ir.provenance_sha256`、`isla.isarch_sha256`、`env.observer_sha256`。运行侧哈希变化来自观察器副本更新；emu/NEMU、重放实现、解码器等运行侧字段不变。生成侧哈希变化来自新 IR、真实生成记录和新 isarch。配置、地图、枚举设置、前态均不变。完整逐项旧/新值见 [profile-differences.json](../../output/ecfg4b/profile-differences.json)、[profile.lock.json](../../output/ecfg4b/profile.lock.json)。

按 design §13，生成侧身份变化后旧守卫标签和节点键失效。本轮重新导出全部种子、在新锁下做 J1，重新选择形状代表并重跑 E3/E4，没有沿用旧标签或旧 PASS。各 samples.manifest.json 绑定新锁全文和实际文件 SHA。

## 可复现命令与核账

以下从本工作树根目录执行。现有产物拒绝覆盖；复跑应另建空输出目录，并同步脚本中的 BASE/OUT。原始完整 argv、环境、耗时和退出码以 generation.json、各 done.json、case.json、result.json 为准。

```sh
export PYTHONDONTWRITEBYTECODE=1
export GIT_OPTIONAL_LOCKS=0
export TMPDIR="$PWD/output/ecfg4b/tmp"
export XDG_CACHE_HOME="$PWD/output/ecfg4b/cache"
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME"
python3 output/ecfg4b/snapshot.py
python3 output/ecfg4b/generate_ir.py
python3 output/ecfg4b/pipeline.py
# pipeline 顺序：prepare → export_all → 全种子 run_j1 → continue。
# continue：分析/排除证明 → count → E3 → 定向 → E4 → 非叶隔离 → audit。
python3 output/ecfg4b/verify_alignment.py
python3 output/ecfg4b/compare_results.py
cd difftest-xiangshan/tests
PT_DECODE_DIR="$(realpath ../../../isla-enumerate/agents/path_merge_call_support/pt_decode)" \
  python3 -m unittest discover -s .
```

指定 Python 单测 **124/124**，日志见 [unittest.log](../../output/ecfg4b/unittest.log)。实际本轮初版驱动在 J1 完成后因导出退出1停止，随后使用 `resume_when_j1_done.py → continue.py` 继续至 E3；修正定向脚本的冻结输入路径后，由 `post_e3.py` 完成剩余阶段。最终 `pipeline.py` 已把同一证明门接入复现入口，不再依赖退出0。

[final-audit.json](../../output/ecfg4b/final-audit.json) 核对 8541 个已有文件内容未变、输入身份未变、全部 587 个 E4 ELF 哈希一致，J1 分母完整。没有 Git 写操作、Sail/Isla 源码修改或其他工作树写入。只写本轮产物、本文和 ecfg4 结果开头更正；所有日志、缓存、临时文件在本工作树。按用户限定写范围，没有更新全仓 TODO、RESULTS 或 findings。

## 未做与遗留

- 未修改官方发布 IR；本轮新生成的是 ecfg3 配置下的香山专用 IR，二者不能互换结论。
- 未签收浮点/向量指令、类内全部具体值、全部源码分支或设备响应。
- 未扩大 PBMTE=1 行为验证；本批前态固定 PBMTE=0。
- 未对584个 E4 正例逐一追加独立 NEMU 子进程；页异常独立判断限于列定4+2个输入。
- 原始 `partial/errors` 和退出1仍存在；本批按有证明的排除域口径限定通过，没有宣称 isarch 原始执行完全无错误。
- 本轮没有超时，没有触发单步40分钟无进展停止条件。未增加时限、改过滤规则或跳过失败。
