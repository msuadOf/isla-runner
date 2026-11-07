# Fuzzing P1 完成结果（2026-11-07）

**结论：P1 六项全部完成，无当前阻塞。728 个种子原样重判通过；500 个变异体全部通过 J1 并完成重放，原始结果为 498 agree、2 个优先级差异。后续按具体输入过滤这两例，保留 2 个代表，未过滤 mismatch 为 0。形状 × 切片桶 4423→4983；unittest 115/115 PASS。**

用户已澄清：P1 按设计 B.4 记录“形状 × 切片桶”；父种子守卫类只是来源。变异体实际类号留到 P2 的 J1′，不修改 Isla。文末原阻塞记录保留为历史，已由此澄清解除。

| 项目 | 实施与验证 | 本批结果 |
| --- | --- | --- |
| 种子读取、绑定与去重 | 完成，PASS | 728 输入、728 唯一代表、728 个来源守卫类，种子重复0；原样 J1 重判728/728一致 |
| M1/M2/M5 与 J2+J1 | 完成，PASS | M1 168、M2 140、M5 192；500/500 恰好一条一致路径；M5 192/192 result及形状不变 |
| convert/build/run/classify | 完成，限定 PASS | emu/NEMU 重放500/500；原始498 agree、2 xs!=nemu；两例差异见下文，不写成500原始agree |
| 精确 mismatch 过滤与归并 | 完成，PASS | 2 个具体PTE键、2例过滤、每组保留1个代表；未过滤0；没有整类忽略 |
| 形状 × 切片桶反馈 | 完成，PASS | 136→142形状；4423→4983覆盖元组，增加560；拟入语料331例，只记录，不参与本轮选择 |
| 500例campaign与统计 | 完成，PASS | 610次尝试→500个不同变异体；重复输入110；正式批平台拒绝0、判官不一致丢弃0 |

## 两例差异：样本照常运行，之后精确过滤

例如 [mutant-0083](../../output/fuzz-p1/campaign-20261107-r3/replay/mutant-0083/result.json) 的 L0 PTE 是 `0x000040000000000b`：PPN 达到 `2^36`，即 PA 达到 `2^48`，同时 A=0。Isla 与独立 NEMU 报 PF **13**，XiangShan 报 AF **5**。这是[设计稿 A.3](design-gaps-and-fuzzing.md)已经列出的多故障优先级组合。本轮记录实际行为，不裁决规范合规性，也不宣称发现新的 RTL bug。

| 代表 | 实际故障PTE | Isla / 独立NEMU / XiangShan cause | 原始桶 | 后续过滤计数 |
| --- | --- | --- | --- | ---: |
| mutant-0083 | L0 `0x000040000000000b` | 13 / 13 / 5 | xs!=nemu | 1 |
| [mutant-0095](../../output/fuzz-p1/campaign-20261107-r3/replay/mutant-0095/result.json) | L2 `0x000040000000009f` | 13 / 13 / 5 | xs!=nemu | 1 |

过滤键保存**整条实际walk的PTE级别、地址和值 + 两侧观察cause + 与Isla一致的一方**。本轮两键的一致方都是 NEMU。表只匹配这些具体观察值；不同 PTE、cause 或一致方不会被同一条记录过滤。未知 cause 或未完成 C2 且缺少充分DUT证据时，不猜测一致方，也不允许登记为已知过滤项。

重放时的已知表为空，因此[原始summary](../../output/fuzz-p1/campaign-20261107-r3/summary.json)仍保留498/2及filtered=0。全部样本运行后，按A.3的明确组合登记[已知表](../../output/fuzz-p1/known-mismatches.json)，再用同一个 `MismatchTable` 对账本做后续过滤；[后续汇总](../../output/fuzz-p1/post-filter-summary.json)记录filtered=2、unfiltered=0、每组计数及代表。[逐例过滤记录](../../output/fuzz-p1/post-filter-results.json)和[优先级证据](../../output/fuzz-p1/known-priority-evidence.json)均保留。没有覆盖或修改原始重放结果。

