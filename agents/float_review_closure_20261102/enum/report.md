# 枚举 checkpoint 重放修复与验证

## 问题与修复

Isla `cf1aa14` 的 `Solver::from_checkpoint` 在同一 Z3 `Context` 重放枚举时，新 Solver 的私有 `Enums` 为空，再次调用 `Z3_mk_enumeration_sort` 声明同名类型。官方 Z3 `1fd1d3613` 拒绝该操作；原三项枚举重放测试因此不能完成模型回读。`from_checkpoint` 没有限定必须使用新 Context，故这是可修复的实现缺口。

本轮只改 `isla/isla-lib/src/smt.rs`。`Context` 按实际 Z3 sort 符号缓存枚举 sort、构造器和识别器，自己持有一套引用直到销毁；每个 Solver 仍持有和释放自己的引用。同 Context 重放沿用原 sort，原 `DefineEnum` 仍消耗相同数量的 `fresh` 编号；不同 Context 独立声明。相同名称但成员数量不同，以及空枚举，直接 panic，不进入 Z3 声明。模型回读仍按原整数 sort 名映射 `EnumId`。独立设计审查见[设计意见](../review/enum/design.md)。

## TDD 与实际结果

受测源码 HEAD `cf1aa1431d5f2d05584c78c0e7c84862a9a9b1fa` 加本地 `smt.rs` diff；最终 diff SHA256 `440b7a98765c8d92184fb066dde8d0e5170fb164e4858aa86db52c78baf10a1a`。所有 Release 测试仅在 CPU124（同胞 CPU60 预检空闲）上以 `--test-threads=1` 执行。构建使用独立 `enum/target`，从此前官方 target reflink 复制；未覆盖正式 `isarch` 或正式 target。

```sh
cd isla
z3_lib="$HOME/.local/opt/z3-official-1fd1d3613/lib"
taskset -c 124 env CARGO_BUILD_JOBS=1 \
  CARGO_TARGET_DIR="$(pwd)/../agents/float_review_closure_20261102/enum/target" \
  RUSTFLAGS="-L native=$z3_lib -C link-arg=-Wl,-rpath,$z3_lib" \
  cargo test --release --no-run -p isla-lib --lib
```

上述变量展开与实际构建的绝对目录、RUSTFLAGS 相同，详细输出见[RED 构建](tdd-build-red.log)与[GREEN 构建](build-green.log)。受测二进制 `enum/target/release/deps/isla_lib-2540c7f0f5fc82f1` SHA256 为 `1ebb556f1c09b669f83701c23afec98b6ad6dee746e47fded6010d5bf7422209`。`ldd` 指向官方 `libz3.so.5.3`；该库真实文件 SHA256 为 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`，与正式库一致。

先用旧官方二进制单跑原多成员测试，退出 1，报 `enumeration sort name is already declared`，见[原 RED](red-official.log)。先新增来源 Solver 销毁后重复重放、不同 Context、双枚举与模型回读测试，再编译旧实现，同样退出 1，见[新增 RED](tdd-new-red.log)。加入缓存后，原三项同 Context 重放和新增测试均通过；[SMT 过滤测试](smt-tests-green.log) 23/23，[完整 isla-lib 单测](isla-lib-full.log) 280/280，退出码均 0。新测试另核相同 sort 身份、不同枚举同名成员符号的类型隔离、同/跨 Solver 成员数量冲突、`DefineEnum` 直接调用冲突及空枚举拒绝。

`cargo fmt --check` 与 `git diff --check` 通过。未修改模型、IR、其他 Rust 文件或父仓 gitlink；未做 Clause 性能和 `make solve` 验收，本修复不据此声称改善正式浮点 Clause。
