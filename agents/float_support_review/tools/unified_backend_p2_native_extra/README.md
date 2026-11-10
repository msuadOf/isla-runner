# P2 native-extra 隔离实现与验证

日期：2026-09-27。状态：本包 62 个 typed 数值入口的真实 Sail 生成、链接和数值测试通过。完整 190 声明、公有库接线、共享 ISA 与 flags 的最终门槛由 P1 集成方完成，本包结果不覆盖这些门槛。范围和语义依据见[适配合同](../../unified-backend-adapter-contract.md)。

## 实现范围

| 入口 | 数量 | 实现 |
| --- | ---: | --- |
| `undefined_float16/32/64/128` | 4 | 选择合法的 +0 代表；Sail 声明仍为 impure |
| 四格式 NaN、±inf、-0；H/S/D 的 +0 | 19 | 整数位构造，`fp128_zero` 保留 P1 的唯一定义 |
| 四格式 neg | 4 | 非 NaN 翻转符号位；NaN 归一 |
| 四格式 normal/subnormal/zero/infinite/positive | 20 | 原始 exponent/fraction 分类；NaN 的 positive 为 false |
| f128 → H/S/D | 3 | 五 RM，直接原生转换、一次舍入 |
| 四格式 rem/min/max | 12 | IEEE remainder；min/max 对单 NaN 返回另一值，对异号零选择 min=-0、max=+0 |

所有 NaN 出口统一为正 quiet NaN：H `7e00`、S `7fc00000`、D `7ff8000000000000`、Q `7fff800000000000:0000000000000000`。不使用宿主浮点类型。原生运算通过真实 P1 `Scope` 隔离 RM、tininess 和 flags，原生 flags 不进入架构结果。异号零选择属于 SMT 允许关系，不能据此宣称 Z3 必须给相同位串。undefined 的 +0 是本实现的选择，不代表符号任意取值全集。

## 文件与接线

- `sail_softfloat_extra.h/.cpp`：62 个 public 定义，依赖 P1 的 `sail_softfloat_types.h`、`sail_softfloat.h` 和真实 `Scope`。
- `generate_fixture.py`：校验冻结 bindings SHA，生成 62 个 Sail wrapper，保留 4 个 impure effect。
- `generate_tests.py`：以 Python 整数及 `Fraction` 计算分类、neg、min/max、remainder、窄化期望值；没有宿主 float。
- `test_support.h`：真实生成函数调用的返回值与三环境哨兵检查，以及直接 SoftFloat 参考。失败使用 `abort`；测试同时传入 `-UNDEBUG`。
- `CMakeLists.txt`、`red_main.cpp`、`verify_red.py`：独立红/绿构建，红测必须恰好缺少 62 个 public 符号。
- `run.sh`、`write_manifest.py`：复现及版本证据；校验生成调用集合、62 项运行覆盖和每个 public 定义恰好一个。

只有 P1 owner 编辑主头对 extra 的 include 和主构建接线。编译库及所有调用方均需 `SOFTFLOAT_FAST_INT64`，C 使用 `THREAD_LOCAL=_Thread_local`，C++ 使用 `THREAD_LOCAL=thread_local`；不能与非 TLS SoftFloat 混链。

## 复现

从仓库根目录运行：

```sh
bash agents/float_support_review/tools/unified_backend_p2_native_extra/run.sh \
  .tmp/unified-backend-p2-native-extra
```

默认首次从 `tools/unified_backend_p1_adapter/` 复制 P1 三个源码/头文件及 `softfloat_tls/` 到输出目录的 `p1_snapshot/`，随后在本包 build 目录重建真实 P1 和 TLS SoftFloat。已存在的快照不会被覆盖；生成、测试及 adapter 仍使用本次包源码。P1 正在独立继续集成，复验本次冻结版本可显式指定保存的快照，避免混入后来的 P1 改动：

```sh
bash agents/float_support_review/tools/unified_backend_p2_native_extra/run.sh \
  .tmp/unified-backend-p2-native-extra/recheck \
  .tmp/unified-backend-p2-native-extra/p1_snapshot
```

第三个可选参数是 patched Sail 的 wrapper，默认 `isla/target/float-solve-evidence/unified-backend-p0/20260926T162859Z/sail-src/sail`。必须用 wrapper 加载 C/C++ plugin。脚本参数和实际生成/构建命令均保存在包脚本及输出构建文件中。新的 P1 公有库接线后，应将生成的 `extra.cpp`、`numeric_tests.cpp` 与集成公有库重新链接运行；单独重用旧二进制不能证明集成版本通过。

