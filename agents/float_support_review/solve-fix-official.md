# 浮点 77 项官方批：冻结与运行记录

本记录属于已授权的浮点审计修复。77 项固定名单沿用 [既有清单](tools/official_float/targets77.txt)，官方入口是 Isla `scripts/run.mk` 的 `solve-fd-nonmem`。旧 d012 批次的 40 自然退出、36 外限、1 SMT 失败仅是历史；本轮须在最终源码、IR、严格配置和运行器冻结后新建证据。10 个浮点访存项及两个 RV32 限定构造函数不在本组。

## 编排与验收门槛

辅助脚本为 [official_batch.py](tools/solve_fix_official/official_batch.py)。调用者先对冻结主 `isla/` 执行 `preflight`，核对 `FD_NONMEM_RV64` 与固定名单顺序及所有目标专用配置。活跃配置若有 `case_quota`、`max_forks_per_branch`、region fork 限制或 `on_limit_reached`，记录并阻止正式启动。准备时最初预检发现 `VFMERGE`、`VFMV` 加载旧全树/region 限制；IR 集成负责人随后从 `run.mk` 去掉这两项的加载，保留原配置作历史证据。当前主树再预检为 77/77 名单相同、活跃目标无这些限制；最终冻结后仍须重新核对。本编排不修改生产文件。

`snapshot` 从主 Isla 复制实际 Cargo 工作区源码到全新独立运行目录，不复制 `.worktrees`、`target`、`output`；快照前后逐文件哈希必须一致。正式 IR/79 配置从同一外部冻结候选以 `--ir`、`--workarounds` 装入 stage，脚本核生成记录 exit、IR/配置 SHA、候选迁移报告 PASS、候选FD基础配置和逐文件模型源清单，并在证据中复制候选模型与生成记录。79 份文件中，77 份仍服务现行目标并绑定新 IR；`vfmerge.toml`、`vfmv.toml` 是不再被 `run.mk` 加载的历史限制，保留主树原字节与旧 IR/region，不把纯选择优化后的代码伪装成旧采样区域。正式运行目录选用 Git 忽略且磁盘空间充足的 `isla/target/float-solve-evidence/<批次>`，脚本只允许该专属子目录作为仓库内运行位置，并拒绝覆盖非空目录。manifest 记录 stage 中全部复制文件、Sail-RISC-V model `.sail` 文件、两个 HEAD、IR、FD 配置、每项 workaround、固定名单和构建命令。正式运行从 stage 构建含 `itrace` 与 `smt-thread-interrupt` feature 的 release `isarch`，再以同一 stage 执行：

```sh
make -o build-isarch -k -j4 solve-fd-nonmem ITRACE=1 Z3_TIMEOUT_IMPL=thread_interrupt \
  IR_FILE=./rv64d.ir ISA_CONFIG=./configs/riscv64_difftest_fd.toml THREADS=2 \
  OUTER_TIMEOUT=300s SOLVE_TIMEOUT=270s SMT_TIMEOUT=30s TASTIC=qfaufbv \
  TIMEOUT_SMT_OUTPUT=file TIMEOUT_SMT_DIR=output/timeout-smt
```

`-o build-isarch` 仅跳过已经单独成功构建的前置目标；`-k` 使单项目标失败后仍尝试全部 77 项。仍由原 `solve-%` recipe 选择目标专用 workaround、输出路径和外层 timeout。脚本清理可能覆盖 make 行为的环境变量，显式绑定 IR 与 FD 配置，并用真实 `make -n` 检查 77 条有效 CLI。`-j4` 限制最多四项目标并行，各目标 `-T 2`。上述 300/270/30 秒属于本轮批准预算，不与旧 90/80/15 秒结果比较性能。正式批需真实运行所有原 make 目标，不以代表样例或截断输出代替全组。

`audit` 保存每项 make/底层退出、墙上时间、原始日志、JSON、itrace 和运行时 branch catalog 的原文与规范化哈希、规范化 state-domain 哈希、终态计数、提示和异常。每条 `gen` 对应唯一 `(z-clause, case-id)` terminal，保留 complete pre/post、真实编码与译码；日志及 trace 的终态、source edge 必须与 catalog 双向守恒。自然退出 0、summary complete、suppressed=0、无 sampled/error/witness-error、至少一个合法 Retire、gen 与 emitted 对齐且 trace 有运行时 catalog，才列为单项无已知运行器错误。`non-encodable`、`decode-rejected`、`illegal` 分开计；不可编码不算合法覆盖。全组无已知错误后，按独立 replay 消费端 schema 生成运行目录根的 `replay-manifest.json`，将全部 `gen` 交独立 replay。数值与 flags 正确性还需独立 oracle，branch 源码覆盖还需有明确分母，不从自然退出自动推断。

## 本轮准备验证

- `python3 -m unittest discover -s agents/float_support_review/tools/solve_fix_official -p 'test_*.py' -v`：当前 9/9 PASS，覆盖固定集合、旧采样配置注入后的拦截、真实 make dry-run 的 77 CLI、真实 P1 FLI JSON 的 z-clause、终态/trace 守恒、replay manifest 消费端 schema、实际初始化声明、被 Git 忽略的独立路径，以及外部候选IR/77活跃+2归档配置和模型字节的完整快照；每轮脚本修改后复跑。
- 移除旧加载前，对主树执行 `make -n -o build-isarch -j4 solve-fd-nonmem ...`：打印 77 条唯一 `solve-state --clause` 命令，77 条均使用 `riscv64_difftest_fd.toml`，当时 `VFMV` 的旧 workaround 被带入。移除加载后的当前预检为 77 项且活跃限制为零；正式冻结后须再次 dry-run 并记录每项实际命令。以上均是 recipe 静态核对，不是正式运行。
- 本条准备记录写于 c5 快照启动前。2026-09-26 20:47–21:42 的 c5 批次已经结束；逐项诊断和现行边界见下文。旧宽位 FmtVal 输出错误使该批不能转为语义 PASS。
- replay 初始化清单由快照时核对 FD defaults、IR 的 `zPC/zx0` 无 setup、Sail `zero_reg` 与 Isla `init.rs` 后自动生成，并由源码/IR 哈希绑定：物理 `x0`/`PC` 未初始化，架构 `x0=zero_reg`；重放对未导出的 `PC` 读取须失败。物理 `PC=0` 不是可填默认值。该结构已通过独立消费端 `validate_manifest` 的适配测试，最终仍按冻结 IR 再核。

## P1 三代表中间诊断（非正式批）

按性能负责人选定 `F_UN_RM_FF_TYPE_S`、`VFUNARY1`、`FVVMATYPE`。外部 P1 IR SHA-256 为 `f5141217f2695fb53a0584c1bc7dfa059eac15df51c07ae3f02307099e4b4a61`；79 份候选严格配置均绑定该哈希。以当前主运行器另建仓库外 stage 并重建 release binary，SHA-256 `befd74a94a104799e4f04660f9fcde905de38e0a172ccc45ac846b65ad0d360a`。构建日志显示 `--features itrace --features smt-thread-interrupt`；三目标 dry-run 均无额外 `--execution-limits-config`。该混合快照以 P1 模型/IR 和稍后的运行器版本诊断热点，不是最终同批源码验收。

三目标均用 90/80/15 秒、每项 2 线程、最多 3 项并发运行，底层 exit 124、无最终 JSON。`F_UN_RM_FF_TYPE_S` 打印 16 条终态，其中 Retire 2、Illegal 3、不可编码 1、error 10；10 条 error 均为 `fdext_regs.sail:545:16-545:24` 的 CheckSatAssuming 到达 15 秒 SMT 限额。`VFUNARY1` 打印 152 条（Illegal 149、不可编码 3），`FVVMATYPE` 130 条（Illegal 127、不可编码 3），二者无显式执行错误，但外限前均未观察到 Retire。旧全量 itrace 分别约 37.9、723.2、612.3 MB，运行负载与轨迹开销影响时间，不据此比较 P1 运算性能。仓库外原始证据保存在诊断目录 `evidence/` 和 `stage/output/`；摘要已交性能负责人。最终正式批须在紧凑 itrace 版本冻结后重建。

## P2 两向量中间诊断（非正式批）

标量 `F_UN_RM_FF_TYPE_S` 由 FD 负责人独立复跑，编排只跑 `VFUNARY1` 和 `FVVMATYPE`。P2 IR SHA-256 `d86655a415441ad17533742b9d0ee726b43b64acaf2c0fc0754d27979c7859a9`；本编排 compact itrace release binary SHA-256 `38fc91a670b79f166a204053273b729202b9c35015a07872ffc192b84311d585`，构建日志确认 `itrace` 与 `smt-thread-interrupt` feature。P2 基础 FD 配置与生成 manifest 已复制并按 SHA 固定；79 份严格配置此时尚有 6 处旧向量坐标待修，因此本诊断只使用没有 active workaround 的两目标，实际 dry-run 均未带 `--execution-limits-config`。stage 存于 Git 忽略的 `isla/target/float-solve-evidence/p2-vector-diagnostic-20260926/`。

两目标均用 90/80/15 秒、各 2 线程、最多 2 项并发，底层 exit 124、无最终 JSON。`VFUNARY1` 打印 164 条终态（Illegal 161、不可编码 3），compact trace 184.3 MB；`FVVMATYPE` 打印 134 条（Illegal 131、不可编码 3），trace 151.6 MB。两日志无显式执行错误，外限前均未观察到 Retire。这是两项未完成证据，不能把局部 Illegal 计为全域结论。原始日志、轨迹、manifest 与摘要在该 stage，已交性能负责人审查；不转记最终77项验收。

FD 负责人另以同一 P2 IR、90/80/15 秒、2 线程和 compact itrace 跑 `F_UN_RM_FF_TYPE_S`，自然 exit 0、JSON complete=true；79 终态为 Retire 60、Illegal 18、不可编码 1，emitted 78、suppressed 0，SMT timeout 与执行错误均为 0。该独立 stage 的运行器二进制与本编排两向量的二进制不同，证据分别绑定，不能合称一批正式77项。90秒向量未完成不预断最终300秒预算结果。

