# 维护者方案已接入fork main

2026-11-02，fork main已推送d5aa015a24e266578164157d7b0268c2babf3008，正常merge保留PR11506中原作者及维护者提交历史，没有force/rewrite。正式核心solver/test四文件与当前PR head6ef1c356b86d3ad8e58c889bed49bdb99becbc70完全一致。上游PR当前已MERGED，详见upstream-pr.json。

注意最新方案并非先前“纯保留枚举”的B原型：维护者35e192d4已在qffp preamble中加入dt2bv，放在浮点转换/简化之后、Ackermannization之前。放宽现有is-qffp/is-qffpbv probe，不新增独立probe；原default_tactic保持上游原结构，移除fork此前全局A dt2bv前处理。CI说明与BUILD-INFO strategy已同步，不再标A。

验证：增量构建shell/libz3/test-z3成功，fpa PASS；18个C API检查与64次模型原断言求值全部true。当前Isla debug独立副本更换为本轮新库后，CLI不传--tastic及显式qffp两次FLEQ_S均退出0/status finished/gen10/errors0，无执行/SMT/model-query超时；分别10.94/11.69秒，仅debug smoke，不是与旧A/B的性能对照。actionlint与diff-check通过。合并时测试文件冲突按精确受测PR版本解决，最终四文件tree逐字一致。库在提交前构建，版本字符串仍可能包含旧HEAD，具体源码哈希及manifest为本次验证依据；云端将以正式提交重建。

现有五平台发布CI已保留，最新main push自动触发：https://github.com/msuadOf/z3/actions/runs/41328984261。新版二进制尚待CI成功；旧A Release5292580e5保留历史，不能把旧包当新方案。未修改生产Isla源码在途改动/default与Make配置、系统Z3、IR、float/memory gitlinks或上游PR分支。未全Clause/全workload回归，旧性能表只适用于旧版本。
