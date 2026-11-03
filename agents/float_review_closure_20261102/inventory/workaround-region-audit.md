# 模型 6202e23 → 8ad5e8e 的 workaround 源码区域核查

结论：**本轮无需改任何 region 坐标、注释锚点或 workaround 配置。** 六个修改文件均不在 132 个 region 或 22 处锚点引用的源码文件集合内；被引用的 16 个模型文件在两提交间逐字相同。新生成 IR 的哈希仍须按最终产物登记，但本项目约定不因 IR 哈希单独变化而重写 strict=false workaround 的基准哈希。

## 精确交集

git diff --name-only 6202e23 8ad5e8e 只有：

- model/core/ieee_fp_exceptions.sail
- model/extensions/FD/fdext_regs.sail
- model/extensions/FD/softfloat_symbolic_f16.sail
- model/extensions/FD/softfloat_symbolic_f32.sail
- model/extensions/FD/softfloat_symbolic_f64.sail
- model/extensions/V/vext_fp_utils_insts.sail

现行 79 份 configs/isla/workarounds/*.toml 共引用 16 个模型文件的 132 个 region，注释锚点只引用 model/extensions/V/vext_arith_insts.sail（18）和 model/extensions/V/vext_utils_insts.sail（4）。六个修改文件与全部引用文件的交集为空；configs/isla/workarounds/ 本身在两提交间也无 diff。对 16 个被引用文件逐一以 git show <commit>:<path> 比较，6202e23 与 8ad5e8e 的字节全部相同。

其中唯一引用浮点指令文件 model/extensions/V/vext_fp_insts.sail 的两处 region 是：

| 配置 | region 下标 | 源码区间 | 本轮影响 |
| --- | ---: | --- | --- |
| vfmerge.toml | 0 | 2656:2–2668:3 | 文件逐字未变；VFMERGE 不在本轮 64 条改动调用闭包内。 |
| vfmv.toml | 0 | 2746:2–2748:3 | 文件逐字未变；VFMV 不在本轮 64 条改动调用闭包内。 |

本轮 64 条受影响 Clause 与当前 isla/scripts/run.mk 中逐目标 EXECUTION_LIMITS_CONFIG 赋值的交集为 **0**。因此不能说“79 份配置都适用于本轮浮点 Clause”；它们仍需作为全仓配置验证，但没有哪一份因这六个文件的行移动需要迁移。新增 helper 控制流位于当前配置 region 之外，性能预算须由完整 Clause 实测，不能靠扩 region 隐藏新分支。

## 只读验证

直接运行 verify.py 会默认读取原根 dirty sail-riscv，故本次在只读 Python 进程中覆盖其 CONFIGS，并把 --model 与 --ir 指到 runner-float。命令如下，未修改脚本或配置：

~~~sh
python3 - <<'PY'
from pathlib import Path
import importlib.util, sys
p = Path('agents/v_symbolic_ir_workarounds/verify.py').resolve()
spec = importlib.util.spec_from_file_location('workaround_verify', p)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.CONFIGS = Path('.worktree/runner-float/sail-riscv/configs/isla/workarounds').resolve()
sys.argv = [str(p), '--model', str(Path('.worktree/runner-float/sail-riscv/model').resolve()),
            '--ir', str(Path('.worktree/runner-float/isla/rv64d.ir').resolve())]
module.main()
PY
~~~

结果：通过 79 份非严格配置、132 个源码 region、22 处注释锚点；对当前现成 rv64d.ir SHA-256 a877e245cda62b8430b13541faf05a3a2f47719dddad283dd336fa45e068f97e，79 份配置均提示基准 IR 哈希不同。这个 warning 不表示 region 失效；脚本本身只检查坐标合法和锚点文本，不验证新 IR 的运行时 region 命中。六文件与 region 引用集合完全不交是本次“不迁移坐标”的独立依据。

## 后续建议

保持这 79 份配置原样。最终五 IR 安装后，记录 IR SHA、正常运行 verify.py 的 runner-float 参数和 79/132/22 结果；若新 IR 的源文件/源码位置映射发生非预期变化，再按实际 SourceRegion::selects_ir_location 复核命中，不预先移动坐标。受影响 64 条 Clause 的完整预算清单见 [affected-clauses.json](affected-clauses.json) 与 [validation_plan.md](validation_plan.md)。

## 追加：`8ad5e8e` → `21418d0` 精确转换汇编映射

本次只修改 `model/extensions/FD/dext_insts.sail` 与 `model/extensions/FD/zfh_insts.sail`。重新解析 runner-float 的79份配置，仍为132个region、22处锚点，所引用的16个模型文件中没有这两个FD文件；逐文件 `git show` 比较，16个引用文件在 `8ad5e8e` 与 `21418d0` 间逐字相同，配置目录自身也无diff。故这次新增行号移动同样无需更新任何region坐标或注释锚点，不能沿用前节“只改六文件”的描述来代表这次新提交。

本次再次把 `verify.py` 的 `CONFIGS` 限定为 runner-float 配置目录，`--model` 指向 runner-float 模型；结果仍为79份非严格配置、132 region、22锚点通过。运行时所用现成 `rv64d.ir` 仍是旧 SHA-256 `a877e245cda62b8430b13541faf05a3a2f47719dddad283dd336fa45e068f97e`，79个基准哈希warning只说明旧IR与配置基准哈希不同，**不构成新 `21418d0` IR 的运行时命中检查**。新五IR冻结后仍须按最终版重验哈希/region实际命中。

同版静态调用闭包已重生为模型 `21418d0b0d4942fae20061ed580ee04aff4a8a61`、Isla `42000be47596ec088623881d03c0eadc5cf0ba27`：[机读清单](affected-clauses.json) SHA-256 `409edef342a13a28d2d4b817609570a249d070b5379765eb498f4f0ffd241d3b`。受影响仍64条，相对8ad5e8e没有新增/删除Clause；这是源码调用闭包核查，不代替新IR生成和动态预算。