## 正式操作顺序

```sh
python3 agents/float_support_review/tools/solve_fix_official/official_batch.py preflight isla
python3 agents/float_support_review/tools/solve_fix_official/official_batch.py snapshot isla sail-riscv isla/target/float-solve-evidence/<全新批次名> \
  --ir <冻结候选>/ir/rv64d_final.ir --workarounds <冻结候选>/workarounds-candidate
python3 agents/float_support_review/tools/solve_fix_official/official_batch.py run <同一目录>
python3 agents/float_support_review/tools/solve_fix_official/official_batch.py audit <同一目录>
```

运行目录的 `evidence/manifest.json`、`config-preflight.json`、`build.log`、`make.log`、`official-audit.json`、根 `replay-manifest.json` 与 `stage/output/` 是交接给全量 replay 的证据。任何源码、IR、配置、feature 或运行器改动均须新建批次，不将旧 PASS 续用。

## c5 首批完成后的诊断审计（不能转为语义 PASS）

运行目录为 `isla/target/float-solve-evidence/official-c5cbb-20260926-204047/`；原始证据未删除或改写。快照 IR SHA-256 为 `c5cbb0bbdaa9369b669aa7330531bfb1a0cf1ef7d905b071f14f510d10c7385c`，快照 `primop.rs` 为 `6c6d5a4248d9874405bbc48f850f5c32b77e60f0762212244e1a173fa13f4a20`，`ir.rs` 为 `d26e7923712ccf214b7b7dc47d817b66a49e70d11c8c7fdcb9ef171c832c2562`，release `isarch` 为 `4bfaf48080ad1fb8a1344d51f8a0dcb75cdf3a5f29e7a9a6d51ed9ac24c183db`。`evidence/manifest.json` 记录完整源文件、模型、配置和二进制哈希，`make-dryrun.txt` 保存77条实际 CLI。构建启用 `itrace` 和 `smt-thread-interrupt`；原 make 命令使用 `-k -j4 solve-fd-nonmem`、每目标2线程、300/270/30秒、`qfaufbv`，没有限制符号域或抽样。`batch.finished` 与 `make.rc` 均存在，后台已无该批进程；make 最终 exit 2。

诊断命令：

```sh
python3 agents/float_support_review/tools/solve_fix_official/official_batch.py diagnostic-audit isla/target/float-solve-evidence/official-c5cbb-20260926-204047
```

逐项机器可读账本为运行目录 `evidence/official-diagnostic-audit.json`，含77项目标的 make 状态、底层 exit、墙上时间、日志 SHA、终态分布、异常计数与首例、JSON 摘要和轨迹路径/大小。41项 `intime` / 底层 exit 0，36项 `timeout` / 底层 exit 124；没有 exit 1、缺状态、缺日志或缺逐项起止时间。41份最终 JSON 全部 `complete=true`、`suppressed=0`，其 summary、terminal、gen 数量与日志终态计数相符；36个外限目标均没有最终 JSON，不能称完成。77项均保存 itrace，合计 101,441,531,997 字节。流式诊断只逐行核对日志，不把大型残缺 trace 当作完整账本，也不生成 replay manifest。

日志局部终态合计 Retire 40,434、Illegal 60,961、non-encodable 214。其中自然退出41项分别为 Retire 11,580、Illegal 5,574、non-encodable 86；超时36项分别为 Retire 28,854、Illegal 55,387、non-encodable 128。超时项中15项出现过 Retire，另21项尚未观察到 Retire；这些都是终止前的局部路径数，不能推断全域覆盖。六个 `FMAXM_*`/`FMINM_*` 均外限但每项已打印约2,125–2,614条 Retire；`VFMV` 外限且仅15条 Retire。完整名单、各目标三类终态和时长见机器账本。

日志未匹配执行错误、panic、`Z3Unknown` 或 SMT timeout 模式；这仅说明已打印文本中未发现该类错误。独审已复现此快照运行器的 `FmtVal::BitVal::from_bv` 宽于64位具体值输出错误，因此即使41项目标自然退出，输出状态和数值不能据此判为正确；整批标记为**诊断，语义验收未通过**。新运行时修复、纯比较优化及候选 IR/79配置重新冻结后，必须新建 stage 重跑原77项目标，并对完整 JSON/itrace 执行严格 `audit` 与独立 replay/oracle。旧批原始证据仅作故障与性能定位。

本轮工具验证：`python3 -m unittest discover -s agents/float_support_review/tools/solve_fix_official -p 'test_*.py' -v`，9/9通过；上述 `diagnostic-audit` 完成并生成77行账本，41份 JSON 与日志计数一致。尚未对95GB旧批轨迹逐条做完整 catalog/terminal 守恒审计。原 `audit` 的整文件读取路径已改为流式扫描，并用66MB真实 FLI_D 轨迹核对原始 catalog SHA、97终态、326,998条 edge 均一致；这项工具修正不更改旧批或1dcc运行 stage 的源码。

## 1dcc 同版77项基线启动（2026-09-27）

新候选为 `isla-float-solve-fix-final-20260926.GThshy`；IR SHA-256 `1dcc80812b8beaba49abaebf605e8090c2796b5930aefa36635b478c5f2b8180`，候选 `source-manifest.json` SHA-256 `28fb65ee77e2c5e5c629c50b239a2e009337b47936b2fdbb897bf9c11bca055e`。主 Isla 与候选 manifest 中510个工作区文件逐项 SHA-256 相同；主树另有5份候选未列出的 `rustfmt.toml`，正式 stage 也如实复制并记录在源码清单。运行时 `primop.rs`、`fmtval.rs`、`smt.rs`、`ir.rs` 分别为 `6c6d5a42…`、`43806138…`、`3ce7310d…`、`d26e7923…`。候选79配置迁移报告 PASS：77活跃/2归档、130/2 region、22锚点，预检 issues 为空。

独立运行目录为 `isla/target/float-solve-evidence/official-1dcc-20260927-002314/`。冻结消费入口是该目录的 `evidence/manifest.json`、`evidence/candidate/source-manifest.json`、`evidence/candidate/generation.json`、`evidence/candidate/workarounds-report.json`、`evidence/initialization.json` 与 `stage/rv64d.ir`；全部原始输出随后落在 `stage/output/`。候选生成器使用按 IR 名命名的 `ir/generation-rv64d_solve_fix_final.json`，批次脚本已按这一实际文件验生成 exit 和 IR SHA，再复制为冻结证据里的通用 `generation.json`；对应测试先红后绿，9/9通过。

本批按同一 stage 的 release `isarch` 构建，再运行 `make -o build-isarch -k -j4 solve-fd-nonmem`，`ITRACE=1`、`THREADS=2`、300/270/30秒、`qfaufbv`，无符号域限制或采样。2026-09-27 00:25 写入启动标记，release 构建 exit 0，原77项 make 于北京时间 00:26:21–01:08:40 全部取得退出状态；结果与审计见下节。运行期间再次核对 stage 源码清单零漂移、二进制哈希一致。本批可作后续统一 CPP/Isla extern 架构的当前版本基线，其结果仅适用于上述哈希。

## 1dcc 整批结果与严格核账

`evidence/build.rc=0`；release `isarch` SHA-256 为 `f46d36c9d58ab71cec8e6a620ca8f4cd636e5b9c399009b21f3f5a22dcdf891f`。stage 源码树清单哈希为 `1b4afb838c9fc6823cdfdd40517c6c9fe7c1720c0b40146b265be7b6f0a5e397`，模型树清单哈希为 `e46681849ad811b4ba399dd2860cbb67ac9b41e9d1d436a66d97259266b9db33`。冻结的 FD 配置 SHA-256 为 `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`。`evidence/make.log` 记录77条启动行，最终 make exit 2；`batch.finished` 与 `make.rc` 均已写入。77项目标中50项 `intime` / 底层exit 0，27项外限 `timeout` / 底层exit 124，无其他失败，全部按原 make recipe 执行。详细逐项目标表见[新77项执行表](solve-audit-batch.md)。

运行后 `evidence/source-candidate-comparison.json` 再核候选源清单的510项：432项字节不变，IR和77份活跃严格配置按冻结候选受控替换，共78项；stage另外记录5份未列入候选清单的 `rustfmt.toml`，无不受控漂移。第一次机械逐字比较曾把这78个预期替换误报为漂移，其原始报告保存在 `evidence/source-candidate-comparison-initial.json`；修正报告同时核对 stage 文件和manifest SHA，结果 PASS。

逐项诊断账本 `evidence/official-diagnostic-audit.json` 记录77项目标状态、时长、日志 SHA、局部终态、异常计数、JSON 摘要和轨迹大小。50份最终JSON均 `complete=true`、`suppressed=0`，其18,584条终态包括 Retire 12,903、Illegal 5,574、non-encodable 107；`gen`/emitted与日志逐项对齐。27个外限目标没有最终JSON；退出前日志打印 Retire 9,500、Illegal 77,437、non-encodable 107，仅属于残缺路径。超时项中6项已观察到Retire（`F_BIN_RM_TYPE_H`、`F_BIN_RM_TYPE_S`、三个 `F_MADD_TYPE_*` 和 `VFMV`），21项未观察到Retire。77份itrace原文合计118,202,010,583字节，其中超时项约100.0GB；没有删除原文。日志中未匹配执行错误、panic、`Z3Unknown` 或SMT timeout模式，这不证明未完成路径无错误。

