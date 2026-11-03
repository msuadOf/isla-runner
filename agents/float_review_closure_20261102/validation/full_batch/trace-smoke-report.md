# 带轨迹程序 FLEQ_S 启动验收

本次使用 `inputs.model-8ad5e8e-itrace.json` SHA-256 `0e57cf681917c9a3f05070c146b877b7ed30e108dc2135d3f31740966965f90c`，正式模型 `8ad5e8e`、Isla `42000be`、带 `smt-thread-interrupt+tracetool` 的 binary SHA-256 `acda0dceb259205fe0c43a3785484ffcafbef26b3194de3b9f67ad38eccbcf7d`。原 `validation/run_clause.py` 当前 SHA-256 `b154941be1eaf7cd788c66053edbe564458a39eb8ba65f962aa85d26eaabc7b1` 先 `--dry-run` 退出0，再用 CPU35 执行独立 `float-closure-itrace-smoke-20261102/FLEQ_S`。

真实运行 exit0、summary.finished、48 条 JSON、seed17拦截有效、runner PASS，耗时18.269秒。itrace 17,956,365字节，SHA-256 `457110f4240585a536c7f9e882f1d6b275beacd81f7ae9eec5e429d61654b818`；输出 JSON SHA-256 `e299bfe083aaaac18a3fe032038a9b3384458dbf42318c61ce9901455f434e6b`。该 JSON 与 enum reviewer 的独立 FLEQ_S smoke 输出 SHA 完全相同，详 [独立证据](../../review/enum/harness-smoke-itrace/result.json)。

本次只证明这套冻结资产的 FLEQ_S 启动、轨迹、seed与完整结果链路。主 agent 随后确认还需修五个精确转换的 canonical RM_RNE 汇编映射，模型及 IR 将换版，故暂不启动77条主批；最终新版 inputs 到位后再做一次相同启动验收，并用新唯一名称启动主批。首批缺轨迹失败仍保留在 [启动失败记录](batches/float-closure-8ad5e8e-42000be-20261102/startup-failure.md)。
