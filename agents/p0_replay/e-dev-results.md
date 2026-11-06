# E-dev：设备区判死实验（2026-11-07）

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
