# Z3 default浮点/枚举源码修复（2026-11-01）

## 已实现的行为

独立源码检出位于 `.tmp/z3-enum-fp-default`，分支 `fix/default-fp-enum-11500`，基线为上游master `8fbb275aba0472e862e289c7af1331b3bd5d512c`。此检出构建产物自报Z3 5.3.4，明确不同于先前系统安装的Z3 4.16.0；同版本修复前后二进制已保留，性能结论只在该基线内部比较。

修复只改default的策略选择：现有纯FP分支之后，增加严格的FP＋有限枚举识别分支，满足时调用Z3已有 `dt2bv → qffp`。普通整数/BV/数组/纯FP原分发不改。保留现有公开is-qffp的严格含义，新增内部识别器重用原谓词，额外接受简单枚举常量/构造器；必须同时实际出现FP和枚举，不因未使用的sort声明触发。无量词、无数组、不接受一般ADT或枚举函数/枚举ITE；proof与unsat-core模式保留原路径。

这不是对datatype求解语义做近似，也没有改变Sail/IR、操作数域或折叠分支。dt2bv使用原有限域约束和模型转换。代码修改4文件，约134行新增（主要是测试），未提交/推送或创建PR。

## TDD与结果

先仅补测试并构建未修master。`test-z3 fpa`在2,000,000资源预算下得到unknown，断言失败、退出114，见[红例](red-test.json)。该预算是Z3资源计数，不是毫秒时间上限；同测试在修复后返回SAT。

修复后构建z3、test-z3、libz3均成功。最终验证如下：

- `test-z3 fpa` PASS：包含新增八个识别边界、有限枚举混合FP的固定资源回归、枚举模型回读、枚举合法域UNSAT、浮点UNSAT及该文件原有浮点/数组/datatype等测试。
- `test-z3 check_assumptions`、`bit_vector`、`get_consequences`、`model_evaluator`均PASS。
- 使用修复后的裸default（不在命令里手动组合dt2bv）：25个实际超时dump全部SAT；另10个数组/BV/枚举/混合FP/record探针符合SAT/UNSAT预期，含原始类型模型输出。
- 两个真实query通过C API `default` solver，路径断言、check_assumptions、push/pop及条件正反两侧都SAT；每次model_eval的分支条件与原路径约束均true。
- 上述35项外加最小例修复前/后三次各一组，共41次验证命令全部得到预期结果。真实dump与合成probe明确分列；这不是全指令/全内存域验收。

本轮最小例墙钟：同源码未修版本三次2.715、5.014、4.913秒；修复版0.210、0.418、0.415秒。25个实际dump在修复版：NaN13项0.208–0.309秒，flags12项1.912–9.218秒。是独立query进程耗时，不能相加或外推完整Clause两小时完成性。

C API同一solver两侧：NaN约0.088/0.077秒，flags约8.259/12.269秒。命令和输出见api-nan/api-flags文件，原始完整断言在对应输入中；不把此结果说成完整执行器深度增量历史重放。

## 复现与交付

```sh
cmake -S .tmp/z3-enum-fp-default -B .tmp/z3-enum-fp-default/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DZ3_ENABLE_EXAMPLE_TARGETS=OFF -DZ3_BUILD_PYTHON_BINDINGS=OFF
cmake --build .tmp/z3-enum-fp-default/build --target z3 test-z3 libz3 -j 24
.tmp/z3-enum-fp-default/build/test-z3 fpa
.tmp/z3-enum-fp-default/build/z3 \
  agents/branch_ablation_20261031/z3-upstream-assessment/enum-default/query.smt2
```

运行query批次入口为[validate.py](validate.py)，该脚本拒绝覆盖既有验证输出目录；重跑应使用新输出目录。C API脚本使用系统`/usr/bin/python3`，避免当前conda运行时自带旧libstdc++与新编译库冲突。早期conda加载失败及后续系统Python成功记录均保留；最终核账见[final-regression-index.json](final-regression-index.json)，不使用旧的失败汇总作为最终通过证据。

- [可应用补丁](default-fp-enum.patch)
- [来源、构建命令和哈希](manifest.json)
- [41项原始结果](validation/results.json)
- [最终回归与API索引](final-regression-index.json)
- [首次修复后的浮点组结果](green-test.json)

系统Z3未替换，生产Isla/Sail/float/memory未修改；官方issue11500未新增评论或PR。该补丁解决已复现的混合类型策略选择问题，尚未证明所有工作区Clause均能在7200秒内完成。接入Isla default时仍须单独处理其顶层seed参数描述检查，不能把本Z3补丁说成已完成Isla策略接入。

## 独立审查后的修订

两位独立reviewer发现大枚举转换的性能P2及域测试不足，现增加4096枚举模型成本护栏、增强自由枚举域UNSAT与低预算回归。初版结果只适用于initial-manifest.json；当前代码/补丁哈希以manifest.json及guarded-snapshot.json为准。修订后fpa组和41query再次通过；最终独审意见见[independent-review/summary.md](independent-review/summary.md)。

## 当前策略：按用户要求恢复无4096护栏版本

已移除成本计数/阈值与对应护栏策略测试，保留类型限制和增强枚举域正确性测试。五组测试通过；护栏版独审报告仍按原snapshot保存，大枚举性能开销现按用户选择保留，不声称所有输入只提速。[恢复记录与实际对比](restored-no-cost-limit/report.md)。
