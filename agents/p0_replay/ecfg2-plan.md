# E-cfg2：新 IR、平台绑定与 E3/E4

状态：完成（2026-11-07；E-cfg 限定 PASS、E3 474/474、E4 477/477，详见 ecfg2-results.md）。本轮用户授权重新生成 IR；不做 Git 写操作。新产物只写 `output/ecfg2/`，旧 `output/ecfg/` 全部只读。

## 目标与范围

解除 Svrsw60t59b、设备 PMA、平台 lock 三项前置；在 Sv39/Sv48 LOAD/STORE 四场景以 class_cap=1 重建目录。每形状选代表，先具体化再同配置 check-samples（E3）；通过后 E4 先 20 条再扩展全部可接受代表及 N1–N3。

可写：本目录新文档、`difftest-xiangshan/paging_replay.py` 及测试、`output/ecfg2/`。不改 Sail 语义，不动其他工作树。Sail 配置使用隔离副本，最终差异为 `extensions.Svrsw60t59b.supported: true → false` 和 `platform.clint.size: 786432 → 0`（设备 excluded 需要同时停用 Sail 内建 CLINT；TOML 的 clint_enabled 仅控制 Isla 内容区）；源码与旧 IR provenance 清单逐文件一致。

## 实施步骤

1. 复核 XiangShan PteBundle 的 reserved 字段宽度与 isPf，记录 false 的依据。
2. 冻结旧 IR 对应模型、同版 Sail 与插件、单项变更 JSON；严格 SYMBOLIC 生成 `output/ecfg2/rv64d.ir`。记录命令、输入输出哈希、耗时。
3. 从旧 TOML 派生完整已核实 PMA 与设备 excluded；核对不重叠。平台描述规范化后生成两个哈希与 lock。
4. 四场景最多四路、每路 -T32 导出；绑定 lock 和 samples SHA，独立严格解码、检查地址并统计类/形状；Sv39 LOAD 另跑 count。
5. 每形状代表按 R0–R9 判定；具体化 null 与诱饵后 E3，同一 lock/config/IR/isarch 检查恰好一条路径及结果一致。C3 不一致单独记录。
6. E3 全通过后 E4；退出 PC 精确匹配符号，记录每个桶、原因与失败输入；无法确认的差异标待查。

## 验证与停止条件

单测使用指定 `PT_DECODE_DIR`；所有产物与临时文件在 /data1。isarch 定向 -T64、批量 -T32；emu 最多 8 路。单步 15 分钟无进展停止；需要改变 Sail 语义或超出范围时停止报告。旧 F16/E-cfg 的 PASS 仅适用于 IR `c0e4661a73888c56438a6f76059370667d141a026502d0511291586067bd31c0`；对新 IR 均为**待复验**。

## 待查

NEMU 全设备/空洞行为没有完整源码证据；设备不重放。Debug 访问条件无法直接映射，按 design v2 设备排除。PMP 参数沿设计 §4.4 推迟，不扩本轮 Sail 配置变更。
