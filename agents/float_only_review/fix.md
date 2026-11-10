# 仅浮点分支修复交付（2026-10-08）

**已修复本轮确认的旧IR缺函数回归和FD快速访问状态缺陷。** `feat/float-only-20261008` 现为 `be1296b`，两个提交均按用户指定格式；工作树干净，未push。受审工作树为`.worktree/isla-float-only-20261008`。原审查结论仍适用于修前 `d04883b`，见 [审查报告](report.md)。

| 提交 | 内容 |
| --- | --- |
| `5ceb3ad` | `fix(float-ir): 补齐各架构模型的普通浮点函数实现` |
| `be1296b` | `fix(float-state): 恢复快速浮点寄存器访问的状态副作用` |

## 修复及边界

第一提交保持Rust专用SoftFloat分派退役，从冻结d012默认IR中装配普通浮点helper的完整依赖闭包。RV32补齐63个原缺体接口，三个历史RV64产物各补齐67个；原函数、寄存器、初始化和实际架构参数保持。函数、类型及extern绑定严格匹配；提供方SourceLoc重映射到保留旧前缀的files表，未知位置ID分配到不冲突的区间。

第二提交仅替换五份IR的`get_F_bits/set_F_bits`。快速getter恢复Ext_F断言与位型转换；快速setter顺序为断言→转换→写入→原值callback→Dirty，保持快速寄存器访问方式。其依赖全部复用目标定义，包括架构专属`dirty_fd_context`，因此RV32更新SD31，RV64更新SD63。没有导入提供方的RV64 Dirty函数。另加固装配工具的参数一一映射和元组字段顺序冲突检查，两个负例先RED再GREEN。

相对d04883b，原有定义仅上述两FD函数和files改变；其余原定义逐字保留。严格重装配能逐字重现两层提交的五份IR，重复装配显式拒绝。主审机器核账见 [assembly-verification.json](fix-evidence/assembly-verification.json)，独立gpt-6-astra high用独立参数双射、位置和pragma核对，并读取实际输出JSON复核，最终未发现阻塞问题。

历史`ir/rv64d_v512_e64.ir`实际仍为VLEN256，未夹带改成512；RV32仍为XLEN32/FLEN64/VLEN256/ELEN32。其他旧IR的BF16 execute历史实现保持，不能把默认IR的BF16修复通过迁记到它们。

## 来源与重现

本轮是**冻结生成IR组件装配**，不是五份完整模型重新生成。纯helper提供方为d04883b中的d012默认IR。精确d012模型原临时目录已不存在，未使用当前未提交Sail-RISC-V工作树冒充该源链。

FD提供方从已有c5cbb候选的165个冻结模型文件重新生成；模型manifest SHA-256=`128d59a5661c3efdba566682c58ee6733f4799d9afd19fa3c6a542d24d95f346`，每件源码及实际Sail stdlib与manifest一致。Sail0.20.1（446fb477），插件SHA-256=`c4eccb06af9f85820c28bd67556ae0f191361c93cbe1afb334900f9e1f0e22f6`，配置V128/E64 SHA-256=`89923ebff21718bb382df38bf246207cbb1eb5ae0cd314d078d87c0ab2b9f625`。严格SYMBOLIC生成退出0、516.72秒；提供方IR SHA-256=`cdd2234dff60ff74eb380182c57f4d124b25a6d2d0e35cf086c3067bbc64ac01`。

完整生成命令、165件hash及输出见 [state-provider.json](fix-evidence/state-provider.json)，脚本见 [generate_state_provider.py](fix-evidence/generate_state_provider.py)。组件装配命令见 [migration-commands.json](fix-evidence/migration-commands.json)、[state-migration-commands.json](fix-evidence/state-migration-commands.json)。同一路径fdext_regs.sail的旧函数与替换函数来自不同冻结版本，其行号应结合这些组件来源解释，不能假定整份IR来自同一模型快照。

