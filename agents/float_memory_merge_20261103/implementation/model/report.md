# 模型合流实施与源码区域审计

固定输入：memory `c70482a73be2a67c5a89d88b1e6c2bbea224940c`，float `0f7b8fbc6724103f91f929ef6918f123df75d6c9`。只在隔离候选 `.worktree/merge-float-memory-20261104/sail-riscv/` 解合并；原 memory、float、主工作树未作修改。本文件记录源码和配置实施，严格 IR 生成及动态验证由后续验证负责人记录。

## 源码合同

自动合并保留 memory 的 `get_start_element() -> nat = unsigned(vstart)` 和 vstart 超界非 Illegal 语义，但 float 新增的 SYMBOLIC `VFMERGE` 与 `init_masked_source` 仍将其当作 `result` 匹配。候选仅将这两处改为 `let start_element : nat = get_start_element();`；无新增 trap。合并前索引中两处旧匹配各 1，候选各 0；其余模型生产源码保持自动合并树。float 纯数据回退的五个文件逐字保持 float blob：

| 文件（相对 `sail-riscv/`） | float 与候选 blob |
| --- | --- |
| `model/core/ieee_fp_exceptions.sail` | `1dcfafed536b08af64b4f2a3cf0fded68428080a` |
| `model/extensions/V/vext_fp_utils_insts.sail` | `b3e915800067c012e18eb1077e3e3dbc0c11b31b` |
| `model/extensions/FD/softfloat_symbolic_f16.sail` | `05a5a08c7f7d208dd63b277831f8a7e2ce8b477b` |
| `model/extensions/FD/softfloat_symbolic_f32.sail` | `3ed6aa2dc16b57b46b8c3df46bbd618b8b934dfe` |
| `model/extensions/FD/softfloat_symbolic_f64.sail` | `5437a1900a490ea8623bd1076118529092b93f4a` |

这些 blob 覆盖 33 项异常原因、8 项窄转换和 36 项整数包装数据选择回退；NaN、真实 trap 与 OPEN 没有额外修改。

## 19 份配置的并集

逐来源 occurrence、旧坐标、当前坐标、全部 region 参数与目标 occurrence 见 [region-map.json](region-map.json)，重映射脚本见 [remap.py](remap.py)。19 份配置的 memory 64 项加 float 66 项映为当前 64 项：57 项同位置同预算去重，`vvtype.toml` 七项同位置但预算不同，另两项因 memory 的旧 vstart 陷阱分支删除而退役。全仓 79 份配置合计 130 region、22 注释锚点。

| 配置 | memory / float → 合并 | 决策 |
| --- | --- | --- |
| `masktypei`, `masktypev`, `masktypex`, `mvvcompress`, `mvxmatype`, `vmvrtype`, `vfmerge`, `vfmv` | 各 1/1→1 | 同源区域重映射、去重 |
| `mvvtype` | 7/7→7 | 七处参数一致；四个除法/余数 arm 位置各自保留 |
| `mvxtype`, `nitype` | 各 2/2→2 | 坐标重映射、去重 |
| `nvtype`, `nxtype`, `rivvtype`, `rmvvtype` | 各 3/3→3 | 坐标重映射、去重 |
| `vitype` | 13/13→13 | 坐标重映射、去重 |
| `vexttype` | 4/5→4 | float 旧 `get_start_element` trap 区域退役；`valid_rd_mask` 合并为当前完整表达式 46:2–47:79 |
| `vvtype` | 7/7→7 | 七处 region 同位置，保留 memory 的预算 0；float 为 1，未双计 |
| `vxtype` | 9/10→9 | float 旧 `get_start_element` trap 区域退役；首项是当前 `VX_VSADDU` 逐 lane 区域 |

`vvtype` 七项的预算 0 是 memory 目标已有修正；共同祖先与 float 为 1，float 后续仅迁移这些项的坐标。保留 memory 预算和 `case_quota.Illegal_Instruction = 2`，每项的 `sample_bias`、方向及其它参数按同区间保留。两处旧 get_start 陷阱 region 已无对应源码分支，不迁到别的判断，也不复活陷阱。配置的 `strict=false` 与基准 IR SHA 保持；新 IR 尚未生成，旧哈希只供警告。

## 已执行的限定检查

- 索引自动合并树与候选检查：两处错误 `match get_start_element()` 各由 1 变 0，返回类型仍为 nat。
- `agents/v_symbolic_ir_workarounds/verify.py` 指向候选模型与配置：79 份非严格配置、130 个源码 region、22 注释锚点通过；使用旧 float IR 时 79 份基准哈希均按预期告警。此检查只核坐标有效与锚点文本，不给 IR 或行为 PASS。
- Python `tomllib` 解析全部配置；候选自身修改路径 `git diff --cached --check` 通过。自动合入的 float 历史文件存在既有尾部空行和 patch 内空格，整个 staged diff 的 `--check` 会报告这些继承内容；本轮不改其 blob。
- staged tree `8b991abd601777a07c62504ad457651b9728fab2`，无 unmerged index 项。[Sol 独立源码审查](../../review/model/source-review.md)签收后形成双亲合并提交 `bf861b3e687894480aec701a886a38d4e50b8a99`：第一父 memory `c70482a7`，第二父 float `0f7b8fbc`；候选模型工作树 clean。严格生成与动态验证仍待后续阶段。
- 原 `.worktree/runner-memory/isla/` 的 `README.md` 和 `scripts/run.mk` 仍是原 dirty 状态，SHA-256 分别为 `ac4003d412be230cc1efd2b853495b5ac7fce450924c26359a479a07a449225c`、`683c2b49ffee648ab38a303e2f3db7b7e0b89ea08d3c6d670607d29e11fb318c`，与预检前快照一致。原 memory/float 模型树分别保持 clean 于 `c70482a7`/`0f7b8fbc`。
