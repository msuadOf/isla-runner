# 本轮复现入口

从根仓执行。需要已有本机历史浮点 Sail 快照、Isla 插件、SoftFloat oracle、官方 Z3 与离线 Cargo 缓存。历史工作区只读。下面 `../..` 指本隔离 worktree 的原根仓；也可给 `--prior-workspace` 指定其他只读副本。普通发行版 Sail 不能替代该快照。

输出根目录为 `output/memory-enum-20261107/`。脚本拒绝覆盖已有批次；再次运行前先保留并改名现有输出。本轮首批缺配置的失败记录在 `generation/initial-missing-config/`，成功重跑在 `generation/current/`。四份生成 JSON 已按当前模型模板补齐 Svnapot/Svpbmt：RV64=true，RV32=false。

```sh
python3 agents/memory_enum_ir_20261107/provision.py --prior-workspace ../..
python3 agents/memory_enum_ir_20261107/prepare_validation.py --prior-workspace ../..

export CARGO_TARGET_DIR="$PWD/output/memory-enum-20261107/target"
export CARGO_BUILD_JOBS=8
export CARGO_NET_OFFLINE=true
export Z3_PREFIX="${Z3_PREFIX:-$HOME/.local/opt/z3-official-1fd1d3613}"
export RUSTFLAGS="-L native=$Z3_PREFIX/lib -C link-arg=-Wl,-rpath,$Z3_PREFIX/lib"

make -C isla build-isarch ITRACE=1 Z3_TIMEOUT_IMPL=thread_interrupt \
  > output/memory-enum-20261107/build.log 2>&1
cargo test --manifest-path isla/Cargo.toml --workspace --tests --offline \
  --features smt-thread-interrupt,tracetool \
  > output/memory-enum-20261107/workspace-tests.log 2>&1

python3 agents/float_memory_merge_20261103/validation/freeze_source.py \
  --tree isla --isla-source --output output/memory-enum-20261107/isla-source.json
python3 agents/float_memory_merge_20261103/validation/freeze_source.py \
  --tree sail-riscv --output output/memory-enum-20261107/model-source.json
python3 agents/float_memory_merge_20261103/validation/dynamic/prepare_config.py \
  --fd isla/configs/riscv64_difftest_fd.toml \
  --memory isla/configs/riscv64_difftest_mem.toml \
  --output output/memory-enum-20261107/mixed-directed.toml

python3 agents/memory_enum_ir_20261107/generate.py \
  --sail output/memory-enum-20261107/toolchain/sail-src/sail \
  --plugin output/memory-enum-20261107/toolchain/sail_plugin_isla.cmxs \
  --commit d79d8b320beec68b596e5e01e69cc353eb78f7a4 \
  --batch current --cpus 24,25,26,27 \
  > output/memory-enum-20261107/generate.log 2>&1
python3 agents/memory_enum_ir_20261107/install.py \
  > output/memory-enum-20261107/install.log 2>&1
python3 agents/v_symbolic_ir_workarounds/verify.py \
  > output/memory-enum-20261107/workaround-after.log 2>&1
python3 agents/memory_enum_ir_20261107/validate.py \
  > output/memory-enum-20261107/validate.log 2>&1
python3 agents/memory_enum_ir_20261107/update_metadata.py
python3 agents/memory_enum_ir_20261107/check_provenance.py --check-topic
```

`generate.py` 沿用旧合流生成器，仅将输出移到本轮 `output/`；普通严格检查先行，四组 SYMBOLIC 任务各用独立缓存，最多四路。实际 Sail 命令数组保存在各组 `generation.json`；安装时复制为 `isla/ir/provenance/generation-*.json`，并将工作区路径改为 `repo:/`。

`prepare_validation.py` 复制旧验收器到 `output/`，只调整输出、依赖路径、Cargo 依赖和并发参数。批量求解改为每例 `-T 32`、最多四路，保留旧核绑定；ExecuteAs 单次为 `-T 64`。定向用例时间上限为1200秒，原合流的7200秒预算只作历史记录。未改数值期望值、生成配置母本或检查规则。Make 仍调用当前 `run.mk` 和 `solve_process.py`；wrapper 仅注入旧签收相同的机器字和前态。

`install.py` 不执行 Git 写操作。它将默认 RV64 与 VLEN128 安装为相同字节，保存旧 manifest 哈希和四组历史 IR 哈希，核对工具、配置和模型在生成前后未变化。`check_provenance.py` 再独立重算五入口、四配置和来源记录，并核对根仓版本记录；它不代表完整模型语义验收。
