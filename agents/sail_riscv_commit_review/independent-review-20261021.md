# Sail-RISC-V 独立审阅（2026-10-21）

本轮未发现新的、已确证的浮点数值或寄存器最终状态回归。建议保留这组候选，但完整接纳仍需闭合编译器依赖，并修复三个失效的测试入口。这里的构建问题与测试问题不等同于 IEEE 算法错误。

## 范围与版本

- 基线：`4f2ac293654a02db26dac5055be7f93fd6e3141e`。
- 候选：`feat/sail-riscv-by-category-20261019@3ea3cbaf599b0b210a365eac50736f097b4b2337`，工作树 `.worktree/sail-riscv-by-category-20261019`。
- 12 个提交，151 个变更路径；候选 tree 为 `6fafcbc406156ee275bcf301e6db1743eb417a0f`，与 `755fea6e` 相同。审阅前后该工作树均干净。
- 阅读根协作规则、目标/结构/状态入口、Git 与 IR 工作流、相关既有发现后，直接核对候选源码和基线 diff。重点覆盖 IEEE 异常、三个格式包装、C++ adapter、FPR/VPR setter、向量纯 helper、逐元素改写、归约、BF16、译码匹配及测试构造器。
- 未修改生产源码、Git 索引/分支、原测试产物或共享状态文件。证据仅写入本报告及 [independent-review-20261021/](independent-review-20261021/)。

## 确证问题，按优先级排序

### F1 — P1：普通 C++ 构建已依赖未在本候选交付的 Sail lowering 补丁

适用边界是“使用项目声明支持的普通 Sail 工具链独立构建”。已明确配置补丁工具链的实验工作区可绕过此问题。

定位：`model/prelude/ieee_fp_primops.sail:12`、`model/core/softfloat_interface.sail:38`、`model/riscv.sail_project:7,192`、`model/CMakeLists.txt:90`；顶层 `CMakeLists.txt:24` 仍只要求 Sail 0.20.1。

第 06 提交 `70e3890b` 移除旧 `riscv_f*` 包装的 C++ extern 映射，普通构建开始使用含 `float16/32/64/128` 与 `float_rounding_mode` 的 Sail 函数体。仓内 C++ adapter 实现了对应操作，但标准 Sail 0.20.1 的 C++ lowering 不认识这些类型。仅增加 adapter/header 不能解决生成阶段失败。

独立复现使用候选原样 prelude 与一条 `fp32_add` 保留函数，而非沿用旧失败日志：

| 工具链 | `--cpp` 结果 |
| --- | --- |
| 已安装标准 Sail 0.20.1，源码版本 `446fb477c508853595ccc937ed60765aa685ae31` | 退出 1：`C backend: No C type for type float_rounding_mode`，位置为上述第 12 行 |
| 既有 `toolchain-a198-v2-20260927/sail-src/sail` 补丁版 | 相同输入退出 0 |

命令和小模型见 [checks.json](independent-review-20261021/checks.json)、[stock-probe.sail_project](independent-review-20261021/stock-probe.sail_project)、[失败日志](independent-review-20261021/stock-compiler.log)。本轮没有重跑全模型标准编译器失败；小模型已经直接隔离出候选必须使用的缺失 lowering。

修正建议：把固定 Sail 基线、补丁哈希和构建步骤纳入可获取的工具链交付，并在公共构建入口进行能力预检，不能只检查版本字符串。另一选择是保留普通 C++ 旧包装直到新工具链交付。已有补丁位于父仓库 `agents/float_support_review/tools/unified_backend_p0/compiler.patch`；不能把只含 Sail-RISC-V commit 的 checkout 宣称为可独立构建。此项需要修改构建入口/依赖交付，不要求改 IEEE 公式。

### F2 — P2：三个随候选提交的回归入口在当前源码上无法执行到被测语义

这是当前测试代码的可复现缺陷；没有据此判定生产语义失败。

| 文件/行 | 触发与本轮结果 | 原因及建议 |
| --- | --- | --- |
| `test/solve_fp_legality/build_probe.py:37` | 对候选运行构造器，退出 1，`unapproved change outside four functions in vext_utils_insts.sail` | 测试仍限定旧四函数变化，当前还改了寄存器分组与 mask 辅助层。应按当前接纳范围更新冻结对照和测试合同，并单独验证新增合法性修复。 |
| `test/solve_pure_compare/restore_before.py:27` | 外部独立目录还原后退出 1，`ieee_fp_exceptions.sail` SHA 不等于 manifest | 冻结反向 patch/manifest 与当前生产树不配套。应保留旧版本适用说明，并提供当前候选可运行的对照入口；不能只删除哈希检查。 |
| `test/symbolic_fp/solve_vector_lanes/build_helper_probe.py:23` | 构造器退出 0，但补丁 Sail 类型检查退出 1，`Function old_fp_min_pure not found` | 全局字符串替换把现行 `fp_min` 内的 `fp_min_pure` 也改名成未定义的旧函数。应显式取得旧函数体或正确绑定对照 helper，避免两边实际都使用同一新实现。 |

本轮日志：[合法性](independent-review-20261021/legality-fixture.log)、[旧比较还原](independent-review-20261021/old-compare-fixture.log)、[向量 helper](independent-review-20261021/vector-helper.log)。这些旧审阅问题仍然存在；已重新执行确认，不是复制旧结论。修复属于测试源码与适用版本文档，不是改生产逻辑来迎合旧 fixture。

## 本轮新增数值验证

