# 标量浮点运行结果本地备份

快照日期：2026-09-29。压缩包为本工作区的 `_raw/float-scalar-73df-20260929.tar.zst`，大小约 80 MiB，SHA-256：`c011139457134cbb48c396ec567ee98b3b328d18c1e61c64409bfa3aeaa09815`。`_raw/` 被 Git 忽略；这是**本机副本，不是远端备份**。

内容包括 73df 隔离 IR 的 51 个标量目标 JSON、对应 51 份日志与 trace（1344 条生成结果）、v3 求解命令与核账、冻结 IR／配置／isarch；以及当前工作区 XiangShan DiffTest 的输入、ELF、全部 `current-*` 运行／重试／异常日志、逐例审计、本地 emu 和 NEMU SO。所用消费端 `pipeline.py` 的原版本另存为 `pipeline-used.py`，SHA-256 与逐例审计的 `8099715d…22390c` 一致；当前工作树里的 `pipeline.py` 后来已变化，不能拿它代替受测版本。

[manifest.json](manifest.json)逐个记录 5639 个原始文件／链接的相对路径、大小、SHA-256 或链接目标及受测身份。生成脚本为 [make_manifest.py](make_manifest.py)。归档时验证：51/51 源 JSON `summary.complete=true`，合计 1344 gen；`zstd -t`、`tar -I zstd -df` 均退出 0；归档 5641 项（5639 原文件／链接＋manifest 和生成脚本）；归档后原始文件逐项哈希 5639/5639 相符。原文件没有删除或移动。

在仓库根目录复核压缩包：

```bash
sha256sum archives/_raw/float-scalar-73df-20260929.tar.zst
zstd -t archives/_raw/float-scalar-73df-20260929.tar.zst
tar -I zstd -tf archives/_raw/float-scalar-73df-20260929.tar.zst | wc -l
```

归档保存工作区相对路径；部分 DiffTest manifest 内仍有本机绝对路径，迁移后重放前须更新那些路径。再次运行 `make_manifest.py` 会重算并改写快照清单，不应用它检查冻结归档的身份。
