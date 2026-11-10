# 全量JSON生成计划

输入固定根memory29aa4765、Isla4d085b14、模型bf861b3e。核验五个IR入口及来源，默认RV64与VLEN128同字节只记别名；RV32 solve-state现有入口主动panic，记录不支持，不修改实现来扩范围。默认运行三个可用RV64配置的ALL全集，各347Clause，共1041任务。

从run.mk展开ALL及目标策略，不使用排除浮点/访存的默认make solve。qffp79、qfaufbv268，每Clause一线程，外层Clause/路径/单SMT均7200秒。每任务实际调用未改动的run.mk及solve_process。访存选正式memory配置，浮点访存将正式FD配置与同一完整memory_regions组合，保持原范围；其余继承Make目标配置。

运行资产冻结到独立批次：已审编译产物、五IR及sidecars、脚本、配置、workarounds、官方Z3和seed17。原runner-memory target是共享链接，不覆盖它；批次target/release/isarch指向冻结的已审新程序。ALL按多个独立任务执行，失败/partial/超时分别归档，不把有退出码或有JSON等同全量成功。

批次可从runner-memory/output/full-generation-20261104访问，实体放剩余空间更多的归档文件系统。12个单核worker，日志FIFO实时gzip，进度JSON/Markdown每15秒更新，结束保存每例exit、summary、JSON哈希。低磁盘/低可用内存暂停新任务；STOP文件只停止排队，运行中任务保留预算。工作区及原有输出不清理、不修改生产源码。

## 2026-11-04 用户裁决：收敛v128并提并发

三配置旧批停止；122项v128已完成结果原样保留，只跑剩余225项。采用40worker、每ClauseT2、无taskset、128CPU继承亲和性，不再跑v256/v512。同预算/策略/资产并保留失败状态。入口/收据见status.md及v128-relaunch.json。

## 最新裁决：10并发×每Clause32线程

优雅停止40×T2，保留全部历史结果；仅完整成功作为成功继承，其余终态重试。最终v128共347项，66成功继承，281重跑；10worker、T32、无taskset，各7200秒。新入口见status.md。

## 重启后续跑：4并发×每Clause32线程

按最新用户裁决，旧132项全部落盘成果只读校验并保留（含partial/failed，不改成功状态），10中断+205未执行共215项进入工作区新批次；4worker、T32、无taskset，各7200秒。新主机PID101892，指定Terra每60秒巡检，旧home资产只读。11881是后来一批用例，实际继承总14085（含早先2204）。当前入口见status.md。
