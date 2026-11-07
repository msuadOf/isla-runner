> **更正：本轮用错 IR（官方 IR vs 香山对齐 IR），见 [ecfg4b](ecfg4b-results.md)。** ecfg4 使用的官方 IR 与 ecfg3 专用配置不同，原失败不能据此判定为新模型缺陷；下文保留原始测试记录。

# ecfg4：新 IR 的 P0 重放结果（2026-11-07）

**结论：ecfg4 未通过，未完成可与 ecfg3 对照的全套验证。四场景原样命令均触发 900 秒外限，没有最终汇总 JSON。共留下 8005 条种子；J1 逐条检查中 5692 条满足唯一接纳且结果一致，426 条失败。另有 1887 条未取得最终 J1 结果。严格解码另有 6426 条失败。E3、E4 因前置失败未运行，不迁用 ecfg3 的 PASS。**

已确认的新差异是 **IR 内置 CLINT 大小从 0 变为 786432（0xc0000）**，不是只有浮点合并带来的 fcsr。另有同一 IR、同一 isarch 下导出种子与 J1 不一致的问题；尚未定位其源码根因。没有修改配置、IR、源码或已知分歧规则，没有过滤失败以取得 PASS。

## 固定输入与构建

| 输入 | SHA-256 |
| --- | --- |
| 新 IR（复制前及运行后核验） | `1220297d0e7dc202c43bb0cee1d95941c4bc3cf62be6fd141d35dbd5a3ad2059` |
| 正式 release isarch | `a7d715b1d2ca7cf38b5d0f27f907847bc912b0f8aebcb8a484f85f8a69a7cc89` |
| config-xs.toml（与 ecfg3 相同） | `a6625f05fd680fc621f646e67b87b8ac027d8c79fcb8f2f1e9808a9ff167e0bd` |
| emu（原路径、同一文件） | `871416926352103051fce0efac7bf219602547c0852d5aa24af0c01a35ea85ee` |
| NEMU SO（原路径、同一文件） | `9188e7dda30709962f0bfbc1dd87cea73d88a18c92c30892f93ed529c22def43` |
| 动态 Z3 库（与 ecfg3 相同） | `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970` |

isarch 从 `../runner-memory-enum/isla` 的 `ae1a33550c6d06ecbf85ac2e2daa85d196bd3e53` 构建，release、默认 features，`CARGO_TARGET_DIR` 指向本树 `output/ecfg4/target`；正式构建 56.64 秒。IR 来自用户指定文件，未重新生成。原始生成记录直接复制到 `generation.json`，其中模型版本为 `d79d8b32`，生成时的 Isla 记录为 `d7c25993`；生成记录与本轮执行器版本分别保留，不冒充同一次构建。

初次构建误连系统 Z3 4.13.3，四路都在初始化求解器时退出 250，无种子。原因是该库不支持当前默认 tactic 的随机种子参数。原始二进制、日志和锁保留在 [system-z3-attempt/](../../output/ecfg4/system-z3-attempt/)。正式构建只修正链接路径，实际加载 ecfg3 已用的同一份 Z3；没有改源码、SMT 参数、指令或前态。见 [build-record.json](../../output/ecfg4/build-record.json)、[ldd.txt](../../output/ecfg4/ldd.txt)、[input-verification.json](../../output/ecfg4/input-verification.json)。

## 四场景：完整数量未取得，前缀单列

所有场景 `class_cap=1`，最多同时四个 isarch，每路 `-T 32`。前态、PMA/设备排除地图、指令、SATP、SMT 时限、内部 890 秒和外部 900 秒均与 ecfg3 相同。四路均 `returncode=-9`、`timed_out=true`，无 `output/rv64_zLOAD.json` 或 `rv64_zSTORE.json`。因此**完整类数、完整形状数、最终路径数都未知**。

下表只记录外限前写出的完整 JSON 行。每行的 `(path_signature,class_id)` 唯一；“已出现路径”是样本内不同路径标识的数量，不是最终完成路径总数。

| 场景 | ecfg3 完整类/形状/路径 | ecfg4 已导出种子/类标识 | 已出现路径 | 前缀可解码样本/形状 | 解码失败样本 | ecfg3/ecfg4 导出秒 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sv39-load | 728/136/26 | 2055 | 25 | 438/83 | 1617 | 313.240/900.323 |
| sv39-store | 380/120/26 | 2015 | 23 | 336/64 | 1679 | 160.628/900.327 |
| sv48-load | 1122/174/35 | 2048 | 18 | 515/52 | 1533 | 543.350/900.383 |
| sv48-store | 606/154/35 | 1887 | 21 | 290/50 | 1597 | 303.242/900.417 |
| 合计 | 2836/584/122 | 8005 | 87 | 1579/249 | 6426 | — |

