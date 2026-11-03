# 显式分支恢复独立语义审查

当前结论：五文件源码与四配置新 IR 的独立审查均通过，安装后的五份 IR 与 manifest 同源、哈希一致。永久回归的旧五 IR 红测、新五 IR 绿测及真实 mask CFG 核对通过。组合七 Clause 尚在运行，由验证 agent 另行报告；本审查不声称所有浮点特殊情况已恢复。

本审查只写本目录，不修改生产源码，不启动子代理。审阅基线为 float 模型 `9c339044b07e235fe48d5bc585cbd3975ceeba5a`；根 Isla 与 runner-float Isla 均基于 `80231ce9` 并有既有未提交修改。根 `sail-riscv` 的用户内容未触及。

## 审查边界与证据

- 实际审阅对象：[实施补丁](../implementation/model.patch)，SHA-256 `b58119f9d277056f1384368cd0bf630b1acaa35e2d3a2a99a078d404e5a857c9`。五份实际源码哈希见 [source-evidence.json](source-evidence.json)。本次审查不是只读旧 B 变体。
- 单变量来源：`agents/branch_ablation_20261031/` 的 `minmax/source.diff`、`minmax/C`、`mask_reduction/{mask,reduction}/source.diff`、`guards/B_{valid,normal,reduction}/source.diff`、`classification/{nan_f32_if,class_if}/source.diff`；这些实验各只恢复一个局部行为选择。
- 官方 Z3 受测输入与差异函数来自 `agents/branch_ablation_official_z3_20261102/input-verification.json`，2053 函数、preamble 相同，按源码位置与形参 alpha 规范化后只变预期函数。此项不等于本次组合新 IR 已验。
- 预算快照为 `live-summary.json` 的 `2026-11-01T19:36:23.784040+00:00`。策略 qffp、单线程、种子 17/29/43、同核 AB/BA/AB、进程与 SMT 都 7200 秒。class 已六臂自然完成；flags-arithmetic 和 sat 仍未齐。

## 逐项语义分类

| 项目 | 语义性质 | 本次决策与预算证据 |
| --- | --- | --- |
| min/max 双 NaN、单 NaN | 特殊值决定返回 canonical NaN 或另一操作数，是行为选择 | 恢复；minmax B 三次 57.48–60.72 秒 |
| min/max 异号零 | ±0 数值比较相等，但结果符号取舍不同，是行为选择 | 恢复，与原分支优先级相同 |
| min/max 普通有限数大小 | 同一普通运算的结果数据选择；不要求为所有 SMT ITE 机械建路径 | 本补丁沿实验 B 保留显式 if，未认定所有普通比较均须如此 |
| minm/maxm 任一 NaN | NaN 传播方式不同，是行为选择 | 恢复；minm B 9.63–20.12 秒，maxm B 9.64–15.37 秒 |
| FVVTYPE 活动/不活动 lane | 决定执行运算、flags 贡献与目的寄存器更新，是控制流 | 恢复；mask B 28.46–54.85 秒 |
| RFVVTYPE 活动/不活动 lane | 决定是否进入当前累加步骤，是控制流；浮点加法顺序不能重排 | 恢复；reduction B 9.63–14.43 秒 |
| f32 结果 NaN 规范化 | NaN 返回规范值，其他值返回 IEEE 位表示，是特殊行为 | 恢复；nan B 92.05–187.92 秒。非 NaN 的零/无穷/有限数共用位表示出口，无须仅为编码再添无行为差别的分支 |
| valid_fp_op 的 SEW、RM | 不同非法原因须分别可探索，是合法性控制 | 恢复；guard-valid B 22.64–36.18 秒 |
| illegal_fp_normal 的 vill、vd/mask、FP 合法性 | 不同拒绝原因的控制 | 恢复；窄域 B 26.84–42.07 秒，宽域 B 525.34–826.43 秒 |
| illegal_fp_reduction 的 vill、vstart、FP 合法性 | 不同拒绝原因的控制 | 恢复；B 11.12–15.85 秒 |
| fp_class_onehot_pure 十分类 | sNaN/qNaN、±无穷、±零、±次正规、±普通数的语义分类 | 恢复；class B 1325.32/1444.04/1645.57 秒，六臂均 finished、非 partial |
| accrue_fflags 的 changed | 决定更新 FS/SD 的异常状态行为 | flags-compare B 已完成，但共用算术 B 未完成；本次暂缓，不能用比较 Clause 成功代替算术预算 |
| 窄整数转换 overflow/limit | 饱和界与 NV 替换均为特殊行为 | sat B 尚未完成，暂缓；原 B 只拆 overflow，不足以单独保证正/负饱和边界分别见证 |
| IEEE 纯 predicate、普通字段拼装、舍入算术内部 ITE | 须按其是否选择特殊行为具体判断 | 不把 strict Bool 或 ITE 语法本身一律判成控制。对纯 predicate 可保留 strict 组合，在使用 predicate 选择行为的位置恢复 if |

