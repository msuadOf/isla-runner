# 统一 Sail FP C++ 数值适配包

本目录保存数值 adapter、生成 fixture、构建及测试入口。七个冻结源码文件已由
`copy_frozen.py` 单点复制到生产 `sail-riscv/c_emulator/` 和模型候选；两处逐文件
SHA-256 相同。主三文件位于本目录，wide 与 extra 四文件位于
`agents/float_support_review/tools/unified_backend_p2_wide/` 和
`agents/float_support_review/tools/unified_backend_p2_native_extra/`。
`production-cmake.patch` 是三处生产 CMake 的可审建议；实际 CMake 由模型集成人
单点维护。

SoftFloat 库和全部调用端共用 `SOFTFLOAT_FAST_INT64`。C 库使用 C11
`THREAD_LOCAL=_Thread_local`，C++ 使用 `THREAD_LOCAL=thread_local`，两者均由
`softfloat` target 的 PUBLIC 使用要求传递。每次 native 数值调用保存并恢复 RM、
tininess、flags；native flags 丢弃，架构 flags 由共享 Sail 公式计算。generic
equality 将所有 NaN 视为相等、区分正负零；数值比较遵循 IEEE 规则。

## 复现

从仓库根目录执行。默认 P0 wrapper 会加载 C++ 插件，所用 Sail 源码 archive 为
`446fb477c508853595ccc937ed60765aa685ae31`；单独的 `--version` 不能证明此
来源。`run.sh` 第二参数可传其他 P0 wrapper；P0 原始补丁及重建说明见
`agents/float_support_review/tools/unified_backend_p0/README.md`。

```sh
P2_WIDE_DIR='' P2_EXTRA_DIR='' \
  bash tools/unified_backend_p1_adapter/run.sh .tmp/unified-backend-p1-adapter/p1-only
```

P1 单包生成 101 条声明、114 个实际 C++ 方法：97 条 typed FP、四个纯 Sail 工具、
八个额外 32/64 位多态实例及五个 equality/ITE 探针。365 个数值样例由实际生成
Sail C++ 与独立进程原生 SoftFloat 比较完整结果位，原生五 flags 另保留。
`test_generated.cpp` 检查 NaN、两种 equality、record/宽位串深拷贝、无效整数域
总定义、嵌套环境及确定性 TLS 线程交错。

完整公开接口先重建 extra 的独立 fixture，再重建集成库：

```sh
bash agents/float_support_review/tools/unified_backend_p2_native_extra/run.sh \
  .tmp/unified-backend-p1-adapter/extra-fixture
FULL_BINDINGS="$PWD/isla/target/float-solve-evidence/unified-backend-bindings/20260927/candidate-final/bindings.json" \
P2_EXTRA_TEST_DIR="$PWD/.tmp/unified-backend-p1-adapter/extra-fixture" \
  bash tools/unified_backend_p1_adapter/run.sh .tmp/unified-backend-p1-adapter/full
```

冻结 bindings 可由持久入口 `agents/float_support_review/tools/unified_backend_bindings/generate.py`
从 Sail 声明、`native_calls.tsv` 和策略文件重建；本脚本接受路径参数，不把 ignored
产物当源码。完整 fixture 保留原声明的 effect 与 C/C++ 绑定，生成、链接并运行
190 条公开声明的 251 个方法实例。返回值证据由四部分组成：

- 当前闭包 97 条 FP typed 声明的 365 个独立 native 数值样例；
- `test_public_values.cpp` 中的 17 个 wide 公有出口、任意宽整数实例和十个
  对称 native 入口，包括 bit64 非零的 65 位输入及整数有效端点；
- extra 独立生成的 62 入口 `numeric_tests.cpp`，在最终集成库上重新链接运行；
- `test_generated.cpp` 中四个纯 Sail 工具的值检查。

每次运行的 `manifest.json` 记录源码、bindings、P0 补丁及工具 binary、生成 C++、
构建 flags、库、可执行文件与结果日志哈希。`tls_symbols.txt` 记录三个 SoftFloat
状态符号的 TLS 类型。本工作区 P1 单包基线及源码副本在 ignored 的
`.tmp/unified-backend-p1-adapter/p1-baseline/`。

本包验证数值原语与生成 C++ ABI；共享 Sail helper 的 flags、整条 ISA 状态、Isla
执行及 77 条指令属于模型集成门槛，不能由本包结果代替。
