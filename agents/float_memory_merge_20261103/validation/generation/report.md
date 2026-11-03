# 合流模型严格生成与 IR 来源

模型提交为 `bf861b3e687894480aec701a886a38d4e50b8a99`，合并树在生成前后保持干净。`generate.py` 先执行普通 `--just-check` 严格检查，再并行执行 RV32、RV64 VLEN128/256/512 的完整 `SYMBOLIC` 生成。全部任务使用独立目录及独立 `sail_smt_cache`；本批未复用旧 memo。实际命令、完整模型文件哈希、工具和配置哈希、执行时间、退出码及采样到的 Sail/Z3 可执行文件见[可移植来源清单](merge-bf861b3e-20261104/source-portable.json)及[实际命令摘录](../../implementation/generation-commands-curated.json)。原 `source.json`、各 `driver.json` 和 `generation.json` 含本机绝对路径，保留在候选工作区；可移植清单只规范化路径前缀，原件与副本的哈希见[精选清单](../../implementation/evidence-selection.json)。

| 配置 | 退出码 | 秒数 | IR SHA-256 |
| --- | ---: | ---: | --- |
| 普通严格检查 | 0 | 147.687 | 无 IR |
| RV32 | 0 | 351.109 | `2387c44ed3890816c8373b9fd63c797642ea3a8d09f8b5dbe3d6c2c0b278bc66` |
| RV64 VLEN128 | 0 | 350.845 | `40f34f706963afcca7dfbf8504ee888bdd004cd0c437712f097b7dda64a705c9` |
| RV64 VLEN256 | 0 | 353.465 | `598ed3a004b609b7dd5821af84f1ef56fa6a9085e08947aab26fb6b0a3a486d9` |
| RV64 VLEN512 | 0 | 353.474 | `c5fed455a865bcc7ac481395a784cf20b7dc231d46185335c20e3a65be842bf1` |

独立输入审计确认 166 个已跟踪模型输入、149 个 Sail/插件/标准库/驱动/配置文件在生成前后逐哈希相同，文件 ctime 早于批次开始。Sail 0.20.1 实际可执行文件 SHA-256 为 `373a37c268779bad65381b98c3dc13d56c3db9db90102d28d6f410278b23d45a`；类型检查期间捕获的 Z3 4.16.0 可执行文件 SHA-256 为 `a7eac84c5493ac5766c2179620c3a4628b151198af9e6e9c488163c84561b3e9`。运行时官方 Z3 动态库另在 Release 构建与测试中核对，不能混同。

五个入口及 manifest 已由 `integration/install_ir.py --install` 安装，RV64 默认与 VLEN128 逐字相同。四份配置 sidecar 保持生成时哈希，manifest 为 `8e06ec617ca8378d965f8d9b2f0f882e7262520e9ac5cb488604f7470949268b`，逐项保存四个生成结果和配置哈希。79 份 workaround 配置、130 个 region、22 个源码锚点通过；79 个旧基准 IR 哈希仅警告，按 `strict=false` 合同处理。独立 Sol 来源、安装和索引复核见 [`ir-review.md`](../../review/model/ir-review.md)。以上是来源与结构验证，动态行为另记。