观察器复用 ecfg3 的只读 `nemu_native_observer.so`，转发同一锁定 NEMU SO，并在真实初始化状态的 payload 前 fork 独立子进程。独立分支不调用 guided_exec。500例中，498例双方与期望一致，2例仅独立NEMU与期望一致；没有把页异常强制同步当成NEMU独立判断。

## 生成、判官与覆盖

| 算子 | 尝试 | 不同变异体并重放 | 重复去重 | 平台拒绝 | 判官不一致丢弃 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 flag位翻转 | 204 | 168 | 36 | 0 | 0 |
| M2 PPN重排 | 203 | 140 | 63 | 0 | 0 |
| M5 未测位扰动 | 203 | 192 | 11 | 0 | 0 |
| 合计 | 610 | 500 | 110 | 0 | 0 |

M1 在实际读取的PTE上翻转1–2位，覆盖常规flag、N/PBMT/RSW/reserved；没有旧R4/R7/R8屏蔽。M2包含子树页搬迁66、边界43、别名31。M5扰动G及RSW[9:8]；result和形状保持不变，PTE与数据地址重合时，rd仍由J2重算。固定VA场景本轮使用PPN重排，VA重排不在本批内。

J2补齐新PTE/数据读取，生成result、rd、完整寄存器后态及实际内存足迹，并用标准分页适配后的pt_decode严格解码。TLB后态按冻结模型已有的 `translate_TLB_miss/add_to_TLB` 规则预测，包含最终数据AF前已经发生的TLB填充。全部728个原始种子的result、完整寄存器后态及内存足迹重新预测后逐项相同，见[J2原始样本重建](../../output/fuzz-p1/j2-seed-reconstruction.json)。后端不内嵌求解器；最终期望须经锁定isarch的J1确认。

| J1批 | 输入数 | 一致 / 故意错误期望 | isarch批耗时 | 每输入均摊耗时 |
| --- | ---: | --- | ---: | ---: |
| 原样种子＋判官负对照 | 729 | 728 / 1个inconsistent | 90.059秒 | 123.538毫秒 |
| 变异体 | 500 | 500 / 0 | 54.011秒 | 108.023毫秒 |

均摊时间包含整场景符号执行，不是逐例独立SMT计时。变异与J2预测合计平均7.882毫秒；逐例时间在[变异记录](../../output/fuzz-p1/campaign-20261107-r3/mutations.json)。J1两批均使用 `-T 32`，原始summary保留partial/errors=5；每批5次终止均有逐查询excluded证明，harness重叠不可满足，其他执行/SMT/终值查询超时及unfinished-paths均0。这10次路径过滤不计入变异体丢弃。完整命令、原始summary、证明和输入哈希见[种子批](../../output/fuzz-p1/campaign-20261107-r3/judge-seeds/done.json)与[变异体批](../../output/fuzz-p1/campaign-20261107-r3/judge-mutants-00/done.json)。

emu并发8，500例重放阶段墙钟 **703.592秒**，吞吐 **0.711例/秒**；包含构建、观察器和账本写入。逐例emu耗时合计5544.615秒，平均11.089秒。额外的N3负对照不计入这500例：只翻转已通过判官的成功样本的ELF期望rd一位，实跑得到 `xs!=expected(rd)`，见[负对照](../../output/fuzz-p1/campaign-20261107-r3/negative-N3/result.json)。

覆盖元组为 `(pt_decode形状键, PTE级别, 字段, 取值桶)`。flag记录0/1，其他小字段记录具体取值，PPN按根表、页表区、DRAM低端/中段/顶端、≥2^43、≥2^48等区域分桶。142个形状不表示142个实际守卫类。变异体metadata的class_id为null，父种子类号只在source里保存。全部桶见[coverage.json](../../output/fuzz-p1/campaign-20261107-r3/coverage.json)，331条拟入语料记录见[feedback.json](../../output/fuzz-p1/campaign-20261107-r3/feedback.json)；没有反馈调度、能量分配或实际类号推断。

## 实现、TDD与版本证据

