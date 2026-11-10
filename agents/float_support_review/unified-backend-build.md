# 统一双后端 P1 隔离构建集成记录

日期：2026-09-27。当前状态：隔离工具链、完整 C++ emulator 与 V128/E64 IR 已构建成功；新离线缓存参数完成配置和快照验证。此项只负责**完整模型的独立工具链与构建入口**，不以构建成功代替双后端语义验收。P0 的编译器补丁、小模型探针和 `agents/float_support_review/tools/unified_backend_p0/` 由其负责人独占，模型/CMake/adapter 候选由模型负责人独占。这里不修改安装 Sail、生产模型、主 IR/严格配置或 1dcc 冻结目录。可复用脚本和完整调用说明在 [unified_backend_build/](tools/unified_backend_build/README.md)。

## 只读入口调查

- 根工作区当前没有 `sail/`；干净 Sail 源在工作区外 checkout，HEAD `446fb477c508853595ccc937ed60765aa685ae31`。当前 opam 安装 `sail --version` 为 0.20.1，同一提交，安装 binary SHA-256 `8915ef46daf4bd9a7a99c563e007f554665930b5def7dd34aeeff9341bcc2a6a`。
- `isla/isla-sail/Makefile` 通过 `dune build --release` 生成 `sail_plugin_isla.cmxs`。旧 1dcc 候选插件 SHA-256 为 `c4eccb06af9f85820c28bd67556ae0f191361c93cbe1afb334900f9e1f0e22f6`；补丁后必须针对隔离 `libsail` 重新构建并记录，不以旧插件文件名推断 ABI。
- `sail-riscv/model/CMakeLists.txt` 的 `generated_sail_riscv_model` 经 `SAIL_BIN` 调 Sail 生成 `sail_riscv_model.cpp/.h`；`sail_riscv_sim` 才进一步编译链接完整 emulator。Isla IR 需独立调用该 Sail wrapper 与同版插件，不沿用 CMake 现有 `isla-sail`/V256 默认入口。
- P0 补丁现持久化在 `agents/float_support_review/tools/unified_backend_p0/compiler.patch`，SHA-256 `a19828d5b390183e6b1a178c8e50601a6f14096a5bc8a3608c68310d09bc4875`，仅改 `src/sail_c_backend/c_backend.ml`。对干净基线执行只读 `git apply --numstat` 为该单文件，`git apply --check` exit 0。P0 小模型 CPP/Isla 探针的最终 `manifest.json` SHA-256 `d05ddcf56e9f98819d25e414230f56dc99ecb947fc8db9c0083b892e7ddf7b72`，status PASS；其源码、补丁、compiler binary 哈希与这里的工具链一致。该次仅补全历史预期失败的原输入/日志哈希，P0绿证据状态与编译器版本未变。

## 隔离工具链结果

初次工具脚本在根 Isla Git 工作树内使用 `git apply --numstat` 检查复制后的 Sail 源；Git 将路径锚到父仓库，预检 FAIL，未应用补丁。失败证据保留在 `isla/target/float-solve-evidence/unified-backend-build/toolchain-a198-20260927/`。工具随后改为先严格解析单文件补丁头，在隔离副本以 GNU `patch -p1 --fuzz=0` 先 dry-run 再应用；未修改根仓库或原 Sail checkout。

修订后 `toolchain-a198-v2-20260927/` 构建 PASS，`toolchain-build.json` SHA-256 `009f76a6caacb742bc299a86727e709a55acdfd8e847615cdb1dbb8fe78a6202`。脚本从固定提交 `git archive`，补丁应用前后目标源码 SHA-256 分别为 `98e15fc867d2d9ba3c61ebf37fdd89ca1d53865106bd515e2666b382638f32f9`、`359e79158fd54d51eb834e37bf9ac7f76a14ffcc5a4f486afeff1cf5470f1536`；`dune build --release @install` exit 0。隔离 Sail binary SHA-256 `373a37c268779bad65381b98c3dc13d56c3db9db90102d28d6f410278b23d45a`、隔离 `libsail.cmxs` SHA-256 `139cc59812bbe5bc8bc761dfa95b0383a702492270679f723ed9e1345f545971`。

Isla 插件以该隔离安装的 `OCAMLPATH`/`DUNE_DIR_LOCATIONS` 重新编译，构建日志的 `-I` 指向隔离 `libsail`；`-plugin ... --version` 动态加载 exit 0。重编插件 SHA-256 仍为 `c4eccb06af9f85820c28bd67556ae0f191361c93cbe1afb334900f9e1f0e22f6`，与此前同源码插件字节相同，这不替代对真实新 IR 的运行验证。隔离 wrapper 的 `--dir` 正确指向其源副本；`--version` 显示 Sail 0.20.1，但括号中的 Git 描述被外层 Isla Git 工作树污染，不能作为 Sail commit 证据，实际源码版本以固定 HEAD、补丁及 binary 哈希为准。

