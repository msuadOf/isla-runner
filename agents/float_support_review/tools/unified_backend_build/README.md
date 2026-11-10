# 统一浮点双后端：隔离构建入口

此目录只负责**完整 RISC-V 模型的工具链与构建集成**。P0 负责人维护 `agents/float_support_review/tools/unified_backend_p0/`、最小探针和 `compiler.patch`；本入口消费其**已冻结**补丁及通过记录，不重新实现编译器补丁或小探针。所有大产物写入被 Git 忽略的 `isla/target/float-solve-evidence/`。不修改现有 opam 安装、原 Sail checkout、主 `isla/rv64d.ir` 或 1dcc 冻结目录。

## 当前核实的入口

- 真正的干净 Sail 源 checkout 位于工作区外，提交 `446fb477c508853595ccc937ed60765aa685ae31`；当前工作区根目录**没有** `sail/`。`command -v sail` 当前指向 opam 安装的 Sail 0.20.1，不能当作补丁后工具链。
- Sail 官方构建为 `dune build --release @install`；源码自带的 `sail` wrapper 从本源码的 `_build/install/default/bin/sail` 运行并设置本地 `SAIL_DIR`、`DUNE_DIR_LOCATIONS`。
- Isla 插件源在 `isla/isla-sail/`，`dune` 目标为 `sail_plugin_isla.cmxs`，依赖 `libsail`。补丁后须用隔离安装的 `OCAMLPATH` 和 `DUNE_DIR_LOCATIONS` **重建插件**，不能直接把旧 `c4eccb06…` 插件视为新编译器的 ABI 证据。
- 模型 C++ 生成命令的权威入口在 `sail-riscv/model/CMakeLists.txt` 的 `generated_sail_riscv_model`；实际 emulator 链接目标为 `sail_riscv_sim`。CMake 的 `SAIL_BIN` 必须固定为隔离 wrapper。V128/E64 Isla IR 另按冻结配置显式调用同一 wrapper 和同版插件，保留历史79接口及三个直接状态接口。

P0 编译器补丁已持久化到 `agents/float_support_review/tools/unified_backend_p0/compiler.patch`，SHA-256 `a19828d5b390183e6b1a178c8e50601a6f14096a5bc8a3608c68310d09bc4875`，只改 `src/sail_c_backend/c_backend.ml`。P0 隔离 CPP/Isla 探针最终 `manifest.json` SHA-256 `d05ddcf56e9f98819d25e414230f56dc99ecb947fc8db9c0083b892e7ddf7b72`、status PASS，完整模型构建入口会要求它与新工具链的源码、补丁及 binary 哈希同版。P0 隔离 wrapper 曾将 `--version` 的 Git 描述误显示为外层 Isla 提交；本入口以源 checkout HEAD、补丁 SHA、应用前后文件哈希及实际 binary SHA 定义版本，单独记录 `--version` 字符串。

## 1. 构建隔离工具链

从 P0 审定的补丁和干净 Sail checkout运行；下列变量由调用者指向真实路径，`TOOLCHAIN_OUT` 必须是新的空目录：

```sh
python3 agents/float_support_review/tools/unified_backend_build/build_toolchain.py \
  --sail-source "$SAIL_SOURCE" \
  --compiler-patch "$P0_COMPILER_PATCH" \
  --expected-patch-sha256 "$P0_PATCH_SHA256" \
  --plugin-source isla/isla-sail \
  --out "$TOOLCHAIN_OUT"
```

脚本从固定提交 `git archive` 到隔离目录，先检查补丁目标与 SHA，再在副本内用 `patch -p1 --fuzz=0` 应用、构建 Sail、使用隔离 `libsail` 重编插件，并记录实际命令、日志和三个 binary 哈希到 `toolchain-build.json`。输出为 PASS 前，不进行完整模型构建。该入口不会运行 `dune install` 到 opam。

