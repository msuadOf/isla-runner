# 77 处纯返回分支回退：模型实施核账

按主流程授权，已将[独立 Sol 签收的五份候选](../../architecture-candidates-review-20261103.md)逐字应用于独立模型树 `.worktree/sail-riscv-float-converged-20261103`，分 core、V、FD 三次提交。模型基线为 `e9d69d2f28586c089244c8e37ee4c904c5114458`；最终 HEAD 为 `0f7b8fbc6724103f91f929ef6918f123df75d6c9`，分支 `fix/float-converge-20261103`，工作树干净。此处 `0008fae` 是 Isla 的共同参照，不是模型提交。

| 职责 | 提交 | 模型文件与最终 SHA-256 |
| --- | --- | --- |
| 算术异常原因 | `3d9ceebb8ae81b45ccafcde7cab81c0ab5b49bd8` | `model/core/ieee_fp_exceptions.sail` — `7ed9529baac57717875ea49e8fff5130d3ec611f824aa71483b2b856d67c96b4` |
| 窄转换纯返回 | `7eb4bd5c137c500209678f2f6eb007b572179b74` | `model/extensions/V/vext_fp_utils_insts.sail` — `34191de93086708b44f552606b39878e1ad68be07c67fb2321eb7bec1b1172e1` |
| 整数包装结果 | `0f7b8fbc6724103f91f929ef6918f123df75d6c9` | `model/extensions/FD/softfloat_symbolic_f16.sail` — `715795790c0efb100806c0a82195e137c4de66c4a9614baac9ee2b0b333a0646`；`softfloat_symbolic_f32.sail` — `ffe71d8f99652a20f9c7c6d969648af75bdc575ee9f2ca34e459fdfa879c5e17`；`softfloat_symbolic_f64.sail` — `b5b8ea9e4723e647fa74ea8ebfa47129106993a3a99d9df80105f9b3eab545ce` |

应用前逐文件核 e9 源 SHA 和候选 SHA，并核独审 JSON 中相应哈希；提交后回读完整文件字节与候选一致。相对 e9 仅上述五文件改变，三个提交各只含本职责文件。18 个算术异常 helper 删除 33 个仅选择 NV/DZ 的原因 `if`；六窄 `_pure` 删除本轮新增的 5 个 overflow 和 3 个 signed sign `if`；12 个整数包装删除 36 个纯结果选择 `if`。合计 77 处源码 `if`，不将此计数冒充动态 fork 数。

[实施核账脚本](implementation-verify.py)退出 0，[机器结果](implementation-audit.json)核对提交链、干净状态、五文件精确哈希和仅五文件差异。脚本将 18 个目标异常函数置回 e9 后要求 core 整文件逐字相同，并逐一确认其 `finite/valid` gate 仍在；将 12 个目标整数包装置回后要求三个 FD 文件逐字等于 e9，因而两处 ROD 模式 guard 及非目标内容保持；六个普通窄转换逐函数与 e9 相同，既有 f16→i16 外层 overflow `if` 保留。`fdext_regs.sail` 等其余文件未改，flags changed、其他 finite/valid gate、NaN 结果传播、真实陷阱和合法性控制继续保持 e9。OPEN 项仅冻结源码，不因此获得架构接纳。

应用后的检查：五文件 `sail --fmt-only` 均退出 0；`git diff --check e9d69d2 HEAD` 退出 0；只读候选独审脚本 `architecture-candidates-review-20261103.py` 退出 0，核 18 个异常函数、33 处原因分支、12,288 个 wrapper 选择组合、64 个任意 flags/gate 组合和 90 个不变 FP 数值绑定。上述是源码及局部公式核对；普通/SYMBOLIC strict、IR/CFG、动态数值和 77 条完整 Clause 预算由后续验证另记，新模型不继承 e9/214 的 PASS。生产 e9 和冻结 runner-float 214 树均未修改。
