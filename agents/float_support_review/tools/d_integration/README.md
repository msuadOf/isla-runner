# D 隔离验收源码与样例

此目录保存 D 隔离候选验收中可复用的源码和输入，不包含候选 IR、构建产物或 Spike 二进制。原始记录及动态结果见 [D 运行记录](../../d-run.md)。这里的文件来自 D 隔离工作目录；复制的文件保持原字节，下面列出 SHA-256。`prepare_runner.py` 和 `reference/refresh_curated.py` 是归档时新增的路径配置与 350 例刷新工具。

## 固定来源

- Isla 基线 `f4f8e4584a70588c66c9e7a6286cc20211618f18`、Sail-RISC-V 基线 `f8ce8490981eac6396a31013180a2e718615757d`；D 使用这两个基线加隔离快照补丁与已删除旧分发的 executor。补丁及候选源码未收录在本目录，不能只凭这两个 commit 重现 D 结果。
- 独立参考是 Ara `toolchain/riscv-isa-sim` 的 Spike SoftFloat API，固定 commit `204b88deda9bcb7537bc09ae5c320f691e8839ef`；调用 `f16/f32/f64_recip7` 与 `f16/f32/f64_rsqrte7`。验收时该 checkout 的 `riscv/` 另有改动，`softfloat/` 源文件未改。参考可复现性依赖取得该固定源码并自行构建库。
- RISC-V V v1.0 规范来源 commit `3570f998903f00352552b670f1f7b7334f0a144a`，`v-spec.adoc` SHA-256 `bfe42bd33dc6abeef5362f475605dda3d229e722257a613b0691cee760f04a19`。规范文件未在此重复收录。
- D 原测试 IR `rv64d_d_reproduced.ir` SHA-256 `74e3bc71fcf0d2e6b70aff3b005af780317b6eb8b8f6fc21b4ae21e5dd52a934`，需要按 [D 运行记录](../../d-run.md) 在外部目录重建或提供同哈希文件。

| 归档文件 | 原 D 文件 SHA-256 | 行数 |
| --- | --- | ---: |
| `d_runner/src/main.rs` | `9a9c8e264534540dd51a716d21e1e4206093b5449873ccf39980cf7042df07e2` | — |
| `d_runner/Cargo.lock` | `e2c2d82a23696e13e830fdb206a52d86c2225375929005bc1da2027759cd7b98` | — |
| `d_runner/cases.tsv` | `d7c2f633e066bff78a39b766f4b1834a748778fd61b50c099e5df5650f02408c` | 67 |
| `d_runner/old12_cases.tsv` | `f0db644d9a61721b5a4b12828bdf0aacf47bf23f61cfcf685d5e1f1eb3a69098` | 39 |
| `reference/spike-estimate-oracle.c` | `7a7e874b8d5f62c6583e733b120b30ce76c63bae06d593d64a042d7236b9de94` | — |
| `reference/spike-estimate-cases.tsv` | `92e0e300bb322fad9a27db79ceb9661971a115ebb6dbe89b0daba67360d98236` | 350 |
| `reference/estimate_sweep.tsv` | `3cd9c03ec220a7f7810dc3294c2750178f55a6673ac214b3882b1c42eeca08ad` | 1618 |
| `reference/generate_estimate_sweep.py` | `63ff893759aabb21d02ad09b0bc37b6069f6318aa903e0a29b305b60bad9d3de` | — |
| `reference/estimate_sweep.json` | `41f07c4c5275c2fc1c1506d8d105b3f56622cde8338ae72044846c3ddc67391e` | — |
| `reference/estimate_special.tsv` | `ad4da3fc89b9be734f5fde80766e5eae69fd6f55b67613cb13a3a5b81928cfe9` | 420 |
| `reference/generate_estimate_special.py` | `89e574535ec2ff04a6ddbb5fc6536553209bf34882feb70532f533df38c9a6ac` | — |