## 实际 diff 的等价性与行为核对

1. `fp_min_pure`/`fp_max_pure`：顺序仍为双 NaN → 左 NaN → 右 NaN → 两种异号零 → less-than。min 取 −0、max 取 +0；双 NaN 仍 canonical；单 NaN 仍返回另一操作数。比较和 flags 在结果链之前计算，未因短路漏算 flags。宽度仍由 `'m in {16,32,64}` 约束，没有改变位宽、符号扩展或 canonical 常量。
2. `fp_minm_pure`/`fp_maxm_pure`：仍先运行 min/max 取得 flags，再根据任一 NaN 改结果。不能把调用移进非 NaN 分支，否则 sNaN 的 NV 可能漏算。当前实现没有此问题。
3. FVVTYPE：初始结果仍来自 `init_masked_result`，含 prestart/tail/掩码及 agnostic 的既有处理；活动 lane 才求值纯运算、写结果并 OR flags。不活动 lane 保留 initial_result；无候选值的求值作用泄漏到体系状态。统一 helper 均不在内部 accrue flags，原与新都在循环后统一一次 accrue。
4. RFVVTYPE：sum 初值仍是 vs1 第零元素；按 lane 递增，活动时算 candidate 并更新 sum/flags，不活动时两者不变。未引入结合重排；vl=0 的提前退出、写 vd 第零元素、其他 tail 保持与 vstart 清零均保留。
5. 三个 guard：`valid_fp_op` 等价于 `8<=SEW<=64 && rm not in {5,6,7}`，保留 SEW=8 转换合法域；standard helper 继续排除普通算术 SEW=8。`valid_vtype` 与 `valid_rd_mask` 仅读取状态和比较；改为短路不会跳过 CSR 写入或回调。normal/reduction 的拒绝优先序清楚，未改变最终合法集合。
6. `riscv_f32_symbolic_bits`：测试的仍是 native `fp32_is_nan(value)`；NaN 常量仍 0x7fc00000。非 NaN 才进行 `fp32_to_ieee`，与原纯数据选择的位值语义相同。这个出口区分 NaN/非 NaN，不独立证明输入的 sNaN/qNaN 或左右源组合见证齐全。
7. `fp_class_onehot_pure`：quiet bit 仍取 f16 bit9、f32 bit22、f64 bit51，NaN 优先于符号。正数链最后只能落 +0；负数链最后只能落 −Inf，因为前面已排除 NaN/zero/subnormal/normal。十个常量的 bit9..bit0 顺序与原 concat 相同。

本审查以 IEEE 指数字段/尾数字段的独立分类 oracle，穷举全部 65,536 个 f16 位模式，并对 f32/f64 各取 40 个字段边界模式，十类输出一致；同时枚举 640 组 SEW/RM/vill/mask/vstart 的布尔关系。结果记于 `source-evidence.json`。这是静态审阅辅助核算，不是执行 Sail/IR 的功能测试。生产 `git diff --check` 通过。

## Sail 编译器、普通模式与 Isla 协同

