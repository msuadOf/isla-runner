# Isla可以使用新的fork Z3：隔离验证完成

Linux GitHub Release fork-5292580e5840已下载，SHA256通过，BUILD-INFO指向5292580e58404c43566cd81fd7fcc151974f0ff2。原float isarch依赖libz3.so.4.16；对其独立复制件用patchelf显式替换DT_NEEDED为发布包libz3.so.5.3，未动原二进制/工作树/系统库。不是正式重新编译，正式部署建议重新链接新库。

ldd -r无缺失符号，--version显示Z3 5.3.4.0及5292580e5。新库default和qfaufbv初始化均通过种子能力校验（未提供arch时只报Required option arch missing）。源代码configure_tastic仍要求seed/random_seed，本次未删/跳过该检查。新5.3default已可用，旧4.16结论不能直接外推新库。

同一生产float IR rv64d_v128_e64.ir及riscv64_difftest_fd.toml，T1，显式SMT7200秒：
- 新库default FLEQ_S：退出0，4.08秒，JSON status=finished，gen=10，errors/SMT/execution/model-query timeouts均0，unfinished=0。
- MRET：新库qfaufbv/新库default/旧库qfaufbv均退出0、gen=4，但三者JSON均partial、unfinished=1，不能作为完整Clause验收或新库回归。
- 此前18API/64原断言模型检查属于补丁测试，不冒充本次完整Isla测试。未验证全部77指令、全算术/内存Clause与所有C API。

要消费方案A，必须让Isla链接新libz3并选择--tastic default；只替换PATH中的z3无效，保留默认qfaufbv也不会走A的default分发改动。隔离可运行副本在.tmp/isla-z3-a-smoke/isarch-new-z3，完整命令/二进制/IR/配置哈希及输出在本目录，manifest.json记录方法与版本。正式float/memory分支、子模块和gitlink尚未改动。