这些前缀数量不能替代完整类数，也不能把 249 个可解码形状与旧 584 个全量形状直接作增减比较。可解码前缀没有出现 ecfg3 之外的形状；尚不能判定哪些旧形状消失。完整逐样本统计见 [export-prefix.json](../../output/ecfg4/export-prefix.json)、[comparison.json](../../output/ecfg4/comparison.json)、[prefix-analysis.json](../../output/ecfg4/prefix-analysis.json)。每路的 `running.json/done.json` 记录实际 argv、环境、锁、输入 SHA、耗时和退出状态；日志在 `output/ecfg4/<场景>/stdout.txt`、`stderr.txt`。

### 新增路径与失败的形状层面解释

ecfg3 的 Sail 配置和 IR 都将 CLINT 大小固定为 0；指定新 IR 为 786432。TOML 的 `clint_enabled=false` 只关闭 Isla MemoryBuilder 的 CLINT 零值内存区，不覆盖 Sail 的 `zplat_clint_sizze`。新模型仍可通过 `clint_load/clint_store` 返回异常，绕过本批内存回调上的设备排除条件。配置原文、IR 片段和未修改输入在 [ir-configuration-difference.json](../../output/ecfg4/ir-configuration-difference.json)。

例如 Sv39 LOAD sample 33：根 PTE 为 `0x0000000000800001`，下一层 PTE 地址 `0x02000800` 落在新 CLINT 区间。种子记录 Isla cause=5，但只带根 PTE，没有下一级读取字节；原解码器报告 missing_memory。这种 CLINT 内部访问异常路径不属于 ecfg3 关闭 CLINT 后的原有可重放形状。

全部 169 条 missing_memory 都指向 CLINT 区间。但这**不能解释全部错误**：还有原解码器预测页异常、种子却记录成功或访问异常，以及额外下级读记录等问题。Sv39 STORE sample 34 的根 PTE `0x0800000020040001` 已含不允许的 RSW[60:59]，种子仍多带 `0x80100800` 的下级读取；J1 给出 `(2,0,2)`。它属于“早期页异常输入却带下级访问记录”的失败，不能算作新增合法形状。该输入及 J1 行见 [sample 34](../../output/ecfg4/j1-failure-examples/sv39-store/34/sample.json)。

| 场景 | 缺少所需字节 | 预测结果不符 | 额外内存无法归属 |
| --- | ---: | ---: | ---: |
| sv39-load | 58 | 1489 | 70 |
| sv39-store | 82 | 887 | 710 |
| sv48-load | 5 | 1226 | 302 |
| sv48-store | 24 | 70 | 1503 |
| 合计 | 169 | 3672 | 2585 |

这里的“预测结果不符”是原严格解码器与导出结果的差异；没有硬件重放，不能称为 emu/NEMU 分歧。更多原始输入按类别保存在 `output/ecfg4/decode-examples/<场景>/<sample_id>/`。

## 全种子 J1

对导出文件的全部 8005 行运行 `isarch --check-samples`，没有挑选可解码子集。输入 SHA 与导出清单及当前锁绑定；三份已取得报告的行数和 sample_id 全集逐项核对；Sv48 STORE 没有最终报告。通过条件严格为 `(accepted_paths,consistent_paths,inconsistent_paths)=(1,1,0)`。

| 场景 | 满足条件/全部种子 | 失败数 | 接纳/一致/不一致路径数分布 | 秒 |
| --- | ---: | ---: | --- | ---: |
| sv39-load | 2035/2055 | 20 | `{'(1, 1, 0)': 2035, '(2, 0, 2)': 20}` | 507.376 |
| sv39-store | 1611/2015 | 404 | `{'(1, 1, 0)': 1611, '(2, 0, 2)': 20, '(1, 0, 1)': 384}` | 216.187 |
| sv48-load | 2046/2048 | 2 | `{'(1, 1, 0)': 2046, '(1, 0, 1)': 2}` | 888.342 |
| sv48-store | 未知/1887 | 无最终报告 | `{}` | 900.596 |
| 合计 | 5692/8005 | 426 | — | — |

