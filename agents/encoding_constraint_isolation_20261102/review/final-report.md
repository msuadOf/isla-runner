# 编码约束隔离与饱和分支：最终独审

结论：**源码、四配置IR及约定正式验收全部通过，无阻断。** 独立审查未修改生产源码；初版与修订版证据分开保存。

## 受审版本与等价性

最终 Isla `cf1aa1431d5f2d05584c78c0e7c84862a9a9b1fa`，冻结 Release SHA256 `abce451a11e0e4a8a3c9658d4a8462634f284085f219cca79f439ca176853a1a`；官方 Z3 `1fd1d3613`，实际库 `899cbc70…9970`。Sail-RISC-V `6202e23`，V128 IR `a877e245…f97e`。精确来源见 [最终源码清单](selective-source-manifest.json)及[安装IR清单](installed-ir-checks.json)。

辅助编码保留全部声明、定义和事件，只保留由指令字段及常量得到的原Assert子集；最终仍合并完整原执行checkpoint与每条候选增量。完整原域是辅助域的子集，normal优先、compressed正常拒绝域、全部可达候选与异常/UNKNOWN/error传播保持。符号编号、枚举、trace和初态/后态/返回值/编码同模型关系已核。见 [修订源码审查](selective-source.md)。

模型只恢复活动lane内f16→i16的overflow显式分支，数值和flags逐点等价。四配置生成的166个源文件哈希与Git提交逐项一致，规范化仅目标helper变化；实际CFG、20个活动gate、五处安装及25步IR回归核实。见 [模型源码](model-source.md)和[IR审查](ir-review.md)。

## 最终正式结果

|验收|最终结果|
|---|---|
|新模型完整VFUNARY0|22.33秒，46 JSON，22退休/24非法|
|新生产IR完整flags|1127.51秒，728 JSON，680退休/48非法|
|冻结旧显式B完整flags|2626.07秒，328 JSON，280退休/48非法|
|特殊值/活动lane定向|56项，156 JSON，3518语义检查及9272个初态值独立复核|
|三表示及正式Make|126项实际工具链字节检查；Make3.19秒、8 JSON/15语义检查|
|官方Z3下Rust定向|15/15独立重跑通过，实际动态库装载已确认|

三条完整Clause均自然退出0、finished、无错误/采样/partial，进程和SMT预算均7200秒。两条flags的960条退休见证及96条非法见证均独立做实际数值、boxing、flags与寄存器保持检查，共41088项通过。新饱和另有精确有理数及字段/状态662项检查。两版四组产物的1258条五字段具体见证多重集合完全一致。详见 [最终动态审查](selective-dynamic-review.md)、[数值检查](selective-flags-json-checks.json)及[集合比较](semantic-comparison-checks.json)。

保留三个边界：时间为记录配置下单次运行，不宣称稳定提速比例；已生成集合相同不等于全部具体值/编码或全模型覆盖；额外enum同Context重放测试仍单列失败，不计入15项通过，官方库未跑旧基线。旧 eager-lane sat B 的初版诊断最终在7200.20秒外限退出124（TIMEOUT），无完整JSON，不计PASS；它不改变修订版三条正式Clause的已签收结果。终态元数据见 [诊断核对](old-sat-diagnostic-terminal.json)。