## 完整模型入口与历史状态

[build_model.py](tools/unified_backend_build/build_model.py) 已支持两种来源：直接工作树，或模型负责人生成的隔离候选目录及逐文件 `source-manifest.json`。后者优先；脚本先要求 P0 PASS manifest 与工具链的源码、补丁、binary 哈希同版，再核候选 manifest SHA、所有原/新增模型文件哈希，复制前后再次比对，通过原 CMake 构建 C++ emulator，用隔离 Sail/插件生成新 V128/E64 IR，并检查 [legacy79.json](tools/unified_backend_build/legacy79.json) 指定的79个历史接口及 `get_F/set_F/set_V`。CMake 必须显式 preserve `ext_decode`/`execute`，生成头必须导出 `zext_decode`/`zexecute`；结果还记录模拟器、模型库和 SoftFloat 库哈希供完整重放。真实命令、生成的头/source、模拟器、IR 和哈希将写 `model-build.json`。所有输出只允许放在 `isla/target/float-solve-evidence/` 的新空目录。

历史：`unified-backend-model/20260927-candidate-v1/` 的 manifest 为893个文件，逐项一致时 adapter 尚未冻结，完整 C++/IR 为未测。此结论仅适用于 candidate-v1，不再代表当前 v7 构建状态。当前 CMake 已 preserve `ext_decode`、`execute`，真实生成头已核导出 `zext_decode`、`zexecute`。

## v6 stage 恢复构建与 v7 源码绑定

构建目录为 `isla/target/float-solve-evidence/unified-backend-build/model-p1-v6-20260927/`。首次 `model-build.json` 为 FAIL：CMake 通过失效代理下载 CLI11 失败；原日志 `cmake-configure.log` 保留。恢复时使用 `dependency-cache/cli11_hpp-src/CLI11.hpp` 及 `jsoncons-v1.4.3.tar.gz`，分别核 SHA-256 `8bad421104bbac1d763be60e3f833768e72c2d9f6fa14a6d19162979ba97c2e9` 与 SHA3-256 `7ae49b206a2d271c4b1a122824fa76efaad91703f3124ac7a66a26d1eea1d07e`，均与模型 CMake 声明相同，再用 `FETCHCONTENT_SOURCE_DIR_CLI11_HPP`、`FETCHCONTENT_SOURCE_DIR_JSONCONS` 和 `FETCHCONTENT_FULLY_DISCONNECTED=ON` 配置成功。本次恢复没有网络下载。

随后旧冻结/复制规则递归排除所有 `build/`，导致 SoftFloat 缺少受 Git 管理的 `build/Linux-x86_64-GCC/platform.h`，失败保留在 `cpp-build.log`。两处 x86 源补件由 `cpp-source-supplement.json` 记录；模型冻结器与本入口随后改为只排除根 `build/`。最终 `unified-backend-model/20260927-final-v7/source-manifest.json` SHA-256 `7e945fbace1f28fdf86ff94744100311a97db31576cebaba2d2b141fb1502093`，920项。stage 又补齐其余平台文件，并由 `cpp-source-v7-bind.json`（SHA-256 `d4a31e791c46e777353bfa9c9656c2ca7d2b0fab7b255b5f13ec64c8a344d723`）绑定；本轮实读 stage 的920个文件与 v7 manifest 完全相同。

成功恢复配置见 `cmake-configure-v7.log`，exit0；随后从仓库根执行以下实际命令，exit0，日志 `cpp-build-v7.log` 最终为 `Built target sail_riscv_sim`：

```sh
cmake --build isla/target/float-solve-evidence/unified-backend-build/model-p1-v6-20260927/cmake-build \
  --target sail_riscv_sim --parallel 4
```

V128/E64 IR 由同版隔离工具链生成，具体 argv、配置和输出见 `ir-generation.json`，SHA-256 `46f9c877d4d5f093e0f89d2a4a1e80ab4261a789bcb5ebad07dcbd83198f62f6`，exit0。IR 输入使用 v6 manifest `749c3c5bba2995ecc048e22fd9baf375e6daec9b677c562b96d3c6d07ec7c911`；补齐的是 C++ 平台构建文件，v6与v7的整个 `model/` 文件集合/哈希相同，因此保留已有 IR，不重新生成。本轮重新核验 IR 的79个历史声明及函数体和三个直接状态函数均无缺失。