`python3 agents/float_support_review/tools/solve_fix_official/official_batch.py audit isla/target/float-solve-evidence/official-1dcc-20260927-002314` exit 1，并生成 `evidence/official-audit.json`。50个自然退出目标逐项通过完整JSON、日志终态、itrace终态和运行时branch catalog守恒，branch edge无效数为0，逐项错误列表为空；27个超时项分别记“目标超时或失败、缺最终JSON”，残缺trace只保留文件路径/大小，不当作完整branch账本；全局唯一错误为make退出2。因此严格运行器核账为50/77无已知错误，整批**未通过**，没有生成全量 `replay-manifest.json`。50个可消费目标已按结束状态和哈希逐次交独立replay；数值/flags及源码分支覆盖须使用其独立结论，不能由本表推断。

诊断脚本的 `known_wide_fmtval_output_bug` 曾硬编码为旧批的 `true`，新1dcc初版诊断JSON因此误带旧标签。已先写失败测试，再按冻结 `fmtval.rs` SHA-256 精确映射：旧 c5 `ae02f6e0…` 为 `true`，已局部验证的本批 `43806138…` 为 `false`，未知哈希为 `null`；重生本批诊断JSON后字段为 `false`，`semantic_pass` 仍为 `false`。旧c5账本保留 `true`。脚本10/10单测通过；此修正只改诊断元数据，不改冻结stage或原始输出，也不影响严格audit结论。

## 3481 统一后端两代表同预算复验（已完成，0/2）

完整77项先等待两代表结果，未启动新批。统一模型 IR `348147f833432008d559be0e673dbd45982148b0750cd4533c68589a55aac061` 的独立候选包为 `isla-unified-p1-candidate-20260927.fa8Sg2`；候选 `source-manifest.json` SHA-256 `1890f0a13d9dc877185c46bcf398ea0b2f12fbe3b0ee6802adb5de0a845f1ed9`，模型166项、Isla源码510项，主 Isla 的对应510项逐文件匹配。`workarounds-report.json` SHA-256 `affdc1e30cf84131b7d340d7a73eb1756592175d4679097e7ba0e5c777ab32e5`，状态 PASS：79配置、77活跃/2归档、130/2 region、22锚点；严格 region 语义报告130/130通过。FD基础配置 SHA-256 `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`。

新stage为 `isla/target/float-solve-evidence/representatives-3481-20260927-041103/`，保留候选模型、IR、配置、源码和构建证据。`official_batch.py run-representatives` 只运行 `FVVMATYPE` 和 `F_MADD_TYPE_D`，真实make `-k -j2`，每目标2线程、完整ITRACE、外/内/SMT限时300/270/30秒、`qfaufbv`，不限制符号域或采样。两条实际dry-run CLI 均无 `--execution-limits-config`。release构建exit0，二进制SHA-256 `1cdf1d153c7e78d5e51960f10268f2de1691d67b42202a79d0db4cd3c7e4dd98`；目标在北京时间04:13:35同时启动，04:18:37/38分别外限结束，make exit2。`evidence/representatives-dryrun.txt`、`representatives-build.log`、`representatives-make.log`、`representatives-timing-events.jsonl`、`representatives-run.json` 和 `stage/output/` 是原始证据入口。运行工具先红后绿测试，11/11通过；source哈希/启动标记阻止在同一stage混跑完整77。

`official_batch.py audit-representatives` 生成 `evidence/representatives-audit.json`，诊断审计返回0表示所检查的证据没有完整性错误，**不表示目标完成**。`FVVMATYPE` 底层124、墙上303.22秒，日志局部 Illegal 4,014、non-encodable 3、Retire 0，残缺itrace 4,589,626,383字节；`F_MADD_TYPE_D` 底层124、墙上302.14秒，局部 Retire 2,826、Illegal 633、non-encodable 4，残缺itrace 2,107,842,472字节。两项均无最终JSON，因此0/2完成；无其它退出码，日志未匹配执行错误、panic、`Z3Unknown` 或SMT timeout模式。审计再次核对stage源码/IR/配置及运行二进制哈希未漂移，逐项状态、make错误行、时间事件相符，原始日志保留。轨迹均为外限中止的局部原文，未当作完整branch账本。

后续独立流式轨迹复核见 `isla/target/float-solve-evidence/unified-performance-review/review.json`，SHA-256 `ebd528bef43c969fe0fb3091b8bebf561091193fd3509a56e5cee247097a9ea5`。`FVVMATYPE` 的4,017条完整轨迹终态与日志一致；`F_MADD_TYPE_D` 的完整轨迹终态为2,825 Retire、633 Illegal、4 non-encodable，**比日志少1条Retire**，两份轨迹尾标记均完整。原代表诊断审计只核退出、日志、文件存在与大小，未把外限轨迹做终态守恒，因此其返回0不能覆盖此差异；差异保留为未解释的局部trace/log不守恒，不能把该目标的局部日志计数当作已严格核账的完整路径数。

1dcc同预算基线中的对应两项同样外限124：`FVVMATYPE` 无Retire、Illegal 2,772/non-encodable 3；`F_MADD_TYPE_D` Retire 2,744、Illegal 387/non-encodable 4。旧批最多4项目标并发，新代表最多2项，且主机负载不同；仅可判定3481两目标在本轮预算内仍未收敛，局部终态差异不能直接换算成性能提升或源码覆盖。完整77项3481批尚未启动，等待代表诊断与后续编排决策。

## 56cc V4+AMO 两代表同预算复验（已完成，1/2）

新候选 IR SHA-256 `56cc69a44ee1acdb4cadf40a992283aa2084e281e85fbe88ab10a3153d9956ac`，候选 `source-manifest.json` SHA-256 `fdf105d19a9ac62f9c5036fbc80759adb7e9b500a51a34fcc4f886016329129e`，成功生成记录 SHA-256 `9f01067ea8f2da31b37f5089e4c5870e47e8299f7622b9a456585a0648176a77`。79严格配置报告 `4f23d098…` PASS：77活跃/2归档、129活跃region+1精确退役、2归档region、22锚点，0问题；退役manifest `bb32421f…`、退役证书 `72e53ee…` 和129区域语义报告 `2ba44c66…` 已逐项绑定。候选freeze `09e456ae…` 与架构最终独审 `0ab22029…` 亦复制到运行证据。主Isla与候选记录的510源码文件逐项哈希一致，FD配置 SHA-256 `20851fdb…`。

独立stage为 `isla/target/float-solve-evidence/representatives-56cc-20260927-061428/`。快照预检77目标、活跃限制零问题；`evidence/manifest.json`、`config-preflight.json`、`candidate/`、`gate-signoff.json` 固定输入与签收。运行工具经先红后绿12项测试通过，新增独立 `prepare-representatives`：先真实make dry-run校验两条CLI，再从stage同源release构建含 `itrace` 与 `smt-thread-interrupt` 的isarch并核源码/IR/config哈希；`run-representatives` 复核准备阶段输入和二进制后执行原两目标。预算保持300/270/30秒、`-j2`、每目标2线程、完整ITRACE、`qfaufbv`，不限制符号域或采样。

两目标北京时间06:20:07启动，build exit0、二进制SHA-256 `4fc2ea00c2750842b2553722d0ca5a3d118d894e64803b5550ac2a15a8de075b`。`F_MADD_TYPE_D` 自然exit0、墙上86.50秒，JSON complete=true、1096终态（Retire840/Illegal252/non-encodable4）、1092gen/suppressed0；日志与完整trace的终态五元组全对齐，3,418,976条branch edge无效0。其独立 `replay-manifest-F_MADD_TYPE_D.json` SHA-256 `00366671…`，消费端schema通过；双后端1092gen+4负例配对PASS见独立重放摘要 `ee922578…`。`FVVMATYPE` 外限124、墙上301.93秒，无最终JSON，局部Retire53/Illegal3353/non-encodable3；代表make exit2。逐项目标和负载在 `evidence/representatives-run.json` 与 `representatives-audit.json`。独立性能复核 `independent-performance-review/review.json` SHA-256 `b47106b0…`：V局部trace 3409终态与日志全对齐，53 Retire实际到达4或8 lane循环，V4/AMO内部冗余fork消失；仍属未完成证据。

## 56cc 全77长预算首批资源止损

架构按上述代表前沿批准一个**独立**77项长批，stage `isla/target/float-solve-evidence/official-56cc-long-20260927-064348/`。真实make命令 `-k -j8 solve-fd-nonmem`，每目标2线程、`ITRACE=1`、外/路径/SMT限时1800/1740/30秒、`thread_interrupt`、`qfaufbv`、完整原输入域、无目标抽样；启动北京时间06:46:37。release构建exit0，build日志warning行与同源56cc代表逐项相同（54行；isarch自身12条，包括unused变量），与运行错误分账。运行期间8个向量实例RSS增大，主机swap15Gi用满、可用内存降至约28–45GiB；`FVFTYPE` 底层137，另五项目标返回15，尚不能单凭退出码判定OOM或trap跨目标误杀：本机`timeout`为uutils0.8.0，子进程接SIGTERM和自行exit15均可使wrapper返回15；内核dmesg无读取权限，cgroup所查 `oom/oom_kill` 计数为0。

按资源止损裁定，先SIGSTOP已确认stage内make以阻止后续调度，再仅向该make的同stage cwd子孙发SIGKILL，最后结束make；未用全局 `pkill`。`evidence/controlled-interruption.json` 保存当时8个活跃目标/PID/RSS及状态；`stopped-batch-audit.json` 将77固定名单严格分为：26自然退出0、6非预算失败（137/15）、8人为中断、37未启动，合计40项已启动。`batch.finished`、make.rc=-9为人为收束，不是全组正常结束。`official-diagnostic-audit.json` 保存77行局部日志/文件信息，所有原始证据未删除。停止后MemAvailable回升约152GiB，旧stage没有求解进程残留；swap当时仍满。26项自然完成目标由独立replay冻结到 `replay-wave-001-manifest.json` SHA-256 `0bb5cd9f…`，含6195gen/6230终态；消费端manifest校验PASS。6失败、8中断、37未启动均不转记PASS。

