# FVFTYPE caller 纯 Bool 组件验证

本工具只验证已批准的 SYMBOLIC FVFTYPE 两处表达式。实施证据在 `isla/target/float-solve-evidence/fvftype-caller-pure-20260927/`；输入读取该目录的 `baseline/` 和 `candidate/model/` 完整冻结源码，不把当前活动 Sail 文件作为历史输入。

实现边界：overlap 使用既有 `strict_and_bool` 与 `eq_anything`，四个拒绝因子使用三个 `strict_or_bool`。最终 Illegal/正常分支、getters、get_num_elem、assert、shape、普通 clause、其它 caller 和全局 valid_reg_group 保留原字节；整文件总行数不变。

## 复跑

在仓库根目录，给准备步骤一个尚不存在的新输出目录，例如证据目录下 `recheck/`：

```sh
python3 agents/float_support_review/tools/fvftype_caller_pure/check_source.py
python3 agents/float_support_review/tools/fvftype_caller_pure/prepare.py isla/target/float-solve-evidence/fvftype-caller-pure-20260927/recheck
python3 agents/float_support_review/tools/fvftype_caller_pure/run.py isla/target/float-solve-evidence/fvftype-caller-pure-20260927/recheck
python3 agents/float_support_review/tools/fvftype_caller_pure/check_ir.py isla/target/float-solve-evidence/fvftype-caller-pure-20260927/recheck/caller.ir --report isla/target/float-solve-evidence/fvftype-caller-pure-20260927/recheck/structure.json
python3 agents/float_support_review/tools/fvftype_caller_pure/run.py isla/target/float-solve-evidence/fvftype-caller-pure-20260927/recheck --phase proof
python3 agents/float_support_review/tools/fvftype_caller_pure/cpp_check.py isla/target/float-solve-evidence/fvftype-caller-pure-20260927/recheck
```

冻结包中的 `tools/` 副本可以替换上述工具目录；各脚本从祖先的 `specs/GOAL.md` 定位仓库。工具链与 Isla 依赖取已冻结的旧 V4 工具链和 sharedtrace stage，逐项绑定见证据 manifest；不会写它们的目录。Rust 单独构建到新输出目录，固定 Z3 链接参数见 `run.py`。

## 验证口径

- 复用 `sail-riscv/test/solve_fp_legality/` 的精确函数抽取与 runner 配置。helper 体来自冻结生产文件；正除/模声明来自冻结 RISC-V prelude，保持 `valid_reg_group` 原函数体。
- 枚举完整 7 个 LMUL、4 个 SEW、13 个 fvffunct6，共 364 个形状。每个形状的 vtype64、vs2/vd5、vm1、RM3 为独立未知输入。旧新每条正常路径先 SAT，再证明 overlap、完整拒绝 Bool 和 vtype 差异 UNSAT。
- 单独执行新体，每形状必须一条 SAT 路径，无 Fork、无非平凡 Assert、无未解释函数；检查五个独立输入的宽度与身份，再与独立位串公式比对。这也覆盖原先被短路的寄存器组函数在本 caller 域上额外求值的 total 性。
- 280 个具体边界各执行旧、新一次：非法 RM 5/6/7、mask-v0、vill、vs2/vd 组、slide 重叠和普通合法侧。正常侧 SEW=8 保留断言失败；共 560 项 Isla 结果/异常检查。其余 258 个非断言边界在生成 C++ 中各执行旧、新一次，共 516 项，核 vtype 和异常标志。
- 小 IR 旧 guard 4 个 Jump，新 guard 0；旧 boundary 5 个 Jump，新 boundary 保留 1 个最终分支。原 `valid_reg_group` 内部 1 个、`assert_lmul_pow` 7 个、`assert_sew` 4 个 Jump 保留。

该 fixture 在 typed guard 入口注入完整参数；固定 VLEN=256 仅为执行原 get_num_elem 前置断言。getters 的原位置、未改 shape/异常代码及剩余模型由完整字节边界核对保留。boundary 用 Bool 标记 Illegal/正常并保留 SEW=8 断言，不替代完整指令执行、全 IR 严格配置迁移、双后端指令重放或性能对照。