| 完整产物 | SHA-256 |
| --- | --- |
| `ir/rv64d_p1_unified.ir` | `348147f833432008d559be0e673dbd45982148b0750cd4533c68589a55aac061` |
| `cmake-build/sail_riscv_model.cpp` | `3f2af389cc81ca8ba276cb6007a3a08fa2f56ca0783fb7b2efbccf61659e54ca` |
| `cmake-build/sail_riscv_model.h` | `45fd0f832f01fb2b1bfa40d6bb2c76d942c2683e4262a4d81ec721259c46538d` |
| `cmake-build/c_emulator/sail_riscv_sim` | `2251afe3945d89d1846ddd7b7aae34e1c71a38da8815b9bd869bb42ae9773124` |
| `cmake-build/c_emulator/libriscv_model.a` | `8cd6d91d1cb6769f56cc571e614d5b710c4ef44f4e3ea548f302054d60fbdb5d` |
| `cmake-build/dependencies/softfloat/libsoftfloat.a` | `1671ac4816c2b093baefaffb1fffccc124619822283c01812e12e26aacb3d226` |
| `cmake-build/sail_runtime/libsail_runtime.a` | `4fd316e18773f144ab73f34336f72636ef6ac596a982c6a7c3cdfb1e68dca4e2` |

新增 `integration-result.json` 聚合以上成功证据，SHA-256 `96bcba4447f5fb580bafa4de6cb89734086b323e14c2900934b9f03d77c25a10`。其 scope 为已有产物与 provenance 的只读审计，成功命令退出码由原执行者确认；原始 FAIL 的 `model-build.json` 不改写。该总记录同时绑定工具链 manifest `009f76a6…a6202`、P0 manifest `d05ddcf5…f7b72`、v7源码、依赖缓存与实际产物。

## 离线公共入口与局部验证

[build_model.py](tools/unified_backend_build/build_model.py) 新增 `--dependency-cache DIR`：严格读取冻结模型的 FetchContent URL/hash 声明，检查原缓存和复制后的字节，CLI11 按 SHA-256、jsoncons 归档按 SHA3-256 校验；从已校验归档重新解压到输出目录。旧解压树不参与输入，归档仅接受单一顶层目录下的普通文件/目录，拒绝链接及越界路径。缺失或损坏均直接失败，不静默切换在线下载。CMake 指定两个 source override、断开 FetchContent 下载/更新，并关闭 GMP 下载；本机 GMP 仍是依赖。

`--configure-only` 只完成快照与配置，退出0时状态为 `CONFIGURED`、产物表为空；完整默认流程仍以 `PASS` 表示 C++/IR 构建与接口门槛通过。未传 cache 参数时保留原 CMake 下载模式并在 manifest 显式记录。脚本还在配置和构建后复核依赖快照不变，记录受测脚本 SHA、依赖声明 SHA、逐文件 hash 和实际配置命令。

局部验证目录为 `isla/target/float-solve-evidence/unified-backend-build/offline-cache-validation-20260927/`。已执行该目录 `validate.py`（完整命令在 `validation.json`）：

| 项目 | 实际结果 |
| --- | --- |
| 全部代理指向 `127.0.0.1:1`，新目录配置 | exit0，`CONFIGURED`；920项源码和1723项依赖快照一致 |
| 有效归档旁放置故意损坏的旧解压树 | 配置成功，生成的新解压树来自已校验归档 |
| CLI11 缓存追加损坏字节 | exit1，hash错误；配置命令未启动 |
| jsoncons 归档追加损坏字节 | exit1，hash错误；配置命令未启动 |
| jsoncons 归档缺失 | exit1，缺文件；配置命令未启动 |

本轮受测工具 SHA-256 `8cf04d844ca0ed83eeadaeea735d04c20b60c64dd51309c62a089af6343a5813`；`validation.json` SHA-256 `20c2a4f5cb114c721a7738af10d0878e5b0aee20ffbf1f87a40be2d99970dbc8`；成功配置的 `valid_archive/model-build.json` SHA-256 `1801c1247c844c245c098ea870e5457ae880d5473979358c104f9bcf41d0e59e`。配置日志有上游 CMake policy/effect 弃用提示，以及 source override 已生效后未读取断网变量的提示；没有依赖下载或配置失败。本轮没有重跑完整 C++/IR。

面向用户的完整命令、固定 hash 和后续完整构建用法见[工具 README 第2节](tools/unified_backend_build/README.md#2-固定-v7-源码并使用离线依赖缓存)。后续状态/flags语义、witness replay与官方77项验收仍由对应任务负责，不以这里的构建 PASS 代替。