旧 `scripts/run_ctrl_c.mk` 的INT/TERM trap 使用全局 `pkill -KILL -f target/release/isarch`，实际命令能够匹配别的stage；这提供跨目标清理的风险路径，但不单独证明本次137/15的确切来源。局部进程清理修复由性能负责人TDD实施，后续将建新stage用修复后脚本、`-j1`×每目标2线程先单独跑`FVFTYPE`，预算仍1800/1740/30秒，记录5秒RSS/VmHWM/MemAvailable。该新stage与此旧长批的脚本源码哈希必须分别固定，结果不能合并成同一全组自然批。

### 首批已完成输出与低并发止损

26项自然完成目标已由独立消费端冻结 `replay-wave-001-manifest.json`（SHA-256 `0bb5cd9f…`），含6,195条gen和6,230个终态；同版Isla/CPP全量6,230/6,230配对结果当时记录在 `isla/target/float-solve-evidence/unified-backend-cpp-replay/official-long-wave001-56cc69-20260927/paired/paired-summary.json`（SHA-256 `154efe14…`），含22条直接不可编码负例与13条按真实encoder派生的负例。后续审查确认该消费端遗漏异常let的纯读及完整状态等价检查；因此现行结论仅为**完整输入归账与已观察数值/状态配对PASS**，纯读与完整等价待异常let补证，不能沿用旧报告的全语义PASS表述。新的observer三组全量复跑另立证据；这26项也不能替代其余51项官方求解。

局部清理修复已冻结：新 `scripts/run.mk` SHA-256 `3e603415…`、`run_ctrl_c.mk` `8081d772…`、新增 `solve_process.py` `1eb8621c…`。真实信号与跨stage隔离测试10项通过，性能负责人证据manifest SHA-256 `be714b41…`，架构独审 `306ce57f…`。新脚本把每条原 `timeout` CLI 交给本目标专属进程组监督，删除旧全局 `pkill`；对外部INT/TERM保留实际子进程wait并只清本组。新stage与旧候选510项源码清单仅有这两份既存脚本字节差异，另有新增监督脚本与测试；Rust运行时、IR、FD配置及79严格配置仍按各自冻结SHA绑定。

新 `FVFTYPE` 单目标stage为 `isla/target/float-solve-evidence/fvftype-j1-56cc-20260927-084800/`，`evidence/runtime-script-delta.json` 逐文件记录清理脚本差异。原预算1800/1740/30秒、`-j1`、每目标2线程、全ITRACE、原域无采样；release构建exit0，真实make北京时间07:33:43启动。目标内存持续上升，约697秒时外部资源止损：手动核supervisor PID/cwd/argv及isarch子进程归属，仅向该supervisor发TERM。停前RSS/HWM 125,275,944 kB（约119.5GiB）、主机MemAvailable 31,958,968 kB、swap近满；supervisor报告收到SIGTERM、timeout child wait为signal9、本组残留清理完成，返回143，make退出2。三PID均已消失，主机可用内存恢复。此状态是**人为 `external_resource_stop`，不属1800秒外限或模型语义FAIL**。日志仅有局部Illegal4,801、non-encodable3、Retire0，无最终JSON；残缺trace 5,430,518,981字节。详细进程状态、哈希和命令见 `evidence/fvftype-resource-audit.json`、`resource-stop.json`、`stage/output/process/FVFTYPE-1954470.json`。

本轮每5秒资源采样共52点，实际覆盖北京时间07:41:01–07:45:16；**目标最早约7分18秒没有采样**，不能声称全程5秒覆盖。主机最保守阈值为进程RSS达到96GiB或MemAvailable降至48GiB，先到即止损；手动判定和信号下发有延迟，停前已越过两个阈值。新进程清理的显式 `kill --pid` 首次调用因当前Python没有 `signal.pidfd_send_signal` 主动拒绝，没有执行全局清理；随后手动严格核PID身份并仅发supervisor TERM。该兼容入口正在单独修复；下一新stage须在spawn前启动自动5秒监视与阈值止损，不回写本次证据。单目标-j1也未使本版`FVFTYPE`在可接受资源内收敛；性能负责人正在做trace存储共享优化，修后另冻新版本比较。

### 共享 itrace 新runtime准备（尚未运行）

新独立stage `isla/target/float-solve-evidence/fvftype-sharedtrace-j1-56cc-20260927-080749/` 已快照并完成同源release构建（exit0、binary SHA-256 `0c73a17e6cf289b0b0827b2526bdb862c781fd8ff9dcd2751fc298c8c1b7cce3`），当前没有任何solve启动标记。IR `56cc69a…`、FD `20851fdb…`、79严格配置仍同候选；`evidence/runtime-delta.json` 单列相对于旧候选510项的5份既存源码变动：itrace生产存储文件 `itrace.rs` SHA-256 `38c2947a…`，`executor.rs` 和 `executor/frame.rs` 仅测试适配，以及本stage的 `run.mk`、`run_ctrl_c.mk` 局部清理脚本；另列新增 `solve_process.py`（Python兼容版 SHA-256 `48aedd3e…`）及测试。stage源码树 SHA-256 `b298e395…`，515+新增文件完整记于stage manifest，旧候选源码证书只绑定IR/模型/配置来源，不声称覆盖这些新运行时文件。共享itrace包manifest SHA-256 `b1fef6f2…`、cleanup兼容包及架构证书已复制入stage evidence；数值独审尚未放行，故只准备构建。

新监控工具 `tools/solve_fix_official/monitor_single.py` 会在目标spawn前写首条资源采样，随后每5秒核本stage的supervisor及其isarch后代PID/starttime/cwd/argv，记录RSS/HWM/MemAvailable；达到RSS96GiB或MemAvailable48GiB时仅通过新局部监督脚本向该已核supervisor发TERM。用真实sleep进程和低阈值完成止损测试，连同原官方工具共15/15通过。下一轮将在数值独审签收后运行该stage的单目标 `FVFTYPE`，预算1800/1740/30秒、`-j1`、每目标2线程、完整ITRACE、原域无采样；结果将另立，不复用本次旧runtime的局部结论。

共享itrace组件独审证书 `evidence/trace-sharing-independent-review.json` SHA-256 `7a36af35…` 放行后，stage中 `FVFTYPE` 北京时间08:27:12开始，监控首样本08:27:11在目标spawn前。原1800秒外层预算结束时监督器无外部信号，timeout子进程自然返回124，make2；没有最终JSON。日志局部Retire17/Illegal24,990/non-encodable3，完整残缺trace 28,924,314,971字节；`evidence/fvftype-trace-prefix-audit.json` 流式核25,010条终态与日志五元组双向一致、146,336,129条branch edge无效0，仍不能当全域完成。自动资源监控345样本覆盖全运行，峰值RSS 36,453,884 kB（约34.8GiB）、最低MemAvailable 110,846,708 kB（约105.7GiB），未触发96/48GiB止损。较旧j1约697秒时119.5GiB人为中断，内存得到控制，**求解仍在1800秒外限未完成**。新solve与新observer精确来源桥独审证书 `evidence/new-observer-bridge-review.json` SHA-256 `309dc98e…` 只允许本版未来完整case逐条重放，不搬旧case语义PASS。

## 56cc 同源共享trace家族单目标流水

按架构批准，继续从旧1dcc自然完成但56cc首长批未启动的目标收证。`F_BIN_TYPE_F_S` 与 `F_BIN_TYPE_X_S` 各在独立stage以同IR/FD/79配置、`-j1`×2、1800/1740/30秒、完整ITRACE及启动前自动资源监控运行，均自然exit0并严格核JSON/日志/完整trace终态守恒，v1回放manifest各自冻结。随后21项固定序列自动逐target建立独立stage，状态索引为 `isla/target/float-solve-evidence/single-family-queue-20260927-014615/status.json`，21/21自然退出0；`frozen.jsonl` 各行给冻结stage/v1 manifest/hash，均通过完整tuple与branch catalog核账。前2+21共23项，日志/trace/JSON原文各留stage；同版二进制仅在源码树、IR、FD配置和构建日志完全一致时按SHA复制复用，`single-binary-reuse.json` 逐stage记来源，避免重复编译。旧j8自然26项与FMA-D代表1项加本23项相互无重叠，机器去重索引 `single-family-queue-20260927-014615/aggregate-completed-56cc.json` 得50/77唯一自然完成；这是跨stage、两版runtime的库存，**不是单批全77完成或全语义PASS**。新sharedtrace输出须交新observer独立配对；旧26消费端原异常let纯读遗漏仍待新版补证。

余27项中，架构先批准同sharedtrace/56cc j1固定七项目标顺序 `F_MADD_TYPE_H/S`、`F_BIN_RM_TYPE_H/S/D`、`VFMERGE`、`VFMV`；自动队列状态与逐项冻结manifest索引在 `single-family-queue-20260927-020959/`。前5项自然完成并严格冻结。`VFMERGE` 于2026-09-27 03:30:00 UTC结束：`single-56cc-20260927-020959-06-vfmerge/stage/output/process/VFMERGE-*.json`记录supervisor无外部信号、timeout child实际wait退出124、历时1800.73秒；make2，未生成最终JSON，残缺trace约36GB，不计完成。队列于03:30:01 UTC自动进入`VFMV`；该目标03:37:48 UTC自然退出0（监督器child wait 0、无外部信号，464.49秒），make0。`VFMV-freeze.json`核最终JSON/日志/完整trace的5,475终态守恒（Retire1,872/Illegal3,600/non-encodable3），38,148,123条branch edge无效0；其独立回放入口`single-56cc-20260927-020959-07-vfmv/replay-manifest-VFMV.json` SHA-256 `db6f11c1…681a`，已在`frozen.jsonl`登记。队列七项因此为6项自然完成严格冻结、1项外限；更新机器去重索引`single-family-queue-20260927-020959/aggregate-completed-56cc.json` SHA-256 `b099be75…133e`得到跨stage唯一自然完成56/77、未完成21项，不代表全77语义PASS。每个运行目标均保留原输入域/无采样、1800/1740/30、5秒自动资源止损；非预算失败或资源stop使队列停下来等审查。

