# Fuzzing P1b 扩展 campaign 结果（2026-11-07）

**四场景5000个变异体全部完成重放及逐例核账：4986 agree、14 原始 mismatch；3 个新形态待查。unittest 119/119 PASS。新形态的简化输入已通过 J1 并重新实跑，三方 cause 见下表。**

| 场景 | 变异体 | agree | mismatch | 新形态数 | 丢弃数 | 形状×切片桶增量 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sv39-store | 1000 | 996 | 4 | 2 | 228 | +848 |
| sv48-load | 1000 | 997 | 3 | 0 | 209 | +1153 |
| sv48-store | 1000 | 999 | 1 | 0 | 256 | +932 |
| sv39-load | 2000 | 1994 | 6 | 1 | 712 | +1297 |
| 合计 | 5000 | 4986 | 14 | 3 | 1405 | +4230 |

agree 要求 emu 与独立 NEMU 都符合经 J1 确认的 Isla 期望；mismatch 保留原始观察。覆盖增量各自相对该场景种子库，四场景的键包含模式和访问类型，可相加；不是实际守卫类覆盖。
Sv39 LOAD 相对原 P1 另新增 **817** 个桶，P1 与 P1b 累计 **5800** 个桶；本批2000例中有 **94** 例具体输入与原500例重复。随机种子不同不表示两批输入完全不相交。

## 分歧归并与例子

共 14 个形态，其中 11 个符合已知的“叶PPN超宽且A=0”条件，另 3 个列为新形态待查。形态键保留模式、访问类型、页表级别、叶权限、A/D、结构位、PPN区域桶及三方cause，忽略具体地址、G与RSW；不同形态不等于不同bug。

加载原 P1 的两条精确已知输入键，本批过滤 1 例；没有新增过滤项、整类忽略或覆盖原始结果。新形态不作规范裁决。

| 新形态 | 原代表 | 简化后末级实际PTE | emu / NEMU / Isla cause | 输入字节变化 | 复现证据 |
| --- | --- | --- | --- | --- | --- |
| sv39-load-02 | mutant-0153 | L0 `0x0000400000000009` | 5 / 13 / 13 | 48→24 | [输入](../../output/fuzz-p1b/minimal-new/sv39-load-02/input.jsonl)、[证据](../../output/fuzz-p1b/minimal-new/sv39-load-02/reproduction.json) |
| sv39-store-01 | mutant-0119 | L1 `0x0000400000000003` | 7 / 15 / 15 | 32→16 | [输入](../../output/fuzz-p1b/minimal-new/sv39-store-01/input.jsonl)、[证据](../../output/fuzz-p1b/minimal-new/sv39-store-01/reproduction.json) |
| sv39-store-04 | mutant-0793 | L2 `0x0000400000000019` | 7 / 15 / 15 | 16→8 | [输入](../../output/fuzz-p1b/minimal-new/sv39-store-04/input.jsonl)、[证据](../../output/fuzz-p1b/minimal-new/sv39-store-04/reproduction.json) |

三个新形态都同时含超宽叶PPN与A=0，但pt_decode记录的失败原因是权限：LOAD例R=0、X=1且MXR=0；两例STORE均W=0，其中一例R=1，另一例X=1。SUM=1，U位本身不构成这三例的权限阻挡。按这一具体失败原因与已知accessed_update_disabled形态分列，新形态的规范判断待查。

简化输入只保留实际读取内存，清除G/RSW与叶PPN冗余位，保持本轮形态、固定前态及页表级数。每份输入都经锁定isarch的J1检查，恰好一条路径一致，再以emu和独立NEMU重放验证相同形态。它们是在这一简化范围内保留的复现输入，未证明全局最小。构建时P0会重新加入检查错误寻址的诱饵槽。

已知条件例子：Sv48 LOAD mutant-0589 的L0 PTE为 `0x000040000000000f`，PPN超宽且A=0，emu cause 5、独立NEMU与Isla cause 13。STORE的相应观察为emu cause 7、独立NEMU与Isla cause 15。这里只按已知条件归类，不从cause相同推断RTL根因已确认。

完整形态、每组计数与最简原代表见 [归并结果](../../output/fuzz-p1b/triage-forms.json)，逐场景合计见 [核账汇总](../../output/fuzz-p1b/triage-summary.json)。每个场景的triage-ledger.json保留逐例输入/ELF身份、原始桶、三方cause及NEMU末态。

## 生成、丢弃与覆盖

| 场景 | 种子 | 随机种子 | 尝试 | M1 / M2 / M5 | 重复丢弃 | 平台拒绝 | J1丢弃 | 形状 | 桶 |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |
| sv39-store | 380 | 20261108 | 1228 | 328 / 292 / 380 | 226 | 2 | 0 | 120→128 | 3807→4655 |
| sv48-load | 1122 | 20261109 | 1209 | 344 / 272 / 384 | 207 | 2 | 0 | 174→188 | 7028→8181 |
| sv48-store | 606 | 20261110 | 1256 | 346 / 269 / 385 | 254 | 2 | 0 | 154→162 | 6096→7028 |
| sv39-load | 728 | 20261111 | 2712 | 626 / 536 / 838 | 703 | 9 | 0 | 136→148 | 4423→5720 |