对候选 `git ls-tree -r --name-only HEAD` 列出的 1011 个路径与 `.tmp/sail-riscv-split-20261016/final-source` 做逐文件字节比较，无差异。使用该来源已经生成的普通 C++ 模型库，重新编译本轮独立调用器；没有重新生成或重新编译完整模型。模型生成文件、库、配置和调用器 SHA-256 见 [numeric-check.json](independent-review-20261021/numeric-check.json)。

受测接口仅为 **f16/f32/f64 × Add、Sub、Mul、Div、Sqrt、MulAdd，共 18 个包装**。调用实际生成模型的 `zriscv_f*` 方法，逐次对比结果位与 Berkeley SoftFloat 原操作的异常 flags；oracle 每次设置相同 RM、after-rounding tininess 并清零 flags。NaN 结果按 RISC-V canonical NaN 比较。没有用候选 Sail 异常公式计算 oracle flags。

| 输入 | 结果 |
| --- | --- |
| 固定随机种子 `20261021`，18 个包装 × 5 RM × 2000 次调用 | **180000/180000 相等** |
| 每格式 18 个边界值，5 RM，三个操作数位置的笛卡尔组合 | **524880/524880 次调用相等（含重复）** |

边界值包括 ±0、最小 subnormal、最大 subnormal、最小 normal 及邻值、1/2 的邻值、最大有限值、±inf、qNaN、±sNaN。二元/一元操作不使用全部三个位置，因此边界调用数包含重复，不能表述为 524880 个互异输入。

证据：[随机调用器](independent-review-20261021/numeric-probe.cpp)、[随机结果](independent-review-20261021/numeric-run.log)、[边界调用器](independent-review-20261021/directed-probe.cpp)、[边界结果](independent-review-20261021/directed-run.log)。直接构建命令在 `numeric-check.json`；边界调用器使用相同命令替换源文件和输出文件名。二进制与临时构建输出在记录哈希后删除，保留源码、命令和日志。

该检查特别支持新增 **Sail 异常计算与 SoftFloat flags** 在列定输入上的一致性。两边数值运算仍共用 SoftFloat，因此它不是独立数值算法的证明，也不是全部 67 包装或 SYMBOLIC 执行的 PASS。

## 源码复核结论与风险边界

- **旧快速 FPR/VPR 副作用缺陷已修复**：`fdext_regs.sail:253–291` 补齐扩展断言、寄存器表示转换、写回调和 Dirty；`vext_regs.sail:242–258` 补齐向量 Dirty 与写回调。普通臂继续调用原 helper。本轮未重跑直接寄存器状态探针。
- **BF16 无活动元素误置 NV 已修复**：普通 `VFWMACCBF16_VF` 仅在首次活动 lane 累计标量转换异常；SYMBOLIC 把标量、向量转换与 FMA flags 一同按活动 mask 筛选。没有把 BF16 当作 f16，也没有以分离乘加替代融合 FMA。本轮未重跑 BF16 指令测试。
- **IEEE 旧反例未继续沿用为当前缺陷**：当前实现明确屏蔽 NaN/非有限输入的 NX/OF/UF、保留 sNaN 判定、区分 quiet/ordered 比较、检测 FMA 无穷抵消，并处理无效整数转换的 ISA 饱和值；本轮 18 包装对照未发现反例。格式/整数转换、ROD 和 BF16 窄化没有新增动态结论。
- **归约保留依赖顺序**：候选每 lane 先从当前 `sum` 计算候选，再以 mask 选择新 `sum`；没有把 ordered reduction 改成并行树。widening 的转换 flags 与加法 flags 同时受 mask 筛选。零 VL 返回及非零 vstart 合法性检查仍在。未新增完整向量/SYMBOLIC 状态等价证明。
- **合法域修正不应与等价优化混淆**：第 07 提交明确拒绝普通 FP 的 SEW8，并保留 INT8↔FP16 合法转换；BF16 仅 SEW16。`VFWUNARY0/VFNUNARY0` 仍保留旧模型“部分 SEW8 在首个活动 lane 才报 Illegal”的行为。这是保留的 constructor/映射边界，不是本轮新引入的回归；直接 constructor 使用者不可据此宣称所有非法状态都在统一入口拒绝。
- **callback 等价有明确限制**：SYMBOLIC `accrue_fflags` 直接用 ITE 更新 mstatus，没有调用普通 `dirty_fd_context` 中的 mstatus callback；源码内 SYMBOLIC callback 函数体为空，所以未把它判定为当前 Isla 最终状态错误。若以后用 SYMBOLIC 生成带外部 callback 的 C++ 或观察调用 trace，需要单独恢复/约定该合同。普通 C++ 分支保留原 callback 路径，不能把这个风险写成普通 C++ 已漏回调。
- **依赖与验证仍有空缺**：未重新生成 IR、重绑 workaround、运行完整求解/硬件测试；未重新执行所有 67 helper、转换、宽整数 adapter、RV32 或完整向量状态矩阵。本轮数值检查不能替代这些验收。

## 接纳建议

1. 汇编文本、快速寄存器状态修复、合法性修复、BF16 无活动元素修复的接纳价值明确。按依赖取精确提交或整理出最小补丁，不能忽略公共 Bool 接口依赖。
2. 第 06 提交的共用浮点后端可保留为候选；公开接纳前先处理 F1。当前独立数值证据支持列定算术包装，但尚不足以签收全部共用接口。
3. 第 08–10、12 提交的向量优化先处理 F2，并补当前精确树的双分支状态/flags 对照。不得用本轮标量算术 PASS 替代 mask、vstart、vl、SEW/LMUL 与归约验收。
4. 若父仓库仅记录候选快照，可以固定本 SHA 并明确工具链及测试限制；不能标为联合验收通过。此报告不要求回滚已保留的原工作区或移动现有 Git 边界。