逐样本失败行、原始完成状态、退出码、排除路径证明和代表输入见 [j1-audit.json](../../output/ecfg4/j1-audit.json)。J1 失败属于新模型/Isla 组合下的导出或复验不一致，具体由哪一处变化造成尚未定位，不能归给 emu 或 NEMU。原始 `partial/completed=false` 保留；本轮没有取得 excluded 逐查询证明，不能豁免原始执行错误，更不能豁免种子不一致或多路径接纳。

三份已完成 J1 报告的原始执行错误为 5/5/7，SMT/执行/模型查询超时及 unfinished-paths 均为 0，但 `badread/` 均为空。ecfg3 的观察器在 `is_read()` 中写死旧 isarch 的函数地址：read=`0x336be0`，write=`0x337500`；新二进制对应地址为 `0x2dc970`、`0x2dd280`。所以不能把相同错误数或错误文本当作旧排除证明。源码保持原样；符号核对见 [新符号](../../output/ecfg4/observer-symbols-new.txt)、[旧符号](../../output/ecfg4/observer-symbols-old.txt)。这项问题影响错误归因的观测，不将种子本身的 J1 失败归因于观察器。

## E3、E4 与失败分类

| 阶段 | ecfg3 | ecfg4 通过/实际运行 | 状态与原因 |
| --- | ---: | ---: | --- |
| E3：形状代表具体化后复验 | 584/584 | 0/0 | 阻塞；完整导出、严格解码和全种子 J1 均未通过 |
| E4：emu+NEMU，正例及 N1–N3 | 587/587 | 0/0 | 阻塞；E3 未通过，未构建或运行 E4 ELF |

0/0 表示没有运行，不表示通过。没有本轮 emu/NEMU cause、退出 PC 或三方差异判定，也没有迁用历史三方观测作为本轮结果。上述两个示例的 Isla cause 分别为 5 和 15；emu/NEMU cause 均未测。

失败按已取得的证据分类（机器摘要见 [failure-attribution.json](../../output/ecfg4/failure-attribution.json)）：

- 构建环境问题：首次错误链接系统 Z3，已修正并保留首次失败。
- 模型/Isla 变化相关：新 IR 的 CLINT 配置差异已确认；四路导出外限失败；426 条已证实的 J1 种子失败。另有 1887 条未取得最终 J1 结果。各项可能重叠，不能合并成一个失败总数；未把全部错误都归到 CLINT。
- 重放辅助链问题：旧观察器写死的函数地址在新二进制上失效，未捕获查询，17 个原始执行错误缺少逐查询排除证明。本轮 E3 具体化与 E4 未运行；严格解码器没有被改成接受新错误。
- 新 emu/NEMU 分歧：未测，不能写成“零分歧”。

已知分歧表原样保留两条精确键，并直接复制当前 `paging_fuzz.py` 的规则型条目 `xs_leaf_ppn_af_over_permission_pf`。生成 [known-mismatches.json](../../output/ecfg4/known-mismatches.json)，逐项核对与原文件/常量相同。没有删种子、改原始结果或添加规则；因 E4 未运行，规则未命中也未实际用于豁免。J1 和严格解码失败不属于该过滤表的处理范围。

## 平台锁与失效规则

| 字段 | ecfg3 | ecfg4 |
| --- | --- | --- |
| platform_gen_sha256 | `d2820d0f918373af6ace0cd71c67d6d2a8b413dc65f6b3db0b711c69a293451b` | `846f42302b7611126ceb1d2878470e07bad6aae1bf21bdae406e2613d61c845c` |
| platform_env_sha256 | `8a6ae7197518cd649d9bae47142125a7ceec4ab7426a6127e8a1d02519722147` | `8a6ae7197518cd649d9bae47142125a7ceec4ab7426a6127e8a1d02519722147` |

profile 只有三项变化：`ir.ir_sha256`、`ir.provenance_sha256`、`isla.isarch_sha256`。配置、枚举参数、内存地图、扩展描述、前态和运行侧字段保持相同。生成记录 SHA 变为 `252c446701ece3048a35293b7d02a014e8fca8b54e1f1215f95434c8a8926892`。IR 自带的 CLINT 差异由 IR 和真实生成记录的哈希绑定，不伪造为旧配置。