其余复制文件 `d_runner/old12_narrow_boundaries.tsv`（SHA-256 `3003ba7e877cc49872a3df15dc31530fffa43f49037855144eace9ba94dd67da`）和 `reference/estimate_special.json`（SHA-256 `50ffde6e51c99b47b9bead989b9b7a99f7e361688127b2a9e7a3f6bad26b4e8f`）也与原 D 文件逐字节一致；350 例的原输入选择脚本不在 D 快照中，`refresh_curated.py` 仅按已有 TSV 输入重新调用 Spike，不重建选择过程。

## 在仓库外构建与运行

以下变量由调用者指定，均可指向仓库外的工作目录；命令从本目录执行。`ISLA_LIB_DIR` 应指向含 D 隔离补丁、删除旧分发的 Isla 候选 `isla-lib` crate。普通当前 Isla 源码不能替代它作为 D 动态复现证据。

```sh
: "${D_WORK:?set an external work directory}"
: "${ISLA_LIB_DIR:?set D candidate isla-lib path}"
python3 prepare_runner.py --isla-lib "$ISLA_LIB_DIR" --output "$D_WORK/d_runner"
cargo fmt --manifest-path "$D_WORK/d_runner/Cargo.toml" --check
cargo check --manifest-path "$D_WORK/d_runner/Cargo.toml" --locked
cargo build --manifest-path "$D_WORK/d_runner/Cargo.toml" --locked

: "${D_IR:?set wrapped D candidate IR path}"
for cases in d_runner/cases.tsv reference/spike-estimate-cases.tsv reference/estimate_sweep.tsv reference/estimate_special.tsv d_runner/old12_cases.tsv d_runner/old12_narrow_boundaries.tsv; do
  "$D_WORK/d_runner/target/debug/isla-float-d-runner" "$D_IR" "$cases"
done
```

Runner 检查每例 SAT、结果位与五 flags 的差异 UNSAT、普通函数调用事件和恰好一条完成路径。样例测试不能推导所有输入的符号等价，也不覆盖 E 正式集成。

要重新生成 1618/420 例，先使用上述 Spike commit 构建 SoftFloat 共享库。调用者按该 checkout 的布局设置头文件目录、库目录，编译归档的 C API 调用源；所有输出在外部工作目录：

```sh
: "${SPIKE_INCLUDE_DIR:?set fixed Spike softfloat.h directory}"
: "${SPIKE_LIB_DIR:?set fixed Spike SoftFloat shared-library directory}"
cc -I "$SPIKE_INCLUDE_DIR" reference/spike-estimate-oracle.c -L "$SPIKE_LIB_DIR" -lsoftfloat -o "$D_WORK/spike-estimate-oracle"
SPIKE_ORACLE="$D_WORK/spike-estimate-oracle"
export LD_LIBRARY_PATH="$SPIKE_LIB_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
python3 reference/generate_estimate_sweep.py --oracle "$SPIKE_ORACLE" --output "$D_WORK/estimate_sweep.tsv"
python3 reference/generate_estimate_special.py --oracle "$SPIKE_ORACLE" --output "$D_WORK/estimate_special.tsv"
python3 reference/refresh_curated.py --oracle "$SPIKE_ORACLE" --input reference/spike-estimate-cases.tsv --output "$D_WORK/spike-estimate-cases.tsv"
cmp reference/estimate_sweep.tsv "$D_WORK/estimate_sweep.tsv"
cmp reference/estimate_special.tsv "$D_WORK/estimate_special.tsv"
cmp reference/spike-estimate-cases.tsv "$D_WORK/spike-estimate-cases.tsv"
```

Spike 二进制、SoftFloat 库、完整候选补丁/IR 与 D 快照均为外部依赖，未归档在此目录。原 D 记录的 `reference/spike-estimate-oracle` 和 `reference/libsoftfloat.so` 哈希分别是 `5df09858c896ffeff02fb170dd07372114071a93bafe604cba23c95c2cfe6833`、`f1592214d4845ba004aaa487f3f3285e6cbd0909597e126e5438c2f4ae614b41`；它们仅标识原运行物，不要求另一机器上的重编译二进制同哈希。