- 生产模型的 native FP 操作声明在 `model/prelude/ieee_fp_primops.sail`。`ite`/strict Bool 在普通执行中有 Sail body，而 c extern 供 Isla 使用；符号模式的 strict/ITE primop 只生成 SMT 表达式，不生成分支。
- Isla `isla-sail/sail_plugin_isla.ml` 设置 `eager_control_flow=false`；受用 Sail snapshot 的 `src/lib/jib_compile.ml` 对 `AE_if` 只有 `C.eager_control_flow` 打开才走 eager ITE，否则生成 `iif`。所以本次应改 RISC-V wrapper 的行为边界，无须为原生 `fp_is_nan` 谓词改编译器语义。仍须对产物核真实 Jump，不能仅凭 Sail 的 if 字样签收 IR。
- 既有专用 Sail 工具链为 `isla/target/float-solve-evidence/unified-backend-build/toolchain-a198-v2-20260927/sail-src`；当前环境 PATH 中 `sail` 则为 opam 安装版。重生必须明确选择前者及记录二进制/插件哈希，不能用裸命令名推断版本相同。
- `fp_minmax.sail` 与三个合法性 helper 是普通/符号共用代码；循环、class helper 与 `softfloat_symbolic_f32` 属符号实现。普通模式原循环与状态行为保留，但共用 helper 已变，所以普通严格检查仍必须做。
- Isla `isla-lib/src/primop.rs` 注册 `strict_and_bool`、`strict_or_bool`、`isla_bool_to_bit` 与 `ite`；`primop_util::ite` 对符号 bool 建 `Exp::Ite`。本轮无须撤销这些通用接口，撤销接口会误伤其余纯数据使用者。

## 保留项与限制

这些是范围限制，不是证明本次补丁算错，也不是已授权把全模型一次性回退：

- f16/f64 算术出口、f32 宽化/窄化/BF16 出口、转换 invalid 结果仍有 NaN ITE；本次只恢复 `riscv_f32_symbolic_bits` 的十一处调用。语义同属特殊值选择，须列后续预算与验证，不能称所有 NaN 分支已恢复。
- FVVTYPE/RFVVTYPE 之外的宽化、FVF、比较、转换、BF16 等循环仍有 mask ITE/vector_select。不能把两个 Clause 的小域实验外推为所有格式/LMUL/VLEN 的可完成性。
- `valid_fp_standard_op`、`valid_rd_mask` 等仍有 strict 组合。`illegal_fp_normal` 的 if 已在整体拒绝条件处分叉，但 masked vd0 与 unmasked vd0 等内部等值子情况未保证逐一见证。合法集合等价与每个原因的覆盖是两个结论。
- sNaN/qNaN 对 NV 的不同影响仍在 IEEE exceptions 的纯 Bool/bit packing 里；min/max 的 NaN 结果 if 只分 NaN 值种类，不自动拆开两个源各自的 signaling 分类。不能宣称此次补丁闭合 sNaN/qNaN 与所有异常 flags 组合。
- 新组合模型可能因每个新增分支相乘而超过旧单项预算，必须实测；本次既有单项数据仅支持恢复候选的选取。

## 产物复审与最终 IR 签收

四配置严格 SYMBOLIC 生成和普通严格检查已经完成，全部退出 0。模型固定于 `fd71c9ab58fe6f41b97c976a5f7e470318c708a8`（FD 提交 `7f3f50dc`、V 提交 `fd71c9ab`），工作树干净，五份已审源码字节未变。四份生成记录和普通检查使用同一组 166 件模型文件；配置、Sail launcher、真实 Sail 二进制和插件哈希全部核实。[提交及工具核对](commit-toolchain-checks.json)、[独立产物审计](ir-artifact-audit.json)。

| 生成配置 | IR SHA-256 |
| --- | --- |
| RV64/V128（同时安装为 rv64d.ir 与 v128 文件） | `0e7a9bfd9bb0655e48fbb02097c31a83f97b59d0eb3fbbf4b048c606eee7a85f` |
| RV32 | `65a11d9900d695500f85cf64a1ddc032ff85eb39aa6e94fa0bb9cdfdabfbb520` |
| RV64/V256 | `946d28643cf4566fb64ef41212ddef757d62a8b592207756572252865a740bb6` |
| RV64/V512 | `03ba34ebb2b7cd2782f68a9754fee1cd464ca17ce3487f3f529b96390e6637d6` |