- 新模块：[paging_fuzz.py](../../difftest-xiangshan/paging_fuzz.py)；测试：[test_paging_fuzz.py](../../difftest-xiangshan/tests/test_paging_fuzz.py)。原重放测试仅增加可选 `PAGING_TEST_OUTPUT_DIR`，将本轮测试临时文件放到fuzz-p1目录。
- 15项新回归加既有100项，完整discover **115/115 PASS**，见[最终测试日志](../../output/fuzz-p1/unittest-final.log)。TDD先红后绿日志包括[tdd-red](../../output/fuzz-p1/tdd-red.log)、[驱动红](../../output/fuzz-p1/tdd-driver-red.log)、[别名红](../../output/fuzz-p1/tdd-alias-red.log)、[TLB红](../../output/fuzz-p1/tdd-tlb-red.log)与[观察证据红](../../output/fuzz-p1/tdd-observation-red.log)。
- 全部种子来自只读ecfg3 `class_cap=1` Sv39 LOAD导出，SHA `8ea48f49…90e2c`；新IR `3f16d5e7…f0a67b`、isarch `610df539…a3db`、emu `8714169…a85ee`、原NEMU `9188e7d…ef43` 沿用[ecfg3版本](ecfg3-results.md)。生成侧哈希 `d2820d0f…93451b`、运行侧哈希 `8a6ae719…22147`，文件身份及本轮Python/观察器哈希见[manifest](../../output/fuzz-p1/campaign-20261107-r3/manifest.json)。
- [最终核账](../../output/fuzz-p1/final-audit.json) **PASS**：500例ELF哈希与日志重新归类一致，已检查的result/完整寄存器后态及实际读字节全部保留。P0转换额外初始化的9160字节诱饵均未被模型读取，不覆盖判官绑定字节。
- ecfg3全部旧文件逐项SHA前后相同，锁定输入在运行前后重新验证；没有修改Sail、Isla、pt_decode、旧重放代码或锁定二进制，没有Git写操作。所有新增产物、缓存、临时文件在本工作树的output/fuzz-p1下；没有触发15分钟无进展停止条件。

实际命令如下，从工作树根目录执行；再次运行须换一个新的 `--out` 目录。`apply_known.py/audit.py` 是本批账本工具，绑定r3目录；复现到其他目录时需同步其RUN。

```sh
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$PWD/output/fuzz-p1/tmp"
export PAGING_TEST_OUTPUT_DIR="$PWD/output/fuzz-p1/tests"
export PT_DECODE_DIR="$(realpath ../isla-enumerate/agents/path_merge_call_support/pt_decode)"
python3 -m unittest discover -s difftest-xiangshan/tests -v
python3 difftest-xiangshan/paging_fuzz.py \
  --out output/fuzz-p1/campaign-20261107-r3 \
  --pt-decode-dir "$PT_DECODE_DIR" --count 500 --seed 20261107 --workers 8
python3 output/fuzz-p1/apply_known.py
python3 output/fuzz-p1/audit.py
```

后续同环境campaign可用 `--known-mismatches output/fuzz-p1/known-mismatches.json` 加载两条精确过滤项；不因此屏蔽生成或跳过重放。原始分类始终保留。

## 中间失败与已解除的历史阻塞

首次campaign在原样种子728/728和判官负对照通过后，因多余的“M5必须rd不变”断言停止，未上emu。PTE/数据别名回归先红后绿后移除了该额外限制。日志见[首轮](../../output/fuzz-p1/campaign-driver.log)。

r2生成500例，J1接纳500，但仅304一致、196不一致；M1/M2/M5分别不一致13/49/134。原因是J2漏算TLB后态，而非受测硬件mismatch。这一批未上emu，原始输入、检查报告与[C3分析](../../output/fuzz-p1/campaign-20261107-r2/c3-analysis.json)保留。补TLB回归及完整728例重建后，正式r3重新生成、核对和重放；正式批判官不一致丢弃0，不能将历史196条混入其统计。

最初因覆盖口径冲突而停止的说明原文如下。**用户已经确认按B.4使用形状覆盖；以下“阻塞／未实施”只描述澄清前状态，不是当前结论。**

