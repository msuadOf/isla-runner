# general、float按序合并状态

2026-10-29完成。`isla/` 当前 `feat/float-support@31506ee3354b70b52dadf6dd1af6708ca4264823`，工作树干净。

1. `2dbad3ba42263ce3572fcd453019b0ee79972b88`：先合general ef882f0，保留两个父提交。
2. `9217e1709a0f49f9a0ae3736bde7811425fc7ca7`：再合float be1296b；解决float.rs/exec.rs冲突并补两runner共4行配置字段。
3. `31506ee3354b70b52dadf6dd1af6708ca4264823`：独立小修，将ret_val用最终Model具化并扩展已有collector测试。

独立GPT-6.1 Sol subagent三轮只读核对：最终无确证P1/P2，顺序/父链与最小改动符合要求。[review记录](review.md)。

验证：测试先RED，Split fixture返回Retire_Success(Sym(1))与同编码模型后态具体值不一致；修复后isla94/94、isarch25/25通过，fmt/diff通过。最终候选make（T1，SOLVE_TIMEOUT45，OUTER_TIMEOUT60s，qfaufbv）MRET4、C_ADDI1、VSETIVLI12、FLEQ_S16、FCVT_S_BF16 63均退出0，所有ret_val无Sym。C_ADDI输出为具体ExecuteAs，不代表递归执行完成或硬件重放。最终实际1015件受跟踪文件与受测候选逐字节一致，tree c315cc1f99d46394a6f29e2a2568f4da8ecf697b。

核心267（跳三项enum）＋集成20，以及1615helper/180state/20guard沿用本轮此前[同核心及runner源码的组合验证](../general_float_review_20261029/report.md)；这些源码在ret_val小修后未改变，未重复跑全组。全77/硬件/整体性能未验收。

原isla24件dirty文件（含原staged/unstaged区分）完整保存在持久stash `8f7b8d043b1cbb2088d3ee21dc806f76bd059cde`，stash文件逐项hash与原快照一致；原index另存本地`.tmp/general-float-merge-20261029/original-index`，原补丁见evidence/before-*.patch。旧dirty大多是已拆分并由新提交修复替代的早期实现，未apply覆盖最终代码；文件内容对照见[evidence/dirty-to-final.json](evidence/dirty-to-final.json)。不删除备份。

源general/float-only分支保持ef882f0/be1296b，父仓gitlink未改，未push。临时review工作树保留未提交候选以追溯；生产分支已是真实有序merge。[精确合并版本](evidence/merge.json)、[测试摘要/返回值](evidence/final-smoke.json)、[小修补丁](evidence/fix.patch)。

## 提交说明与术语修订（2026-10-29）

按用户要求新增根TRANSLATOR.md，根AGENTS.md声明中英文术语对照统一以该文件为准。将原31506ee重做为daa8bb157587df07c7aabe7ef84d3d7225038f77，说明为`fix(solve): 使用最终求解模型具体化返回值`。仅改提交说明，父提交9217e17和tree c315cc1f99d46394a6f29e2a2568f4da8ecf697b完全不变，既有验证仍适用；未重复测试、未push。根术语文档与规则已写入工作区，未夹带提交根仓既有dirty内容。上文31506ee保留为改写前的历史记录。

2026-10-29术语后续：源general已cc7700b、float-only已99a28b0，分别独立统一具体化命名并新增术语规范，目标按序合回75e7440。[状态与验证](../terminology_concretization_20261029/status.md)。

2026-10-29用户澄清后，原两个merge已分别重做为0df2388/42ac15e，ret_val小修重放为b0138b7；当前分支不再含额外术语同步merge，最终代码tree与重整前一致。[现行历史](../terminology_concretization_20261029/status.md)。