## 本轮实测

证据目录：`.tmp/unified-backend-p2-native-extra/`。

| 验证 | 结果与范围 |
| --- | --- |
| RED | `red.stderr` 与 `red_summary.txt`：生成代码编译成功，去掉 extra 实现后链接退出 2，恰好 62 个 public 符号未定义 |
| GREEN | `test.stdout`：62 个入口全部运行并检查结果；15,623 次返回值和环境哨兵检查通过 |
| 常量 | 23 次，包含四个 undefined 的 +0；Q 正零由 P1 负责 |
| 分类、neg | 四格式各 24 个边界/特殊值和 128 个固定种子随机位串，合计 3,648 次；覆盖正负 qNaN/sNaN、±0/inf、normal/subnormal 和 Q 的低字 |
| rem/min/max | 四格式各 716 对，合计 8,592 次；包含 24×24 特殊/边界矩阵、正负 3/5/7 除以 ±2 的 tie-even quotient、128 对固定种子随机数 |
| Q 窄化 | 224 个 Q 输入 × 五 RM × 三目的格式 = 3,360 次；含最小 subnormal 半 ULP、min-normal 边界、1 的半 ULP、overflow 半 ULP 及相邻 Q 编码的正负值 |
| 独立原生参考 | 原生 rem 2,864 次、Q 窄化 3,360 次均与 Python 整数/有理数结果一致，合计 6,224 次；参考自行保存/恢复 TLS，不调用 adapter 或其 Scope |
| 环境与构建 | 每个生成调用前轮换五 RM、两种 tininess、32 种 flags 哨兵，调用后逐一比较；生成、绿构建、运行 stderr 均为空 |

已按上述第二条命令在 `recheck/` 新输出目录完整重建，RED/GREEN 结果一致，`extra_test` 与 `test.stdout` 的 SHA 均与首次运行相同。

`manifest.json` 保存包源码、生成源、P1 快照、Sail executable 与 C/C++ plugin、compiler patch、bindings、原生 source 输入、库和二进制 SHA，记录编译器与构建选项。SoftFloat dependency 没有单独的 git 身份，其版本以 source 输入哈希为准。

## 冻结 SHA-256

| 对象 | SHA-256 |
| --- | --- |
| extra header | `5a0d4a0eb08aeaff5fee79ad4750ee2b6289e2173d1a7aa48c53eb7627405372` |
| extra source | `11c18c5fbf904af9e6e581660e1cd0ba25164a6184931f8c6c1464d20bfd77be` |
| P1 snapshot source | `acaab7023df8dd384e72e1fa2d0bef620c845a29dd95d4e5e8c5e145e5d896b1` |
| P1 snapshot header | `b7cf2a83d619801b9c6f1667740d14517382597f03a293589db1a068885ff9c5` |
| bindings.json | `a98a8fdf466326f9bcb8a3843045c3f17b5c5bf3efc350bba66b713e7e6f9255` |
| compiler.patch | `a19828d5b390183e6b1a178c8e50601a6f14096a5bc8a3608c68310d09bc4875` |
| Sail executable | `373a37c268779bad65381b98c3dc13d56c3db9db90102d28d6f410278b23d45a` |
| 本包重建的 TLS SoftFloat 库 | `4fa95fac0b0a1b03fdf370d4b2adfda968cffa0d018666569e16b62a0e0aceab` |
| extra_test | `639a540d1af9835f2f31b43e7afcd6ecb5dacfcb3d59c76a68f39e2e0b0ffbc2` |
| test.stdout | `3e54ad6a4fcc314dd4fc78f4cd31dfb70af4db2a6b6cf131e5451aa2421a9a1e` |

Sail archive commit：`446fb477c508853595ccc937ed60765aa685ae31`。wrapper 的 `--version` 可能拾取父 checkout 的 git 信息，不能用它替代本表和 manifest 的实际输入记录。

未决：P1 公有库重新链接本包全部 62 个生成入口，以及完整 190 声明的唯一符号、返回值和允许关系验证。本包未改生产接线、P0、P1、P2 wide 或共享状态文档；主 agent 负责同步议题摘要和全仓验证状态。
