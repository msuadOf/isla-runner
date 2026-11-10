# D 阶段隔离候选工具

本目录只提供源码快照和 IR 名称静态检查。脚本不会建立 worktree、改执行器、生成 IR，或改动正式 `isla/rv64d.ir`、配置与 `isla/scripts/run.mk`。A、C/D 格式文件与共享异常库冻结并经主 agent 确认后，再运行快照命令。

## 1. 冻结两个子仓的输入

从父仓库根目录执行，输出目录必须在仓库外且为空：

```sh
D_OUT="$(mktemp -d)"
python3 agents/float_support_review/tools/snapshot_d.py --output "$D_OUT/snapshot"
```

`snapshot_d.py` 记录两个子仓的 HEAD、包含 staged 与 unstaged 修改的 `git diff --binary HEAD`、补丁 SHA-256、受改文件哈希和 Sail 新增文件哈希。Isla 仅接受 A 包的 `float.rs`、`smt.rs` 修改；出现其他未提交文件就停止。Sail 新文件白名单覆盖六个新模型文件、BF16 定向汇编及 `test/symbolic_fp/`、`test/ieee_exceptions/` 的源码/脚本；Python 缓存排除。任何其他未跟踪文件使快照失败，避免遗漏或意外混入。快照复制前后重新核对源码状态，变化即失败；此时应丢弃输出重新冻结。`manifest.json` 使用仓库相对路径，不保存本机目录。

快照只有补丁和新增文件，尚未构成候选源码。授权后的 D 隔离候选应使用 manifest 中的 HEAD 分别建立 **detached** worktree，在各自候选中 `git apply --check`、`git apply` 对应补丁，再复制白名单新增文件。worktree 和全部构建、Cargo、Sail 缓存放在 `D_OUT` 下；不要复用 `isla/.worktrees/memory-consistency`，也不要在共享主工作树构建候选。记录应用后 `git status --short` 和源码哈希并与 manifest 逐项对照。

## 2. 生成独立 V128 IR 后逐名检查

在**隔离 Sail 候选**中用 CMake 生成 `config/rv64d_v128_e64.json`。从候选的 `model/` 目录调用当前候选 Isla 插件，必须传 `-D SYMBOLIC`、`--config "$D_OUT/build/config/rv64d_v128_e64.json"`、四个 `--isla-preserve encdec_compressed_*`、独立 `--isla-output-dir`、外部 memo 路径及严格 Sail 标志。示意命令如下；实际命令和版本写入运行证据：

```sh
mkdir -p "$D_OUT/memo" "$D_OUT/ir"
sail -plugin "$ISLA_PLUGIN" -isla -D SYMBOLIC \
  --strict-var --strict-bitvector --strict-exponentials --require-version 0.20.1 \
  --memo-z3-path "$D_OUT/memo/sail_smt_cache" --all-modules \
  --isla-preserve encdec_compressed_forwards \
  --isla-preserve encdec_compressed_forwards_matches \
  --isla-preserve encdec_compressed_backwards \
  --isla-preserve encdec_compressed_backwards_matches \
  --isla-output-dir "$D_OUT/ir" \
  --config "$D_OUT/build/config/rv64d_v128_e64.json" \
  -o rv64d_d riscv.sail_project
```

`--memo-z3-path` 指向缓存**文件**；只创建其父目录，不要把 `sail_smt_cache` 自身建成目录。2026-09-26 第一次 D 全模型生成误把该选项指向已有目录，约 7 分钟后退出 2，报 `Is a directory`。当时虽写出约 15 MiB IR，该产物不计为通过；正式结论以修正路径后退出 0 的重跑产物为准。

不能用默认 `generated_isla_rv64d` 目标：其配置为 VLEN256。检查候选时显式传入原 IR、候选 IR、实际 JSON 和同一 Sail 快照中的接口声明：

```sh
python3 agents/float_support_review/tools/check_d_ir.py \
  --baseline "$ISLA_CANDIDATE/rv64d.ir" \
  --candidate "$D_OUT/ir/rv64d_d.ir" \
  --config "$D_OUT/build/config/rv64d_v128_e64.json" \
  --sail-interface "$SAIL_CANDIDATE/model/core/softfloat_interface.sail" \
  --report "$D_OUT/check_d_ir.json"
```

检查器从原 IR 逐名导出 79 个声明、12 个已有函数体和 67 个待迁移名称，验证 Sail 外部接口与 67 名称相同、候选 IR 保留全部原声明及 12 个旧体、67 个新体均已出现，同时检查同名 `riscv_*`/`ieee_*` 模型调用是否有普通函数体。它还检查实际配置文件名和 XLEN64、VLEN128、ELEN64。新增 RISC-V 纯辅助仅放行已审定的 9 个名称；其中 `riscv_f32_to_f16_normal_rm_bits` 来自 f32→f16 的 ROD 实现，把 ROD 编码 `0b110` 对应的普通窄化候选改用合法 RTZ `0b001`，避免提前求值时传入非法舍入编码。名单变化须审查并更新脚本。JSON 报告记录输入哈希、名称与错误。**静态 PASS 只证明 IR 结构，不能证明实际调用和语义。**

## 3. D 候选执行门槛

只在隔离 Isla 候选中先把旧 `softfloat_dispatch` 命中改为立即 `panic!`，使漏迁移暴露。候选构建通过后，再删除候选执行器中的旧分发入口并重跑。不得把这一步单独带回主工作树：旧正式 IR 仍有 67 个无体函数。

真实调用测试应由包装函数或指令路径调用每个 helper，再启用对应 `trace_functions` 并检查 `Event::Function { call: true }`。`execute_ir_function` 直接以 helper 为根调用时不会产生根函数的进入事件；可复用 `sail-riscv/test/symbolic_fp/run_stage_b.rs` 的包装器做法。运行还须检查每个结果位、五 flags、符号输入的完成路径数与依赖调用；`check_d_ir.py` 不能替代这些测试。67 项和 12 项各自留逐名结果及失败原因。正式源码、新 IR 和严格配置的切换属于 E 阶段。
