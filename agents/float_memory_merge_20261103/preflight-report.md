# float→memory状态与冲突预检

本阶段已完成状态核对、三仓隔离merge-tree、memory既有dirty叠加预检及GPT-6.1 Sol独审。未在原memory仓执行合并、构建或IR生成，未移动任何输入分支。输入HEAD及记录的dirty补丁/文件哈希在预检前后保持一致，见[前快照](preflight/state-before.json)、[后核验](preflight/state-after.json)。

## 版本与状态

| 仓库 | memory目标 | float输入 | 共同祖先 | 工作区 |
| --- | --- | --- | --- | --- |
| 父仓 | 31ef3b9a | 0665526d | a85d6dfb | float干净；memory仅因Isla子树dirty |
| Isla | bdd047bc | 591693df | 0008fae76 | memory README.md/scripts/run.mk未提交，其余干净 |
| Sail-RISC-V | c70482a7 | 0f7b8fbc | 4f2ac293 | 两侧干净 |

memory两项dirty补丁2888字节，SHA256 `e67728f312f49c5505cd651be547c5514064a5709e78432df865b06dbc93e5d8`，原样保存。其内容为Make具体策略/官方Z3配置，float已有大量同义内容，不能机械重复追加。

## 冲突预检结果

| 层级 | 纯提交冲突路径数 | 主要内容 |
| --- | --- | --- |
| 父仓 | 9 | 两gitlink及README/GIT/结果文档/TODO/topic元数据 |
| Isla | 15 | 六Rust文件、run.mk、五IR、manifest、两文档；叠加既有dirty后新增README至16项 |
| 模型 | 19 | 全部为workaround TOML；三项重叠Sail生产文件无文本冲突，但存在两处自动合并后的类型不兼容 |

Isla六Rust冲突为executor/execution_limits.rs、executor/frame.rs、smt.rs、src/isarch/exec.rs、mod.rs、target.rs。exec.rs有15个冲突块，target.rs有6块。涉及内存事件/初态、最终Model、寄存器与返回值、错误/partial、ExecuteAs和三表示，需要按调用链拼合。纯提交预检[父仓](preflight/root-preflight.json)、[Isla](preflight/isla-preflight.json)、[模型](preflight/model-preflight.json)，dirty叠加[单列结果](preflight/isla-with-dirty-preflight.json)。

自动合并模型中的get_start_element返回nat，float新增SYMBOLIC VFMERGE及init_masked_source仍match Ok/Err：分别见虚拟树vext_fp_insts.sail:2591、vext_utils_insts.sail:429。必须最小适配为接收nat，保持memory超界vstart非trap约定；这是源码合同判断，尚未运行strict验证。19个配置按最终源码重新定位region/锚点，保留两侧预算意图及新增region，不选择整边。

## 合流实施步骤

1. 固定上述SHA及dirty哈希，在隔离候选树开始；原memory两文件保持原样。用候选记录已有配置与float同义合入的对应关系。只合固定分支，不导入其他研发树。
2. 合Sail-RISC-V，适配两处nat调用，处理19配置冲突；保留NaN/真实trap、77纯数据回退及OPEN现状。Sol审实际源码与区域映射。
3. 合Isla生产源码，按最终Model统一内存事件与浮点见证，保留枚举重放、ExecuteAs和三表示；Make兼容memory SOLVE_CONFIG与float ISA_CONFIG覆盖、官方Z3及策略和trace feature。无文本冲突的接口文件同样检查。先相关回归锁合同，再最小解冲突。
4. 从合并模型重新ordinary strict与四配置SYMBOLIC生成，替换五IR及全部来源sidecar，不文本合IR。核指定官方Z3构建/watchdog、源/工具/配置/IR哈希及workaround全region/锚点。大型产物使用有余量的文件系统。
5. 新版本跑Rust相关、永久IR回归、浮点定向数值/异常、内存见证与原有partial分账、ExecuteAs、GCC/Clang三表示及真实make浮点/访存/压缩入口；单Clause/单SMT各7200秒。Sol分阶段独立签收，不继承float旧PASS。
6. 子模块合并结果验收后，父memory合float：两gitlink填组件合并提交，topic保持memory，重写组合版本、IR哈希、排除清单及本轮验证状态，保留两侧历史结果；核原工作区dirty未变并按其对应关系保护，再更新目标。

旧F1–F5 memory修复证据不对应当前目标四个Rust源码哈希，不能视为目标已含，也不自动取其他dirty树。当前固定memory既有缺陷及float旧全77超时分别作为基线边界；不因合流引入新开发。任何合流新失败仍必须定位。通用ITE配置、OPEN策略研究及路径线性化均不在此次范围。

独立结论见[Sol审查](review/report.md)。可以继续隔离候选实施；不能把有冲突的虚拟合并当可编译、语义通过或整个合流完成。
