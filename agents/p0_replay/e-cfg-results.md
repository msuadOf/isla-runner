# E-cfg：配置对齐实验结果（2026-11-07）

**结论：本轮 Sv39 LOAD 配置对齐实验 PASS。** 新配置正常完成，20 条路径、2404 个守卫类、2404 条样本、104 种页表形状。6376 次 PTE 读取和 544 次数据读取全部位于 `[0x80100000,2^43)`；低端 RAM 与 harness 实际读取均为 0。运行耗时 24.961 秒。

此 PASS 只表示本次输入、配置和样本的生成与地址断言通过。XiangShan/NEMU 重放、STORE、Sv48、完整具体值枚举及模型覆盖均未测，不改变 E0 的验收状态。

## 实施与运行结果

| 项目 | 本轮新配置 | 旧实验配置参考 |
| --- | ---: | ---: |
| 完成路径数 | 20 | 20（历史记录） |
| 守卫类数 | 2404 | 16592 |
| 导出样本数 | 2404 | 16592 |
| pt_decode 形状数 | 104 | 106 |
| path_truncated 路径数 | 0 | 0（历史记录） |
| truncated=true 样本数 | 2382 | 16570 |
| class_cap / path_cap / sample_stride | 1 / 1000000 / 1 | 1 / 1000000 / 1 |
| mode | samples | samples |
| 执行线程 | `-T 64` | `-T 8`（历史记录） |
| 运行耗时 | 24.961 秒 | 未以本轮运行器重测 |
| 解码与地址统计耗时 | 3.419 秒 | 不作性能比较 |
| 退出码 / summary.status | 0 / finished | 本轮未重测 |
| 执行错误 / 执行超时 / SMT 超时 / 未完成路径 | 0 / 0 / 0 / 0 | 本轮未重测 |
| 地址断言 | PASS | 本轮未重测 |

16592 是守卫类数，不是形状数。新配置的守卫类数较历史值减少 14188（约 85.5%），仅作参考：历史数据来自额外开放低端 RAM 的实验配置，运行器版本、线程数及代表模型选择与本轮不构成严格单变量对照。没有为了比较另跑旧配置。

旧形状参考来自 `../isla-enumerate/output/stride-validation/decode-sv39-1/merge/shapes.json`，记录在 [old-reference.json](../../output/ecfg/old-reference.json)。按 pt_decode 的完整 shape_key 比较，本轮观察到旧 106 种中的 104 种；未观察到 L2、L1 `leaf_--x_u0` 的 `superpage_misaligned` 两种，未新增形状。不据此认定两种形状不可达；class_cap=1 与代表值选择不证明形状全集。

2382 个类的类内具体值仍有剩余解，故样本保留 truncated=true；20 条路径的 path_truncated 全为 false。守卫类枚举完成与类内具体值穷举是两件事。本轮按要求只取每类一个代表。执行 `-T 64`；枚举线程沿用默认上限 16，各路径实际枚举工作线程数为 2、4、8、10 或 16。

| 处理器结果 | 样本数 |
| --- | ---: |
| Retire_Success | 544 |
| E_Load_Page_Fault | 786 |
| E_Load_Access_Fault | 1074 |

## 配置改动与理由

只修改 [config-xs.toml](../../output/ecfg/config-xs.toml)，原件保留。完整差异在 [config.diff](../../output/ecfg/config.diff)。

| 声明 | 本轮处理 | 理由 |
| --- | --- | --- |
| memory_regions.low_ram | 删除 `[0x04000000,0x80000000)` symbolic 声明 | 撤掉实验后加的低端 RAM 内容声明 |
| pma_regions.experiment_low_ram | 删除同一区间的 RAM 属性 | 撤掉实验后加的低端可访问属性；未匹配 PMA 的目标走访问异常 |
| memory_regions.code | 删除 `[0,0x1000)` concrete 区 | 本轮直接执行 LOAD clause，不要求此处有指令快照；实际成功解析和执行验证其不是本命令的必需项 |
| memory_regions.harness | 新增 `[0x80000000,0x80100000)` excluded 区 | 符号执行前排除对重放程序保留区的实际读写 |
| ram_before_pt | 改为 `[0x80100000,0x80200000)` symbolic | 从 harness 末端开始，避开保留区和单列页表区 |
| page_tables | 保持 `[0x80200000,0x80203000)` symbolic | 保留原语义；satp 根页 `0x80200000` 位于其中 |
| ram_after_pt | 改为 `[0x80203000,0x80000000000)` symbolic，size=`0x7ff7fdfd000` | 接续页表区，内容声明覆盖至 XS DRAM 顶界 |
| pma_regions.ram | 保持 `[0x80000000,0x80000000000)`，size=`0x7FF80000000`，attr=ram | harness 只在内容层排除，硬件访问属性保留完整 DRAM |
| mmio_hole / clint_enabled | 保持原 excluded `[0x02000000,0x04000000)` / false | 保留其余设置，无需新增低端设备地图 |

