# E-cfg2 实施记录（2026-11-07）

本轮结果入口；验收结果见 [ecfg2-results.md](ecfg2-results.md)。范围遵循用户本轮限定，不修改旧结果、全仓 TODO 或其他工作树。旧 F16/E-cfg 的结论适用旧 IR `c0e4661a73888c56438a6f76059370667d141a026502d0511291586067bd31c0`，对本轮新 IR 全部**待复验**，不能迁记旧 PASS。

## 已核实的配置事实

- 受测 XiangShan 源码 HEAD 为 `a13efc8775abb093e23727772a562f0605380685`。`src/main/scala/xiangshan/cache/mmu/MMUConst.scala:160` 设置 pteResLen=7；`MMUBundle.scala:774` 把该字段放在 N/PBMT 与 PPN 之间；`:807` 起 isPf 首先拒绝 reserved 非零。因此 PTE[60:59] 属保留位，Sail JSON 必须关闭 Svrsw60t59b。
- 实际 PMA 取 `src/main/scala/system/SoC.scala:57` 的 PMAConfigs，TOR 初始化与匹配在 `backend/fu/PMA.scala`。采用六段低端允许区的 mmio+excluded；禁访空洞不写 PMA。设备窗口与 DECERR 的具体响应不参与 P0；NEMU 全设备响应、IMSIC 可用性和 Debug 条件标待查，跳过设备重放。
- Sail `model/sys/platform.sail:23` 的 within_clint 直接读取顶层 let `plat_clint_base/size`，`:336` 的 within_mmio_readable 优先进入内建 CLINT。Isla 的 `clint_enabled=false` 没有关闭这条 IR 分派。实际失败语料读到 0x02000000/0x02001000/0x02004000 等设备地址时，没有普通内存字节。
- 当前锁定 isarch 的 `isla-lib/src/init.rs:66` 对顶层 let 运行初始化体，不从 const_primops 覆盖其值；因此旧 TOML 的 `plat_clint_size` 与本轮临时改为 0 都不生效。必须在 Sail JSON 修改 `platform.clint.size:786432→0` 并重新生成 IR。该项只停用被 P0 全部排除的设备专用分派，不改变 Sail 源码。
- 本轮使用与旧 IR provenance 逐文件哈希完全一致的冻结模型，以及同一 Sail 工具和插件。第一份新 IR 与旧 IR 只有 Svrsw 支持常量一处差异；第二份追加 CLINT 配置变化，最终 IR 为 4e9fb66e…41b91e2。

## 保留的失败尝试

| 目录（output/ecfg2/ 下） | 结果 | 处理 |
| --- | --- | --- |
| initial-map-error/ | 配置删除脚本越界删掉 RAM PMA，Sv39 LOAD 仅 1 类 AF | 本轮脚本缺陷；已收窄删除范围并增加原 RAM PMA 完整保留断言 |
| clint-generation-v1/ | 第一份新 IR ddc4f9bc…a3c03c，513.8966 秒生成成功 | 仅 Svrsw 对齐，CLINT 尚未关闭；不能作为最终 E3 输入 |
| clint-bypass/ | 四场景分别 676/360/1046/570 类；严格解码分别失败 186/110/258/154 条 | 配置未对齐：内建 CLINT 绕过 excluded；C3 FAIL，不启动 E3/E4 |
| toml-clint-zero-ineffective/ | TOML 改 size=0 仍有 clint_load；四场景中途主动终止 | 顶层 let 不接受该覆盖；各 cancelled.json 记录包装进程退出 130；子进程收尾情况见下文勘误，不计正式全量结果 |

clint-bypass 的普通内存实际访问仍在 DRAM，不能据此报设备判死 PASS：内建设备读根本不发普通内存事件。严格解码的 missing_memory 是检测到这类遗漏的证据，没有补字节或绕过检查。

## 平台锁与程序实现

`paging_replay.py` 新增两个平台哈希、实物哈希校验、原址具体化与原因码拒绝。LOAD/STORE 的期望只取 Isla result/post；null 初值填为后态逐字节反码。诱饵只进完整前态和 harness 回读表，check-samples 后态仍保持实际访存足迹，避免把未读诱饵误报为额外触碰。

设备过滤仍沿 isarch 既有 BadRead/BadWrite 通道记录，保留 partial/errors 原始摘要。本轮用 LD_PRELOAD 只读转发 Z3 调用，导出真实失败查询；离线删除当前 excluded 条件并保留历史约束与读值一致性，证明 UNSAT→SAT。只有逐项证据充分时才另记 excluded_filtered，不能把所有同名错误统一豁免。

运行脚本、日志、失败批次、模型冻结副本、临时目录和缓存均在 `output/ecfg2/`。未改 Sail 源码、未提交、未做其他 Git 写操作。

## 取消流程勘误

TOML 无效批次的 Ctrl-C 只终止包装进程，独立进程组中的 isarch 曾继续收尾；随后搬移目录使部分子进程在写摘要/排序收尾时因旧路径不存在而 panic。这是本轮取消流程问题，不归为被测模型缺陷，也不计正式运行结果。已在 run_scenario.py 加入 KeyboardInterrupt 时 killpg 并等待回收的处理；所有子进程均已自然退出或失败收尾，正式批次启动按活跃 isarch 数保守计入最多四路。日志和未收尾产物完整保留。
