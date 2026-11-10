# 两个 mapping 优化的实际 decoder 审计

本工具只生成显式的 `audit-only` 比较制品，不生成或替换正式模型 IR。它比较旧 c5 的真实 `ext_decode` 与最终新 IR 的 `ext_decode`，范围是下述固定编码形状和官方 R1 符号初态；结果不代表整个 decoder 或官方 77 项通过。

## 比较形状

| 模式 | 固定编码 | 唯一未知编码字段 |
| --- | --- | --- |
| `vfmacc_vv` | `0xb2401457`：funct6=0x2c，vm=1，vs2=4，funct3=1，vd=8，opcode=0x57 | bits[19:15]，完整未知 5 位 vs1 |
| `vfwmacc_vf` | `0xf2405457`：funct6=0x3c，vm=1，vs2=4，funct3=5，vd=8，opcode=0x57 | bits[19:15]，完整未知 5 位 rs1 |

完整 word 为固定编码与未知字段左移 15 位后的组合。权限、FS、VS、SEW、LMUL、vl 等状态不在本工具内固定；它调用实际 `RV64::setup_pre_state`，使用真实 `hartSupports` 与官方域约束。

## 证明义务

旧、新 IR 进入同一个字符串符号表。工具复制旧 `ext_decode` 的完整直接调用闭包，为旧函数及对应签名建立独占名称，并重写闭包内调用。类型、字段、constructor 与全局名字保持共享，禁止跨两个独立符号表直接比较数值 Name。共享类型、全局初始化、外部接口及元数据必须核对；不兼容即失败。

旧 decoder 和共享初始化的函数闭包、签名、局部声明、表达式及全局类型共同决定递归类型可达集。旧 IR 独有且不在该集合内的类型及对应 pragma 可以作为明确记录的无关差异排除；必需类型缺失仍失败，不补类型掩盖差异。文件表按路径建立并集，旧 SourceLoc 显式重映射，保留原始文件归属及转换记录。

两边都经过 `assertions_to_jumps`，采用 `Optimistic` 和模型寄存器初始化。分开执行前，R1 初态及惰性辅助寄存器只分配一次符号；两边共享该状态与 solver checkpoint。静态纯读检查涵盖寄存器、全局 let、间接地址、Monomorphize 与所有 callee，动态事件只接受 Smt、Fork、Function 和 ReadReg。

每个形状先确认初始域 SAT、完整编码差异 UNSAT，再分别执行旧→新和新→旧。每条外层 SAT 完成路径必须被内层 SAT 路径覆盖；每个路径对先按共享 IR 返回类型递归校验 constructor、Struct 的完整字段集合、enum、位宽和符号类型，并拒绝任意深度 Poison，再用原 typed AST/payload 的完整等值取反查询，要求 UNSAT。单一模型 witness、构造器名称计数或打印文本相同均不足以通过。Dead 只在再次证实 UNSAT 后单列；错误、Unknown、采样或未完成都会失败。两个受影响 mapping 在旧、新两侧的四个精确函数名均须实际到达。

## 使用

以下路径参数由本轮冻结制品提供。`--isla` 指向完整运行时或冻结 stage；`--output` 均须为空目录。构建清单固定源码、锁文件、编译命令与二进制哈希，运行前再次核对。构建会先清理自身审计 crate 以防共享 target 复用旧程序，随后保留一份项目独有的二进制；`--offline` 可使用已有依赖缓存。

```sh
python3 prepare.py --isla ISLA_STAGE --output AUDIT_PROJECT --build --offline
python3 run.py --project AUDIT_PROJECT --old-ir OLD_C5_IR --new-ir FINAL_IR --config FD_CONFIG --output PREPARE_EVIDENCE --mode prepare
python3 run.py --project AUDIT_PROJECT --old-ir OLD_C5_IR --new-ir FINAL_IR --config FD_CONFIG --output VV_OLD_NEW --mode vfmacc_vv --direction old_to_new
python3 run.py --project AUDIT_PROJECT --old-ir OLD_C5_IR --new-ir FINAL_IR --config FD_CONFIG --output VV_NEW_OLD --mode vfmacc_vv --direction new_to_old
python3 run.py --project AUDIT_PROJECT --old-ir OLD_C5_IR --new-ir FINAL_IR --config FD_CONFIG --output VF_OLD_NEW --mode vfwmacc_vf --direction old_to_new
python3 run.py --project AUDIT_PROJECT --old-ir OLD_C5_IR --new-ir FINAL_IR --config FD_CONFIG --output VF_NEW_OLD --mode vfwmacc_vf --direction new_to_old
```

每次运行外限最多 120 秒；`--direction` 仅选择先执行的一侧，不改变任何输入约束。默认 `both` 包含该形状双向义务，也可按上述四个方向顺序运行。超时终止整个进程组并记为 124，保留全部已写日志；内部即使残留 `pass` 也不能覆盖外层超时。只有自然退出 0、制品绑定不变、形状/方向和完整结果状态符合预期时，外层账本才标记 `accepted`。四个独立方向须使用相同源码、二进制、IR、配置和输入域，全部被接受且覆盖账本齐全后，才能汇总两个形状的双向证明。`prepare` 的成功仅表示比较制品和静态门槛已准备，不表示动态形状证明通过。

当前实施与动态结果由所属议题报告登记；本说明列出协议，不预先宣称任何候选 PASS。