<details>
<summary>首次阻塞记录（历史，已由用户澄清解除）</summary>

# Fuzzing P1：准备核对与阻塞（2026-11-07，历史）

**结论：种子来源核对完成；P1 实现与 campaign 阻塞。要求中的“守卫类 × 切片取值桶”需要变异体的实际类号，现有 J1 不返回类号。设计稿 B.4 对 P1 明确使用形状代替守卫类。本轮不自行选择替代口径，也不提前实现 P2 的 J1′ 或 P4 的 J3。**

| 项目 | 状态 | 本轮结果 |
| --- | --- | --- |
| 只读核对种子 | 完成 | Sv39 LOAD 728 条，728 个不同的 `(path_signature, class_id)` |
| 种子读取与去重模块 | 阻塞／未实施 | 完成来源核对，尚未写生产模块或测试 |
| 变异、J2 预测与 J1 确认 | 阻塞／未实施 | 生成 0，判官检查 0；未将旧 E3 当作本轮全种子重判 |
| convert/build/run/classify | 阻塞／未运行 | campaign 重放 0/500 |
| 已知 mismatch 过滤表 | 阻塞／未实施 | mismatch 与过滤计数未测，不能写为 0 |
| 守卫类 × 切片桶覆盖 | 阻塞 | 缺少变异体实际守卫类归属；不能沿用父种子类号 |
| 丢弃统计、吞吐与覆盖数字 | 未测 | 未生成变异体，无实测统计 |
| unittest discover | 未运行 | 代码与测试均未修改，不迁用 ecfg3 的历史 PASS |

## 阻塞证据与例子

读取 [ecfg3 的现有检查报告](../../output/ecfg3/sv39-load-e3/check.json)，每条记录只有 `sample_id`、`accepted_paths`、`consistent_paths` 和 `inconsistent_paths`。该报告覆盖 136 个形状代表；它没有接纳路径或守卫类号。原始种子里的类号描述该种子，不能证明变异后仍属于同一类。

例如 M1 翻转 PTE 的 V 位后，页表遍历可能提前报页异常。J1 即使返回恰好一条一致路径，也不说明它与父种子同类。把结果挂到父种子类号下，只能表示“从哪个种子生成”，不能表示变异体实际覆盖了哪个守卫类。

[设计稿 B.4 与 B.6](design-gaps-and-fuzzing.md)已说明这个接口限制：P1 使用“形状 + 切片桶”；P2 才通过 J1′ 获得实际路径与类号。当前任务同时要求真实守卫类覆盖、禁止修改 Isla、禁止提前做 P2+，尚无设计内的实现途径。导出的 `guard_assignment` 也不能直接给新输入分类：守卫条件引用符号号；自行实现表达式求值属于尚未实施的 J3 路径。

需要确认的唯一口径：**P1 是否按 B.4 记录“形状 × 切片桶”，另记父种子守卫类作为来源，并把变异体实际守卫类覆盖留到 P2。** 若必须在 P1 取得真实类号，则需要另行确定接口方案和允许修改的范围。

## 已确定的边界

- 算子沿用设计稿编号：flag 翻转为 M1，PPN 重排为 M2，未测位扰动为 M5。M3 是维度迁移，属于后续阶段。现有场景固定 VA，PPN/VA 项可先实现 PPN，VA 重排 M2′ 留待符号 VA 场景。
- R4/R7/R8 的拒绝和变异屏蔽已被用户推翻，不作为本轮实施要求。保留差异样本，后续按具体 PTE、观察到的 cause 与一致方归并。
- Sail、Isla、锁定二进制和旧产物均未修改；没有 Git 写操作。
- 依据本次任务的“语义问题停下报告，不自行取舍”规则，在覆盖验收口径明确前暂停实施和 campaign。

机器可读核对结果见 [preflight.json](../../output/fuzz-p1/preflight.json)。种子文件 SHA-256 为 `8ea48f49f8c39596cd2b635eb6493f723cc1dfae033743f20793ec7dea790e2c`。本轮仅新增本报告、preflight，并更新本议题 status；没有修改范围外的全仓状态表。

</details>
