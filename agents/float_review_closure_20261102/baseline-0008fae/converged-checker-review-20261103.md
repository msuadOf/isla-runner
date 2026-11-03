# 最终永久检查器独审

**限定签收；当前未发现需修改的检查器缺口。** 冻结`isla/test/float_ir/check_float_closure_branches.py` SHA256为`9ebd0d937edc805e49103984bffbb507470115d349d7262553b6943b9e2763cf`，[完整冻结字节](converged-checker-9ebd0d937edc805e49103984bffbb507470115d349d7262553b6943b9e2763cf.py)保留供复现。

已读实际条件、返回值和CFG检查：18个异常helper仅保留finite/valid Jump；源分类支配Jump；两返回facts保持同一NV/DZ，非有限不提前产生OF/UF/NX，有限计算受gate控制，同一rounded事实提供三flags。检查器对12类代表位模式逐项验证源分类、原因NV/DZ和gate，不以Jump数量替代返回事实。六窄转换核同一转换值的overflow谓词、NV/原flags、饱和/原低位以及符号端点；仅既有f16→I16保留外层Jump。12整数包装核异常/候选结果及最终invalid/NaN/符号ITE。原changed/Ext_F/FS/SD、round/convert/ROD模式及jam合同继续保留。

独立测试按一次冻结模块运行，避免事后取文件哈希冒充各次测试版本：

- 四最终生成IR，各运行closure和special，两类共8项通过；RV64 closure53目标、RV32为51目标。旧a877及e9均被新checker拒绝。[正控记录](converged-checker-positive-20261103.json)、[脚本](converged-checker-positive-20261103.py)。
- 独立施加104处实际IR负变异，全部拒绝：18异常返回NV清零；三格式DZ清零/quiet分类；FMA积符号、sqrt负零、Inf抵消、AND/OR与gate；六窄overflow自比较及flags/bits/正负端点；12包装invalid最终两臂、NaN/符号端点、inexact代替invalid；changed/SD、rounded/exact/round/fpint、ROD flags及jam。[负控记录](converged-checker-negative-20261103.json)、[脚本](converged-checker-negative-20261103.py)。
- 安装后根Isla五IR另以同一冻结checker核验通过，哈希对应本轮新生成产物。[安装后记录](converged-checker-installed-20261103.json)。

这份审查验证永久静态合同及列定负变异，不保证任意变异均可检出，也不替代动态SoftFloat预期、后态、汇编及完整Clause预算。独立旧新IR值流解释器共276672组比较另见[最终IR签收](converged-ir-review-20261103.md)。