解析 TOML 后检查所有 memory_regions 互不重叠；除 memory_regions / pma_regions 外，全部设置与原配置逐项相等。原配置没有其他与已删除低端 RAM 区间重叠的声明；mmio_hole 与其仅在端点相接。symbolic 是内容声明，不能单独充当地址白名单；本轮由 PMA 去掉低端 RAM 属性，excluded 排除 harness，仍允许图外访问异常目标。未生成新 IR，也未在生成后搬迁页表或修改样本。

## 地址区域直方图与断言

下表以每个样本中的一次 8 字节读取计数；同址跨样本重复计入。访问异常目标由 pt_decode.termination 提供，未发生读取，独立列出。字节计数也逐字节检查边界；唯一读取起始地址另有 PTE 498 个、数据 6 个。

| 物理地址区间 | PTE 实际读 | 数据实际读 | PTE 访问异常目标 | 数据访问异常目标 |
| --- | ---: | ---: | ---: | ---: |
| `[0,0x1000)` | 0 | 0 | 2 | 2 |
| `[0x1000,0x04000000)` | 0 | 0 | 0 | 0 |
| `[0x04000000,0x80000000)` | 0 | 0 | 0 | 32 |
| `[0x80000000,0x80100000)=harness` | 0 | 0 | 0 | 0 |
| `[0x80100000,2^43)` | 6376 | 544 | 0 | 0 |
| `[2^43,2^48)` | 0 | 0 | 10 | 866 |
| `[2^48,2^64)` | 0 | 0 | 6 | 156 |
| 合计 | 6376 | 544 | 18 | 1056 |

| 断言 / 核对 | 结果 |
| --- | --- |
| `[0x04000000,0x80000000)` 的 PTE / 数据实际读取均为 0 | PASS |
| harness 的 PTE / 数据实际读取均为 0 | PASS |
| 两个禁读区的实际读取字节数均为 0 | PASS |
| 全部实际读取位于 `[0x80100000,2^43)` | 本轮观察成立 |
| ≥2^43 的访问异常目标单独统计并允许存在 | 1038 个：PTE 16、数据 1022 |
| JSON 路径汇总、MERGE_STATS、样本行数与守卫类数一致 | PASS |
| 全部样本严格解码、输入哈希复核 | PASS |

例如成功样本 1196 读取 PTE 地址 `0x80200000`、`0x400000a0800`、`0xa0000000`，数据地址为 `0x40000400000`，全部在允许区间。访问异常样本 106 只读取根 PTE，数据目标是 `0x20000000`；目标在原低端 RAM 区，因 PMA 不允许而未读取。表中 32 个低端数据异常目标属于后一类，不能算成低端实际读取。

PTE 实际读取共 51008 字节，数据实际读取共 4352 字节。完整事件、字节、去重地址和异常目标直方图见 [regions.json](../../output/ecfg/sv39-load/validation/regions.json)。

## 锁定输入与源码版本

本工作树的 `isla/` 未初始化；指定 IR 的现存源文件通过主仓 `../../isla/.worktrees/memory-consistency/rv64d.ir` 只读取得。为确保所有运行产物留在本工作树，同时冻结一份同哈希 IR 到 output/ecfg/rv64d.ir；运行使用该副本。运行器同样先复制再运行，后续只调用 output/ecfg/bin/isarch。

| 输入 | SHA-256 |
| --- | --- |
| isarch 副本 | `496f63b6f8997a6aa74da56ac6c2631c6a1f7ca6efb046dab455799a36570657` |
| rv64d.ir（原件与副本相同） | `c0e4661a73888c56438a6f76059370667d141a026502d0511291586067bd31c0` |
| 原配置（原件与副本相同） | `c91fd405d69dd0f0d0f171fe9fcd369d63245103bc4910b9881bb5ea92469301` |
| config-xs.toml | `40d728925731cd7a8d7308b4f1f0b0f61940a79881ad4955780c48a366704129` |
| 外部路径导入的 pt_decode.py | `2ddc69915d0cde369759160182dd34d2ea7191fffc258ed93ab167645a4d7e47` |
| 本轮 samples.jsonl | `a7bc21e1781a791739265d78f52963277011c85e007ebc75ec90e3972ac69451` |

| 工作树 | 读取时 HEAD |
| --- | --- |
| isla-enumerate（运行器所在源码工作树） | `64af144f84f0e4c02a2b930d111770fa1e969aaa` |
| memory-consistency（IR 所在工作树） | `bdd047bc67c357f3c6e9c4d34b5ec9daaf81ab57` |
| mmu-symbolic-experiment（原配置所在工作树） | `cf4cedf74ef32262d139f9b0b81a8c0b4f235dff` |
| replay-p0（本工作树） | `ec5f6b2f26d5b4c2128b74a3a85030d6f0ca2b6b` |

