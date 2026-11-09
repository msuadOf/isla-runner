# isarch fuzz smoke

本目录归档原生 fuzz 的三份配置、20 个 corpus entry 和运行入口。配置与 corpus 来自 Isla 原工作树 `output/fuzz-isarch-loop-smoke/`，基线 `a8b610dd`；当前模型须通过本轮成员认证，旧结果不自动继承。文件哈希不决定 corpus 是否有效。

从 runner 根目录执行：

```sh
python3 difftest-xiangshan/smoke/isarch-fuzz/run.py --output output/isarch-fuzz-smoke
```

需要 Python 的 pytest、pytest-subtests、RISC-V ELF 编译器、已构建的 `isla/target/release/isarch`，以及与当前 Sail-RISC-V 对齐的 `isla/rv64d.ir`。输出目录必须尚不存在。默认运行 Python 全部回归及原生 campaign；可用 `--mode python` 或 `--mode native` 单独执行。

独立工作树可以传 `--isla-dir`、`--binary`、`--ir`。原生 smoke 使用 Sv39 STORE、32 线程、20 次变异及完整成员认证；`--threads` 可调整线程数。单路径预算 60 秒，进程总预算 360 秒。日志及实际命令写入输出目录。

运行成功要求 Python 测试退出 0，原生 fuzz 退出 0、20/20 corpus entry 认证通过，并输出 20 个变异体及 20 条判定。该 smoke 不执行 XiangShan/NEMU，不代表硬件差异测试或所有配置的完整回归。

动态 prestate 的四个 Python 核心脚本及原测试来自 `feat/p0-replay@ffcc98e1` 加原工作树的未提交修改。它们按实际 GPR、SATP、立即数和地址域消费输入，保留原 replay-p0 工作树。
