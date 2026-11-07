# E-cfg2 / E3 / E4 结果（2026-11-07）

> ecfg3 适用范围标注（2026-11-07）：下列结论仅适用旧 IR `4e9fb66ecb42a7ca8464af56159ac5efdfe3b5a71b6b7e24fbe6cbd8941b91e2`；对拟补 Svnapot、Svpbmt 与非叶保留位检查的新模型／IR 全部**待复验**。历史结果保留。ecfg3 已改用 sail-std-gaps 工作树提供的冻结新 IR `3f16d5e7…`，该阻塞已经解除；本次重新验证及新旧对照见 [ecfg3 结果](ecfg3-results.md)。

**结论：IR 对齐完成、设备地图/PMA 与平台绑定完成；E-cfg 限定 PASS；E3 474/474 PASS；E4 PASS（本批代表范围）。** 正例 474 条，负对照 3 条。E4 验收符合预期 477 条，未符合 0 条。原始运行桶和验收通过分开统计，负对照正确失败也计验收 PASS。

此结论仅覆盖本轮 class_cap=1 的场景与代表，不代表类内具体值穷举、源码分支全集或全部平台设备行为。每场景各取一个形状代表，四场景之间不合并分母。历史 F16/E-cfg 结论仅适用旧 IR `c0e4661a73888c56438a6f76059370667d141a026502d0511291586067bd31c0`，对新 IR 全部**待复验**，旧结果不静默改写。旧目录清单 37 项哈希未变。

## 每步结果与固定输入

1. **完成：Svrsw60t59b 对齐。** XiangShan `MMUConst.scala` 的 pteResLen=7；PteBundle 的 reserved 覆盖 [60:54]，isPf 拒绝非零。Sail JSON 把 `extensions.Svrsw60t59b.supported=true→false`。原配置、精确差异、生成命令和源码逐文件哈希均保留。
2. **完成：设备地图/PMA。** 以旧 TOML 为底，保留 DRAM PMA 与根表分段，移除被六段设备 excluded 覆盖的 mmio_hole。PMA 来自受测 XiangShan HEAD `a13efc8775abb093e23727772a562f0605380685` 的实际初始化表，见 [过程和源码事实](ecfg2-progress.md)。低端六段 mmio 分别为 `[0,0x10000000)`、`[0x10000000,0x20000000)`、`[0x20000000,0x38020000)`、`[0x38020000,0x38021000)`、`[0x38021000,0x39002000)`、`[0x3a000000,0x80000000)`；Flash 与 Debug 的 executable=true。`[0x39002000,0x3a000000)` 与 ≥2^43 不写 PMA。NEMU 完整设备响应、IMSIC/Debug 条件仍待查，设备全部跳过重放，没有猜测设备返回值。
3. **完成：关闭设备专用分派。** 本轮发现 `clint_enabled=false` 只控制 Isla 内容区，不能关闭 Sail 内建 CLINT；当前 isarch 也不以 const_primops 覆盖顶层 let。最终 JSON 再把 `platform.clint.size=786432→0`，重新生成 IR。未改 Sail 源码。最终 IR 对旧 IR 只有两处配置常量差异；第一次生成 513.897 秒，第二次复用 SMT 缓存生成 110.531 秒。无运行超过 15 分钟无进展。
4. **完成：生成时绑定。** `profile.json → profile.lock.json` 在正式导出前生成；实际 IR/isarch/config/emu/NEMU 哈希逐次检查，样本清单包含 lock 全文和 samples SHA-256。生成哈希对 regions/harness/isa/csr_init/ir/isla 的 UTF-8、sort_keys、紧凑 JSON 计算；env 单独计算运行侧哈希。profile 的 isla 段还绑定完整 TOML、枚举配置及四场景前态/指令，避免其他参数脱离生成身份。

| 输入 | SHA-256 |
| --- | --- |
| 最终 IR | `4e9fb66ecb42a7ca8464af56159ac5efdfe3b5a71b6b7e24fbe6cbd8941b91e2` |
| config-xs.toml | `a6625f05fd680fc621f646e67b87b8ac027d8c79fcb8f2f1e9808a9ff167e0bd` |
| isarch（指定 target_edev 的冻结副本） | `610df5395219d4202a0dc347d05104737f521562d85dd47a70fbe25d8d31a3db` |
| emu | `871416926352103051fce0efac7bf219602547c0852d5aa24af0c01a35ea85ee` |
| NEMU SO | `9188e7dda30709962f0bfbc1dd87cea73d88a18c92c30892f93ed529c22def43` |
| platform_gen_sha256 | `e1543ec3a88998208a87e4c55df6e44871711c626964c9f3d1d8fdc804f91e6e` |
| platform_env_sha256 | `a87fdc730c2da1f2a61c6b4585bc8f4c903f71dab9ad4f4b0544406fd33cfccb` |
| Sail JSON | `9bdebd102a10f4249a510b6e108f3bb4666896feb26d77e05770cdb0ab2fad56` |
| IR provenance | `e9d9608f76be26f60f56f09990c2202e0e3f6118430e12a46e6a73757a0075e0` |