四份 IR 的 files 表中，实际分类库路径均来自既有 Sail snapshot；逐一核实表内 15 件实际标准库文件存在并记录内容哈希。额外核对 opam 安装位置的 `float/interface.sail` 和 `float/classify.sail`，与 snapshot 对应文件分别字节相同。不能仅凭 wrapper 的 SAIL_DIR 变量推断 include 来源；本结论依据本轮新 IR 文件表。真实二进制哈希为 `373a37c2…b23d45a`，插件为 `c4eccb06…f0e22f6`。Sail snapshot 无独立 `.git`，版本字符串不充当完整源码树提交证明。

v128 旧新各 2053 函数。规范化源码位置、形参和局部编号后，恰有 `zexecute`、min/max 四函数、f32 结果出口、三个合法性 helper 和 class 共十目标函数改变；未见意外函数漂移。[差异清单](v128-normalized-diff.json)。四配置 helper Jump 均为 min/max 8、minm/maxm 1、f32 1、三 guard 各 3、class 17；旧 class 的 8 个位宽/类型检查没有冒充本次分类恢复。

按主 agent 授权，已修复永久测试 `isla/test/float_ir/check_explicit_semantic_branches.py` 的审查问题：原先仅以 zexecute 总 Jump +2 判定 mask 恢复，无法确认新增 Jump 的语义。测试现在按源码文件表和 if 区间识别 FVVTYPE/RFVVTYPE 的 mask Jump，沿定义使用关系确认条件来自活动位与 1 比较；再解析 numeric PC 控制流，确认真分支可到达全部六/四处纯运算、假分支在合流前绕过运算，并验证从函数入口避开该 mask Jump 无法到达这些运算。没有改动其他生产源码。

实际 v128 CFG：FVVTYPE 的 mask Jump 为 PC24232，真出口24235、非活动出口跳24538；RFVVTYPE 的 mask Jump 为 PC37612，真出口37615、非活动出口跳37661。其余配置逐一得到同样支配与绕过关系，详见 `ir-artifact-audit.json` 中各 `mask_cfg`。这里核的是运算求值受 mask 控制，覆盖强于仅检查条件结果写回。

永久测试改前旧五 IR 均按预期失败；改后新五 IR 均通过。[旧五 IR 红测](permanent-old-five-red.json)、[新五 IR 绿测](permanent-new-five-green.log)。另以旧单 mask B 确认只接受已改 FVVTYPE、拒绝未改 RFVVTYPE，并注入“运算移到 mask 前”和“非活动出口执行运算”两种反例，都被 CFG 断言拒绝。[反例证据](mask-cfg-negative-checks.json)。

复现命令（根目录执行）：

```sh
python3 agents/explicit_branch_restore_20261102/review/audit_ir.py
python3 isla/test/float_ir/check_explicit_semantic_branches.py
```

安装后再次独立核对 `isla/ir/provenance/manifest.json`：五件 IR、配置与每件模型来源哈希全部匹配生成记录。[安装审计](installed-manifest-audit.json)。普通检查首次因缓存父目录缺失在保存缓存时退出 2，实施方保留 failed-driver 日志并改平面缓存路径重跑；最终普通检查退出 0、596.44 秒，模型未变。此失败没有静默抹去。

最终签收：本轮五文件源码、四配置生成来源与五份实际 IR 的显式分支恢复通过独立审查，无阻断项。workaround 区域未触及且实施记录核对两处原区域行号保持；本次未独立声称全套 workaround 行为已验收。组合七 Clause 的结果和预算由独立验证记录继续汇总；截至本审查收尾，minmax/minm/maxm 已完成，其余仍在跑。该运行状态不影响上述已完成的 IR 签收，也不构成整个浮点模型的覆盖闭合。

