# 六窄纯返回控制的候选回退准备

当前只准备候选，不改生产模型树、IR或冻结输入。现行模型为 `e9d69d2f28586c089244c8e37ee4c904c5114458`；比较对象为模型 `6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a`，与 Isla 基准 `0008fae` 分属不同仓库。热点只有 `model/extensions/V/vext_fp_utils_insts.sail`；[候选文件](candidate-vext_fp_utils_insts.sail)和[精确差异](source.diff)均从这两个 Git 对象制备，[逐函数核账](source-audit.json)记录哈希和计数。

最新准则的首批 Sol 裁决要求回退本轮六窄 `_pure` 的五个新增 overflow 外层 `if` 和三个 signed 饱和符号内层 `if`：这些分支只选择返回的钳位位串和 NV，没有 trap、模式或架构状态写回。给定 A 21.74–35.36 秒、B 45.15–64.14 秒均完成的配对结果，当前没有支持新增 fork 的超时依据。既有 `riscv_f16ToI16_pure` 外层 overflow `if` 单列 OPEN，本候选原样保留；其饱和端点改回原 `ite` 数据流。另五个 `_pure` 恢复原 ITE 返回式。六个普通 `riscv_f16ToI16`、`riscv_f16ToI8`、`riscv_f32ToI16`、`riscv_f16ToUi16`、`riscv_f16ToUi8`、`riscv_f32ToUi16` 函数逐字保留。

`e9d69d2` 该文件 SHA-256 为 `2c6042a67c1798e746178725ab42a3cf2ff9c1df5b4552a18bcb1e1757ec3564`；候选为 `34191de93086708b44f552606b39878e1ad68be07c67fb2321eb7bec1b1172e1`，与 `6202e23` 的完整文件逐字相同。差异只在 `$ifdef SYMBOLIC` 的六个 `_pure` 函数和相邻注释，候选相对 e9 为 14 行增加、16 行删除。核账确认删除五个新增 overflow `if` 和三个 signed 内层符号 `if`，保留 f16→i16 的既有外层 `if`；普通六函数逐字相同。

待最终 Sol 条目签收后，主流程在独立新候选树应用该文件，先以精确文件哈希和函数差异核对范围，再跑 Sail 普通 strict、四配置 SYMBOLIC 严格 IR 生成与 CFG 审核。代码或 IR 改版后，e9 的 819 helper、282 标量、183 向量，以及正式 qffp/Make 和相关 Clause 结果均退为历史证据；按新 IR 重新冻结来源、输入并定向复验，由独立 Sol 审动态结果。f16→i16 既有外层分支是否保留为最终最小结构，等待单列 OPEN 的最终裁决；本候选不预先改动它。

本次准备验证仅包括两个 Git 对象逐字读取、六普通函数逐字不变、六纯函数与6202逐字相同、5+3新增 `if` 计数归零、既有外层 `if` 保留，以及差异无空白错误。未运行类型检查、生成 IR、数值测试或完整 Clause，不能据候选文件宣称新版本 PASS。
