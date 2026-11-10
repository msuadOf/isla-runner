# 全寄存器访存早退清零 vstart

2026-11-02。`process_vlre` 和 `process_vsre` 原来在 `vstart >= evl` 时正常退休，但跳过函数末尾的 `set_vstart(zeros())`。现仅在这两个既有早退出口清零后退休，保留非陷阱策略和其余执行结构。源码为 `.worktree/sail-riscv-memory-by-model-20261022/model/extensions/V/vext_mem_insts.sail`，HEAD 为 `c70482a73be2a67c5a89d88b1e6c2bbea224940c`，改动未提交、未移动分支。

## 回归结果

入口为 [check_vstart_post.py](check_vstart_post.py)，通过重命名两个 IR helper 并附加 wrapper，在原函数返回后断言 `vstart=0`。原 helper 函数体逐字保留；只改隔离 IR。固定 `VLEN=128`、`EEW=8`、`nf=1`，因此 `evl=16`。输入 `vstart=15` 是正常访存对照，16 恰等于 evl，17 超过 evl，全 1 检查高位非陷阱策略。

| 阶段 | `vstart=15` load/store | `vstart=16/17/全1` load/store | 结论 |
| --- | --- | --- | --- |
| 源模型 IR | 2/2 通过，各一次访存 | 6/6 后态断言过滤，无访存 | RED：早退未清零 |
| 修复后 V128 IR | 2/2 通过，各一次访存 | 6/6 通过，无访存 | GREEN：8/8 正常退休且后态清零 |

RED 的精确命令、IR/执行器/配置哈希、每例 summary 见 [red-v2/result.json](red-v2/result.json)；GREEN 见 [green/result.json](green/result.json)。最初 `red/` 中判定器将返回值误写为 `Retire_Success`，实际输出是 `Retire_Success(())`，导致两个正常访存对照被误判；修正后在独立的 `red-v2/` 重跑，没有覆盖原证据。测试严格要求 `summary.status=finished`、零错误/断言过滤、恰一条退休结果及相应访存次数。RED 输入 IR 为现有 `isla/.worktrees/memory-consistency/rv64d.ir`，其旧来源由该目录 `ir/provenance/manifest.json` 锁定为模型 `c70482a7`；GREEN 输入为本次新生成的隔离 `generated/rv64d/rv64d.ir`。

普通和 `-D SYMBOLIC` 两次 Sail 严格 `--just-check` 均退出 0，日志为 [ordinary-check.log](ordinary-check.log) 和 [symbolic-check.log](symbolic-check.log)。参数均含 `--all-modules --require-version 0.20.1 --strict-var --strict-bitvector --strict-exponentials --memo-z3-path`，受测项目是该模型目录的 `riscv.sail_project`。这证明模型通过类型及严格约束检查；动态后态结论仅覆盖上述八例。

## 隔离 IR 生成与来源

[freeze_and_generate.py](freeze_and_generate.py) 将当前 dirty 模型的 159 个 `model/` 文件复制到 `generated/frozen-model/`，逐文件比较后生成 IR。它同时保存完整 `generated/worktree.patch`：包含本修复及协调方同步的 `vmtype.toml` 预算坐标调整。现有 `isla/.worktrees/memory-consistency/scripts/regenerate_ir.py` 要求干净模型，会拒绝本次未提交改动，因此本脚本明确记录 dirty 状态并从冻结快照生成。`generated/source-manifest.json` 保存 HEAD、dirty patch SHA-256 `27395dea774f2c089028f4da0e005e584efdcfeb1586b288bb879af370065893`、全部模型文件哈希、四配置哈希、工具哈希和版本。该 manifest 自身 SHA-256 为 `d3ae6602e16599a0b109d431b00d15419c6ac0b81aaa7733793973dd85751251`。相对旧配套 IR 的 159 文件 manifest，只有 `extensions/V/vext_mem_insts.sail` 改变，其新 SHA-256 为 `6c7ae6ca4f482a2e624205ce7e2b504ce991a089e39a9305f51f0d7f97c80de5`。

使用既有 Sail 0.20.1 构建：启动脚本 SHA-256 `2e89d5f5467195ea0a2fb4b072133a0ee73933db3e8808b8a6518c7ef59ec807`，其实际执行的 `sail` 二进制 SHA-256 `373a37c268779bad65381b98c3dc13d56c3db9db90102d28d6f410278b23d45a`，版本输出 `Sail 0.20.1 (feat/float-support @ f4f8e4584a70588c66c9e7a6286cc20211618f18)`。Isla Sail 插件 SHA-256 `c4eccb06af9f85820c28bd67556ae0f191361c93cbe1afb334900f9e1f0e22f6`。生成参数与旧配套 manifest 相同：`-isla -D SYMBOLIC`、三个严格开关、四个压缩译码和七个 F/V helper 的 `--isla-preserve`、`--all-modules` 及各配置 JSON。每项完整命令和日志在 `generated/<名称>/generation.json`、`generation.log`。

| 配置 / 隔离 IR | 配置 SHA-256 | 新 IR SHA-256 | Sail 退出 |
| --- | --- | --- | --- |
| `rv64d` / V128 | `89923ebff21718bb382df38bf246207cbb1eb5ae0cd314d078d87c0ab2b9f625` | `c0e4661a73888c56438a6f76059370667d141a026502d0511291586067bd31c0` | 0 |
| `rv32d` / V128 | `bf36f1d84bc96d1229d546eefe3cae0b7282a03cea5064ade904eb1d90a23b30` | `79a02c9d084581673aaa672c73a48b191edeeb28565382138284318f3ed5964d` | 0 |
| `rv64d_v256_e64` | `e28ac77273be6a31c544db6b196914dfb55b3b9fb72295ae7ef6cfc7b99dfc47` | `4f78d1106220f032f8f4003d77aee82a5162ce99f99a2c65eb51047eb5034ed0` | 0 |
| `rv64d_v512_e64` | `9b32561d0d880d01732da669769237d8fc881e5de3e4b6384073c928ef3c3ff1` | `e1ccaba2bf85380cd2af5ed65cbb498f457ead4696fbc20820ce00ffe316e6dd` | 0 |

在仓库根目录可运行 `python3 agents/coordinated_memory_fixes_20261102/model/freeze_and_generate.py --out agents/coordinated_memory_fixes_20261102/model/generated --verify` 核对四份 IR、四配置、来源 manifest 与当前模型文件；本轮退出 0。`--resume --only <名称...>` 可复用并核对已完成的项，本轮四项复用核对也退出 0。原先顺序生成进程写完 V128 的 `generation.json` 后，因并行进程已创建 RV32 输出目录而收到 `FileExistsError`；该进程总退出 1 是调度冲突，V128 的 Sail 退出 0，其余三项并行 Sail 也各退出 0。隔离 IR 的后续生产安装和 provenance 更新由主 agent 负责。