四场景全部2836个种子原样J1重判一致，每场景各有一个错误期望负对照检出inconsistent。LOAD的N3翻转rd期望、STORE的N3翻转写后内存期望，均落入对应xs!=expected原因。J1原始partial/errors与逐查询excluded证明保留在各judge目录；这些路径终止不算变异丢弃。所有批次的执行/SMT/模型查询超时与unfinished-paths均为0。

覆盖只记录“形状×切片桶”，父种子类号只作来源，变异体class_id为null；没有反馈调度、实际守卫类推断或P2/J1′改造。

## 接续过程与运行限制

接手时Sv39 STORE已有完整1000例；先逐例核对其ELF、日志、独立NEMU轨迹及原始分桶，再保留该场景。Sv48 LOAD的driver日志停在80例，但账本实际已有85例且缺summary；只删除其目录与driver日志后，按相同随机种子从头重跑，见 [清理记录](../../output/fuzz-p1b/restart-cleanup.json)。

Sv48 LOAD完成后，Sv48 STORE的监控驱动遇到编译器已删除的临时.s文件，抛FileNotFoundError退出；此时151例已完成，8例在途。修复进度扫描忽略tmp/cache并容忍文件消失后，保留151例原结果，将8个未完成目录移动到 [中断证据](../../output/fuzz-p1b/interrupted-sv48-store/event.json)，复用原1000个J1已接纳输入续跑849例。没有删除这些证据、重生成输入或把这8次中断计入变异丢弃。

四场景按Sv39 STORE、Sv48 LOAD、Sv48 STORE、Sv39 LOAD顺序运行；emu最多8并发，isarch每批-T32且本批最多1个并发。驱动15秒检查一次，15分钟无进展即停止；没有触发该停止条件。Sv48 STORE的replay_seconds按首个program.S的mtime至续跑结束估计，包含中断与恢复，不能直接当连续运行吞吐。

后台使用nohup+setsid，并保留运行会话。初次试启动证明工具沙箱会在启动命令退出后回收后台进程，因此未能验证跨工具会话断线存活；本轮在监控会话保持期间完成。命令、返回码与耗时见 [批次账本](../../output/fuzz-p1b/driver-results.json)，驱动中断与接续日志分别为resume-driver.log、resume-driver-2.log。

## 验证、版本与复现入口

最终逐例核账验证5000例的唯一输入、J1接纳、ELF哈希、日志重新归类、独立NEMU轨迹及cause、形态归并、覆盖重算与平台锁定；结果见 [最终审计](../../output/fuzz-p1b/final-audit.json)。ecfg3逐项身份与各场景readonly-before一致，原P1产物及既有paging_fuzz.py/test_paging_fuzz.py改动保持接手时字节。

冻结版本：IR `3f16d5e7…f0a67b`、isarch `610df539…a3db`、emu `87141692…a85ee`、NEMU `9188e7dd…def43`；paging_fuzz.py `737a6106…af8d3`。各场景manifest.json保留完整哈希、文件身份、随机种子、判官模板与观察器身份。没有修改Sail、Isla、pt_decode、旧产物或锁定二进制，没有Git写操作；新增产物及测试临时文件均在本工作树output/fuzz-p1b内。

接续与最终unittest discover均为119/119 PASS；日志见 [最终测试](../../output/fuzz-p1b/unittest-final.log)。最终命令在difftest-xiangshan/tests下执行，并设置用户指定PT_DECODE_DIR、指向本批tmp的TMPDIR和PAGING_TEST_OUTPUT_DIR。

批次脚本 [run_all.py](../../output/fuzz-p1b/run_all.py)保留已完成场景；[triage.py](../../output/fuzz-p1b/triage.py)重建核账与归并；[minimize_new.py](../../output/fuzz-p1b/minimize_new.py)生成新形态简化复现。重跑campaign或简化复现须使用新输出目录，避免覆盖已完成证据。

复验命令（先从工作树根目录执行；输出仍在本工作树）：

```sh
campaign_root="$PWD"
export PYTHONDONTWRITEBYTECODE=1
export PT_DECODE_DIR="$(realpath ../isla-enumerate/agents/path_merge_call_support/pt_decode)"
export TMPDIR="$campaign_root/output/fuzz-p1b/tmp"
export PAGING_TEST_OUTPUT_DIR="$campaign_root/output/fuzz-p1b/tests"
cd difftest-xiangshan/tests
python3 -m unittest discover -v
cd "$campaign_root"
python3 output/fuzz-p1b/triage.py
```
