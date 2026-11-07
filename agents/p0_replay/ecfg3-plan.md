# ecfg3：新 IR 的 P0 重放接续

状态：完成。四场景与REPORT一致，E3 584/584、定向4/4＋隔离2/2、E4 587/587验收PASS，unittest100/100；具体证据见 [ecfg3-results.md](ecfg3-results.md)。

本轮直接使用 sail-std-gaps 工作树已冻结的 final 输入；不生成 IR、不改 Sail。旧 ecfg/ecfg2、来源工作树、isarch、emu 与 NEMU SO 均只读，不做 Git 写操作。已有阻塞记录先完整保存到 output/ecfg3/previous-blocked-results.md，结果报告保留历史说明。

## 目标、范围和执行顺序

可写范围仅 paging_replay.py、tests、agents/p0_replay/ 与 output/ecfg3/。所有产物、缓存、临时目录在本工作树 /data1 内。

1. 核对来源 REPORT、manifest 与指定 isarch 的 SHA-256；复制 ecfg2 的 profile/lock 流程，绑定新 IR 和配置。
2. 四场景 class_cap=1、每路 -T32、最多4路。检查类/形状 728/136、380/120、1122/174、606/154；不一致停止。
3. 解码器在允许范围内适配已补齐的标准语义，不修改外部 pt_decode；原址 PTE 不改。每形状选最小 sample_id，具体化后使用同配置 check-samples。保留 partial，并逐查询证明 excluded 过滤。
4. E4 前验证合法 NAPOT、非法 N 编码、非叶 U/A/D（Sv39 LOAD 各一例）。明确区分 emu 自检与 NEMU 被引导的页异常；需要时用只读观察器独立执行同一 payload 观测 NEMU。
5. E4 先20条再扩全，保留 N1–N3 负对照。按精确退出 PC 分类；真实分歧不屏蔽，不改 Sail。不确定原因标待查。
6. 记录命令、版本、哈希、类/形状、E3、E4 与旧 IR 对照。更新 ecfg3-results 与本议题摘要；用户限定范围外的 specs/TODOs、docs/RESULTS、agents/findings 不写。

## 验证和停止条件

使用指定 PT_DECODE_DIR，在 difftest-xiangshan/tests 下 unittest discover。emu 并发不超过8；单例120秒，isarch 外限900秒；单步15分钟无进展或发现设计未覆盖的语义问题即停止报告。

旧 IR 为 4e9fb66e…，历史 PASS 只对旧版本有效。新 IR 为 3f16d5e7…，所有结果均重新验证。
