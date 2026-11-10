# 合流模型严格生成与 IR 来源独审

ordinary strict、四配置 SYMBOLIC 新生成来源、五入口安装与索引身份均已独立签收，无本范围源码或 IR 来源阻断。本结论不包含动态语义或完整 Clause 预算。

来源固定模型 `bf861b3e687894480aec701a886a38d4e50b8a99`，批次为候选根目录下 `agents/float_memory_merge_20261103/validation/generation/merge-bf861b3e-20261104/`。166 个模型文件全部与已签源码清单相同。独立在 ordinary 执行期间读取预冻结清单，149 个 launcher、实际 Sail、标准库、插件、driver 与配置文件逐哈希一致，见 [输入回读](generation-inputs-independent.json)。

另从实际 `/proc` 进程树捕获生成器、ordinary Sail 的命令、工作目录及 Sail 可执行文件哈希，并捕获其编译期 Z3 可执行文件哈希，见 [独立进程证据](generation-live-processes-independent.json)。这里的 Z3 是既有 Sail 工具链使用的 Brew 4.16.0，仅用于模型类型约束；Isla 运行时指定官方 Z3 的构建与动态链接另行验收。

已审本轮新的生成、审计与安装脚本：生成前冻结模型/工具/配置哈希，每个任务结束复核不变，采集 live Sail/Z3；安装器分别核 ordinary 和 SYMBOLIC 的严格参数、模型/工具/配置/IR 哈希，再安装五入口和新 manifest。manifest 中旧工具来源字段以本轮实际工具哈希和 reported commit 更新。未修改 float 历史脚本或旧签收证据。

普通检查实际命令包含 `--just-check`、三个 `--strict-*`、`--all-modules` 与 `--require-version 0.20.1`，不带 `SYMBOLIC`；退出 0，147.687 秒。模型、149 工具文件及编译 Z3 前后哈希均保持，实际 live Sail/Z3 哈希与预冻结值相符。四配置结束后才核新 IR、配置侧车和 default/V128 别名；不将普通检查当作行为验收。

四配置均在本次从干净合并模型实际生成，没有复用旧 memo 或旧 IR；任务、generation 记录、实际文件和配置侧车哈希一致，完整源清单与全部严格选项、11 个 preserve helper 及输出目录逐项核对通过。四配置 source/tool/compile-Z3 前后哈希和 live 可执行文件均匹配。耗时与 IR SHA-256：

| 配置 | 秒 | IR SHA-256 |
| --- | ---: | --- |
| RV64 V128 | 350.845 | `40f34f706963afcca7dfbf8504ee888bdd004cd0c437712f097b7dda64a705c9` |
| RV32 | 351.109 | `2387c44ed3890816c8373b9fd63c797642ea3a8d09f8b5dbe3d6c2c0b278bc66` |
| RV64 V256 | 353.465 | `598ed3a004b609b7dd5821af84f1ef56fa6a9085e08947aab26fb6b0a3a486d9` |
| RV64 V512 | 353.474 | `c5fed455a865bcc7ac481395a784cf20b7dc231d46185335c20e3a65be842bf1` |

还独立解析实际 IR 函数，删除源坐标和空白、仅按签名位置重命名编译器生成的参数名后比较表达式及分支。每配置的 `get_start_element` 返回 `%i`，函数体精确等于 memory 直接读取 `vstart` 的 helper。相对同配置 float，core 异常、V 浮点工具、FD 三格式包装及 FD 寄存器文件导出的函数体保持：RV64 每配置 220 个、RV32 215 个。这涵盖本轮 77 处纯数据回退、NaN 特殊值及冻结 OPEN 的相关 helper，不以该函数身份检查代替新动态结果。

逐任务记录及函数名列表见 [实际生成独立证据](generated-ir-independent.json)。原 float/memory 旧 PASS 没有改署本版；本次来源结论只基于本批新日志、新 IR 和前后哈希。

安装后独立重跑 `--installed`，核五入口逐字对应本轮四份生成文件，`rv64d.ir` 与 V128 别名相同；四配置侧车保持原字节且哈希等于本批实际使用值。新 manifest 的模型、工具、166 源文件、四配置、五路径及 audit 链全部匹配。再直接读取 Git 索引中的五 IR 和 manifest，其字节与工作文件相同，manifest SHA-256 为 `8e06ec617ca8378d965f8d9b2f0f882e7262520e9ac5cb488604f7470949268b`。见 [安装独立证据](generated-ir-independent-installed.json) 和 [索引身份](installed-index-independent.json)。

独立后验脚本为 `python3 agents/float_memory_merge_20261103/review/model/audit_generated_ir.py`；安装后增加 `--installed`。脚本只写本审查目录；新 IR 来源签收不包含动态预算或全域语义结论。