冻结模型与旧 IR provenance 的逐文件哈希一致；来源工作树的 HEAD/dirty 状态见 output/ecfg2/source-state.json。它们与二进制构建身份分别记录，不用当前 HEAD 冒充重建 provenance。未修改 Sail-RISC-V 子模块、isla-enumerate、emu/NEMU；未做 Git 写操作。

## E-cfg 与 E3

| 场景 | 路径 | 类/样本 | 形状 | C3失败 / 地址违规 | 已核实 excluded 终止 | E3 PASS / FAIL | 导出秒 |
| --- | ---: | ---: | ---: | --- | ---: | --- | ---: |
| sv39-load | 20 | 490 | 107 | 0 / 0 | 5 | 107 / 0 | 181.188 |
| sv39-store | 20 | 250 | 95 | 0 / 0 | 5 | 95 / 0 | 114.358 |
| sv48-load | 27 | 788 | 144 | 0 / 0 | 7 | 144 / 0 | 274.641 |
| sv48-store | 27 | 416 | 128 | 0 / 0 | 7 | 128 / 0 | 177.032 |

四场景合计 1944 类/样本、474 个形状代表，C3 和地址断言逐条通过。所有实际 PTE/数据读写逐字节位于 DRAM、避开 harness/device；AF 目标全部在 hole。完整直方图、RSW 非零 PF 计数、处理器结果分布、样本流与 E3 输入哈希在各场景 analysis.json。Sv39 LOAD 独立 count 模式为 490 类，与 samples 模式一致。

**原始摘要保留 partial，不改写为 finished。** 四场景 raw errors 为 5/5/7/7，合计 24；每项都有真实 UNSAT 查询。仅移除当前 excluded 条件，保留历史路径和当前读值等式后得到 SAT，逐区域核对可行地址落设备排除区；harness 重叠查询均 UNSAT。另记 excluded_filtered_paths=24、已核实其他执行错误=0；执行/SMT/终值查询超时与未完成路径均为 0。证据为 filtered-proofs.json 与各 badread/query-*-proof.json。该限定签收不把 errors 文本或进程退出码单独当证明。

E3 按形状键稳定排序，每形状取最小 sample_id，不搬地址、不改 PTE。STORE null 初值填后态逐字节反码；每个实际 PTE 旁添加一个不覆盖原输入的诱饵槽。诱饵进入完整前态和 harness 回读表，成员检查的后态仍只保留实际访存足迹。`--check-samples` 使用同一 config/IR/isarch，绑定输入 SHA；每条必须 accepted_paths=1、consistent_paths=1、inconsistent_paths=0。E3 不生成 ELF，没有退出 PC；其 PASS 依据为上述成员检查计数。E3 原始 partial/errors 亦为 5/5/7/7，另有 e3-filtered-proofs.json 对全部 24 次终止逐项证明。构建期拒绝计数 0，不静默丢样本。

code 区未声明仍能完成本批 solve-state；threads/symbolic_addrs 没有自动产生额外样本内存，实际访问已经全量归属核验。此检查不迁给其他执行入口。79 份上游 workaround 的既有坐标诊断在旧/新 IR 下相同；本批只加载无源码 region 的枚举 TOML，不消费这些 vector workaround，未扩大范围修订。

| 场景 | 原样本 SHA-256 | 具体化 E3 输入 SHA-256 | E3 秒 |
| --- | --- | --- | ---: |
| sv39-load | `33b78b48e90afc357d340910fd43f8932662cd5f7d01b9d8f71af6aebf402ea3` | `7763ec73df05f27c7745feb8cd06627205af4e5abbd998f14939895fcaa448ff` | 18.407 |
| sv39-store | `aa0e62b45a65ee639243de020521b360f406ed08a0c85c95c0bd2a8edcbd778d` | `88f3767a1edaa1bddc92ca27ae9893cb84390ce392f910117c499a3ffedf6ac4` | 16.113 |
| sv48-load | `8cd14efc5fe680d301fcc392aa3b7ccba6aee8a3b8de433b063ce5686b123531` | `22e7215ec3832e92802b67fc7a70723b24376d8b9a67bd0fb468260948611345` | 35.446 |
| sv48-store | `9b1aa275c7616e6f60e59c82c8d0261d3f5765aa15982fd7e345e45f29be36e7` | `e89e816502c642cece380b0ed18590d1c904f4a4530be70bf1b61b857cb025b3` | 27.485 |

