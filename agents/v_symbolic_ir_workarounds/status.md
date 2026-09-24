# 当前状态

2026-09-25：用户确认更新 P1。已从当前 `sail-riscv` `f8ce8490` 源码用 `rv64d_v128_e64.json` 重新生成 `isla/rv64d.ir`，SHA-256 为 `6fc39efd0f72b0ee8eae247d9965e680b6874f9954334c20d748b42c0987792c`，与此前性能测试的新 IR 逐字节一致。

79 份 `strict=true` workaround 已全部绑定新哈希；21 份配置中指向三个修改过的 Sail 文件的 67 个 region 已按旧、新源码中逐字节相同的起止行迁移。注释中的 Sail 行号一并核对，修正了两处原有的注释偏一行问题。其他文件的 region 坐标未改，限制预算和执行策略未改。

验证：`verify.py` 对 79 份配置、67 个目标 region 和 22 处源码注释锚点通过；`git -C isla diff --check` 通过。`make -C isla -f scripts/run.mk -n solve-MASKTYPEI` 确认默认加载 `./rv64d.ir` 和 `masktypei.toml`。使用正式新 IR 与 `vimctype.toml` 的 `isarch solve-state --clause=VIMCTYPE` 返回 0，生成 121 条完成路径和 JSON；日志与结果放在根目录 `.tmp/ir-sync-smoke/`。`MASKTYPEI` 12 秒短时运行完成 124 条路径，按预设外层时限退出 124，日志无哈希错误。用旧哈希的历史 `masktypei.toml` 加载新 IR 则立即报告 SHA-256 不匹配，证明严格校验生效。历史 `isla/output/` 未触碰；全量 `make solve` 未运行。

当前关注文件：`sail-riscv/model/extensions/V/` 下三份已修改 Sail 文件、`isla/rv64d.ir`、`isla/configs/workarounds/*.toml`、`isla/scripts/run.mk`。

注意：根仓库已有其他未提交内容；实施仅处理本议题文件，历史 `isla/output/` 未改。
