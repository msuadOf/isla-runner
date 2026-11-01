# 特殊值控制分支动态验收

本轮对新模型生成的128位VLEN IR验证实际JSON输入、结果与异常标志；不是性能消融，不把定向输入配置当成已经生成的见证，不把JSON条数当路径数。

## 冻结与预算

- 源提交与IR哈希以 `inputs/generation.json` 为准。等待严格生成成功、源不变、实际IR SHA匹配后才复制至 `inputs/model.ir` 开始求解。
- 固定Isla二进制快照与官方Z3版本见 `launch.json`。不重新编译共享target。
- 最多8任务并发，CPU为不同物理core，每任务T1、qffp、完整Clause外限7200秒、单次SMT限时7200秒，不加更短路径限时。
- `summary.json` 和 `report.md` 随每个任务完成更新。自然退出0、summary finished、无错误/超时/截断且逐条实际断言通过才计PASS。

## 任务

- 三格式FLEQ各sNaN/qNaN：32个FPR分两组固定normal和NaN；指令字段保持符号化。实际JSON必须有normal/normal、左NaN/右normal、左normal/右NaN，并核fflags。非x0目的额外核比较结果，x0结果不直接可观察。
- 半精度/双精度sqrt：负1与正1输入，分别核canonical NaN/NV与1.0/无NV。
- VFUNARY0、FVVMTYPE、FVFMTYPE、RFWVVTYPE：固定具体操作及寄存器，vl2、mask1和mask2。normal与sNaN分lane，核活动lane结果、flags及非活动写回。
- BF16 VV/VF两融合边界，各五RM；逐lane调用独立SoftFloat FMA，核结果、flags及FRM保留。额外调用独立MUL与ADD，以结果和两步累计flags的整体差异确认是可区分真正融合的用例。
- BF16 VV/VF每种来源单独sNaN、vl0、mask0/1/2/3：分别核异常来自活动lane；NV与OF|NX在两lane合并为21，分别屏蔽时为16或5；全屏蔽为0。核完整vr8/vr9、其余VR守恒与vstart清零。
- BF16窄/宽转换各mask1/mask2：核normal/sNaN对应实际结果与NV。

## 固定指令的实验包装

针对向量定向任务，测试IR将原 `zexecute` 函数名改为 `zvalidation_original_execute`，函数体逐字不变（包括Jump目标），新增的薄包装只对原符号指令payload字段增加等值 `sail_assume`，然后调用原函数。原编码函数、指令参数、FMA和状态更新均保持，不通过替代返回值绕过执行。具体字段和包装IR哈希记录在任务 `command.json`；原始IR哈希同时保存。包装可执行性在旧IR先验证，旧probe不计为新模型PASS。

## 红测与限制

`old-probe/` 用旧正式IR验证断言parser与包装；FLEQ_H qNaN实际缺右NaN独立组合，红测失败1项。该旧结果只表明旧生成集合没有该输入组合，不能证明该组合不在符号约束域。新模型结果单独记在 `runs/`。

本轮有限定向验收不能证明所有位串、所有指令或全部特殊值控制分支完整。静态CFG与独立Sol源码/IR审查由主任务单独记录。

大型二进制与原/包装IR通过本目录 `.gitignore` 留在本地，不提交；源提交、工具版本、生成命令与IR哈希及测试包装生成器均保留，可据此复建。