按 [design §13](design.md#13-与-fuzzing-的接口)，生成侧哈希变化后旧守卫标签与节点键失效。本轮重新生成并对全部已导出种子做 J1，没有搬用 ecfg3 的标签、形状代表或 PASS。运行侧锁未变化，emu/NEMU 路径和实物哈希均已复核。但哈希相同不表示观察器内的旧函数地址适用于新二进制；该兼容性问题如上单列。见 [profile.json](../../output/ecfg4/profile.json)、[profile.lock.json](../../output/ecfg4/profile.lock.json)、[lock-changes.json](../../output/ecfg4/lock-changes.json)。

## 复现命令与日志

以下是在本工作树根目录执行的正式流程。输出目录拒绝覆盖；重跑须另建空目录并同步脚本的 BASE，不能覆盖本批证据。构建时 Z3 路径取 ecfg3 原二进制实际使用的库。

```sh
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$PWD/output/ecfg4/tmp"
export XDG_CACHE_HOME="$PWD/output/ecfg4/cache"
Z3_LIB_DIR="$(ldd output/ecfg3/bin/isarch | awk '/libz3/ {print $3}' | xargs dirname)"
CARGO_TARGET_DIR="$PWD/output/ecfg4/target" CARGO_NET_OFFLINE=true \
  RUSTFLAGS="-L native=$Z3_LIB_DIR -C link-arg=-Wl,-rpath,$Z3_LIB_DIR" \
  timeout 2400 cargo build --manifest-path ../runner-memory-enum/isla/Cargo.toml \
    --release --locked --bin isarch > output/ecfg4/build.log 2>&1
python3 output/ecfg4/prepare.py > output/ecfg4/prepare.log 2>&1
python3 output/ecfg4/export_all.py > output/ecfg4/export-driver.log 2>&1
# 上条失败后，仅检查已产出的全部种子；不启动 E3/E4。
python3 output/ecfg4/run_j1.py > output/ecfg4/run_j1-driver.log 2>&1
python3 output/ecfg4/compare.py > output/ecfg4/compare-driver.log 2>&1
python3 output/ecfg4/summarize_prefix.py > output/ecfg4/prefix-analysis-driver.log 2>&1
python3 output/ecfg4/collect_configuration_evidence.py
python3 output/ecfg4/finalize_j1.py > output/ecfg4/finalize-j1.log 2>&1
python3 output/ecfg4/audit.py > output/ecfg4/audit-driver.log 2>&1
```

原始四场景 argv 保存在各场景 `done.json`。固定前态为 `x1=0x20000000`、Supervisor、`mstatus=0x0000000a00040000`、`menvcfg=senvcfg=mseccfg=0`；SATP 为 `0x8000000000080200` 或 `0x9000000000080200`，指令编码为 `0x0000b103` 或 `0x0020b023`。每路 `-D sr --smt-timeout 5 -T 32 --timeout 890 --path-merging solve-state --clause=LOAD/STORE`；导出时另带冻结 `enumeration.toml`。完整参数以 `done.json` 为准。

单测按用户指定的测试目录及 PT_DECODE_DIR 运行，**124/124 通过**，0.691 秒。环境设置如上，命令为从根目录进入 `difftest-xiangshan/tests` 后，设置 `PT_DECODE_DIR` 为 `../../../isla-enumerate/agents/path_merge_call_support/pt_decode` 的绝对路径，再执行 `python3 -m unittest discover -s .`。日志为 [unittest.log](../../output/ecfg4/unittest.log)。该结果不抵消导出和 J1 的失败。

身份核对见 [final-audit.json](../../output/ecfg4/final-audit.json)：14878 个已记录文件内容未变；ecfg3 全部历史产物、其他工作树源码和原始 IR 保持不变。新文件只在 `output/ecfg4/` 和本文。未执行 Git 写操作；所有日志、缓存与临时输出在本工作树，读取已有 Z3 库没有向其目录写输出。每个正式 isarch 步骤最长 900 秒，没有触发“40 分钟无进展”的停止条件。

## 未做与遗留

- 未取得四场景完整类数、完整形状数和最终路径数；不把 8005 条导出前缀当作全量。
- 未做独立 count 测量；没有加时重跑导出来取得预期数量。
- 未做 E3 形状代表具体化、E4 首批20条及全批、N1–N3 负对照、定向及独立 NEMU 观测。
- 未适配旧观察器的固定地址，也未重跑以取得排除证明；未把未证明的执行错误记为正常过滤。
- 未定位 J1 不一致的具体源码原因；需要同时核查新 IR 配置变化与新 Isla 的导出/复验行为。没有改 Sail/Isla 源码或 IR，也没有改规则。
- 后续若要得到完整可对照结果，须先处理新 IR 的 CLINT 配置差异，并解决导出前缀的 J1 不一致，再重新执行整条链。本轮保持用户指定哈希和参数，不能自行替换成另一份 IR 或改配置签收。
