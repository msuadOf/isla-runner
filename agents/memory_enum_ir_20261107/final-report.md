# 枚举分支 IR 重生交付

五个 IR 已重新生成，来源与最终哈希复算通过；本轮本机定向验证通过。publication：**待发布**。未执行 Git 写操作、gitlink 更新或远端回读。旧 `4d085b14/bf861b3e` 的签收只适用旧版本，本轮结果不表示新独立签收、完整域覆盖或硬件验收。

## 实施与来源

- 根仓：`29aa47656e437d7f41e87d90a894edd125f429c2`，分支 `feat/memory-enum`。
- Isla 执行器/插件源码基准：`d7c259938a35aa9b712cb44b350a6f122bc020ef`，来源分支 `feat/postprocess-enumeration`。已核实包含 `4d085b14`；含区域合并/枚举。`isla-sail/`、生成驱动及永久 IR 检查器相对 `4d085b14` 无源码增量。
- 模型：`d79d8b320beec68b596e5e01e69cc353eb78f7a4`，来源分支 `feat/sail-riscv-memory-by-model-20261022`。新增 Svnapot、Svpbmt、非叶 PTE U/A/D 保留位检查，并含 `70b4d10` 的全寄存器访存早退清零 vstart 与 vmtype 坐标补件。本轮未改模型或 workaround。
- 工具：浮点 Sail `0.20.1 (feat/float-support @ f4f8e4584a70588c66c9e7a6286cc20211618f18)`；实际 Sail 可执行文件 `373a37c268779bad65381b98c3dc13d56c3db9db90102d28d6f410278b23d45a`；插件 `c4eccb06af9f85820c28bd67556ae0f191361c93cbe1afb334900f9e1f0e22f6`。复制历史快照到本轮 output；原目录只读。快照身份沿用二进制/标准库/插件哈希，不额外宣称核验全部 Sail 源码史。
- 首批普通严格检查通过，四组生成因缺 `Svnapot.supported` / `Svpbmt.supported` 退出1。按当前模型模板 `CONFIG_XLEN_IS_64`，四份生成 JSON 仅补 RV64=true、RV32=false。第二批使用全新独立缓存，普通严格检查退出0（221.094秒），四组 SYMBOLIC 生成全部退出0（约481–486秒），五入口安装成功，默认 RV64 与 VLEN128 字节相同。
- 166个模型输入、149个工具/配置文件经生成前后哈希核对，实际 Sail 与编译期 Z3 进程均被捕获。编译期 Z3 为4.16.0；运行时官方 Z3 库为 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`，两者分别记录。

## 五入口 SHA-256

| 文件 | SHA-256 |
| --- | --- |
| `isla/rv32d.ir` | `8ecc13f8f346b53efdd9598833cca8d2c5759ca99009130d8db358fbd61dca8e` |
| `isla/rv64d.ir` | `1220297d0e7dc202c43bb0cee1d95941c4bc3cf62be6fd141d35dbd5a3ad2059` |
| `isla/ir/rv64d_v128_e64.ir` | `1220297d0e7dc202c43bb0cee1d95941c4bc3cf62be6fd141d35dbd5a3ad2059` |
| `isla/ir/rv64d_v256_e64.ir` | `99f5efb054b5171fe060ad7815401ba3ec9ec6ca20550ac511e2f5eb1259ac86` |
| `isla/ir/rv64d_v512_e64.ir` | `e8fe8b380e6bac3563d4a0da52de02b5b9e5273c7ccf296a52d6a01787db34b3` |

新 [manifest](../../isla/ir/provenance/manifest.json) SHA-256：`26d458fe21ccabbdb0e928df81dd1a090bd487cab423c3797192ae0fd379fa14`。四份 `generation-*.json` 保存实际命令、模型/配置/工具哈希、退出码及日志哈希；`generation-inputs-20261107.json` 保存普通严格检查与共同输入。旧 manifest `8e06ec61…`、主 IR `40f34f70…` 及四配置历史哈希保留在 manifest 的 history、根仓 topic-version 的 history 和旧合流报告，未改署新版本。

Isla 的本轮 IR/provenance 仍未提交；manifest 中的 `isla_commit` 是执行器/生成源码基准，四份配置补项与本轮产物均有明确标记。后续形成 IR 提交并更新根仓 gitlink 时，须由 Claude 将最终提交绑定清楚。

## 本轮验证

受测 Release SHA-256：`674c0aaa9f1e7607a17363d95d3da5f84c43ac97ab72e766db9af932ea9c42ca`。批量求解每例 `-T 32`、最多四路，保留旧脚本核绑定；ExecuteAs 单次 `-T 64`。定向超时1200秒。旧 T1/7200秒结果保留原版本，不用于本轮性能对照。

| 验证项 | 本轮结果 | 证据（均以根仓为基准） |
| --- | --- | --- |
| 普通严格检查、四配置生成、五入口安装 | 通过 | `output/memory-enum-20261107/generation/current/`、`installed.json` |
| 来源与最终哈希 | 五入口、四配置、五份来源记录及根仓元数据一致 | `output/memory-enum-20261107/final-provenance-check.json` |
| Rust workspace --tests（含库与集成） | 1185通过、6忽略 | `output/memory-enum-20261107/workspace-tests.log`；安装新IR前运行，之后未改Rust源码；新IR另由永久回归与动态用例核验 |
| 永久 IR 回归 | 26/26步退出0 | `output/memory-enum-20261107/permanent-ir/checks.json` |
| 定向错误变异 | 104/104被拒绝 | `output/memory-enum-20261107/negative-104.json` |
| 浮点异常数值/flags | 315/315通过 | `output/memory-enum-20261107/dynamic/runs/numeric315/summary.json`；定向约束IR，非全部Clause |
| flags状态 helper | 五入口共300/300通过 | `output/memory-enum-20261107/dynamic/runs/flags/flags-300/result.json` |
| Schema Union 混合访存 | 九组全部 finished、各gen1；既有复算器复核九例无失败 | `output/memory-enum-20261107/dynamic/runs/union/union/`、`union-audit.json` |
| GCC/Clang 三表示 | 九组54/54一致 | `output/memory-enum-20261107/dynamic/runs/union-assembly/assembly/result.json` |
| vstart 两处指令边界 / mask helper | 8/8 / 4/4通过 | `output/memory-enum-20261107/dynamic/runs/vstart/`、`dynamic/runs/mask/` |
| ExecuteAs | `C_ADDI4SPN=0x1fe0`，x2=7→x8=1027；Retire、finished、无partial | `output/memory-enum-20261107/executeas/inspection.json` |
| 当前 run.mk 真实 Make 定向四入口 | FLEQ_S、LOAD_FP、STORE、C_LD均退出0/finished/无partial，gen数24/1/1/1 | `output/memory-enum-20261107/dynamic/runs/make/make/`；wrapper仅注入旧签收的机器字与Machine/mstatus前态 |
| Make JSON 双工具链核对 | 27条JSON、162/162字节一致 | `output/memory-enum-20261107/dynamic/runs/make-assembly/assembly/result.json` |
| 源码与格式 | 模型保持干净，源码前后清单相同，根仓/Isla diff --check通过 | `output/memory-enum-20261107/validation-checks.json`、`final-worktree-check.json` |

315项首次启动仅在预检阶段因缺 oracle.cpp 副本退出1，未执行数值用例。补齐本工作树 output 下的只读副本、核对原固定源码哈希后，单独重跑315/315通过。原失败日志和检查条目保留，并以 `superseded_by` 指向重跑；不是把旧失败静默改成通过。首批 IR 失败同样保留在 `generation/initial-missing-config/`。

## workaround 核对

`verify.py` 在新 IR 上通过79配置、130源码区域、22注释锚点。79份基准 IR 哈希均不匹配，按当前 `strict=false` 合同只告警。本轮未改 workaround 文件，也未把旧基准哈希替换成新值。

变更模型文件只影响 `vmtype.toml` 一项区域。`70b4d10` 已将 `process_vm` 从 `[652:2,673:3)` 迁到 `[658:2,679:3)`；按两版本各自配置提取的正文一致。其余区域不指向变更模型文件；全部注释锚点一致。证据：`output/memory-enum-20261107/workaround-diff.json`、`workaround-before.log`、`workaround-after.log`。这是源码位置/锚点检查，不宣称130区域都实际命中IR或覆盖全部语义。

## 文件与复现

Isla：五个 IR；四份生成配置；manifest；四份生成 sidecar 和一份共同输入 sidecar。根仓：topic-version JSON、topic-versions/ir-workflow、TODOs、RESULTS、议题索引/发现和本目录的计划、报告、复现脚本；另补 `/output/` 忽略规则。所有构建产物、原始日志及实际JSON均在本工作树 `output/memory-enum-20261107/`，未写入历史工作区或 home。

完整步骤与工具复制命令见 [reproduce.md](reproduce.md)。总运行命令和退出码见 `output/memory-enum-20261107/validation-checks.json`，输入版本/哈希见 `inputs.json`，实际生成命令还保存在可提交 provenance 中。最终独立重算命令为：

```sh
python3 agents/memory_enum_ir_20261107/check_provenance.py --check-topic
```

## 未做与遗留

- 未单独重复 workspace --lib 入口；--tests已覆盖库与集成，6项忽略按原设置保留。
- 未重跑全部77浮点Clause预算、全部访存/异常域、原域Make或硬件重放；当前控制流全覆盖未测。
- 未重做F1新旧对照、三类Poison逐例复放和旧memory长尾；不将旧缺陷归因转记为本轮实证。
- 本轮未运行新Svnapot/Svpbmt/非叶保留位专用语义测试；本轮严格生成与既有定向回归不替代这些功能的专门验收。
- 未做新独立签收、正式远端可获取性核实或任何Git写操作。两个新源码提交、IR/provenance提交、根仓gitlink与最终发布由Claude处理。publication保持待发布。
