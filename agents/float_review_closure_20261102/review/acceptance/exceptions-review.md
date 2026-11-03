# 异常、ROD 与 BF16 动态独立签收

模型 `8ad5e8e`、Isla `42000be`、新V128 IR `5ecea371…` 的315项固定输入数值/flags/状态验收限定签收，无当前数值阻断。使用首批305条成功输出及修正配置文本后另批10条D向量成功输出；首批10个配置解析失败原样保留，不声称首批全PASS。

正式inputs `25a1a624…`、isarch `fe4bdceb…`、官方Z3 `899cbc70…`、seed17、T1/qffp、CPU17/29。定向预算600秒，不能替代正式整Clause和单SMT7200秒。原始入口：[结果报告](../../validation/exceptions/result.md)、[首批](../../validation/exceptions/runs-model-8ad5e8e/launch.json)、[10项复验](../../validation/exceptions/runs-model-8ad5e8e-vd-retry/launch.json)。259项scalar/ROD/普通转换、30项H/S/D向量、26项BF16均有实际JSON。

独立执行 [audit_actual_json.py](audit_actual_json.py)分别读取两批实际JSON：从**机器字**解码操作、源/目的、宽度、实际舍入模式和mask，从JSON实际初态读源位串，再调用独立SoftFloat计算结果位和五flags，没有读取owner的expected fixture。首批 [305项](exceptions-first-independent.json)与复验 [10项](exceptions-retry-independent.json)全相符，零skip。检查实际FPR boxing、完整目的VR、未激活/尾部保留、vstart和累计flags。

另逐条核JSON自身IR/config来源哈希、实际命令、seed日志fixed17、exit0、单条Retire_Success、完整summary类型/零计数、初后态和保存状态断言；[独立账本](exceptions-evidence-independent.json)列315个不同任务、33566项通过断言。结果与owner [combined-audit](../../validation/exceptions/combined-audit.json)一致，未仅信其PASS布尔值。

首批10个D向量将两个f64 lane拼成128位hex初态，但既有配置解析器将该语法按u64读取，退出1且无JSON；这不是浮点数值不一致。复验脚本从 `6c24b0da…` 到 `43c967d0…` 仅改D向量源配置为已有的128位`0b`位串及相应读取，独立逆替两段文本能精确重建旧脚本SHA。模型/IR/程序/库/seed未改，位模式相同；只对10个受影响任务复验。两批分别保留真实脚本SHA、命令和失败。

已覆盖所列H/S/D加减Inf抵消、左右0×Inf、0/0与Inf/Inf的独立NV原因、有限/±0的DZ及Inf/0等正常对照、负数sqrt与±0/NaN、FMA独立异常源、有限OF/UF/NX五RM、两个ROD宽度的exact/inexact/低位/overflow/tiny/特殊值与普通转换对照、BF16三来源及多lane/mask/fused边界。它们是固定操作数和寄存器域的条件见证，不是全域证明。

未覆盖所有调用入口、全部符号组合、FMA四变体、所有宽化/归约/估算十类、LMUL/SEW/VLEN和任意vl；不以315项推断这些闭合。后续纯assembly修复若改变IR/commit，须说明执行部分逐函数一致性和实际来源适用范围，不能自动将本页改标为新版本测试。三表示GNU宽化文本问题另见[对应审查](representations-make-review.md)及[修复意见](exact-conversion-fix-opinion.md)。