已有独立构建 `unified-backend-build/toolchain-a198-v2-20260927/` 的 `toolchain-build.json` SHA-256 为 `009f76a6caacb742bc299a86727e709a55acdfd8e847615cdb1dbb8fe78a6202`，结果 PASS：隔离 Sail binary SHA-256 `373a37c268779bad65381b98c3dc13d56c3db9db90102d28d6f410278b23d45a`，`libsail.cmxs` SHA-256 `139cc59812bbe5bc8bc761dfa95b0383a702492270679f723ed9e1345f545971`，重建的 Isla 插件 SHA-256 `c4eccb06af9f85820c28bd67556ae0f191361c93cbe1afb334900f9e1f0e22f6`。插件构建日志显示编译输入来自隔离 `libsail`；插件字节与此前同源码构建相同。第一次尝试因 Git 在嵌套父仓库内把 `git apply` 的路径锚到父仓库而 FAIL，保留在 `toolchain-a198-20260927/`；修订工具改为在已检查单文件路径的隔离目录用 `patch -p1 --fuzz=0` 应用，成功重建且未修改父仓库。

## 2. 固定 v7 源码并使用离线依赖缓存

已冻结的 v7 候选为 `isla/target/float-solve-evidence/unified-backend-model/20260927-final-v7/`，920 个文件。脚本验证候选 manifest，再分别比较源目录复制前、复制后和新快照的所有文件哈希。仅排除模型根目录的 `build/`，保留 SoftFloat 上游 `dependencies/.../build/` 中的受版本管理源码。`--out` 必须位于证据目录下且不存在或为空；输出不覆盖已有失败或成功记录。

缓存参数 `--dependency-cache` 指向包含以下文件的目录：

```text
cli11_hpp-src/CLI11.hpp
jsoncons-v1.4.3.tar.gz
```

CLI11 的 SHA-256 和 jsoncons 归档的 SHA3-256 必须分别匹配冻结模型的 `dependencies/CLI11/CMakeLists.txt`、`dependencies/jsoncons/CMakeLists.txt` 声明。脚本复制并再次核 hash，随后从归档新解压 jsoncons；缓存中已有的 `jsoncons-src/` 不作为输入。缺失或 hash 错误直接 FAIL，不转向联网下载。CMake 显式指定两个 `FETCHCONTENT_SOURCE_DIR_*`、`FETCHCONTENT_FULLY_DISCONNECTED=ON`、`FETCHCONTENT_UPDATES_DISCONNECTED=ON` 和 `DOWNLOAD_GMP=OFF`，因此仍需本机已安装 GMP。省略 `--dependency-cache` 时采用原 CMake 的下载流程；这不是离线模式。

以下命令从仓库根目录执行。它与本轮通过的配置参数一致，使用新的输出目录，完成源码、依赖校验及 CMake 配置；`--configure-only` 返回 `CONFIGURED`，不生成 C++/IR，不可记为完整构建 PASS。

```sh
EVIDENCE=isla/target/float-solve-evidence
P1_CANDIDATE="$EVIDENCE/unified-backend-model/20260927-final-v7"
TOOLCHAIN_OUT="$EVIDENCE/unified-backend-build/toolchain-a198-v2-20260927"
PRIOR_BUILD="$EVIDENCE/unified-backend-build/model-p1-v6-20260927"
MODEL_OUT="$EVIDENCE/unified-backend-build/model-p1-v7-offline-$(date -u +%Y%m%dT%H%M%SZ)"
python3 agents/float_support_review/tools/unified_backend_build/build_model.py \
  --toolchain "$TOOLCHAIN_OUT" \
  --expected-toolchain-manifest-sha256 009f76a6caacb742bc299a86727e709a55acdfd8e847615cdb1dbb8fe78a6202 \
  --p0-manifest "$EVIDENCE/unified-backend-p0/20260926T162859Z/manifest.json" \
  --expected-p0-manifest-sha256 d05ddcf56e9f98819d25e414230f56dc99ecb947fc8db9c0083b892e7ddf7b72 \
  --model-source "$P1_CANDIDATE/sail-riscv" \
  --expected-model-head f8ce8490981eac6396a31013180a2e718615757d \
  --source-manifest "$P1_CANDIDATE/source-manifest.json" \
  --expected-source-manifest-sha256 7e945fbace1f28fdf86ff94744100311a97db31576cebaba2d2b141fb1502093 \
  --v128-config "$PRIOR_BUILD/rv64d_v128_e64.json" \
  --expected-v128-config-sha256 89923ebff21718bb382df38bf246207cbb1eb5ae0cd314d078d87c0ab2b9f625 \
  --dependency-cache "$PRIOR_BUILD/dependency-cache" \
  --cpp-target sail_riscv_sim --jobs 4 --configure-only \
  --out "$MODEL_OUT"
```