## e6a FVFTYPE caller新IR准备与复验（外限未完成）

新IR `e6a3232d…` 的运行时来源**只取**上述sharedtrace FVFTYPE 517源码冻结stage，主Isla仍d012/130旧配置，不混入。新候选完整IR、79份配置及源清单以 `fvftype-caller-e6a-prepared-20260927/evidence/manifest.json` 固定；carry-forward仅把56cc已退役配置的IR哈希换绑至新IR，保持129配置region、1处历史退役、无新增退役/坐标变化，并核129项旧新实际选择行为相同。独立strict证书 `evidence/strict-source-review.json` SHA-256 `7681cf6b…` 明确其中127项有实际命中、`vxtype.toml` 两项为旧新同为零命中的历史空范围；旧报告“129全实际有效”不作为现行结论。stage源码517项、构建release binary SHA-256 `b42ac4f5…`、IR/FD/严格配置与生成记录各按SHA固定；候选v2输入字节在本次运行中保持不变，后续v3仅作证据措辞标准化。

e6a单目标 `FVFTYPE` 北京时间11:01:33以原`-j1`×2、1800/1740/30秒、完整ITRACE与原域启动；监控首样本11:01:32早于目标spawn，96GiB/48GiB自动止损可用。`evidence/fvftype-run.json`与`stage/output/process/FVFTYPE-*.json`记录make2、supervisor无外部信号、timeout child实际wait退出124、历时1805.23秒；没有最终JSON，不计完成。流式局部核账`evidence/fvftype-partial-trace-audit.json` SHA-256 `d25388f2…4a0`：原始残缺trace 17,025,686,964字节，14,140条终态与日志五元组逐项双向一致（Retire31/Illegal14,106/non-encodable3），85,694,666条branch edge无效0。这只证明终止前前缀自洽，不代表全域。监控345样本覆盖03:01:32–03:31:33 UTC，峰值RSS32,320,264 kB（约30.8GiB）、最低MemAvailable114,588,560 kB（约109.3GiB），无资源止损。该候选仍未在预算内收敛，后续优化须另冻版本审查。

## 56cc VFMERGE两小时独立预算完成及三目标并行队列（进行中）

架构只读前沿证据位于旧`single-56cc-20260927-020959-06-vfmerge/architecture-vfmerge-frontier-review/`，核旧1800秒目标实际末尾Retire、约4.8GiB稳定RSS，据此批准独立预算扩大，当时不承诺两小时内完成。新stage `isla/target/float-solve-evidence/vfmerge-2h-56cc-20260927-c/`与旧56cc共享trace源树、IR `56cc69a…`、FD配置和已核release binary逐SHA一致；`evidence/extended-run-plan.json` SHA-256 `9efc1733…50d`记录真实dry-run CLI、启动前/启动后manifest哈希及7200/7140/30秒、`-j1`、每目标2线程、完整ITRACE、原符号域无采样。自动5秒资源监控在spawn前启动，RSS96GiB或MemAvailable48GiB触发仅对本stage精确止损。北京时间11:57后已见supervisor与isarch在stage cwd启动，实际argv含7200/7140/30。准备过程保留两次无效尝试：首次从已安装候选的stage再安装候选，预检因配置前像不符而拒绝；第二次`-b` stage在仓根cwd误执行make报缺`solve-VFMERGE`规则、isarch未spawn。两次均未被计作求解结果，`-c`为实际运行。

并行的三项目标固定顺序为`RFVVTYPE`、`RFWVVTYPE`、`VFUNARY1`，队列目录`single-family-queue-20260927-035801/`。每项独立56cc/sharedtrace stage，`-j1`×2、1800/1740/30秒、完整原域与5秒96/48GiB监控；03:58:02 UTC首个`RFVVTYPE`实际spawn，和长`VFMERGE`并发最多两目标。队列`status.json`、`events.jsonl`记录自然退出/外限/资源止损，另一路冻结监视只对自然完成目标执行完整JSON/日志/itrace/catalog核账并写`frozen.jsonl`；未完成项不交回放。两路共用主机可用内存阈值，后续每项启动前还须核资源，若触发阈值则停止新调度并仅清理已核身份的本组进程。

首次约30分钟检查点`vfmerge-2h-56cc-20260927-c/evidence/checkpoint-030m.json` SHA-256 `390c6244…49dcf`，实际采于启动标记后1946.33秒：局部Retire7,103/Illegal21,174/non-encodable3，末100终态全Retire；峰RSS4,957,356 kB、检查点MemAvailable140,231,392 kB、trace原文当时39,787,097,747字节，无最终JSON或资源止损。检查点固定了日志与监控前缀SHA，未给增长中的trace做完整哈希；当时运行继续。

`VFMERGE`于04:36:07 UTC自然完成，supervisor实际wait到timeout child退出0、无外部信号，历时2359.20秒；make/监控退出0，且从未触资源止损。`evidence/VFMERGE-freeze.json`严格核344,728,372字节最终JSON、日志和44,122,131,855字节完整trace的30,603终态五元组双向守恒（Retire8,784/Illegal21,816/non-encodable3），215,491,497条branch edge无效0。冻结回放入口`replay-manifest-VFMERGE.json` SHA-256 `6c5749ca…56e3`已交独立消费端；监控451样本覆盖03:56:47–04:36:02 UTC，峰RSS5,038,620 kB、最低MemAvailable119,502,500 kB。新的机器去重索引`evidence/aggregate-completed-56cc.json` SHA-256 `d0d0988a…8b05d`由旧56项加该目标，得57/77唯一自然完成、剩20项；语义等价仍由独立重放裁定。

三目标队列首项`RFVVTYPE`于04:28:08 UTC外限：`stage/output/process/RFVVTYPE-*.json`记录timeout child实际wait退出124、无外部信号、历时1803.64秒；make2、无最终JSON/资源止损，不计完成。局部诊断`single-56cc-20260927-035801-01-rfvvtype/evidence/RFVVTYPE-timeout-audit.json` SHA-256 `2097f8a6…1b68`记日志Retire361/Illegal30,417/non-encodable3、峰RSS24,310,220 kB、最低可用119,562,344 kB；残缺trace未作全域守恒。队列04:28:09 UTC自动进入`RFWVVTYPE`，已核其独立supervisor和isarch在stage cwd；其结果待退出。

空出的第二并发位经架构批准运行同冻结56cc `VFWMACCBF16_VV`：独立stage`vfwmaccbf16-vv-2h-56cc-20260927/`，7200/7140/30秒、`-j1`×2、完整ITRACE/原域、启动前5秒96/48GiB资源监控；`evidence/extended-run-plan.json` SHA-256 `2c227884…037e`绑定同源哈希及dry-run。04:48:14 UTC已见stage cwd中的supervisor与isarch实际argv匹配预算，首监控目标RSS1,586,348 kB、主机MemAvailable134,121,184 kB。其完成/外限待审，不以较旧目标表现预断。另独立stage`vfwmaccbf16-vf-2h-56cc-prepared-20260927/`仅快照、同源二进制复用和dry-run通过，plan SHA-256 `79a18bb2…aa22`，尚无求解spawn；是否启动取决于空并发位与调度裁定。

三目标队列第二项`RFWVVTYPE`于04:58:12 UTC外限，supervisor实际wait到timeout child 124、无外部信号，make2，无最终JSON/资源止损；`single-56cc-20260927-035801-02-rfwvvtype/evidence/RFWVVTYPE-timeout-audit.json` SHA-256 `7d95387f…5fca`记录局部Retire1,382/Illegal24,608/non-encodable3、残缺trace33,803,455,225字节、峰RSS13,392,668 kB、最低可用126,763,024 kB。局部trace未作全域守恒，该目标不计完成。队列04:58:13 UTC自动进入第三项`VFUNARY1`，与持续运行的`VFWMACCBF16_VV`合计两目标；当前唯一自然完成仍57/77。

`VFWMACCBF16_VV`的固定30分钟检查点`vfwmaccbf16-vv-2h-56cc-20260927/evidence/checkpoint-030m.json` SHA-256 `ac590901…aa53`，实际采于启动后1861.38秒：局部Retire695/Illegal17,116/non-encodable3，末100终态7 Retire/93 Illegal；峰RSS7,195,636 kB、当时MemAvailable117,403,928 kB，trace增长中的前缀27,736,257,012字节，无最终JSON、资源止损或日志中的panic/Z3Unknown/SMT timeout。源运行仍按7200秒预算继续。

三目标队列第三项`VFUNARY1`于05:28:18 UTC外限；监督器实际wait child124、无外信号，make2、无最终JSON/资源止损。诊断`single-56cc-20260927-035801-03-vfunary1/evidence/VFUNARY1-timeout-audit.json` SHA-256 `b4374806…df1a`记局部Retire443/Illegal4,006/non-encodable3、残缺trace5,587,248,770字节、峰RSS5,371,640 kB、最低可用110,875,812 kB；不能记完整目标。该三项队列全部原预算外限，未生成自然完成manifest，57/77库存不变。

空出的并发位按root最终裁定运行旧56cc `RFWVVTYPE`独立两小时**全域诊断探索**；其旧30分钟尾部Retire已核为VL=0早退，不能据此称数值收尾或预言长预算完成。stage`rfwvvtype-2h-56cc-prepared-20260927/`先完成同源517源码/IR/FD配置与release binary哈希复用、严格预检和7200/7140/30秒dry-run；新LMUL+unary `FVFTYPE`当时仍未获完整模型构建及strict/source全门，不能snapshot。新RFW北京时间13:31后实际spawn，05:31:28 UTC监控核supervisor与isarch在stage cwd，真实argv保全符号VL/R1/完整ITRACE、`-j1`×2、7200/7140/30秒；首样本先于目标，初始RSS1,849,804 kB、主机MemAvailable126,212,888 kB，5秒96/48GiB止损继续。与`VFWMACCBF16_VV`合计两目标，30/60/90分钟检查点及最终结果待实测。