| 最终产物 | SHA-256 |
| --- | --- |
| `rv64d.ir` | `aea104c88a3c90f5e3030365d38dbcbc97a058dcfaf22b77b6717bffae59b544` |
| `rv32d.ir` | `88b6f5d8dd4a314a3dc720f2aa943fefebb65c61c9dd581a2e7a214e6081c583` |
| `ir/rv64d_v128_e64.ir` | `d1fff976f4f04d0baf29ec9b9de51105ca8d7bcc252759f6fb5405191563329d` |
| `ir/rv64d_v256_e64.ir`与历史v512 | `2498a77d98d4ce8c071834632606d98b3ec4b3085f3573ddb3c9cda6bfa2e2ed` |

两提交只进入浮点分支，没有通用提交混入。原isla HEAD、索引及staged/unstaged补丁hash逐项未变；未修改Sail-RISC-V源码、父gitlink或其他功能分支。提交及产物hash见 [after.json](fix-evidence/after.json)。

## 验证

| 最终检查 | 结果 |
| --- | --- |
| 独立SoftFloat完整结果＋五flags差异UNSAT | 1615/1615 PASS：四份RV64各327例／67helper，RV32307例／63helper |
| 真实getter/setter/FADD.S状态 | 五份各36例，共180 PASS；快速/普通、FS三态、同值写、其他31FPR哨兵、完整fcsr/mstatus |
| Ext_F=false隔离断言域 | 五份各4例，共20 PASS；修前默认普通两例通过、快速两例失败 |
| 默认BF16 scalar sNaN活动性 | 6/6 PASS，零活动／活动／旧flags保留 |
| 原legacy向量 | 35/35 PASS |
| generic float单测 | 10/10 PASS |
| isla库＋isarch bin | 68＋25 PASS，明确跳过基线已有rv64_target_trait失败 |
| 装配冲突负例 | 两例先RED、加固后2/2 PASS |
| 默认编译、主库及独立runner fmt | PASS |

状态测试是列定具体初态的执行与SAT模型值检查，不是任意初态全域等价证明。Ext_F在这些IR中编译期折叠为true，guard只在测试副本翻转该静态能力臂；不声称TOML关闭了编译能力或完成无F架构的整指令验收。

RV32使用专用测试配置：SATP/Misa按32位、CLINT参数按34位物理地址类型给定，mstatus仍为64位载体。早期误用RV64配置造成初始化101已保留于 [state](fix-evidence/state/)；修正后的实际SD31结果见 [state-final](fix-evidence/state-final/)。早期用const_primops关闭已折叠能力的无效guard实验保留在候选日志；正式证据为`guard-red.log`和最终guard日志。

公共make入口在独立源码副本运行，采用T1、ITRACE、60/50/20秒预算与qfaufbv，逐项核对退出0、最终JSON、gen与编码：

| IR | MRET | FLEQ.S | 其他默认项 |
| --- | --- | --- | --- |
| 新默认V128 | 4 | 16 | FCVT.S.BF16=39、FLI.S=32 |
| 历史V128 | 4 | 16 | — |
| 历史V256 | 4 | 16 | — |
| 历史v512文件（实际V256） | 4 | 16 | — |

旧V256公共入口FLEQ.S从修前退出0／0gen恢复到退出0／16gen；MRET非浮点回归仍4gen。命令及版本见 [make-matrix.json](fix-evidence/make-matrix.json)，原始JSON/日志见 [make-matrix](fix-evidence/make-matrix/)；未覆盖原工作树output。

持久回归入口位于指定浮点工作树，在该Isla仓库根目录运行：

```sh
python3 test/float_ir/run.py --output /tmp/float-ir-regression
```

当前最终证据分别为 [helpers-final](fix-evidence/helpers-final/)、[state-final](fix-evidence/state-final/)、[final-checks.json](fix-evidence/final-checks.json)与[final-bf16.json](fix-evidence/final-bf16.json)。Debug使用实际Z3 4.13.3，make release使用4.16.0；工具与二进制信息见原审查 [after.json](evidence/after.json)及本轮产物记录。

没有运行全77项、全isla-lib、公共RV32 solve-state、完整源码branch覆盖或硬件差分。旧IR的其他历史浮点执行缺陷及“v512实际256”边界仍保留。本交付限定验收本轮兼容性及FD状态修复，不迁记其他候选的全量结果。
