# E1–E4：第一批原址重放与前置阻塞（2026-11-07）

**结论：E1 限定 PASS，E2 限定 PASS；E3、E4 阻塞。** E1 两条 Isla 样本各跑 MPRV 和真实 S 态，共 4/4 agree；E2 两条样本共 2/2 agree，叶 PTE 回读不变。全部 unittest 95/95 通过。未发现本批输入的 RTL 与模型分歧。

本轮没有完成整条 P0 链。按 [design v2 §10](design.md#10-验收与实验修订-v1-8)，完整 E-cfg 是 E3/E4 的前置；当前设备判死、IR 对齐及平台 lock 均未就绪。遵守“前置不满足即记录阻塞”，未启动 E3，也没有绕过 E3 做 E4 的 20 条或全量试跑。E1/E2 是不依赖设备访问的限定探针，不代表完整 E-cfg 已通过。

| 实验 | 来源输入数 | 实际运行数 | PASS / agree | FAIL | 阻塞 |
| --- | ---: | ---: | ---: | ---: | --- |
| E1 | 2 | 4 | 4 | 0 | 无；仅本批 Sv39 LOAD |
| E2 | 2（LOAD 与 E1 PF 共用一条） | 2 | 2 | 0 | 无；仅本批 A=0 / D=0 |
| E3 | 未具体化；STORE 候选 92 形状 | 0 | 0 | 0 | 全项 E-cfg / lock 未通过 |
| E4 | 1204 条原始语料，只读核验 | 0 | 0 | 0 | E3 未通过、平台未对齐 |

E1/E2 的其他桶均为 0：xs!=expected、xs!=nemu、framework-abort、other-failure、timeout、limit、构建期拒绝。另有 6 次只读 REF 观测重跑，均 agree，单列为证据，不增加来源输入数。E3/E4 没有运行桶；0 FAIL 不表示通过。

## E1：MPRV 与真实 S 态

来源是 `output/ecfg/sv39-load/samples.jsonl`，sample_id=124（成功）、285（A=0 页异常）。保持样本中的地址、PTE、GPR、SUM/MXR 和 Isla 结果；不调用历史 E0 的 relocate_sample，不规范化 PTE。期望的 rd 取 post_registers.x2，异常 cause/tval 取 result。独立 pt_decode 只用于检查输入及选择探针，不作为 C2 期望来源。

真实 S 态使用 mret 进入，取指映射放在根表槽 2（地址 0x80200010，1 GiB RX、U=0、A=D=1）；样本 VA=0x20000000 使用槽 0。构建前检查新槽不与任何样本内存重叠，样本 PTE 完全不变。成功后用专用 s_return 处的 ecall 返回 M 态，核对 cause=9、mtval=0、mepc=s_return，再检查 rd 和内存。原异常路径仍检查 mepc=payload_ins。

比较元组是被测指令的 `(cause, tval, mepc 的指令标号, rd)`，另检查所有原样本内存。成功指令没有异常 mepc，记作空；S 态成功后的 ecall 是 harness 返回机制，原始 CSR 另外保留。不能直接比较两份 ELF 不同的绝对 PC 或返回 ecall 的 cause。

| 样本 | MPRV / S 比较元组 | 原样本内存回读 | 结果 |
| --- | --- | --- | --- |
| LOAD 124 | (0, 0, 空, 0) / 相同 | 两边均符合 Isla post_memory | PASS |
| LOAD 285 | (13, 0x20000000, payload_ins, 0) / 相同 | 两边均符合 Isla post_memory | PASS |

只读 REF 代理确认：payload 前 MPRV 入口 mode=3、MPRV=1、MPP=1；真实 S 入口 mode=1、MPRV=0。原始 CSR、入点状态、归类及比较元组保存在 [observer-results.json](../../output/e1-e4/observer-results.json)。普通运行直接使用原 SO，观测重跑另用只读转发代理。REF 的数据回读指令也经过正常 C1 比对；PTE 不变由 C2 检查，不把 PF 的 C1 一致独立当作验证。

## E2：A/D 行为

| 输入 | 叶 PTE 地址 / 初值 | Isla 期望 | emu 与 NEMU 自检 |
| --- | --- | --- | --- |
| LOAD 285，A=0、D=1 | 0x80200000 / 0x93 | cause=13、tval=0x20000000、mepc=payload_ins | agree；PTE 不变 |
| STORE 34，A=1、D=0 | 0x80200000 / 0x4f | cause=15、tval=0x20000000、mepc=payload_ins | agree；PTE 不变 |

两例的 PPN=0，模型在翻译阶段因 A/D 得到 PF，未发出低地址数据访问。此结论只验证该 PF 与 PTE 不变，不证明低地址 PMA/设备已对齐。没有 ABORT，不新增已知差异条目。

## 每次主运行的退出 PC

以下全部匹配精确 good_trap_ins；不是依据 GOOD 文本或退出码单独判定。运行前后均校验 ELF SHA-256。

| 目录（output/e1-e4/ 下） | sample_id | 退出 PC | 符号 | 桶 | 秒 |
| --- | ---: | --- | --- | --- | ---: |
| e1-success-mprv | 124 | 0x80000184 | good_trap_ins | agree | 3.127 |
| e1-success-s | 124 | 0x800001d4 | good_trap_ins | agree | 3.024 |
| e1-pf-mprv | 285 | 0x8000016c | good_trap_ins | agree | 3.076 |
| e1-pf-s | 285 | 0x800001a4 | good_trap_ins | agree | 3.024 |
| e2-a0-load-mprv | 285 | 0x8000016c | good_trap_ins | agree | 3.581 |
| e2-d0-store-mprv | 34 | 0x80000164 | good_trap_ins | agree | 4.077 |

每个目录包含 program.S、program.elf、objdump.txt、symbols.txt、build.log、case.json、difftest.log、result.json、observed.log。主结果总账为 [results.json](../../output/e1-e4/results.json)，汇总为 [summary.json](../../output/e1-e4/summary.json)。

## E3/E4：阻塞及样本口径

1. **设备 PMA 与 excluded 未签收。** [E-dev](e-dev-results.md) 记录原设备配置导致锁定 isarch 的枚举登记 panic；excluded 的设备根探针另有 partial/errors=1，设备数据分支未完成。当前 config-xs.toml 只有 RAM PMA，没有 v2 要求的完整设备地图，不能把其低端 AF 当作 XiangShan 的真实期望。未修改属性、关闭合并或换运行器绕过。
2. **Svrsw60t59b 的 IR 对齐未做。** 当前 IR SHA 仍为 c0e4661a…31c0，允许 [60:59]；E-cfg-b 尚未执行。本任务禁止改 IR，不能在本轮补齐。
3. **缺同一平台生成侧 lock。** 现有 done.json 可核对 config/IR/isarch 文件哈希，但没有 v2 的 profile.lock.json、platform_gen_sha256，也没有完整 profile 生成流程。不能把事后拼出的哈希冒充生成时已有的绑定。
4. **E4 依赖 E3。** v2 要求“E3 的每形状代表＋N1–N3”，不能把全部 class_cap=1 行直接当成已复验代表。原 E-cfg LOAD 的 104 形状与 STORE 的 92 形状分属不同场景，不混成一组签收。

指定语料位于外部 isla-enumerate 工作树的 `target_edev/logs/representative-stability/final-T32/samples.jsonl`，只读使用。SHA-256：`bad0a0998055c75f2a6d84f86b931c9848e68c2408e05463667b2fdb8d86d241`。确认 1204 条、92 种 Sv39 STORE 形状，class_cap=1；done.json 绑定的 config、IR、运行器当前实物哈希全部核对一致。其修复后运行器为 `610df539…a3db`，与 E1/E2 使用旧 E-cfg 样本的生成器 `496f63b6…0657` 不同；未替换或执行外部运行器。

按 design 优先口径，后续 E4 应先对这批语料每形状选一个代表，完成 E3 后再加负对照。按每形状最小 sample_id 已准备 **92 条候选清单**（没有具体化、没有 check-samples、没有 emu 运行）：[e4-representatives-not-run.json](../../output/e1-e4/e4-representatives-not-run.json)。如以后额外跑全部 1204 条，应另列扩展批次，不能覆盖代表批次的前置。

| 只读检查项 | 计数 | 解释 |
| --- | ---: | --- |
| PTE [60:59] 非零 | 976 条 | 配置未对齐线索；不等于 976 条必有可观察分歧 |
| 低地址 AF 目标 | 146 条 | 按 v2 区域表全部属于 device，没有落入 0x39002000–0x3a000000 hole |
| 未对齐超级页 | 40 条 | 语料具备代表候选，但未上 emu |
| PBMT 非零 | 22 条 | 同上 |
| N=1 且不构成 64K NAPOT | 22 条 | 同上 |

计数可能重叠。逐样本严格解码和当前 IR 的结果一致，是准备性核账，**不是**完整 profile 下的 C3 PASS，也不是 E3 的“恰好一条路径接纳”结论。完整检查见 [inspection.json](../../output/e1-e4/inspection.json)。

### 典型问题与归因

| 对象 | 证据与影响 | 分类 | 退出 PC / 符号 |
| --- | --- | --- | --- |
| final-T32 sample 0 | 指针指向 PA=0；Isla 以 pte_read_pma_access_fault 返回 E_SAMO_Access_Fault，v2 将 PA=0 归设备 | 配置未对齐；不能直接给硬件设 AF 期望 | 未运行，无退出 PC |
| final-T32 sample 4 | L1 PTE=0x0800000000000001，[60:59] 非零；当前 IR 继续遍历 | 配置未对齐线索；有重叠错误，不预判硬件最终结果 | 未运行，无退出 PC |
| E1/E2 主样本 | 无失败样本，6 次主运行全部精确退出 good_trap_ins | 本批未发现真实 RTL 与模型分歧 | 见上表 |
| 辅助 NEMU 独立启动 | 6 次未经 emu 完整初始化，2000 指令内未到出口；保留全部尝试，不计运行桶 | 诊断启动流程问题，具体原因未查；不归 RTL 分歧 | 无退出 PC；native-summary.json |

辅助诊断后停止该支线，使用既有 E0 的只读 SO 转发方法，随真实 emu 初始化观察 REF。6 次观测重跑全部 agree。代理只读取 difftest_regcpy 返回值并原样转发 guided_exec；不改寄存器、ExecutionGuide 或 SO 文件。源码及代理产物在 output/e1-e4/，哈希在 observer-provenance.json。

## 实施、验证与复现

仅扩展 paging_replay.py 的 E1/E2 定向入口：原址验证、Isla 后态期望、STORE 写后回读、真 S 态 mret/ecall、独立取指映射。历史 convert 子命令仍是 E0 的重定位实现，**本轮不调用，不能用作 v2 转换入口**。run_probes.py 调用 directed_probe_case/build_case/run_probe；不表示完成 profile/convert 的全部 v2 实现。

新增 3 项测试覆盖原址不改写、STORE null 初值反码填充和真 S 态链接；加原有测试共 95 项全部通过，见 [unittest-final.log](../../output/e1-e4/unittest-final.log)。开发中的测试失败保存在 unittest-development*.log，已修正后跑最终整组，不以失败日志标 PASS。

从根目录执行；外部路径按工作树相对位置表达。run_probes.py 为避免污染证据，会拒绝覆盖已有 result.json；复跑时先复制驱动，将输出根改为新的空目录。观察脚本和汇总脚本需使用相同新目录。

```sh
export PT_DECODE_DIR="$(cd ../isla-enumerate/agents/path_merge_call_support/pt_decode && pwd)"
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$PWD/output/e1-e4/tmp"
export XDG_CACHE_HOME="$PWD/output/e1-e4/cache"
python3 output/e1-e4/audit_inputs.py
python3 output/e1-e4/run_probes.py
# 下列相对路径指向主仓已有的只读 NEMU SO：
gcc -shared -fPIC -Wall -Wextra -Werror -o output/e1-e4/nemu_observer.so \
  output/e1-e4/nemu_observer.c -Wl,--no-as-needed \
  ../../difftest-xiangshan/xiangshan/ready-to-run/riscv64-nemu-interpreter-so -ldl
python3 output/e1-e4/observe_probes.py
python3 -m unittest discover -s difftest-xiangshan/tests -v
python3 output/e1-e4/summarize.py
```

E1/E2 的逐例实际运行命令在 result.json.command，构建命令在 case.json.build_command；形式是 `emu -i program.elf --diff riscv64-nemu-interpreter-so`。E3/E4 未运行，没有伪造的 check-samples 或 emu 命令结果。

### 冻结输入

| 资源 | SHA-256 |
| --- | --- |
| E-cfg isarch | `496f63b6f8997a6aa74da56ac6c2631c6a1f7ca6efb046dab455799a36570657` |
| rv64d.ir | `c0e4661a73888c56438a6f76059370667d141a026502d0511291586067bd31c0` |
| config-xs.toml | `40d728925731cd7a8d7308b4f1f0b0f61940a79881ad4955780c48a366704129` |
| pt_decode.py | `2ddc69915d0cde369759160182dd34d2ea7191fffc258ed93ab167645a4d7e47` |
| emu | `871416926352103051fce0efac7bf219602547c0852d5aa24af0c01a35ea85ee` |
| NEMU SO | `9188e7dda30709962f0bfbc1dd87cea73d88a18c92c30892f93ed529c22def43` |

GCC：14.2.0；XiangShan 版本沿用 E0 已记录的 a13efc8775，受测身份以 emu/NEMU 哈希为准。主运行前后核对冻结输入未变，见 frozen-inputs-unchanged.json。emu 串行（并发 1），每次外部 120 秒进程组止损，最长主运行 4.077 秒；没有 15 分钟无进展。全部临时目录、缓存、ELF、日志及代理编译产物在本工作树 output/e1-e4/。

未改 config-xs.toml、rv64d.ir 或任何 isarch；未重编 emu/NEMU，未做 Git 写操作。保留已有 e-dev-results.md 修改和全部旧 output/。本轮按用户限定范围，只新增本结果文档，未改 status.md、specs/TODOs.md 或 agents/findings.md；本报告与 summary.json 是本轮状态入口。历史 E0/E-exit 的已链接 ELF 证据保留，不能将其当作本轮修改后生成器的全项复验。