`VFWMACCBF16_VV`固定60分钟检查点`vfwmaccbf16-vv-2h-56cc-20260927/evidence/checkpoint-060m.json` SHA-256 `822e5e18…8d49`，实际采于启动后3811.40秒：局部Retire2,485/Illegal21,155/non-encodable3，较30分钟检查点分别新增1,790/4,039/0，末100终态含34 Retire/66 Illegal；峰RSS8,274,140 kB、当时MemAvailable108,449,996 kB、trace前缀37,295,068,990字节，无最终JSON或资源止损。仅证明局部前缀继续增长，不预断全域完成。

`RFWVVTYPE`固定30分钟检查点`rfwvvtype-2h-56cc-prepared-20260927/evidence/checkpoint-030m.json` SHA-256 `a6ba5555…23a1`，实际采于启动后1909.79秒：局部Retire1,263/Illegal21,422/non-encodable3，末100终态全Illegal；峰RSS11,700,328 kB、当时MemAvailable109,055,296 kB、trace前缀27,678,009,258字节，未触资源止损且无最终JSON。早期旧RFW退休含VL=0早退，此处也不据退休数推数值收敛。

`VFWMACCBF16_VV`的90分钟检查点**实际采于启动后5817.78秒**，晚于90分钟标记；`vfwmaccbf16-vv-2h-56cc-20260927/evidence/checkpoint-090m.json` SHA-256 `59c9d715…2225`固定局部Retire3,997/Illegal23,709/non-encodable3、末100为35 Retire/65 Illegal、峰RSS8,705,492 kB、当时MemAvailable114,024,172 kB、trace前缀44,043,053,470字节，无最终JSON或止损。记录按实际elapsed，不将其回填为准点采样。

`RFWVVTYPE`的60分钟检查点**实际采于启动后3955.87秒**，晚于60分钟标记；`rfwvvtype-2h-56cc-prepared-20260927/evidence/checkpoint-060m.json` SHA-256 `dd59bc28…4bcb`固定局部Retire2,774/Illegal31,674/non-encodable3、末100全Retire、峰RSS13,786,916 kB、当时MemAvailable120,409,280 kB、trace前缀45,207,972,337字节，无最终JSON或资源止损。末100退休仍未排除VL=0早退，不作为数值归约收尾证据。

下一空并发位的441c新`FVFTYPE`此前已在`fvftype-lmul-unary-441c-prepared-20260927/`完成snapshot/strict预检与7200/7140/30秒dry-run，原候选freeze字节保持审前flags不改，另以同stage`evidence/independent-gates.json` SHA-256 `95c4a265…2eeb9`联立fullIR与strict/source最终双独审；IR SHA-256 `441c145b…f47c`。517源码除IR及79严格TOML外与e6a已构建stage逐文件同SHA，因此提前复制并核release binary `b42ac4f5…47e7`，来源记录`evidence/single-binary-reuse.json` SHA-256 `1c4e04e8…06d7`；启动前run plan SHA-256 `c90cd1d0…d43f`。这一阶段为**prepared-not-started**，没有占第三官方solver；后续实际启动见下段。

`VFWMACCBF16_VV`在7200秒外限自然结束于06:47:50 UTC：监督器实际wait timeout child退出124、无外部信号，历时7201.33秒，make/监控exit2，无最终JSON/资源止损；不是完整目标。最终局部账本`vfwmaccbf16-vv-2h-56cc-20260927/evidence/VFWMACCBF16_VV-timeout-audit.json` SHA-256 `d9f32f2b…642a`记录Retire5,283/Illegal25,924/non-encodable3、残缺trace49,826,592,779字节、1364资源样本峰RSS8,729,508 kB、最低MemAvailable104,554,688 kB，日志无panic/Z3Unknown/SMT timeout模式。30/60/约97分钟固定前缀与最终日志分账；根据本目标无JSON的结论，不额外扫描全50GB残缺trace，保留原文。

释放并发位后，前段已准备的441c `FVFTYPE`于06:52后实际spawn：`fvftype-lmul-unary-441c-prepared-20260927/` stage的监控核stage cwd中supervisor和isarch真实argv为7200/7140/30、`-j1`×2、R1/全符号域/完整ITRACE，首样本先于isarch，初始RSS928,344 kB、MemAvailable118,051,036 kB。运行仍在进行；按实际启动时间固定1800秒对照checkpoint，并将预算内或扩时后的自然完成分列。此时另一目标仅为旧56cc RFW长预算，合计两目标。

`RFWVVTYPE`固定90分钟检查点`rfwvvtype-2h-56cc-prepared-20260927/evidence/checkpoint-090m.json` SHA-256 `185e1e2f…b8e1`实际采于启动后5499.55秒：局部Retire4,076/Illegal33,049/non-encodable3，末100含43 Retire/57 Illegal，峰RSS13,786,916 kB、当时MemAvailable117,873,220 kB、trace前缀48,321,541,131字节，无最终JSON/资源止损。当前只证明局部日志前缀，不能以末尾退休推数值收尾或全域完成。

`RFWVVTYPE`旧56cc两小时全域诊断于07:30:59 UTC外限结束：supervisor实际wait timeout child退出124、无外部信号，历时7202.35秒，make/监控exit2，没有最终JSON或资源止损。最终局部账本`rfwvvtype-2h-56cc-prepared-20260927/evidence/RFWVVTYPE-timeout-audit.json` SHA-256 `2d74d024…863e`记Retire5,828/Illegal38,171/non-encodable3、残缺trace59,566,629,106字节、1366资源样本峰RSS13,869,676 kB、最低MemAvailable96,281,748 kB；日志未见panic/Z3Unknown/SMT timeout模式。源自然完成库存仍57/77；残缺trace未再作全域账本。

空出的并发位随后运行新441c `VFUNARY1`：独立stage`vfunary1-lmul-unary-441c-prepared-20260927/`从同一441c候选另建快照，源码/IR/FD/79严格配置与新`FVFTYPE` stage逐SHA同源，复用release binary `b42ac4f5…47e7`及fullIR、strict/source双独审sidecar，不重编译。07:41:31 UTC已核stage cwd中supervisor与isarch实际argv含7200/7140/30、`-j1`×2、全符号域/R1/完整ITRACE，启动前监控RSS96GiB或MemAvailable48GiB保护生效；该运行与新441c `FVFTYPE`合计两目标。新的只读checkpoint监视脚本`tools/solve_fix_official/checkpoint_monitor.py`经2项测试，通过既有5秒资源样本时间线自动触发后续检查点，保存真实采样elapsed和trace短尾精确读区间；不修改正在运行的solver或stage源码。

441c `FVFTYPE`原1800秒对照包`fvftype-lmul-unary-441c-prepared-20260927/evidence/checkpoint-030m.json` SHA-256 `be3f5069…61f6`实际采于启动后1976.70秒，晚于原标记，不回填：完整行日志/资源前缀限定字节与SHA、实际IR/binary/argv SHA、短尾trace小文件及mtime均冻结；局部Retire2/Illegal519/non-encodable3，峰采样RSS3,571,376 kB，无最终JSON/资源止损。独立前沿审查`evidence/architecture-030m-frontier-review/manifest.json` SHA-256 `8b58ac8d…c3ef`核短尾1148条edge与冻结IR/runtime相符，同时指出最后块缺header，不将其归入case524或当前前沿。旧e6a与441c输入不同，不能凭较少局部终态称加速。

后续60分钟点已由只读watcher按现有5秒资源样本**自动触发**：触发样本07:51:58 UTC、采集07:51:59、启动标记06:51:58，实际elapsed3601.91秒；`fvftype-lmul-unary-441c-prepared-20260927/evidence/checkpoint-060m.json` SHA-256 `928aaafa…4dcc`固定完整行log/monitor前缀及短尾trace原文精确区间[993210554,993472580)。局部Retire6/Illegal849/non-encodable3、末100全Illegal、峰采样RSS4,459,024 kB/VmHWM4,564,212 kB、当时MemAvailable132,479,100 kB，无最终JSON/止损。两文件前缀及trace尾分别按自己的读取时刻冻结，非原子快照；90分钟点继续由同watcher监管。

441c `VFUNARY1`原1800秒点也由同一只读watcher自动触发：资源样本08:10:47 UTC、采集08:10:48，启动标记07:40:44，实际elapsed1804.26秒；`vfunary1-lmul-unary-441c-prepared-20260927/evidence/checkpoint-030m.json` SHA-256 `75274dd7…49a0`固定完整行log/monitor前缀、实际IR/binary/argv哈希和短尾trace精确原区间。局部Retire48/Illegal1,034/non-encodable3、末100为16 Retire/84 Illegal、峰采样RSS3,229,852 kB/VmHWM3,335,636 kB、当时MemAvailable132,636,904 kB，没有最终JSON或止损。该目标仍按原7200秒预算继续，不据局部路径数比较旧56cc性能。

441c `FVFTYPE`的90分钟点由自动watcher在08:22:00 UTC触发并采集，实际elapsed5402.39秒；`fvftype-lmul-unary-441c-prepared-20260927/evidence/checkpoint-090m.json` SHA-256 `dc7f3b3f…82f`固定局部Retire12/Illegal1,220/non-encodable3、末100全Illegal、峰采样RSS5,620,344 kB/VmHWM5,641,088 kB、当时MemAvailable128,299,564 kB、短尾trace精确源区间[1400914676,1401176686)，无最终JSON或资源止损。watcher正常退出，源solver仍继续到实际退出；截至此点不能判全域完成或性能改善。

