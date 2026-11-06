# E-dev：设备区判死实验（2026-11-07）

**最新结论（E-dev2）：这是 Isla 的枚举类型登记缺陷，配置写法合法。** RAM 的 `reservability="eventual"` 与设备默认的 `"none"` 在路径合并时相遇，求解器尚未登记 `Reservability`，在 `smt.rs:968` 查表 panic。已取得完整回溯与单字段触发复现；修改该属性或关闭合并能避开本次 panic，但前者改变 PMA 语义，后者改变原实验路径，均不签收设备配置。建议先补齐合并前的枚举登记，再重跑原配置；本轮未改生产代码。详见本文末尾 [E-dev2 调查](#e-dev2最小化调查2026-11-07)。下文原实验记录保留。

**结论：实验 FAIL，完整设备判死假设尚未验证。** Sv39 LOAD 合并+样本模式下，新增设备 PMA 的两种配置都触发锁定 isarch 的 panic。不能根据崩溃前设备读取为零宣称通过。额外定向探针已经证明：**仅 mmio 确实能导出读取设备窗口 PTE 的样本**；加 excluded 后，该具体 PTE 读取被 BadRead 拒绝，未导出样本，但摘要为 partial、errors=1。

| 用户问题 | 结论 |
| --- | --- |
| mmio+excluded 能否把 PTE 与数据读取都判死，而且只丢弃路径？ | **尚不能确认。** 直接放入设备窗口的根 PTE 被拒绝；运行报告执行错误，不是干净的 finished/零错误。普通根的整体运行 panic，数据访问目标未完成验证。 |
| 仅 mmio 会不会产生读取设备的样本？ | **会，已观察到设备 PTE 读取。** 根移到设备窗口后，崩溃前导出 10 条 PF 样本，每条读 0x30000000。数据读是否也能产生尚未验证。 |
| 设备目标是否生成正常 AF 样本？ | 本轮前缀没有 AF 目标。不能推断 AF 类不存在；mmio-only 根探针已读 PTE 后得到 PF；excluded 根探针得到 BadRead；其余目标的最终类别被 panic 阻塞。 |

未修运行器、未关闭合并、未改枚举模式，不以变更技术路径绕过失败。没有运行到 20 分钟，无需触发超时终止。

## 配置和运行身份

从 output/ecfg/config-xs.toml 复制，新增 `[0x30000000,0x30010000)`。这是用户允许的人工设备窗口，不声称是实际接入的 XiangShan 设备。原有 RAM、harness、page_tables 和 mmio_hole 不变。两种写法只相差新增 memory_regions excluded 项：

```toml
[[pma_regions]]
name = "device_probe"
base = "0x30000000"
size = "0x10000"
attr = "mmio"

# 仅 config-dev.toml 增加本项，config-mmio.toml 无本项。
[[memory_regions]]
name = "device_probe"
base = "0x30000000"
size = "0x10000"
region_type = "excluded"
```

沿用 E-cfg 冻结文件：isarch `496f63b6f8997a6aa74da56ac6c2631c6a1f7ca6efb046dab455799a36570657`；IR `c0e4661a73888c56438a6f76059370667d141a026502d0511291586067bd31c0`；基础配置 `40d728925731cd7a8d7308b4f1f0b0f61940a79881ad4955780c48a366704129`；pt_decode `2ddc69915d0cde369759160182dd34d2ea7191fffc258ed93ab167645a4d7e47`。每次运行前检查哈希。设备配置 SHA-256：

- config-dev.toml：`f1ada8607dfafd8c5e94747e34b343406685643c7fabae2df2a9e4661a463fa4`。
- config-mmio.toml：`c7d76181ec313994f6ee6d6c22d6b3063bfc60af2c29e070532cf5a64c483e0a`。

## 实测结果

原根表仍为 0x80200000；定向探针只把 satp 改成 0x8000000000030000，让 Sv39 根表位于 0x30000000。均为 T64，指令 ld x2,0(x1)，x1=0x20000000、Supervisor，其他前置状态及 samples 枚举配置沿用 E-cfg。

| 场景 | 退出码 | 耗时 | 已写样本 | 前缀形状 | 设备 PTE / 数据实际读 | 最终状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| mmio-excluded | -6 | 4.379s | 18 | 9 | 0 / 0 | panic；无最终路径 JSON |
| mmio-only | -6 | 4.977s | 10 | 5 | 0 / 0 | panic；无最终路径 JSON |
| root-in-device-excluded | 0 | 2.275s | 0 | 0 | 0 / 0 | BadRead；partial、errors=1 |
| root-in-device-mmio | -6 | 3.826s | 10 | 5 | 10 / 0 | panic；无最终路径 JSON |

mmio-excluded、mmio-only 的崩溃前前缀分别完成 2/1 条路径、18/10 个类；这些不是最终路径数或守卫类总数。前者仅有 18 次 PTE 读，后者仅有 10 次 PTE 读，全部在 DRAM；所有数据读为零。其形状数分别为 9/5，均只对应前缀。root-in-device-mmio 的 10 条样本包含设备 PTE 读取 10 次、80 字节、去重地址 1 个；结果均 E_Load_Page_Fault。完整前缀直方图保存在各 validation/regions.json，按 --observe-only 输出，不标地址断言 PASS。

| 区间 | 普通根 mmio+excluded PTE / 数据 | 普通根仅 mmio PTE / 数据 | 设备根仅 mmio PTE / 数据 |
| --- | ---: | ---: | ---: |
| [0,0x1000) | 0 / 0 | 0 / 0 | 0 / 0 |
| [0x1000,0x04000000) | 0 / 0 | 0 / 0 | 0 / 0 |
| [0x04000000,0x80000000) | 0 / 0 | 0 / 0 | 10 / 0（均在设备窗口） |
| harness | 0 / 0 | 0 / 0 | 0 / 0 |
| [0x80100000,2^43) | 18 / 0 | 10 / 0 | 0 / 0 |
| [2^43,2^48) | 0 / 0 | 0 / 0 | 0 / 0 |
| [2^48,2^64) | 0 / 0 | 0 / 0 | 0 / 0 |

三个前缀所有访问异常目标计数均为 0。设备根 excluded 没有样本，不能调用拒绝空输入的 pt_decode 统计器；其最终 JSON 显示 gen=[]、status=partial、errors=1。

## 失败证据与边界

三个 panic 均为 `isla-lib/src/smt.rs:968:40: no entry found for key`，进程返回 -6（SIGABRT）。设备根仅 mmio 使用 RUST_BACKTRACE=1，调用链为 region_merge::merge_states → merge_val/build_ite_with → Solver::translate_exp → Ast::mk_enum_member。只读核对当前对应源码：mk_enum_member 直接索引 enums.enums[&enum_id.id]。因此可确认是合并枚举值时缺少 enum id；具体为何未登记、属于哪个枚举仍未核实，不能据此给出源码修复结论。完整回溯在 output/dev/root-in-device-mmio/stderr.txt。

设备根 excluded 的 stderr 明确为 `Bad read excluded memory region(BadRead("excluded memory region"))`，调用栈包含 pt_walk/read_pte/checked_mem_read/read_ram/sail_mem_read。它证明这次 PTE 读取到达内容层并被 excluded 拒绝；不证明所有设备目标都走到内容层，也不证明数据读取分支被完整排除。

后续需在另一项获准的运行器修复中解决 enum id 缺失，再用这两份相同配置重跑。当前设计 v2 的“PTE+数据都判死且无违规样本”不得签收。数据访问的设备目标、AF 预先分支和完整统计均为未测/被中断，保持原方案不擅自替换。

## 复现与证据

从根目录运行，使用新的空输出目录，避免追加旧样本：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 output/batch-a/run_scenario.py \
  --out output/dev/mmio-excluded --config output/dev/config-dev.toml
PYTHONDONTWRITEBYTECODE=1 python3 output/batch-a/run_scenario.py \
  --out output/dev/mmio-only --config output/dev/config-mmio.toml
RUST_BACKTRACE=1 PYTHONDONTWRITEBYTECODE=1 python3 output/batch-a/run_scenario.py \
  --out output/dev/root-in-device-excluded --config output/dev/config-dev.toml \
  --satp 0x8000000000030000
RUST_BACKTRACE=1 PYTHONDONTWRITEBYTECODE=1 python3 output/batch-a/run_scenario.py \
  --out output/dev/root-in-device-mmio --config output/dev/config-mmio.toml \
  --satp 0x8000000000030000
PYTHONDONTWRITEBYTECODE=1 python3 output/batch-a/check_regions.py \
  output/dev/root-in-device-mmio/samples.jsonl \
  --out output/dev/root-in-device-mmio/validation \
  --device 0x30000000 0x30010000 --observe-only
```

驱动完整参数与原 E-cfg 一致：--path-merging solve-state --clause=LOAD、-T64、--smt-timeout 5、内部 --timeout 1190、外部进程组 1200 秒强杀。样本配置仍 class_cap=1、path_cap=1000000、sample_stride=1。命令、输入哈希、起止时间、退出码、耗时在各 done.json；command.sh、stdout.txt、stderr.txt、samples.jsonl 均保留。总账 output/dev/summary.json。设备窗口逐字节计数器及 STORE 写统计由 output/batch-a/test_regions.py 先红后绿（2 项），未修改外部 pt_decode。

## E-dev2：最小化调查（2026-11-07）

### 结论、绕过边界与下一步

**原因已定位：合法的 PMA 配置暴露了 Isla 在合并具体枚举值前没有登记对应 SMT 类型的问题。** 决定性对照是两个相同 `attr="ram"` 区域：第二项的 `reservability` 从 `eventual` 改为 `none`，其他输入完全相同，便从正常完成变为 SIGABRT。因此不是 `mmio` 拼写、区域重叠、`excluded`，也不是样本枚举导致的崩溃。

原 `mmio` 和 `hole` 别名都把 `reservability` 设为 `none`，原 DRAM 的值是 `eventual`。两类区域被合成同一条符号路径时，连同属性记录中的该枚举字段一起合并；该次求解器查不到枚举类型，程序终止。设备区是否真正被读取，不是触发这个内部错误的必要条件。

已验证两种避开手段，但**尚无经验证、同时保留原设备属性及合并/枚举流程的配置绕过方案**：

- 在设备项追加 `reservability="eventual"`：本轮 `mmio`、`hole` 小场景均正常完成。它改变 LR/SC 是否允许的 PMA 属性，不作为通用设备窗口配置；本轮也未验证加 excluded 后的全部设备 PTE/数据分支。
- 关闭路径合并：最小触发配置正常完成。仅用于确认故障范围，不代替原合并+枚举验收。

下一步建议是修复枚举登记，再用原 `mmio`、`mmio+excluded` 配置重跑，继续验证 PTE、数据与 AF 提前分支。本任务按用户指定的“缺陷先报告”边界停止在诊断和修复建议，未改 Isla 生产代码、未重编或替换锁定二进制。前轮 excluded 的 `partial/errors=1` 仍是独立未解决问题。

### 输入与执行边界

沿用前轮冻结的四份输入，运行前逐项检查 SHA-256，结束后再次核对，均未变化：

| 输入 | SHA-256 |
| --- | --- |
| `output/ecfg/bin/isarch` | `496f63b6f8997a6aa74da56ac6c2631c6a1f7ca6efb046dab455799a36570657` |
| `output/ecfg/rv64d.ir` | `c0e4661a73888c56438a6f76059370667d141a026502d0511291586067bd31c0` |
| `output/ecfg/config-xs.toml` | `40d728925731cd7a8d7308b4f1f0b0f61940a79881ad4955780c48a366704129` |
| `output/ecfg/enumeration.toml` | `13470943e934b43664c95c9294ac62573790d1b691695843825f2507742d53db` |

本轮只写本报告和 `output/dev2/`。未更新其他状态文档或 findings，以遵守用户限定的写入范围；未做 Git 写操作。实际受测版本以二进制、IR 哈希为准，不把当前源码 HEAD 当作重编证明。

驱动 [run.py](../../output/dev2/run.py) 复用前轮参数，每次固定 `-T 64`、`RUST_BACKTRACE=full`、`--smt-timeout 5`，内部 `--timeout 890`，外部 900 秒终止整个进程组。每次使用独立目录，临时文件、缓存、样本及自动生成的 JSON 全在 `output/dev2/`；关闭 core dump。最长有效测试 80.493 秒，没有 15 分钟无进展运行。

所有运行的参数、配置哈希、起止时间、退出码和摘要见各目录的 `done.json`，当次配置字节另存为 `input-config.toml`。机器总账见 [summary.json](../../output/dev2/summary.json)。

### 分项对照

下表各项均保留原 E-cfg 配置、合并和 samples 枚举，仅增改表中所列项目。正常完成项均为退出 0、`status=finished/errors=0`，其他摘要不完整计数也为 0；它们只证明对应运行完成，不代表完整设备验收。

| 目录（均位于 `output/dev2/`） | 相对基础配置的变化 | 结果 | 耗时 |
| --- | --- | --- | ---: |
| `control-base` | 无，配置副本 | 正常完成，20 路径 | 19.527s |
| `control-excluded` | 只加设备 memory_regions excluded | 正常完成，20 路径 | 22.083s |
| `reproduce-mmio` | 加设备 PMA mmio | panic，退出 -6 | 3.674s |
| `control-mmio-excluded` | 加 mmio 和 excluded | 同一 panic，退出 -6 | 3.826s |
| `control-hole` | 加设备 PMA hole | 同一 panic，退出 -6 | 3.774s |
| `field-ram` | 加设备地址段，但属性用 ram | 正常完成，20 路径 | 71.204s |
| `field-ram-none` | 同上一项，只加 reservability=none | 同一 panic，退出 -6 | 4.577s |
| `field-ram-alignment` | 同 ram 项，只加 misaligned=alignment_fault | 正常完成，51 路径 | 80.493s |
| `field-mmio-eventual` | mmio 项覆写 reservability=eventual | 正常完成，51 路径 | 79.184s |
| `field-hole-eventual` | hole 项覆写 reservability=eventual | 正常完成，24 路径 | 28.947s |

`excluded` 对照仍是 RAM-only PMA，不能从其零错误推出设备访问已被判死。`field-ram-alignment` 证明此场景仅改变未对齐策略不是触发项，不推断其他模型或输入没有同类枚举缺陷。

### 最小复现

已删除全部 `memory_regions`、`const_primops`、额外寄存器默认值、平台说明及非默认工具链，并移除样本导出和 `--execution-limits-config`。仍保留 API 必需的工具链/地址表、PMP 全开、原指令前态和两个 PMA 区域。

最小触发配置是 [minimal-reservability.toml](../../output/dev2/minimal-reservability.toml)（33 行），只需以下 PMA 差异就能触发；其余必需表项见文件：

```toml
[[pma_regions]]
base = "0x80000000"
size = "0x7FF80000000"
attr = "ram"

[[pma_regions]]
base = "0x30000000"
size = "0x10000"
attr = "ram"
reservability = "none"
```

对照 [minimal-control.toml](../../output/dev2/minimal-control.toml) 只把最后一行改成 `reservability="eventual"`；逐字差异见 [minimal-field.diff](../../output/dev2/minimal-field.diff)。这是一项字段的最小触发差异，不声称已证明整个 TOML 每个保留键或每个前态参数均不可删除。

| 目录 | 运行差异 | 结果 | 耗时 |
| --- | --- | --- | ---: |
| `minimal-reservability-v2` | 最小触发配置、合并、无样本/枚举 | panic，退出 -6 | 4.228s |
| `minimal-control-run` | 仅 none→eventual | 正常完成，20 路径 | 6.982s |
| `minimal-v2` | 最小配置，第二项 attr=mmio | 同一 panic，退出 -6 | 4.782s |
| `minimal-misaligned-v2` | 第二项 ram，仅 misaligned=alignment_fault | 正常完成，51 路径 | 7.033s |
| `no-merging-reservability-v2` | 最小触发配置，仅关闭合并 | 正常完成，1709 路径 | 15.986s |

从仓库根运行，输出目录名必须尚不存在：

```sh
python3 -B output/dev2/run.py repro-reservability \
  output/dev2/minimal-reservability.toml --no-samples --no-enumeration
python3 -B output/dev2/run.py repro-control \
  output/dev2/minimal-control.toml --no-samples --no-enumeration
python3 -B output/dev2/run.py repro-original \
  output/dev2/mmio-excluded.toml
```

驱动自身正常退出以便继续记录其他对照，**受测 isarch 的退出码须读输出或 `done.json.returncode`**；panic 预期为 -6，不能用驱动进程的 0 计 PASS。直接调用锁定二进制的完整 argv 见 [最小复现 command.sh](../../output/dev2/minimal-reservability-v2/command.sh)，含 T64、原 Sv39 LOAD 的固定前态与 900 秒外限。原设备复现完整日志见 [reproduce-mmio/stderr.txt](../../output/dev2/reproduce-mmio/stderr.txt)。

### 完整回溯与源码解释

原 mmio 复现与最小字段复现均保存了 `RUST_BACKTRACE=full` 的完整 87 帧回溯：

- [原 mmio 回溯](../../output/dev2/reproduce-mmio-backtrace.txt)。
- [最小字段回溯](../../output/dev2/minimal-reservability-v2-backtrace.txt)。

关键链路为：

```text
region_merge::merge_states
  → primop_util::merge_val（递归合并 struct 字段）
  → build_ite_with（构造两个枚举值之间的条件选择）
  → Solver::define_const / translate_exp
  → Ast::mk_enum_member
  → smt.rs:968: enums.enums[&enum_id.id] 查表失败
```

只读检查的是冻结二进制来源工作树 `../isla-enumerate/` 中的 `isla-lib`。当前 HEAD 为 `16c83b80a1aa31ec6fb8012d06f60d7fe352a59f`，只存在未跟踪构建目录；核对的六份源码相对 E-cfg 清单记录的 `64af144` 均无差异。文件哈希和核对结果见 [source-audit.json](../../output/dev2/source-audit.json)，带当前行号的源码摘录见 [source-excerpts.txt](../../output/dev2/source-excerpts.txt)。回溯中的内联行号与当前源码有少量差异，下列位置采用当前源码行号；panic 行同为 968。

1. `isla-lib/src/config.rs:212`、`:920`、`:961`：`ram/mmio/hole` 都是合法别名，允许显式覆写 reservability；ram 为 Eventual，mmio/hole 为 None。新窗口与既有区域互不重叠。
2. `isla-lib/src/executor/region_merge.rs:820`：合并两个执行状态的值，直接把值与当前 solver 交给 `merge_val`。
3. `isla-lib/src/primop_util.rs:654`、`:674`、`:378`：枚举值不同就构造 ITE；结构体字段递归合并；`smt_value` 在 `:213` 只是把已有 `Val::Enum` 转成 `Exp::Enum`，这条链不登记枚举类型。
4. `isla-lib/src/smt.rs:2261`、`:966`：翻译枚举成员时直接索引当前求解器的枚举表。`no entry found for key` 对应缺少整个 enum id，并非 member 下标越界。
5. `isla-lib/src/smt.rs:2405`：现成的 `get_enum(name,size)` 才会发出 `Def::DefineEnum` 并登记类型；`:2744` 的 checkpoint 重建仅重放记录过的事件，不能从状态中现有的具体枚举值自动恢复类型。

IR 也解释了为什么普通 LOAD 会碰到尚未登记的 Reservability：`output/ecfg/rv64d.ir:48145` 的 `matching_pma_bits_range` 返回整个命中区域，嵌套的 `PMA` 结构包含 reservability（`:3283`）；合并两个候选区域会连它一起合并。普通 LOAD 只用 readable，而 reservability 的语义比较出现在 LR/SC 分支（`:48896` 附近），不能指望先读到枚举常量来登记类型。正常从 IR 取枚举常量的执行器路径在 `isla-lib/src/executor.rs:189` 会先调用 `get_enum`，与这里已有具体值直接进入合并不同。

综合单字段正反对照、完整回溯和源码，可把本例缺失类型定位到 `Reservability`。未动态读取到原始 enum id 数字：尝试只读 GDB 观察时，环境禁止 ptrace，日志留在 [gdb-mmio/gdb.log](../../output/dev2/gdb-mmio/gdb.log)；不把该失败当作运行验证。

### 修复建议（未实施）

优先修复“合并值引用的枚举类型必须已经登记在当前求解器”这一条件，而不是改变设备地图或忽略 panic：

- 在能取得 `SharedState.type_info` 的合并入口，对即将进入合并的值中引用的枚举，依据 IR 类型表取成员数，复用 `solver.get_enum` 登记。要处理结构体、联合载荷等嵌套位置；本例是 `Some(PMA_Region{attributes=PMA{reservability=...}})`，只处理顶层枚举不足。
- 登记必须成为当前 solver 的 `DefineEnum` 事件，使事务提交/回滚和 checkpoint 重建都能保留。若选择在配置注入后、首个 checkpoint 前登记 PMA 涉及的枚举，同样要验证工作线程从 checkpoint 重建后的行为；仅在临时初始化 solver 中登记不够。
- `Ast::mk_enum_member` 不持有 IR 成员数量，不应在该处凭猜测创建 enum、替换默认值或吞掉错误。现有不变量检查可保留。
- 后续修复测试先复现：新 solver、同一枚举的两个具体成员、嵌套 PMA 结构合并；再测事务与 checkpoint 重建。端到端沿用本轮最小正反对照，最后恢复原 mmio、mmio+excluded 和设备根/数据定向场景。修好 panic 不自动解决 excluded 的执行错误分类，也不等于 E-dev 全项通过。

### 准备失败与记录完整性

最小化过程中三次先删掉工具链必需的 `name`，程序在配置解析时退出 1（`minimal-run`、`minimal-reservability-run`、`minimal-misaligned-run`）；补回后使用独立 `*-v2` 目录重跑。第一次关闭合并时误把后面的 `solve-state` 子命令一起删除，CLI 退出 1（`no-merging-reservability`）；修正驱动后重跑为 `no-merging-reservability-v2`。这些记录全部保留，均不计正反对照成功证据。探索性的 `minimal-candidate` 也复现同一 panic（4.077s）。所有受测 isarch 运行均为 T64，没有修改其指令集实现或受测 IR。
