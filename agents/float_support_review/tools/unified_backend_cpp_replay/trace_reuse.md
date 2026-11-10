# 严格 trace 结果复用

`trace_reuse.py` 消费独立 `validate_trace_stream` 全流审计的精确附证。
附证绑定原 trace bytes、完整 `terminals` 语义对象、parser 源文件与选项，
同时绑定原 manifest、JSON、独审结果、终态附证及封证脚本。

包装只在原 `audit_run` 内启用。原代码仍实际计算 trace SHA256，执行 payload
守恒和全部 LLVM assembly 检查。实际 hash 前后、复用时的路径文件及打开文件描述符
必须具有相同设备、inode、长度、mtime 和 ctime；随后核验实际 digest 与独证一致。
复用只返回原严格 parser 的四个结果字段。任何缺字段、失败值或内容漂移均拒绝。

入口顺序为 `trace_reuse.py` → `prepare_diagnostics.py` → `sharded_official.py`
→ 冻结 wave。传入 `--trace-reuse-certificate`、`--trace-reuse-certificate-sha256`
后，其余参数传给原入口。仅成功导出的新 `input-manifest.json` 追加附证与包装来源。
原失败目录、原审计实现及分片实现不修改。

测试入口：

```sh
cd agents/float_support_review/tools/unified_backend_cpp_replay
python3 -m unittest test_trace_reuse -v
```

该工具通过不代表某次官方回放通过。正式结论仍需完整队列的双端执行结果与独审；
`full-closure-pure`、`whole77-complete`、`source-branch-closed` 保持 false。