要运行完整双后端构建，选择另一个新空输出目录，并去掉 `--configure-only`。脚本通过原 CMake 规则构建 `sail_riscv_sim`，并行使用同版 Sail/Isla 插件生成 V128/E64 IR；检查 [legacy79.json](legacy79.json) 的79个历史声明和函数体、`get_F/set_F/set_V` 函数体，以及 C++ 头的 `zext_decode`/`zexecute`。完整构建成功才返回 `PASS`。`model-build.json` 保存工具脚本 hash、输入快照、依赖声明和1723项缓存文件 hash、命令、日志及产物绑定。

若直接从有 `.git` 的模型源码 checkout 构建，可不传 `--source-manifest` 两项；冻结候选优先。`--cpp-target generated_sail_riscv_model` 只构建 C++ 生成目标，仍会生成 IR，但不证明 emulator 编译成功。

## 3. 已验证的构建与公共入口边界

完整 C++ 已在 `isla/target/float-solve-evidence/unified-backend-build/model-p1-v6-20260927/` 成功构建，stage 当前源码与 v7 的920项逐字一致。IR 在补齐 SoftFloat 平台构建文件前生成；前后 `model/` 文件集合与哈希相同。完整结果由该目录 `integration-result.json` 汇总，SHA-256 `96bcba4447f5fb580bafa4de6cb89734086b323e14c2900934b9f03d77c25a10`。原 `model-build.json` 仍保留首次代理下载失败的 FAIL，`cpp-build.log` 保留缺少 `platform.h` 的失败，未静默改写；成功依据是 `cmake-configure-v7.log`、`cpp-build-v7.log`、`cpp-source-v7-bind.json` 和 `ir-generation.json`。

| 已有完整产物 | SHA-256 |
| --- | --- |
| V128/E64 IR | `348147f833432008d559be0e673dbd45982148b0750cd4533c68589a55aac061` |
| C++ 模型 | `3f2af389cc81ca8ba276cb6007a3a08fa2f56ca0783fb7b2efbccf61659e54ca` |
| C++ 头 | `45fd0f832f01fb2b1bfa40d6bb2c76d942c2683e4262a4d81ec721259c46538d` |
| `sail_riscv_sim` | `2251afe3945d89d1846ddd7b7aae34e1c71a38da8815b9bd869bb42ae9773124` |

新增离线参数的验证证据位于 `isla/target/float-solve-evidence/unified-backend-build/offline-cache-validation-20260927/`：在全部代理指向失效地址时，新目录配置退出0、status `CONFIGURED`，920项模型快照一致、1723项依赖文件固定；故意损坏 CLI11、损坏 jsoncons 归档、缺失归档三项均在调用 CMake 前退出1。有效归档测试还放入故意损坏的旧 `jsoncons-src/`，确认入口重新解压。`validation.json` SHA-256 为 `20c2a4f5cb114c721a7738af10d0878e5b0aee20ffbf1f87a40be2d99970dbc8`，受测 `build_model.py` SHA-256 为 `8cf04d844ca0ed83eeadaeea735d04c20b60c64dd51309c62a089af6343a5813`。本轮未重复完整 C++/IR 构建。

构建成功只证明生成、编译、链接和接口检查；完整双后端数值/状态验收仍是后续门槛。新 IR 的严格配置、source catalog、runtime sidecar 和官方77项按实际 IR 哈希另行迁移验证；本入口不切换主 IR 或主配置。