nan-only新IR候选`86f1121b…e61f`经完整IR/CPP与strict/source双独审后，已先在`fvftype-nan-unbox-86f1-prepared-20260927/`独立快照为下一空并发位预备：517运行时前像来自旧sharedtrace冻结stage，新IR与79严格配置从同一候选的`ir/`和`workarounds-candidate/`安装，strict预检零问题；原候选freeze字节保留。`evidence/independent-gates.json`联立fullIR证书`4f0f7e08…31b26`与strict/source证书`43e1e908…ba975`，IR owner机器交接sidecar SHA-256 `dfe340f4…c9d0d`亦复制到stage。517源码除IR及79严格TOML外与441c/e6a运行时逐文件同SHA，release binary `b42ac4f5…47e7`及原build log已复用并核字节，来源记录`evidence/single-binary-reuse.json` SHA-256 `daeb17f9…6d08`；7200/7140/30秒dry-run及plan SHA-256 `be304f9d…a17c`通过。该stage当前**仅prepared、未spawn**，不占两路441c运行的第三solver；待实际空位后按root排程启动，保完整全输入域/ITRACE、5秒96/48GiB保护及1800秒自动检查点。

441c `VFUNARY1`自动60分钟点触发资源样本08:40:47 UTC、采集08:40:48，实际elapsed3604.98秒；`vfunary1-lmul-unary-441c-prepared-20260927/evidence/checkpoint-060m.json` SHA-256 `c5aae242…4b9b`固定局部Retire128/Illegal1,147/non-encodable3、末100为51 Retire/49 Illegal、峰采样RSS3,812,832 kB/VmHWM3,849,304 kB、当时MemAvailable131,429,668 kB、短尾trace精确源区间[1534386356,1534648485)，无最终JSON/止损。原运行继续，不能仅凭局部退休推全域完成或相对旧版加速。

441c `FVFTYPE`于08:52:01 UTC达到7200秒外限：监督器实际wait到timeout child124、无外部信号，历时7200.90秒，make/监控exit2，无最终JSON或资源止损。最终局部账本`fvftype-lmul-unary-441c-prepared-20260927/evidence/FVFTYPE-timeout-audit.json` SHA-256 `71f5581b…63d6`记Retire21/Illegal1,687/non-encodable3、残缺trace2,025,410,713字节、1371资源样本峰RSS6,735,264 kB/VmHWM6,793,720 kB、最低MemAvailable96,312,756 kB；日志未见panic/Z3Unknown/SMT timeout模式。30/60/90分钟固定前缀保留，残缺trace不作全域守恒；该目标不计自然完成，56cc库存仍57/77，新441c全域亦未完成。

空位按root排程立即运行已备nan-only `86f1121b…e61f`版`FVFTYPE`：独立stage`fvftype-nan-unbox-86f1-prepared-20260927/`于08:56:44 UTC实际监控到supervisor与isarch在stage cwd、真实argv7200/7140/30秒、`-j1`×2、全符号域/R1/完整ITRACE；IR/候选严格配置、fullIR/strict双审、旧e6a同字节release binary及provider桥均已在准备时逐SHA核。首资源样本先于目标，初始RSS1,164,096 kB、MemAvailable133,642,212 kB，5秒96/48GiB止损有效。新run与继续中的441c `VFUNARY1`合计两目标；独立只读checkpoint watcher已启动，将按已有5秒资源时间线触发1800秒及后续检查点，不阻塞或改变求解进程。

nan86f `FVFTYPE`原1800秒对照点由只读watcher自动触发：资源样本09:25:58 UTC、采集09:26:00，启动标记08:55:57，实际elapsed1803.81秒；`fvftype-nan-unbox-86f1-prepared-20260927/evidence/checkpoint-030m.json` SHA-256 `8a4fd83c…2c71`固定完整行log/monitor前缀、实际IR/binary/argv哈希与短尾trace精确源区间[695117145,695379099)。局部Retire2/Illegal576/non-encodable3、末100为2 Retire/98 Illegal、峰采样RSS3,748,068 kB/VmHWM3,846,868 kB、当时MemAvailable129,831,736 kB，无最终JSON或止损。继续原7200秒预算；与441c同约30分钟的局部路径差异不能用作性能加速结论。

nan86f `FVFTYPE`自动60分钟点触发/采集于09:55:57 UTC，实际elapsed3600.31秒；`fvftype-nan-unbox-86f1-prepared-20260927/evidence/checkpoint-060m.json` SHA-256 `13ba020a…ae53`固定局部Retire8/Illegal1,014/non-encodable3，末100为1 Retire/99 Illegal、峰采样RSS4,872,552 kB/VmHWM5,028,684 kB、当时MemAvailable125,996,484 kB、短尾trace精确源区间[1172644311,1172906265)，无最终JSON或资源止损。该目标继续原预算。

nan86f `FVFMTYPE`原1800秒独立目标于10:14左右外限：supervisor实际wait timeout child退出124、无外部信号，历时1801.04秒，make2，无最终JSON或资源止损。最终局部账本`fvfmtype-nan-unbox-86f-prepared-20260927/evidence/FVFMTYPE-timeout-audit.json` SHA-256 `d268e381…551`记Retire29/Illegal1,792/non-encodable3、残缺trace2,275,272,421字节、344资源样本峰RSS5,631,700 kB、最低MemAvailable123,706,076 kB；不计自然完成。

同日隔离Z3调用诊断v2另建`z3-diagnostic-nan86f-fvftype-20260927/`，采用独立已审518运行时与e7ba release binary，仍加载nan86f IR/79严格配置；v2 manifest SHA-256 `9b72dfbd…91a6b`、独审review SHA-256 `10115c84…4a056`及新stage prepared manifest SHA-256 `2e0777e5…f005`联立。10:38:02 UTC启动标记，10:38:49监控核supervisor/isarch在独立stage实际执行1800/1740/30秒、`-j1`×2、全输入域/完整ITRACE，只对此进程设置`ISLA_Z3_DIAGNOSTICS`写本stage新JSONL；5秒96/48GiB精确止损可用。此为第三条**非官方诊断**，不计57/77库存，不修改另两路官方binary/进程；正式统计由performance另立分析包。

a040 nan+reduction候选新严格报告采用“两层来源”：517运行时字节前像仍旧56cc sharedtrace，79配置的直接迁移前像为nan86f。原官方snapshot工具只识旧单层报告schema，首次两次尝试在spawn前被拒绝并保留原证；新独立stage`rfwvvtype-nan-reduction-a040-2h-20260927-c/`显式核517源、79旧新配置SHA、1历史退役/0新增、实际IR `a0405074…dfa7d`、fullIR证`d1031e6a…9e5f8`与strict/source证`517a7cad…a7ae`，安装候选IR/77活跃+2归档配置并重新做官方preflight。`evidence/candidate-install-audit.json` SHA-256 `42b1a85e…175b5`和`entry-delta.json` SHA-256 `30e22393…253f`核stage差异仅1IR+77活跃TOML；release binary `b42ac4f5…47e7`从e6a provider同字节复用。独立入口审查`entry-adaptation-independent-review-20260927/review.json` SHA-256 `f43ad333…beef1`放行后，10:42:48 UTC已见supervisor/isarch在stage cwd真实执行7200/7140/30秒、`-j1`×2、原符号域/R1/完整ITRACE，5秒96/48GiB保护。该源run仍在进行，不能沿用旧56cc PASS。

下一个a040 `RFVVTYPE`的独立stage`rfvvtype-nan-reduction-a040-2h-prepared-20260927/`此前从上述同源a040 RFW stage按517源码/IR/配置/binary逐SHA复制，仅clause与真实dry-run argv不同；`evidence/entry-reuse-diff.json` SHA-256 `af5d6dc4…ac8e`、7200/7140/30秒启动前plan SHA-256 `03a55292…63d4b`。当时仅prepared、未spawn，随后实际启动见下段。

nan86f `FVFTYPE`于10:55:58 UTC达到7200秒外限：supervisor实际wait timeout child124、无外部信号，历时7200.89秒，make/监控exit2，无最终JSON/资源止损。最终局部账本`fvftype-nan-unbox-86f1-prepared-20260927/evidence/FVFTYPE-timeout-audit.json` SHA-256 `a3cd4aef…e1ef5`记Retire27/Illegal1,911/non-encodable3、残缺trace2,327,932,160字节、1375样本峰RSS7,341,140 kB、最低MemAvailable120,147,760 kB；无panic/Z3Unknown/SMT timeout日志模式。30/60/90分钟固定前缀保留，不对残缺trace作全域守恒，也不计自然完成。

释放slot后前段已备a040 `RFVVTYPE`于10:58:19 UTC实际spawn：独立stage`rfvvtype-nan-reduction-a040-2h-prepared-20260927/`，stage cwd中的supervisor和isarch真实argv为7200/7140/30、`-j1`×2、全符号域/R1/完整ITRACE，5秒96/48GiB监控先于目标。与仍运行的a040 `RFWVVTYPE`合计两官方目标；另有隔离nan86f Z3诊断一条，三者输出和验收分别记。两a040官方目标的30/60/90分钟检查点由独立只读watcher按照原资源样本时间线触发，不修改solver或stage源码。

隔离Z3调用诊断于11:08:06 UTC自然达到1800秒外限：supervisor实际wait child124、无外部信号，历时1800.55秒，非官方且无最终JSON/资源止损。源退出账本`z3-diagnostic-nan86f-fvftype-20260927/evidence/diagnostic-exit-audit.json` SHA-256 `9cbd316d…246c`绑定v2 `z3-calls.jsonl` 151MB原文 SHA-256 `43b87f55…7e3`、日志局部Retire2/Illegal537/non-encodable3、峰RSS3,663,104 kB、最低MemAvailable120,039,256 kB；v2 JSONL消费与受保护FFI窗口解释另由performance独立封包，不在本官方求解账本推性能原因或PASS。

a040 `RFWVVTYPE`自动30分钟点触发资源样本11:12:05 UTC、采集11:12:06，实际elapsed1805.30秒；`rfwvvtype-nan-reduction-a040-2h-20260927-c/evidence/checkpoint-030m.json` SHA-256 `d73a9151…d4bc`固定局部Retire270/Illegal773/non-encodable3、末100为49 Retire/51 Illegal，峰采样RSS3,056,576 kB/VmHWM3,060,708 kB、当时MemAvailable132,335,072 kB、短尾trace精确原区间[1383769796,1384031792)，无最终JSON/资源止损。继续原7200秒全输入运行；不能据局部退休宣称全域完成或相对旧56cc性能收益。

