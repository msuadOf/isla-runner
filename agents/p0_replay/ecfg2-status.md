# E-cfg2 状态摘要（2026-11-07）

**完成：三项前置、四场景 E-cfg、E3、E4。** 新 IR 4e9fb66e…41b91e2；生成侧 e1543ec3…4f91e6e。四场景合计 1944 类/样本、474 个场景内形状代表。E3 474/474 PASS；E4 先20条通过，再扩全为474 agree＋3个按预期失败的负对照，验收477/477 PASS。unittest 98/98 PASS。

原始 isarch partial/errors=5/5/7/7 保留，24次均有独立的设备 excluded 过滤证明；E3 的24次终止也已单独证明。没有超时或未解释的正例分歧。类内具体值穷举、源码模型覆盖及设备响应不在本次 PASS 内。

旧 F16/E-cfg 结论仅适用旧 IR c0e4661a…31c0，对新 IR 标待复验；旧 output/ecfg 清单37项哈希未变。未做Git写操作或修改Sail语义。

- [最终结果、计数、哈希、命令与失败样本](ecfg2-results.md)
- [计划与范围](ecfg2-plan.md)
- [源码事实、中间失败与取消过程](ecfg2-progress.md)
- [机器最终核账](../../output/ecfg2/final-audit.json)
