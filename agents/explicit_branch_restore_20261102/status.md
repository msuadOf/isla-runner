# 显式语义分支恢复状态

2026-11-02：完成预算内模型分支恢复、独立GPT-6.1 Sol源码及IR审阅，四配置严格SYMBOLIC完整生成、普通严格检查、五IR24步回归均通过。模型工作树干净，提交`7f3f50d`（FD）＋`fd71c9a`（V）；Isla `f152290`记录五IR/provenance和永久分支回归。根float源码、IR与版本记录已同步，未推送。

NaN、正负零、十分类、mask活动性和非法原因按语义行为控制流审查，普通值的纯数据表达式不机械展开。两个mask循环的CFG已核：活动分支支配运算，非活动分支绕过；两种错误位置反例均被测试拒绝。旧五IR红、新五IR绿。

真实`make solve-FMINM_S`退出0、finished、12条；新JSON三表示GCC/Clang72项字节检查通过。新组合七Clause当前已有5项PASS（minmax, minm, maxm, nan, reduction），其余2项后台运行，不把单项消融预算冒充组合预算通过。实时状态见[组合报告](validation/report.md)。

flags共享函数因算术B未完成暂缓，转换饱和B亦未完成；f16/f64其他NaN出口、其他向量/BF16循环等同构位置不在本轮已测范围。普通严格检查首轮保存memo目录错误退出2，原失败保留，修复driver后重跑退出0，未静默覆盖。

- [计划](plan.md)
- [独立GPT-6.1 Sol审查](review/report.md)
- [模型补丁](implementation/model.patch)
- [源码/工具链协同边界](implementation/collaboration-boundary.md)
- [IR及普通严格生成入口](implementation/generate.py)
- [四配置来源独立审计](review/ir-artifact-audit.json)
- [五IR安装独立审计](review/installed-manifest-audit.json)
- [24步回归](ir-regression/checks.json)
- [版本与逐字同步](versions.json)
