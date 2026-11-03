# IEEE 异常控制边界与 ROD jam 局部实施证据

## 源码版本与范围

- 模型基线：`6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a`；仅改 runner-float 模型的 `model/core/ieee_fp_exceptions.sail`。该文件基线 SHA-256 为 `fdb105f1bf911b5d13fef2bfa2ee1f46b66a4ccca3c6d878bc31063937cedbc6`，现为 `23fda9824c2280609062bbe2b9766597681c29af13a1e9cf1be045d9106757a8`。完整差异见 [source.diff](source.diff)，机械重写部分见 [rewrite_exceptions.py](rewrite_exceptions.py)。未提交或推送。
- H/S/D 的 add、sub、mul、div、sqrt、FMA 共 18 个异常函数：各源 NaN 分类仍先独立计算；异号/同号 Inf、零乘 Inf 两个位置、除法三原因、负非零 sqrt、FMA Inf product 抵消各有实际结果出口。普通定向区间计算与 OF/UF/NX 选择只在原有限/有效门控内运行。FMA 仍用原 `fp*_fma`，没有拆成乘加。
- 三个算术 rounded helper 和 exact threshold helper 按最终 OF、UF、NX 结果分支，保留原比较及阈值公式，也保留所有 Bool 组合；未假设 OF 与 UF 互斥或 OF 必伴 NX。整数转换 NV/NX、round NX 和四个跨格式/BF16 转换的有限门控显式化。两个 ROD helper 的 RTZ 基值、原异常 facts 与最低位 OR 保持，精确/非精确分别返回。
- `fdext_regs.sail`、三个 `softfloat_symbolic_f*.sail` 与 `vext_fp_utils_insts.sail` 由其他 owner 修改；本轮未写这些文件。根 `sail-riscv/` 未写。

## 局部验证

- `python3 agents/float_review_closure_20261102/exceptions/verify_equivalence.py`：退出 0。按 H/S/D 的零、有限 1、Inf、qNaN、sNaN及正负号，对旧/新算术 flags 做 33,840 组逐点布尔对照；四类 rounded 出口另测任意 OF/tiny/NX 的 8 种组合；ROD 两宽度测试精确偶/奇、非精确正/负共 8 个数值 oracle 例。测试脚本只核局部 flags 代数与 RTZ jam，不能替代 Sail/IR 或完整指令语义。
- `sail --fmt-only core/ieee_fp_exceptions.sail --fmt --fmt-emit stdout > /dev/null`（在模型 `model/` 下）：退出 0，源码可解析。
- `git -C .worktree/runner-float/sail-riscv diff --check -- model/core/ieee_fp_exceptions.sail`：退出 0。
- `sail --project riscv.sail_project --just-check --no-warn`（在模型 `model/` 下）：退出 1，停在未改的 `extensions/V/vext_utils_insts.sail:391`，`masked_select` 的 `'m >= 0` 量词未解出。本次没有取得完整类型检查结论；该错误不作为本文件通过或失败的判断。

独立源码审查见 `review/model/exceptions-source-review.json`；其签收仅适用上述文件哈希。四配置 IR CFG 与动态 Clause/oracle 尚待主流程按合成模型完成，局部数学对照不写作这些阶段的 PASS。
