# 双精度向量初态解析修订范围

首轮 `runs-model-8ad5e8e/summary.json` 为315条：305 PASS，10 FAIL。10条均为 `VD-*` 双精度向量、SEW64、`vl=2`，在配置读取时因128位 `vr2` 或 `vr4` 十六进制值被按 `u64` 解析而退出1；这些条目无求解 JSON、无seed日志，不能记为模型数值失败或PASS。首轮数据保留原位。

本轮仅改 `run_directed.py` 的两处：`vector_job()` 将宽度64的 `vr2/vr4` 初态写为 `0b` 加128个固定二进制位；`value()` 在检查实际初态时以二进制解释该模式。Isla `isla-lib/src/config.rs` 的 `get_initial_state` 对 `0b` 模式逐位处理，原 `0x` 形式走64位解析。其它格式、作业、预期值、位串与flags核算未改。脚本哈希由 `6c24b0da54defa58cac14456b65ce1a313fffabab010e239924ed7938eafbfbd` 变为 `43c967d0e212aedfea1b50b97e144440598b2dec99ad328dd38cb1596c8f1752`；`expected.json` 保持 `6ed44d0afba816a709fe6f4f18f0e34505c8b3202aaed6e1ad306e5aea135891`。

固定资产 `inputs.model-8ad5e8e.json` SHA-256 `25a1a624cb5dcac76a2261c470e198c64a75b20259322a1c7ee5d0572b83ec24`，受测 IR `5ecea3717205dda77bc3cdbaf7a6b677415152e1f5cd09e541d0530519e25017`，程序 `fe4bdcebd1d970d6f026c0f81ccd22f807f5cb4729da27ef67e20b2c08d09d80`，均不变。新脚本对10条 `VD-*` 的128位模式长度、TOML字符串及值解析预检通过；`--family vector --name '^VD-' --dry-run` 通过并列出10条、CPU17/29。正式动态结果另记新目录，不覆盖首轮10个FAIL。两批仅在独立审查确认后按305+10核算，不声称单批315全PASS。