a040 `RFVVTYPE`的自动30分钟点触发资源样本11:27:41 UTC、采集11:27:43，实际elapsed1806.12秒；`rfvvtype-nan-reduction-a040-2h-prepared-20260927/evidence/checkpoint-030m.json` SHA-256 `30c7e213…ed90`固定局部Retire447/Illegal1,647/non-encodable3、末100为51 Retire/49 Illegal、峰采样RSS5,158,536 kB/VmHWM5,341,972 kB、当时MemAvailable130,536,844 kB、短尾trace精确源区间[2706039687,2706301649)，无最终JSON/资源止损。原7200秒预算继续，源完成库存仍57/77。

隔离Z3 v2诊断另按root授权补了**匹配a040模型的基线**：新`z3-diagnostic-a040-fvftype-20260927/` stage由performance独占准备，518诊断runtime/e7ba binary不变，只将IR及77活跃严格配置替换为已审a040原字节，2归档仍d012；prepared manifest SHA-256 `1828ad36…6de3`、plan SHA-256 `6f858c85…79db`及来源桥逐项绑定。11:31:25 UTC已核独立stage cwd内supervisor/isarch真实执行1800/1740/30、`-j1`×2、全输入域/完整ITRACE，只对本进程设置`ISLA_Z3_DIAGNOSTICS`到本stage新JSONL，文件已创建增长；5秒96/48GiB精确止损可用。此为与两个a040官方目标并存的第三条**非官方诊断**，输出由performance另立分析包，不能把诊断局部路径或时间转为官方通过。

该a040匹配基线诊断于12:00:44 UTC达到1800秒外限：supervisor无外部信号、实际wait child124，历时1800.60秒，无最终JSON或资源止损。源退出账本`z3-diagnostic-a040-fvftype-20260927/evidence/diagnostic-exit-audit.json` SHA-256 `cdfbd2b8…b53d5`固定局部Retire2/Illegal536/non-encodable3、155,837,644字节v2 JSONL SHA-256 `347f964a…a3acf8`、344资源样本峰RSS3,651,548 kB和最低MemAvailable121,042,548 kB；performance已独立消费该源文件并在其最终分析包核算，诊断不计官方完成库存。

该a040诊断的独立最终消费证书`z3-diagnostic-a040-fvftype-analysis-independent-review-20260927/final-030m/review.json` SHA-256 `8e213656…8399c6c`已核源退出、资源、局部终态及199,004次完整调用；performance交接`z3-diagnostic-a040-fvftype-analysis-20260927/final-handoff.json` SHA-256 `73a39c65…bacc5`限定为诊断账本PASS，不转记官方目标或完整数值语义PASS。

a040 `RFWVVTYPE`自动60分钟点触发/采集于11:42:03 UTC，实际elapsed3602.93秒；`rfwvvtype-nan-reduction-a040-2h-20260927-c/evidence/checkpoint-060m.json` SHA-256 `c64a10ee…84b6`固定局部Retire443/Illegal887/non-encodable3，较30分钟点新增173/114/0、末100为61 Retire/39 Illegal，峰采样RSS3,056,576 kB/VmHWM3,098,452 kB、当时MemAvailable128,570,460 kB、短尾trace精确源区间[1725608291,1725870307)，无最终JSON/止损。该固定前缀不代表全域完成或可比较的性能加速。

a040 `RFVVTYPE`自动60分钟点触发资源样本11:57:40 UTC、采集11:57:41，实际elapsed3604.31秒；`rfvvtype-nan-reduction-a040-2h-prepared-20260927/evidence/checkpoint-060m.json` SHA-256 `75c2df55…e07b`固定局部Retire670/Illegal1,940/non-encodable3，较30分钟点新增223/293/0、末100为37 Retire/63 Illegal，峰采样RSS5,582,816 kB/VmHWM5,683,332 kB、当时MemAvailable125,836,640 kB、短尾trace精确源区间[3292086468,3292348442)，无最终JSON/止损。两项目标仍按原7200秒预算运行，旧56cc唯一完成库存仍57/77。

a040 `RFWVVTYPE`自动90分钟点触发资源样本12:12:03 UTC、采集12:12:05，实际elapsed5404.06秒；`rfwvvtype-nan-reduction-a040-2h-20260927-c/evidence/checkpoint-090m.json` SHA-256 `8c670524…d441`固定局部Retire639/Illegal1,135/non-encodable3，较60分钟点新增196/248/0、末100为66 Retire/34 Illegal，峰采样RSS3,394,716 kB/VmHWM3,480,080 kB、最低MemAvailable120,218,080 kB、短尾trace精确源区间[2496161642,2496423657)，无最终JSON/资源止损。继续原7200秒全域运行，局部路径不计完成。

a040 `RFVVTYPE`自动90分钟点触发资源样本12:27:42 UTC、采集12:27:43，实际elapsed5406.02秒；`rfvvtype-nan-reduction-a040-2h-prepared-20260927/evidence/checkpoint-090m.json` SHA-256 `03db0ca6…58b4`固定局部Retire1,039/Illegal2,502/non-encodable3，较60分钟点新增369/562/0、末100为36 Retire/64 Illegal，峰采样RSS6,526,956 kB/VmHWM6,742,304 kB、最低MemAvailable119,125,684 kB、短尾trace精确源区间[4711970151,4712232060)，无最终JSON/资源止损。两目标90分钟watcher均正常退出，原求解继续，旧56cc完成库存仍57/77。

a040 `RFWVVTYPE`于12:42:05 UTC达到7200秒外限：supervisor无外部信号、实际wait timeout child124，历时7200.76秒，make/监控exit2，无最终JSON或资源止损。小账本`rfwvvtype-nan-reduction-a040-2h-20260927-c/evidence/RFWVVTYPE-timeout-audit.json` SHA-256 `5ea8a749…2066`记录局部Retire745/Illegal1,210/non-encodable3、残缺trace2,709,679,027字节、1,377资源样本峰RSS3,607,544 kB、最低MemAvailable119,570,472 kB；日志未见panic/Z3Unknown/SMT timeout模式。该目标不计自然完成；残缺trace未作全域守恒，原90分钟固定前缀另存。

fc4 valid_reg_group末尾相等候选`fc4ce909…86415`已获完整IR/CPP独证`b2fcac07…9be6f`与strict/source独证`618b90ef…f888`，正式模型层交接sidecar`d52b9322…892c`；**官方FVVMTYPE/FVFMTYPE仍须等待新67 helper及89整指令实际回归独证**。单独的同e7ba/518运行时`FVFTYPE` Z3诊断由performance准备，prepared manifest`4baff1e1…1e591`、plan`a3efd81d…d6aff`，只替换raw fc4 IR及77活跃strict，2归档保持d012；初次未启动的CLI解析拒绝留在preparation/attempt-1，最终prepared stage已修复复验。12:48:19 UTC已启动独立stage`z3-diagnostic-fc4ce-fvftype-20260927/`：stage cwd中supervisor/isarch实际argv为1800/1740/30秒、`-j1`×2、全输入域/完整ITRACE，首5秒资源样本先于目标，诊断环境变量只指向本stage JSONL且文件已增长，96/48GiB保护有效。此为**非官方第三路诊断**，不占新67/89尚未放行的官方目标结论，也不计57/77库存。

a040 `RFVVTYPE`于12:57:40 UTC亦达到7200秒外限：supervisor无外部信号、实际wait timeout child124，历时7201.04秒，make/监控exit2，无最终JSON或资源止损。小账本`rfvvtype-nan-reduction-a040-2h-prepared-20260927/evidence/RFVVTYPE-timeout-audit.json` SHA-256 `7bfa96ef…62e3`记录局部Retire1,389/Illegal2,782/non-encodable3、残缺trace5,600,260,763字节、1,376资源样本峰RSS6,872,184 kB、最低MemAvailable109,803,524 kB；日志未见panic/Z3Unknown/SMT timeout模式。两条a040官方目标均无完整JSON，不计完成，旧56cc库存仍57/77；残缺trace不作全域守恒。两官方slot已释放，fc4新官方队列仍待实际回归门齐。

441c `VFUNARY1`于09:40:45 UTC达到7200秒外限，supervisor实际wait timeout child124、无外部信号，历时7200.64秒，make/监控exit2、无最终JSON或资源止损。最终局部账本`vfunary1-lmul-unary-441c-prepared-20260927/evidence/VFUNARY1-timeout-audit.json` SHA-256 `aa24d529…3d78`记录Retire317/Illegal1,615/non-encodable3、残缺trace2,484,724,725字节、1375样本峰RSS4,346,644 kB、最低MemAvailable111,791,268 kB，日志未见panic/Z3Unknown/SMT timeout模式；源完成库存不变。

nan+reduction新候选此时只有完整构建，尚缺候选封装、严格坐标迁移与fullIR/strict/source双独审，不能用于官方求解。空位按root备用排程启动已独立准备的nan86f `FVFMTYPE`：stage`fvfmtype-nan-unbox-86f-prepared-20260927/`与nan86f `FVFTYPE`使用同IR、517源码、79严格配置及双审sidecar，复用同release binary `b42ac4f5…47e7`，来源记录`evidence/single-binary-reuse.json` SHA-256 `c5d3c0ad…2151`；1800/1740/30秒dry-run无execution limits，plan SHA-256 `bbd7ecc7…00a4`。09:44:06 UTC已核stage cwd中的supervisor与isarch真实argv为`-j1`×2、R1/全符号域/完整ITRACE，启动前5秒96/48GiB监控有效；与持续运行的nan86f `FVFTYPE`合计两官方目标。该旧56cc目标曾资源信号15而无完整预算结论，因此本轮只按当前真实退出/完整JSON裁定。
