# BF16 VF 扩宽 LMUL 边界测试

`make_cases.py` 从真实的 `vfwmaccbf16.vf v16, f1, v8` 编码生成 `cases.json` 和单例 `red_case.json`。八个 e16,m8 非法样例交叉覆盖 `vm=0/1`、`vl=0/1`、初始 `fflags=0/1`。`vd=v16` 与 `vs2=v8` 均为对齐的寄存器组，用于单独验证扩宽后 EMUL=16 的拒绝行为。一个带掩码样例以 `vstart=1` 开始；所有非法样例都要求目标寄存器、完整 `fcsr`、`vstart` 和 `mstatus` 不变。两个 e16,m4 合法样例要求正常退休，分别检查精确结果 `1 + 1*1 = 2`、带 NV 的规范 NaN，以及旧 NX 标志的保留。

在仓库根目录运行：

```sh
python3 agents/float_support_review/tools/bf16_lmul/make_cases.py
RUNNER=/path/to/isla-float-e-illegal-runner
IR=/path/to/rv64d.ir
BF16_RESULTS=/path/to/results.json
"$RUNNER" "$IR" agents/float_support_review/tools/e_nonmem/inputs/rv64-e.toml agents/float_support_review/tools/bf16_lmul/cases.json "$BF16_RESULTS"
```

runner 源码为 `agents/float_support_review/tools/e_nonmem/illegal_runner/main.rs`。它检查真实译码与重新编码、唯一完成路径、预期结果构造器，并通过 UNSAT 查询确认所列状态不会与预期不同。Cargo 构建方式见 `agents/float_support_review/tools/e_nonmem/RESULTS.md`；本测试不修改共享 runner。结果 JSON 逐例记录检查结果。

旧正式 V128 IR 的 SHA-256 为 `c9e1bfe29e75452568d61fc3b3407e707eb1bd7e48193e212495ec21b885bc75`，配置的 SHA-256 为 `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`，非法路径 runner 二进制的 SHA-256 为 `e265b79839c1e3b6721342b435d1c974574c7424d47b2edda92246d9f41802b3`。在该组合下，`red_case.json` 得到预期红例：退出码 101，`zvfbfwma_insts.sail:80.28-80.29` 报 `AssertionFailure`，日志见 `old_ir_red.stderr`。旧 IR 下两个 e16,m4 合法样例通过，runner 已检查结果位和 flags，记录见 `old_ir_legal_results.json`。这些结果仅适用于旧 IR。修复后的 Sail 源码 SHA-256 为 `814008056c5a43d1bf3c38af1aa3da1d31bc4518619fdf55051879961ea14b60`；需以该源码重新生成 V128 IR，再运行十例绿灯检查。

重新生成 IR 后，还需用 E 阶段成功路径 runner 复跑已有的 `agents/float_support_review/tools/e_nonmem/inputs/bf16-vector.json` 和 `bf16-vf-extra.json`。它们覆盖 VF 标量 sNaN 的活动与非活动情况，以及已有 VV 行为；`sail-riscv/test/first_party/src/test_bf16_wma_flags.S` 和 `test_bf16_nan_boxing.S` 是 C++ 模型回归。此次 BF16 源码修改保留 VF 标量转换及首次活动元素累计 flags 的逻辑，VV 断言仍位于原处。

## 早期源码的 C++ 回归（历史候选）

2026-09-26 重新构建并运行了现有 BF16 汇编测试。构建的 CMake 源码目录经 `realpath` 确认为本仓 `sail-riscv`，生成目标直接依赖当前 `zvfbfwma_insts.sail`；模型仓库 HEAD 为 `f8ce8490981eac6396a31013180a2e718615757d`，并包含本议题未提交修改。BF16 源码 SHA-256 仍为 `814008056c5a43d1bf3c38af1aa3da1d31bc4518619fdf55051879961ea14b60`，重新生成的 C++ 模型 SHA-256 为 `ef7da7f43bdd145d191d9dbc8025ace396d0349c53f77779c17655b1d5828cb7`，新模拟器 SHA-256 为 `87b4bcac82965862340b2289976f3bfaf68f677aa0dc4aae7a464525ab4c107c`。两条 ELF 的 SHA-256 依次为 `104d301de0bda8937062f2cf4254b3a153783e812d69fc5e935083c5c49be302`（wma flags）和 `3b6e4f92ac8de51ea465ea0983a8b09d99fe2d2482918e0ec70a352ba960062e`（NaN boxing）。完整源码及二进制哈希清单和本次日志保存在独立的仓库外日志目录。

在该模拟器上，显式 V128 配置运行两条 ELF 均输出 `SUCCESS`、退出 0；原 V256 CTest 入口两项均通过、退出 0。构建与运行命令如下；`BUILD_DIR` 指向已配置且源码路径指向当前模型的构建目录，`LOG_DIR` 是新建的独立日志目录。将 CTest 文件和 ELF 复制到 `LOG_DIR` 后运行，以免改写旧构建目录的 CTest 日志。

