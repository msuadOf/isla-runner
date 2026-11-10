# 采用维护者建议的Z3方案

用户要求采用维护者方案。核对PR11506当前修订，使用其扩展现有is-qffp/is-qffpbv probe的实现，移除fork main的A dt2bv前处理，保留五平台预编译发布CI。仅修改独立Z3 fork，不改Isla在途源码/default与Make策略/IR/模型/gitlinks，不覆盖正式isarch。

步骤：读取远端head；将B最终修订的四个solver/test文件落到main工作区（默认分发恢复原结构），更新CI说明/provenance为新策略，检查diff；增量构建/fpa、共享库API及当前Isla隔离副本FLEQ无--tastic和qffp smoke。原慢query可用于查询级验证，但不将旧B原型性能当新修订结果。通过后commit并推送fork main，触发既有CI；上游PR11506保持不变，初次新版Release需等待云端，既有A包保留可追溯。
