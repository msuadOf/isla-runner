# 统一浮点后端 P0 隔离探针

此目录保存可审阅的固定 Sail 0.20.1、`446fb477c508853595ccc937ed60765aa685ae31` 最小编译器补丁，以及 fixture 生成和复现脚本。原 P0 构建、IR、运行日志及哈希清单在 `isla/target/float-solve-evidence/unified-backend-p0/20260926T162859Z/`，该目录为忽略的隔离证据，未改主安装 Sail、生产模型或 `1dcc` 阶段。

`compiler.patch` 只改 `src/sail_c_backend/c_backend.ml`：降低四种原生 FP 与 RM 类型、生成 C/C++ 均合法的异常任意返回值，并把原始 Eq/Neq 的 FP/RM 分派到 typed equality。应用后通过 `dune build --release @install` 构建；调用该副本的 `sail` 包装脚本，才能加载 C++ 后端插件。不能仅调用 `_build/default/src/bin/sail.exe`。

若需要从固定提交另建隔离编译器，从仓库根目录使用新的构建目录：

```sh
P0_BUILD="isla/target/float-solve-evidence/unified-backend-p0/$NEW_BUILD_TIMESTAMP"
test ! -e "$P0_BUILD" || exit 1
mkdir -p "$P0_BUILD/sail-src"
git -C "$SAIL_BASELINE" archive 446fb477c508853595ccc937ed60765aa685ae31 | tar -xf - -C "$P0_BUILD/sail-src"
patch -d "$P0_BUILD/sail-src" -p1 < agents/float_support_review/tools/unified_backend_p0/compiler.patch
(cd "$P0_BUILD/sail-src" && dune build --release @install)
```

其中 `SAIL_BASELINE` 指向干净的该提交源码 checkout。fixture 从指定 `model` 目录复制真实 `ieee_fp_exceptions.sail`、`riscv_f32Add`/`riscv_f64Add` 实现及所需 prelude；两个后端都用 `-D SYMBOLIC`。`make_fixture.py` 明确接受两种源形态：旧 `SYMBOLIC` 宏加原策略 `cpp:softfloat_*` 时，仅在副本中加双绑定、纯 Sail fallback 并移除两个 Add 的策略绑定；已统一的 `{c: ..., cpp: ...}` 与普通函数体则直接复制。其它形态在断言处停止。`fixture/source-manifest.json` 保存源形态及复制前后各文件哈希。C++与Isla使用同一份 fixture；原 P0 精确 argv 见其 `manifest.json`。

用已构建的隔离 Sail、SoftFloat 库、Isla 插件和 Isla runtime 从当前模型重跑。所有手写测试源、case 和 runner 均在 `fixtures/`，`replay.py` 只向一个新的 `--out` 目录写入产物，拒绝覆盖已有证据：

```sh
python3 agents/float_support_review/tools/unified_backend_p0/replay.py \
  --repo . \
  --out "isla/target/float-solve-evidence/unified-backend-p0/$NEW_UTC_TIMESTAMP" \
  --sail "$P0_SAIL" \
  --softfloat-include sail-riscv/dependencies/softfloat/berkeley-softfloat-3/source/include \
  --softfloat-lib "$P0_SOFTFLOAT_LIB" \
  --sail-runtime-lib "$P0_SAIL_RUNTIME_LIB" \
  --isla-plugin "$P0_ISLA_PLUGIN" \
  --isla-lib "$P0_ISLA_LIB"
```

`P0_SAIL` 指向带本补丁的 `sail` 包装脚本，`P0_ISLA_LIB` 指向含 `Cargo.toml` 的冻结 `isla-lib` 目录；其余变量指向已构建的对应文件。也可用 `--model-source` 指向旧形态模型。一次成功的当前统一源码复现在 `isla/target/float-solve-evidence/unified-backend-p0/20260926T184941Z/replay.json`；该文件记录 `unified-native`、23 个命令的实际 argv、退出码和关键产物哈希。旧形态分支已用原 P0 源哈希恢复七份旧输入，并在 `20260926T190230Z/legacy-check.json` 核对生成的七份 fixture 与原 P0 逐文件哈希相同。原 P0 目录及其 `manifest.json` 未被复现脚本改动。

P0 独立验证包括原编译器五类型生成红、补丁后五类型生成和对象编译绿、record/RM Eq/ITE 的 ASan+UBSan 37 项、C11 native 类型对象编译、共用 Sail Add 公式的 C++ 真实运行，以及同 fixture Isla IR 在冻结 runtime 上执行。C++ 31 项和 Isla 26 个 f32/f64 Add 样例全结果位与五 flags 对照直接 SoftFloat oracle；另验证 f128 RD/RU 与两字位序、NaN 抽象相等、未知输入单 SAT 完成路径。C++ adapter 的 SoftFloat 状态按单线程/独立进程合同每次保存、设置并恢复；当前库状态是进程全局，不提供线程并发保证。

`fp.to_ieee_bv(NaN)` 的原始位串在 Isla/Z3 未指定。证据 `ir/history-nan-ieee-raw-fail/` 保留曾对它错误要求固定编码的失败记录；最终只对非 NaN f128 直接出口逐 128 位比较。RISC-V 的 f32/f64 包装用 Sail canonical NaN 选择，仍逐位及逐 flags 比较。

`make_manifest.py` 是原 P0 证据冻结脚本，校验各命令退出码、关键输出和源/库/二进制哈希后写 `manifest.json`；现拒绝覆盖已存在的 manifest。新复现用 `replay.py` 生成独立 `replay.json`。隔离 Sail 源码无 `.git`，其 `--version` 字符串会读到父仓库的 Git 元数据；源码版本以 archive 提交、原始文件哈希及补丁哈希为准。