```sh
BUILD_DIR=/path/to/existing-cmake-build
LOG_DIR=/path/to/new-log-directory
env CMAKE_BUILD_PARALLEL_LEVEL=4 cmake --build "$BUILD_DIR" --target sail_riscv_sim build_rv64d_test_bf16_wma_flags.S build_rv64d_test_bf16_nan_boxing.S > "$LOG_DIR/build.log" 2>&1
"$BUILD_DIR/c_emulator/sail_riscv_sim" --config "$BUILD_DIR/config/rv64d_v128_e64.json" --config-override "$PWD/sail-riscv/test/first_party/src/no_override.json" "$BUILD_DIR/test/first_party/rv64d_test_bf16_wma_flags.S.elf" > "$LOG_DIR/wma-v128.log" 2>&1
"$BUILD_DIR/c_emulator/sail_riscv_sim" --config "$BUILD_DIR/config/rv64d_v128_e64.json" --config-override "$PWD/sail-riscv/test/first_party/src/no_override.json" "$BUILD_DIR/test/first_party/rv64d_test_bf16_nan_boxing.S.elf" > "$LOG_DIR/nan-boxing-v128.log" 2>&1
mkdir -p "$LOG_DIR/ctest"
cp "$BUILD_DIR/test/first_party/CTestTestfile.cmake" "$BUILD_DIR/test/first_party/rv64d_test_bf16_wma_flags.S.elf" "$BUILD_DIR/test/first_party/rv64d_test_bf16_nan_boxing.S.elf" "$LOG_DIR/ctest/"
ctest --test-dir "$LOG_DIR/ctest" -R '^first_party_rv64d_test_bf16_(nan_boxing|wma_flags)\.S$' -V > "$LOG_DIR/ctest-v256.log" 2>&1
```

这两条现有汇编测试验证 BF16 活动元素 flags 与 NaN boxing 回归；它们没有 e16,m8 的 LMUL 非法编码。LMUL 修复的动态绿灯以本目录十例在新 IR 上的运行结果为准。

## P2 冻结模型的 C++ 回归

P2 联合模型由集成方冻结为 `source-manifest.json`，SHA-256 为 `128d59a5661c3efdba566682c58ee6733f4799d9afd19fa3c6a542d24d95f346`。本次先将仓库源码复制到被 Git 忽略的 `isla/target/float-solve-evidence/bf16-cpp-p2/source/`，再以冻结模型覆盖副本中的 `model/`。构建前后均逐项核对 manifest 的 165 份模型文件，哈希全部一致；副本全部 909 个普通文件的哈希清单为 `source-tree.sha256`，其 SHA-256 为 `88d8f6d628be677f946afe7ec294c17e6fb3d4ab4fd9bf5c320ab15ef1369532`。三个 BF16 相关文件的 SHA-256 分别为 `zfbfmin_utils.sail`：`2c0693f4c578e6b237cc5de39d4a0014b6e46580cc69f66efdeb00f1785c6f07`、`zvfbfmin_insts.sail`：`062ccfc5b247bf2a0bd553a4ac7edbec7bf70f574049c669f2ab7c8b951550a2`、`zvfbfwma_insts.sail`：`bdabf5ad2823f203e4bf1c53e11860da58c5fbb1c594f0c376ce98697ac87bac`。Sail 为 0.20.1。CMake 的 `CMAKE_HOME_DIRECTORY` 指向这份副本，未从变化中的主工作树读取模型。

构建命令与日志均在 `isla/target/float-solve-evidence/bf16-cpp-p2/`：

```sh
EVIDENCE=isla/target/float-solve-evidence/bf16-cpp-p2
cmake -S "$EVIDENCE/source" -B "$EVIDENCE/build" -DCMAKE_BUILD_TYPE=Release -DENABLE_RISCV_TESTS=OFF -DFIRST_PARTY_TESTS=ON -DDOWNLOAD_GMP=OFF -DFETCHCONTENT_SOURCE_DIR_JSONCONS=/path/to/existing/jsoncons-src > "$EVIDENCE/configure.log" 2>&1
env CMAKE_BUILD_PARALLEL_LEVEL=4 cmake --build "$EVIDENCE/build" --target sail_riscv_sim build_rv64d_test_bf16_wma_flags.S build_rv64d_test_bf16_nan_boxing.S > "$EVIDENCE/build.log" 2>&1
"$EVIDENCE/build/c_emulator/sail_riscv_sim" --config "$EVIDENCE/build/config/rv64d_v128_e64.json" --config-override "$EVIDENCE/source/test/first_party/src/no_override.json" "$EVIDENCE/build/test/first_party/rv64d_test_bf16_wma_flags.S.elf" > "$EVIDENCE/wma-v128.log" 2>&1
"$EVIDENCE/build/c_emulator/sail_riscv_sim" --config "$EVIDENCE/build/config/rv64d_v128_e64.json" --config-override "$EVIDENCE/source/test/first_party/src/no_override.json" "$EVIDENCE/build/test/first_party/rv64d_test_bf16_nan_boxing.S.elf" > "$EVIDENCE/nan-boxing-v128.log" 2>&1
ctest --test-dir "$EVIDENCE/build" -R '^first_party_rv64d_test_bf16_(nan_boxing|wma_flags)\.S$' -V > "$EVIDENCE/ctest-v256.log" 2>&1
```

构建退出 0；V128 的 wma flags 与 NaN boxing 各输出 `SUCCESS`、退出 0；V256 的同两项 CTest 为 2/2、退出 0。生成的 `sail_riscv_model.cpp` SHA-256 为 `9dfbb762a5d06cf2ee97d88d6356cdd02d44f5076f8dac0acf673111e3b080b5`，模拟器为 `29c6387da426379537f3af80860ef9419f2cc1d215de0f86cb63671a6ffef422`，wma flags ELF 为 `36cb1ffadf4caf243059f4d5df76320d353d9a3ea45909b4b37faf90ae97a1e0`，NaN boxing ELF 为 `8d393a34b88a016980a9be5f437ec5c16be434679cbd262b30c7280640571866`。V128 和 V256 配置的 SHA-256 分别为 `89923ebff21718bb382df38bf246207cbb1eb5ae0cd314d078d87c0ab2b9f625` 与 `e28ac77273be6a31c544db6b196914dfb55b3b9fb72295ae7ef6cfc7b99dfc47d`。

这四次运行只证明现有 BF16 汇编样例在普通 C++ 后端的行为，仍不覆盖 e16,m8 非法编码；后者由新 IR 的十例专包验证。
