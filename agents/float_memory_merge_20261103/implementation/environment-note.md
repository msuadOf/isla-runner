# 隔离候选环境说明

父仓候选是worktree，config默认与主仓共享；曾短暂设置core.commitGraph=false，发现写入共享.git/config后立即移除。后续父仓命令仅用单次`git -c core.commitGraph=false ...`，不修改共享commitGraph文件。两个子模块候选是独立clone，其core.commitGraph=false为各自本地配置，原memory/float子仓配置未改。

父仓标准ort合并因旧commitGraph/子模块历史对象读取错误停止，父owner随后用单次关闭commitGraph与resolve策略安全进入真正双亲merge；仅父索引/文档冲突，不操作两个子模块checkout。具体错误及MERGE_HEAD由implementation/root记录，不能称原对象库已修复。