运行器所在树和 IR 所在树均有未提交内容；上述 HEAD 不是二进制构建 provenance 的保证。以冻结文件哈希为本次实际受测身份，读取时 dirty 清单在 [environment.json](../../output/ecfg/environment.json)。运行器版本自报 Z3 为 `v0.2.0/z3-5.3.4.0 1fd1d3613c1f34c4dff36cba3209b2234f6c6d2b 1fd1d3613`。未做 Git 写操作。

## 命令、校验与日志

从本工作树根目录运行。下列命令展示本轮参数；原始绝对路径 argv、环境、起止时间及退出码保存在 done.json。实际运行由 [run.py](../../output/ecfg/run.py) 创建独立进程组，外限 1200 秒，超时会终止进程组；本轮未触发。运行目录为 output/ecfg/sv39-load，所以 Isla 自动生成的 output/rv64_zLOAD.json 也在该目录内。

```sh
ECFG_ROOT="$PWD/output/ecfg"
cd "$ECFG_ROOT/sv39-load"
ISLA_STATS=1 ISLA_EXPORT_SAMPLES="$ECFG_ROOT/sv39-load/samples.jsonl" \
TMPDIR="$ECFG_ROOT/tmp" XDG_CACHE_HOME="$ECFG_ROOT/cache" \
  timeout --signal=KILL 1200 "$ECFG_ROOT/bin/isarch" -D sr --smt-timeout 5 \
  -A "$ECFG_ROOT/rv64d.ir" -C "$ECFG_ROOT/config-xs.toml" \
  -T 64 --timeout 1190 --instruction-bits 0x0000b103 \
  --prestate 'x1=0x0000000020000000' --prestate 'cur_privilege=Supervisor' \
  --prestate 'satp=0x8000000000080200' \
  --prestate 'mstatus={bits=0x0000000a00040000}' \
  --prestate 'menvcfg={bits=0x0000000000000000}' \
  --prestate 'senvcfg={bits=0x0000000000000000}' \
  --prestate 'mseccfg={bits=0x0000000000000000}' \
  --execution-limits-config "$ECFG_ROOT/enumeration.toml" \
  --path-merging solve-state --clause=LOAD > stdout.txt 2> stderr.txt
```

样本导出会追加，复现时必须使用新的空输出目录；本轮 run.py 在已有样本时直接 raise。枚举 TOML 为 strict=false，enabled=true，mode=samples，class_cap=1，path_cap=1000000，sample_stride=1；未增加其他执行预算。命令依据 enumeration.md、samples.md 及 sv39-pinned.md，未依赖不可用 scratchpad。

校验命令（从工作树根目录）：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 output/ecfg/test_check_regions.py
PYTHONDONTWRITEBYTECODE=1 python3 output/ecfg/check_regions.py \
  output/ecfg/sv39-load/samples.jsonl --out output/ecfg/sv39-load/validation
PYTHONDONTWRITEBYTECODE=1 python3 output/ecfg/collect_results.py
```

校验器按指定外部路径导入 pt_decode，关闭 Python 字节码写出。复用 load_samples、decode_sample、aggregate、shape_key 的既有严格协议，不补缺失字节、不跳过解码错误。断言失败直接 raise，失败统计会先落盘。

| 证据 | 位置（本工作树根目录为基准） |
| --- | --- |
| TDD 先红 | output/ecfg/tdd-red.log：校验器模块尚不存在 |
| 首轮绿测 | output/ecfg/tdd-green.log：4 项通过 |
| 最终定向测试 | output/ecfg/tests-final.log：5 项通过；含区域端点、低端/harness 拒绝、高地址 PTE/数据异常目标、空输入拒绝 |
| 配置副本与静态一致性检查 | output/ecfg/config-xs.toml、config.diff、prepare.py、prepare.log |
| 运行器与输入身份 | output/ecfg/environment.json、sha256-initial.txt |
| 本轮 argv / 时限 / 耗时 / 退出码 | output/ecfg/sv39-load/done.json |
| 运行 stdout / stderr | output/ecfg/sv39-load/stdout.txt（空）、stderr.txt（完整日志） |
| Isla 路径与枚举 JSON | output/ecfg/sv39-load/output/rv64_zLOAD.json |
| 导出的原始样本 | output/ecfg/sv39-load/samples.jsonl |
| 地址断言和直方图 | output/ecfg/sv39-load/validation/regions.json、output/ecfg/validation.log |
| pt_decode 形状与页表代表 | output/ecfg/sv39-load/validation/pt_decode/{shapes.json,page_tables.json,distribution.md} |
| 数量守恒及最终汇总 | output/ecfg/summary.json、collect-results.log |

本轮没有 Isla 报错或异常空样本。尚未执行 XiangShan/NEMU 重放、check-samples 跨模式成员检查、STORE/Sv48 或完整具体值穷举，均记“未测”。未修改 design.md、另一个工作树或原配置；运行产物与脚本全部在 output/ecfg/，只有本报告按任务要求写入 agents/p0_replay/。