## E4：退出 PC 判定

先跑 20 条（含四场景成功例、未对齐超级页、PBMT 非零、N=1 非 NAPOT、N1–N3）。首批符合预期 20/20；随后扩展到全部代表和负对照。 emu 最多 8 路，每例外限 120 秒，完整日志保留。每次运行前后核对 ELF 哈希，GOOD 还须精确匹配 good_trap_ins；退出码 0 不单独判 PASS。

原始桶计数：`{'agree': 474, 'xs!=expected': 3}`。正例 agree 474/474；正例其他桶 `{}`。timeout/limit/other-failure 分别为 0/0/0。

| 负对照 | 实际桶/原因 | 退出 PC | 精确符号 | 验收 |
| --- | --- | --- | --- | --- |
| N1 | xs!=expected(unexpected_trap) | 0x80000310 | fail_unexpected_trap_trap | PASS |
| N2 | xs!=expected(unexpected_trap) | 0x80000310 | fail_unexpected_trap_trap | PASS |
| N3 | xs!=expected(rd) | 0x80000328 | fail_rd_trap | PASS |

N1 翻叶 V、N2 清叶 A，仍保留成功期望；N3 把期望 rd 翻一位。负对照为故意错误期望，不计实际 RTL 与模型分歧。它们不冒充经过 E3 的新正例；其作用是验证 C2 与归类器能检出预设错误。

未发现本批正例的 RTL 与模型分歧。

E3 无失败样本；E4 的典型失败为上表三个预设负对照。

各用例 program.S/ELF、objdump、符号表、case.json、difftest.log、result.json 均在 output/ecfg2/e4/。case.json 记录两个平台哈希、lock、来源样本、pt_decode 哈希和 ELF SHA-256。

## 复现命令与证据

机器账本：[平台描述](../../output/ecfg2/profile.json)、[平台 lock](../../output/ecfg2/profile.lock.json)、[IR 来源](../../output/ecfg2/generation.json)、[E-cfg 统计](../../output/ecfg2/analysis.json)、[E-cfg 签收](../../output/ecfg2/ecfg-acceptance.json)、[E3 汇总](../../output/ecfg2/e3-summary.json)、[E4 汇总](../../output/ecfg2/e4/summary.json)、[最终核账](../../output/ecfg2/final-audit.json)。

以下从仓库根目录执行。脚本拒绝覆盖已有 IR、lock 或运行目录，复现请使用新的输出目录并同步脚本 BASE/OUT；不要覆盖本轮证据。实际完整 argv、环境、耗时与退出码在 generation.json、各 done.json；每个阶段有独立日志。

```sh
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$PWD/output/ecfg2/tmp"
export XDG_CACHE_HOME="$PWD/output/ecfg2/cache"
# 生成时的真实命令和工具路径见 generation.json；只改两项平台 JSON。
python3 output/ecfg2/generate_ir.py
python3 output/ecfg2/prepare_platform.py
python3 output/ecfg2/freeze_lock.py
# 四场景最多四路，每路 -T32；以 Sv39 LOAD 为例。
python3 output/ecfg2/run_scenario.py --scenario sv39-load --out output/ecfg2/sv39-load
python3 output/ecfg2/run_scenario.py --scenario sv39-load --out output/ecfg2/sv39-load-count --count
python3 output/ecfg2/analyze.py
python3 output/ecfg2/verify_filtered.py
python3 output/ecfg2/close_ecfg.py
python3 output/ecfg2/run_scenario.py --scenario sv39-load \
  --out output/ecfg2/sv39-load-e3 --check output/ecfg2/sv39-load/e3-input.jsonl
# 其余三场景使用各自目录；全组 E3 通过后：
python3 output/ecfg2/run_e4.py
```

单测使用用户指定的外部 PT_DECODE_DIR（从工作树根目录可用 ../isla-enumerate/agents/path_merge_call_support/pt_decode 的绝对展开路径），`python3 -m unittest discover -s difftest-xiangshan/tests -v` 为 **98/98 PASS**。测试、所有编译/运行临时目录和缓存均在 /data1。

中间失败和取消尝试完整保留，见 [实施记录](ecfg2-progress.md)；不把失败前缀计作完成目录。本轮按用户写范围只新增本议题文档，不修改旧结果、全仓 TODO 或其他议题状态。现行入口为本报告及 output/ecfg2 的机器账本。
