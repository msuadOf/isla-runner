# 路径合并与写缓存实测计划（2026-11-10）

目标：只测用户新名单的 221 个 clause，分别判断两小时内完成并写缓存、partial、超时或错误。旧实测已有结论的 126 项不再运行。

## 范围与边界

- 实验目录：`.worktree/pathmerge-cache-all-20261110/`；不创建 Git 工作树，不做 Git 写操作。
- 名单：`.worktree/dagcache-all-20261110/todo-clauses.json`，含被停止的 FWVFTYPE。
- 二进制：从缓存工作树的现有 release 复制到实验目录 `bin/isarch`，已冻结；不改缓存实现。
- IR：只读使用 `.worktree/pathmerge-all-20261110/isla/rv64d.ir`。
- 配置与 tastic：沿用旧 347 项映射，筛选成 221 项，冻结三份 ISA 配置。
- 热点文件：实验目录 `driver.py`、`README.md`、`limits-audit.json`；复制复用旧 `solve_process.py` 做进程组收尾。

## 步骤与验证

1. 保留范围变更前的冒烟记录，不计入新结果。
2. 核查命令、环境、ISA 配置和源码中的默认限制行为。任何限制核查不通过则停止。
3. 用名单内 ORCB、RORI 同时冒烟。验证双格式缓存、manifest 发布与条目数、采样路径为零。冒烟计入正式结果，不重跑。
4. 用 `setsid nohup` 后台启动全量 driver；始终最多两项，每项 `-T 32`，内外两小时，SMT 一分钟。
5. 每项写独立日志与缓存。记录路径、合并统计、缓存大小、段去重率、峰值内存及错误。
6. 超时不重跑；连续三个同类启动错误停止；本任务输出达到 150GB 停止。
7. 确认后台存活与进度更新，交付进度和结果入口。全量结束后由 driver 生成汇总。

## 未决问题

尚未测出的 clause 能否结束、是否完整，必须等真实结果。范围变更前 RTYPE 已写缓存但求解报 Poison；仅作为历史观察，不推广到新名单。

## 第二轮追加计划（2026-11-10）

用户明确允许环境错误补跑一次；主轮 outcome=error 且含指定译码 Poison 的项改 default 补跑一次。该规则取代旧计划对这些项的不重试要求，其他错误、partial、两小时超时仍不补跑。主 driver 宿主机 PID 2128518 保持运行，不修改其使用文件。

新增独立 second_round.py、second_support.py、second_solve_process.py 及五项名单／汇总／收尾测试。等待脚本先等主锁释放和收尾证据，再最多两路派发；名单在等待时刷新，在主轮退出后冻结。第二轮结果写 results-second.jsonl，日志写 runs-second/，缓存写 cache-default/。最终 summary.json 汇总两轮，保留主轮原汇总为 summary-main.json。两轮合计继续遵守 150GB 上限。

来源补记见实验目录 binary-commit-note.json：冻结二进制源码与 feat/isarch-path-cache@daf61c04 一致，不重编。
