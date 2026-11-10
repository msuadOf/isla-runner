# 官方完整队列的分片配对

`sharded_official.py` 在既有 `observe-wave.py` 的 `run_pair` 调用处接入分片；原输入导出、负例物化、源码核验和 `pair_official.py` 保持原实现。该入口用于已经自然完成并严格冻结的官方输出。

## 约束

- 先核完整输入 manifest 及其全部来源，再按原顺序连续分片。ID、word、AST、pre、post、ret 和其他嵌套字段全部保留。
- 固定最多 4 个子进程，每片默认 256 条。每片在独立 Python 进程中依次运行冻结的 Isla observer 和 CPP runner。
- 启动子进程前要求 `MemAvailable` 至少 32 GiB；等待不改变输入或分母。
- 子片绑定完整父输入 manifest，避免每片重复读取庞大的原 trace；全组结束后重新核全部父来源哈希。
- 每片继续使用原配对检查，包括初始化、完整 AST、返回值、102 字段、异常槽逐步观察。非零退出、缺结果或不完整分区均阻止总通过。
- 分片通过只说明对应分区。只有全部片通过且原完整对象、ID 和顺序再次守恒，才生成整组 `paired-summary.json`。

## 命令

以下路径均以仓库根目录为基准；输出目录必须不存在：

```sh
python3 agents/float_support_review/tools/unified_backend_cpp_replay/sharded_official.py \
  --wave-driver <冻结的observe-wave.py> --wave-driver-sha256 <其SHA256> \
  --backend-plan <冻结的backend-plan.json> --backend-plan-sha256 <其SHA256> \
  --manifest <完整官方manifest> --manifest-sha256 <其SHA256> \
  --output <新输出目录> --workers 4 --shard-size 256
```

## 验证范围

6 项 TDD 检查覆盖完整对象分区、重复或缺失 ID、相同 ID 内容变更、失败传播和数量守恒。既有完整 7 条输入按 3/3/1 分片实际完成 Isla/CPP 配对，14 个观察阶段、130683 条指令、异常槽写入为 0。

正式大批结果须读取该次运行的最终摘要，不从上述小规模验证推断。输入审计失败时不会提交任何片；LLVM 拒绝的非法操作数组合必须先取得逐条源码 guard 审查，再用既有 `observe-wave-reviewed.py` 的 `--reviewed-illegal` 参数消费原记录。旧超时与首次输入审计失败记录保留。

`prepare_diagnostics.py --prepare-failure-diagnostic <新诊断文件> ...` 可包裹上述分片入口。它只在原 `collect` 拒绝时保存完整返回审计、三个完成标志、manifest 与全部队列 ID，并继续抛出原异常。已有诊断文件拒绝覆盖；成功路径保持原返回。对应 3 项测试覆盖失败保留、成功转发和旧证据保护。

所有结果继续限定 `whole77-complete=false`、`source-branch-closed=false`、`full-closure-pure=false`。
